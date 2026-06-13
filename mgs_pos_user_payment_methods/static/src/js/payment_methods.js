/** @odoo-module **/
import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
patch(PaymentScreen.prototype, {
    setup() {
        this._super?.(...arguments);
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.dialog = useService("dialog");
        this.invoiceService = useService("account_move");
        this.notification = useService("notification");
        this.hardwareProxy = useService("hardware_proxy");
        this.printer = useService("printer");

        // get the logged-in user
        const user = this.pos.user || {};
        const allowed = user.pos_allowed_payment_method_ids?.map(m => m.id) || [];

        // filter payment methods based on user permissions
        this.payment_methods_from_config = this.pos.config.payment_method_ids
            .filter(pm => allowed.includes(pm.id))
            .sort((a, b) => a.sequence - b.sequence);
        this.numberBuffer = useService("number_buffer");
        this.numberBuffer.use(this._getNumberBufferConfig);
    },

    
});

