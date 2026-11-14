## Module <auto_logout_idle_user_odoo>

#### 17.12.2025
#### Version 19.0.1.0.0
##### ADD
- Initial Commit for Logout Idle User.


#### 23.06.2026
#### Version 19.0.1.0.1
##### ADD
- Added the test cases.


#### 11.11.2026
#### Version 19.0.1.0.2
##### FIX
- Logout no longer gets stuck behind the "Leave site?" prompt; unsaved edits are discarded instead of auto-saved.
- Timer is shared across tabs; logging out in one tab logs out all of them.
- Activity detection covers navigation keys, wheel scrolling and same-origin iframes; handlers no longer clash with other modules.
- Warning dialog before logout; retries when the setting can't be loaded.
- Idle time field no longer uses the float_time widget (value is in minutes).
