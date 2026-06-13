/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { _t } from "@web/core/l10n/translation";

patch(ProductScreen.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },
    getNumpadButtons() {
        const cashier = this.pos.getCashier();
    
        const colorClassMap = {
            [this.env.services.localization.decimalPoint]: "o_colorlist_item_numpad_color_6",
            Backspace: "o_colorlist_item_numpad_color_1",
            "-": "o_colorlist_item_numpad_color_3",
        };
    
        return [
            { value: "1", disabled: !cashier.is_allow_numpad },
            { value: "2", disabled: !cashier.is_allow_numpad },
            { value: "3", disabled: !cashier.is_allow_numpad },
            { value: "quantity", text: "Qty", disabled: !cashier.is_allow_qty },
            { value: "4", disabled: !cashier.is_allow_numpad },
            { value: "5", disabled: !cashier.is_allow_numpad },
            { value: "6", disabled: !cashier.is_allow_numpad },
            { value: "discount", text: "% Disc", disabled: !this.pos.config.manual_discount || !cashier.is_allow_discount },
            { value: "7", disabled: !cashier.is_allow_numpad },
            { value: "8", disabled: !cashier.is_allow_numpad },
            { value: "9", disabled: !cashier.is_allow_numpad },
            { value: "price", text: "Price", disabled: !this.pos.cashierHasPriceControlRights() || !cashier.is_edit_price },
            { value: "-", text: "+/-", disabled: !cashier.is_allow_plus_minus_button },
            { value: "0", disabled: !cashier.is_allow_numpad },
            { value: this.env.services.localization.decimalPoint, disabled: !cashier.is_allow_numpad },
            { value: "Backspace", text: "⌫", disabled: !cashier.is_allow_remove_orderline },
        ].map((button) => {
            const colorClass = colorClassMap[button.value] || "";
    
            return {
                ...button,
                class: [
                    this.pos.numpadMode === button.value ? "active border-primary" : "",
                    colorClass,
                ].join(" "),
            };
        });
    }
});
