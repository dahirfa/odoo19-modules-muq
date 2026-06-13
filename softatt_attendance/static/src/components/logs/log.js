/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import {
  Component,
  useState,
  onWillStart,
  useSubEnv,
  useRef,
  onMounted,
} from "@odoo/owl";

export class Log extends Component {
  setup() {
    this.state = useState({ last_ten_logs: [] });
    this.orm = useService("orm");

    onWillStart(async () => {
      const last_ten_logs_data = await this.get_last_ten_logs();      
      this.state.last_ten_logs = last_ten_logs_data;
    });
  }

  async get_last_ten_logs() {
    const result = await this.orm.call(
      "sa.attendance.dashboard",
      "get_last_ten_logs",
      [[]]
    );
    return result;
  }
}

Log.template = "softatt_attendance.LastTenLogs"; // Template name
