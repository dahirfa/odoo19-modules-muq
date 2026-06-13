/** @odoo-module **/

import { loadJS } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
import {
  Component,
  useState,
  onWillStart,
  useSubEnv,
  useRef,
  onMounted,
} from "@odoo/owl";

export class BarChart extends Component {
  setup() {
    this.state = useState({ employee_per_location: [] });
    this.chartRef = useRef("bar_chart");
    this.orm = useService("orm");


    onWillStart(async () => {
      await loadJS("/web/static/lib/Chart/Chart.js");

      this.state.employee_per_location = await this.get_employees_per_location();
    });

    onMounted(() => {
      this.renderChart();
    });
  }

  async get_employees_per_location() {
    const result = await this.orm.call(
      "sa.attendance.dashboard",
      "absent_employee_per_location",
      [[]]
    );

    return result;
  }

  renderChart() {
    const data = this.state.employee_per_location

    new Chart(this.chartRef.el, {
      type: "bar",
      data: {
        labels: data.map((row) => row.department_id[1] ? row.department_id[1] : "Not Set"),
        datasets: [
          {
            label: "Employees",
            data: data.map((row) => row.department_id_count),
            backgroundColor: data.map((_, index) => {
              // Use a different color for each bar (optional logic for dynamic colors)
              const colors = ["#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF"];
              return colors[index % colors.length]; // Cycle through colors
            }),
          },
        ],
      },

     
    });
  }
}

BarChart.template = "softatt_attendance.BarChart"; // Template name
