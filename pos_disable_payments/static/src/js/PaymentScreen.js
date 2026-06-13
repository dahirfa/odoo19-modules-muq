import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PaymentScreen.prototype, {
    async _askForCustomerIfRequired() {
        const splitPayments = this.paymentLines.filter(
            (payment) => payment.payment_method_id.split_transactions
        );
        if (splitPayments.length && !this.currentOrder.getPartner()) {
            const paymentMethod = splitPayments[0].payment_method_id;
    
            if (this.pos.getCashier().is_allow_customer_selection) {
                const confirmed = await makeAwaitable(this.dialog, {
                    title: _t("Customer Required"),
                    body: _t("Customer is required for %s payment method.", paymentMethod.name),
                });
                if (confirmed) {
                    this.pos.selectPartner();
                }
                return false;
            } else {
                this.dialog.add(AlertDialog, {
                    title: _t("Disabled Access !!!"),
                    body: _t("Customer selection is not disabled for the current cashier."),
                });
                return false;
            }
        }
    },

    toggleIsToInvoice() {
        if (!this.pos.getCashier().is_allow_customer_selection) {
            this.dialog.add(AlertDialog, {
                title: _t("Disabled Access !!!"),
                body: _t("Invoice disabled because of current cashier not access of customer selection."),
            });
        } else {
            super.toggleIsToInvoice(...arguments);
        }
    },
    
});