/* @odoo-module */

import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

/** Events that count as user activity. `scroll` is left out on purpose:
 * Odoo scrolls programmatically (chatter, lists), which would keep an idle
 * session alive. Keyboard and wheel scrolling are covered by keydown/wheel. */
const ACTIVITY_EVENTS = ["keydown", "pointerdown", "pointermove", "wheel", "touchstart"];
/** Ignore pointer jitter smaller than this (in screen pixels). */
const POINTER_THRESHOLD = 10;
/** Write the shared activity timestamp at most this often (ms). */
const STORAGE_WRITE_THROTTLE = 1000;
/** Warn the user this many seconds before logout (capped at half the timeout). */
const WARNING_SECONDS = 60;
/** Retry fetching the setting after a failure, up to this many times. */
const MAX_FETCH_RETRIES = 5;
/** Re-read the setting on tab focus at most this often (ms). */
const REFETCH_INTERVAL = 60 * 1000;

function storageGet(key) {
    try {
        return window.localStorage.getItem(key);
    } catch {
        return null;
    }
}

function storageSet(key, value) {
    try {
        window.localStorage.setItem(key, value);
    } catch {
        // Storage unavailable (private mode, blocked): tabs just won't sync.
    }
}

/** Format a positive duration in ms as "1d 2h 3m 4s" (leading zero units dropped). */
export function formatRemaining(ms) {
    const total = Math.max(0, Math.floor(ms / 1000));
    const days = Math.floor(total / 86400);
    const hours = Math.floor((total % 86400) / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const seconds = total % 60;
    if (days) {
        return `${days}d ${hours}h ${minutes}m ${seconds}s`;
    }
    if (hours) {
        return `${hours}h ${minutes}m ${seconds}s`;
    }
    return `${minutes}m ${seconds}s`;
}

class TimerSystrayItem extends Component {
    static template = "auto_logout_idle_user_odoo.TimerSystray";
    static props = {};

    setup() {
        this.dialog = useService("dialog");
        this.state = useState({ idle_time: null });

        const prefix = `auto_logout_idle_user_odoo:${session.db || ""}:${user.userId}`;
        this.activityKey = `${prefix}:last_activity`;
        this.logoutKey = `${prefix}:logout`;

        this.minutes = 0;
        this.lastActivity = Date.now();
        this.lastStorageWrite = 0;
        this.lastPointer = null;
        this.lastFetch = 0;
        this.interval = null;
        this.closeWarning = null;
        this.loggingOut = false;
        this.fetchRetryTimeout = null;
        this.logoutRetryTimeout = null;
        this.mounted = false;

        this.onActivity = this.onActivity.bind(this);
        this.onStorage = this.onStorage.bind(this);
        this.onVisibilityChange = this.onVisibilityChange.bind(this);
        this.blockBeforeUnload = (ev) => ev.stopImmediatePropagation();

        onWillStart(() => this.fetchIdleTime());
        onMounted(() => {
            window.addEventListener("storage", this.onStorage);
            document.addEventListener("visibilitychange", this.onVisibilityChange);
            this.attachWindow(window);
            this.watchIframes();
            this.mounted = true;
            if (this.minutes) {
                this.start();
            }
        });
        onWillUnmount(() => this.destroy());
    }

    // -------------------------------------------------------------------------
    // Setting
    // -------------------------------------------------------------------------

    /** Load the idle time; retries in the background on failure. Never throws,
     * so a network error can't block the web client from starting. */
    async fetchIdleTime(attempt = 0) {
        this.lastFetch = Date.now();
        try {
            const minutes = await rpc("/get_idle_time/timer", {}, { silent: true });
            this.applyIdleTime(minutes);
        } catch (error) {
            console.warn("auto_logout_idle_user_odoo: could not load idle time", error);
            if (attempt < MAX_FETCH_RETRIES) {
                const delay = Math.min(30000, 2000 * 2 ** attempt);
                this.fetchRetryTimeout = setTimeout(() => this.fetchIdleTime(attempt + 1), delay);
            }
        }
    }

    applyIdleTime(minutes) {
        const value = Number(minutes) > 0 ? Number(minutes) : 0;
        if (value === this.minutes) {
            return;
        }
        this.minutes = value;
        if (!this.mounted) {
            return; // not mounted yet; onMounted starts the timer
        }
        if (value) {
            this.start();
        } else {
            this.stop();
            this.state.idle_time = null;
        }
    }

    onVisibilityChange() {
        if (document.visibilityState === "visible" && !this.loggingOut) {
            if (Date.now() - this.lastFetch > REFETCH_INTERVAL) {
                this.fetchIdleTime();
            }
            this.tick();
        }
    }

    // -------------------------------------------------------------------------
    // Timer
    // -------------------------------------------------------------------------

    start() {
        if (this.interval) {
            return;
        }
        this.registerActivity(true);
        this.tick();
        this.interval = setInterval(() => this.tick(), 1000);
    }

    stop() {
        clearInterval(this.interval);
        this.interval = null;
        this.hideWarning();
    }

    /** Most recent activity across all tabs of this user and database. */
    getLastActivity() {
        const shared = parseInt(storageGet(this.activityKey), 10);
        if (shared > this.lastActivity) {
            this.lastActivity = shared;
        }
        return this.lastActivity;
    }

    tick() {
        if (!this.minutes || this.loggingOut) {
            return;
        }
        const timeout = this.minutes * 60 * 1000;
        const remaining = this.getLastActivity() + timeout - Date.now();
        if (remaining <= 0) {
            this.logout();
            return;
        }
        this.state.idle_time = formatRemaining(remaining);
        const warnAt = Math.min(WARNING_SECONDS * 1000, timeout / 2);
        if (remaining <= warnAt) {
            this.showWarning(Math.ceil(remaining / 1000));
        } else {
            this.hideWarning();
        }
    }

    // -------------------------------------------------------------------------
    // Activity detection
    // -------------------------------------------------------------------------

    onActivity(ev) {
        if (!this.mounted || !this.minutes) {
            return;
        }
        if (ev.type === "pointermove") {
            // Compare with the last *counted* position, so slow movement made
            // of many tiny steps still counts once it adds up.
            const { screenX: x, screenY: y } = ev;
            const anchor = this.lastPointer;
            if (!anchor) {
                this.lastPointer = { x, y };
                return;
            }
            if (Math.abs(x - anchor.x) + Math.abs(y - anchor.y) < POINTER_THRESHOLD) {
                return;
            }
            this.lastPointer = { x, y };
        }
        this.registerActivity();
    }

    registerActivity(force = false) {
        if (this.loggingOut) {
            return;
        }
        const now = Date.now();
        this.lastActivity = now;
        if (force || now - this.lastStorageWrite >= STORAGE_WRITE_THROTTLE) {
            this.lastStorageWrite = now;
            storageSet(this.activityKey, String(now));
        }
        if (this.closeWarning) {
            this.hideWarning();
            this.tick();
        }
    }

    /**
     * Listen for activity in a window (the main one or a same-origin iframe).
     *
     * Always removes and re-adds the listeners: when an iframe loads its real
     * content, the browser reuses the window object of the initial blank page,
     * but listeners added before the load no longer receive events from the
     * new document's elements (seen in Chromium). Re-adding them on every
     * load fixes that; adding an identical listener again would be a no-op.
     */
    attachWindow(win) {
        try {
            for (const type of ACTIVITY_EVENTS) {
                win.removeEventListener(type, this.onActivity, { capture: true });
                win.addEventListener(type, this.onActivity, { capture: true, passive: true });
            }
        } catch {
            // Cross-origin iframe: activity inside it can't be observed.
        }
    }

    /** Iframe windows go away with their iframe; only the main one needs removing. */
    detachWindows() {
        for (const type of ACTIVITY_EVENTS) {
            window.removeEventListener(type, this.onActivity, { capture: true });
        }
    }

    /** Activity inside iframes (HTML editor, mail composer, previews) does not
     * reach the parent document, so attach to every same-origin iframe. */
    watchIframes() {
        const hookIframe = (iframe) => {
            if (iframe.__autoLogoutHooked) {
                return;
            }
            iframe.__autoLogoutHooked = true;
            const attach = () => {
                try {
                    if (iframe.contentWindow) {
                        this.attachWindow(iframe.contentWindow);
                    }
                } catch {
                    // Cross-origin.
                }
            };
            iframe.addEventListener("load", attach);
            attach();
        };
        const scan = (root) => {
            if (root.tagName === "IFRAME") {
                hookIframe(root);
            } else if (root.querySelectorAll) {
                root.querySelectorAll("iframe").forEach(hookIframe);
            }
        };
        scan(document.body);
        this.iframeObserver = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                mutation.addedNodes.forEach(scan);
            }
        });
        this.iframeObserver.observe(document.body, { childList: true, subtree: true });
    }

    // -------------------------------------------------------------------------
    // Warning dialog
    // -------------------------------------------------------------------------

    showWarning(seconds) {
        if (this.closeWarning) {
            return;
        }
        this.closeWarning = this.dialog.add(
            ConfirmationDialog,
            {
                title: _t("Are you still there?"),
                body: _t(
                    "You will be logged out in %s seconds because of inactivity.",
                    seconds
                ),
                confirmLabel: _t("Stay signed in"),
                confirm: () => this.registerActivity(true),
            },
            { onClose: () => (this.closeWarning = null) }
        );
    }

    hideWarning() {
        if (this.closeWarning) {
            const close = this.closeWarning;
            this.closeWarning = null;
            close();
        }
    }

    // -------------------------------------------------------------------------
    // Logout
    // -------------------------------------------------------------------------

    onStorage(ev) {
        if (ev.key === this.logoutKey && ev.newValue) {
            // Another tab logged out this session: follow it.
            this.logout({ broadcast: false });
        } else if (ev.key === this.activityKey) {
            this.tick();
        }
    }

    /**
     * End the session first, then leave the page.
     *
     * The session is closed with a background request, so the logout is
     * effective even if the page can't be left. Unsaved form changes are
     * discarded: Odoo's "save on leave" (beforeunload) handlers are blocked,
     * so neither half-finished edits get saved nor a "Leave site?" prompt
     * keeps the page open.
     */
    async logout({ broadcast = true } = {}) {
        if (this.loggingOut) {
            return;
        }
        this.loggingOut = true;
        this.stop();
        this.state.idle_time = _t("EXPIRED");
        if (broadcast) {
            storageSet(this.logoutKey, String(Date.now()));
        }
        window.addEventListener("beforeunload", this.blockBeforeUnload, { capture: true });
        try {
            await fetch("/web/session/logout", {
                credentials: "same-origin",
                redirect: "manual",
            });
        } catch (error) {
            console.warn("auto_logout_idle_user_odoo: background logout failed", error);
        }
        const leave = () => {
            window.location.replace("/web/session/logout");
            // If something still keeps the page open, try again.
            this.logoutRetryTimeout = setTimeout(leave, 5000);
        };
        leave();
    }

    destroy() {
        this.mounted = false;
        this.stop();
        clearTimeout(this.fetchRetryTimeout);
        clearTimeout(this.logoutRetryTimeout);
        this.detachWindows();
        this.iframeObserver?.disconnect();
        window.removeEventListener("storage", this.onStorage);
        document.removeEventListener("visibilitychange", this.onVisibilityChange);
        window.removeEventListener("beforeunload", this.blockBeforeUnload, { capture: true });
    }
}

export const systrayItem = {
    Component: TimerSystrayItem,
};
registry
    .category("systray")
    .add("auto_logout_idle_user_odoo.TimerSystray", systrayItem, { sequence: 25 });
