import { onWillUnmount, useState } from "@odoo/owl";
import { Domain } from "@web/core/domain";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";
import { patch } from "@web/core/utils/patch";
import { useSetupAction } from "@web/search/action_hook";
import { RentalDashboard } from "@rental_management/js/rental";

RentalDashboard.components = { ...RentalDashboard.components, MultiRecordSelector };

patch(RentalDashboard.prototype, {
    setup() {
        super.setup(...arguments);
        // Landlords selected before opening a card come back with the breadcrumb
        this.landlordFilter = useState({ ids: this.props.state?.mgsLandlordIds || [] });
        this.landlordSelectorDomain = [["user_type", "=", "landlord"]];
        this.mgsApexCharts = [];
        this.mgsLoadSequence = 0;
        useSetupAction({
            getLocalState: () => ({ mgsLandlordIds: [...this.landlordFilter.ids] }),
        });
        onWillUnmount(() => this.mgsDisposeCharts());
        // Every statistics request, including the dashboard's initial load,
        // carries the selected landlords.
        const ormService = this.orm;
        this.orm = Object.assign(Object.create(ormService), {
            call: (model, method, args = [], kwargs = {}) => {
                if (
                    model === "property.details" &&
                    method === "get_property_stats" &&
                    this.landlordFilter.ids.length
                ) {
                    kwargs = { ...kwargs, landlord_ids: this.landlordFilter.ids };
                }
                return ormService.call(model, method, args, kwargs);
            },
        });
        // Cards open their records through the action service: restrict them
        // to the selected landlords without changing the card handlers.
        const actionService = this.action;
        this.action = Object.assign(Object.create(actionService), {
            doAction: (action, options) =>
                actionService.doAction(this.mgsApplyLandlordDomain(action), options),
        });
    },

    /**
     * Keep a reference to every ApexCharts instance so the charts can be
     * destroyed and drawn again when the landlord filter changes.
     */
    renderGraph(el, options) {
        const graphData = new ApexCharts(el, options);
        graphData.render();
        this.mgsApexCharts.push(graphData);
    },

    async onLandlordFilterUpdate(resIds) {
        this.landlordFilter.ids = resIds;
        await this.mgsReloadDashboard();
    },

    async mgsReloadDashboard() {
        const sequence = ++this.mgsLoadSequence;
        const propertyData = await this.orm.call("property.details", "get_property_stats", []);
        // Ignore an answer that a more recent filter change already replaced
        if (!propertyData || sequence !== this.mgsLoadSequence) {
            return;
        }
        this.mgsSetPropertyStats(propertyData);
        this.mgsRedrawCharts();
    },

    /**
     * Same state mapping as the dashboard's initial load
     */
    mgsSetPropertyStats(propertyData) {
        this.state.propertyStats = propertyData;
        this.state.propertyType = {
            "x-axis": propertyData["property_type"][0],
            "y-axis": propertyData["property_type"][1],
        };
        this.state.propertyStages = {
            "x-axis": propertyData["property_stage"][0],
            "y-axis": propertyData["property_stage"][1],
        };
        this.state.tenancyTopBroker = {
            "x-axis": propertyData["tenancy_top_broker"][0],
            "y-axis": propertyData["tenancy_top_broker"][1],
        };
        this.state.soldTopBroker = {
            "x-axis": propertyData["tenancy_top_broker"][2],
            "y-axis": propertyData["tenancy_top_broker"][3],
        };
        this.state.tenancyDuePaid = {
            "x-axis": propertyData["due_paid_amount"][2],
            "y-axis": propertyData["due_paid_amount"][3],
        };
        this.state.soldDuePaid = {
            "x-axis": propertyData["due_paid_amount"][0],
            "y-axis": propertyData["due_paid_amount"][1],
        };
        this.state.propertyMapData = propertyData["property_map_data"];
    },

    mgsDisposeCharts() {
        for (const chart of this.mgsApexCharts) {
            chart.destroy();
        }
        this.mgsApexCharts = [];
        const amChartElements = [this.propertyType.el, this.worldMap.el];
        for (const root of [...am5.registry.rootElements]) {
            if (amChartElements.includes(root.dom)) {
                root.dispose();
            }
        }
    },

    mgsRedrawCharts() {
        this.mgsDisposeCharts();
        // Same drawing sequence as the dashboard's initial mount
        this.renderPropertyType(this.propertyType.el, this.state.propertyType);
        this.renderTenancyTopBroker();
        this.renderSoldTopBroker();
        this.renderTenancyDuePaid();
        this.renderSoldDuePaid();
        this.renderMapProperties(this.worldMap.el, this.state.propertyMapData);
    },

    /**
     * Add the landlord condition matching the model a dashboard card opens.
     */
    mgsApplyLandlordDomain(action) {
        const landlordIds = this.landlordFilter.ids;
        if (!landlordIds.length || !action || typeof action !== "object") {
            return action;
        }
        const filterIds = this.state.propertyStats.mgs_filter_ids || {};
        const actionDomain = action.domain || [];
        let landlordDomain;
        switch (action.res_model) {
            case "property.details":
            case "property.vendor":
            case "rent.invoice":
            case "property.project":
            case "property.sub.project":
                landlordDomain = [["landlord_id", "in", landlordIds]];
                break;
            case "tenancy.details":
                landlordDomain = [["property_landlord_id", "in", landlordIds]];
                break;
            case "account.move":
                landlordDomain = [["sold_id.landlord_id", "in", landlordIds]];
                break;
            case "property.region":
                landlordDomain = [["id", "in", filterIds.region_ids || []]];
                break;
            case "res.partner": {
                const isLandlordList = actionDomain.some(
                    (leaf) => Array.isArray(leaf) && leaf[0] === "user_type" && leaf[2] === "landlord"
                );
                landlordDomain = [
                    ["id", "in", isLandlordList ? landlordIds : filterIds.customer_ids || []],
                ];
                break;
            }
            default:
                return action;
        }
        return {
            ...action,
            domain: Domain.and([actionDomain, landlordDomain]).toList(),
        };
    },
});
