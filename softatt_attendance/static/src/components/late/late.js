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

export class Late extends Component {
  setup() {
    this.state = useState({ late_today: [] });
    this.orm = useService("orm");

    onWillStart(async () => {
      const late_today_data = await this.get_late_today();

      this.state.late_today = late_today_data;
    });
  }

  async get_late_today() {
    const result = await this.orm.call(
      "sa.attendance.dashboard",
      "get_late_today",
      [[]]
    );

    return result;
  }
}

Late.template = "softatt_attendance.LateToday"; // Template name
