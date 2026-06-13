import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
  setup() {
    super.setup(...arguments);

    // Use finalized instead of uiState.locked
    if (this.config.auto_invoice_on_payment && !this.finalized) {
      this.update({ to_invoice: this.config.auto_invoice_on_payment });
    }
  },
});
