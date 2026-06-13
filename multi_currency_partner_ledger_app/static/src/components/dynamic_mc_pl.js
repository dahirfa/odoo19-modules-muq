/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
  Component,
  useState,
  onWillStart,
  useSubEnv,
  useRef,
  onMounted,
} from "@odoo/owl";

class DynamicMcPL extends Component {
  setup() {
   
  }
}
DynamicMcPL.template = "multi_currency_partner_ledger_app.dynamic_mc_pl_template";
// DynamicMcPL.components = {};
registry.category("actions").add("multi_currency_partner_ledger_app.dynamic_mc_pl_tag", DynamicMcPL);
