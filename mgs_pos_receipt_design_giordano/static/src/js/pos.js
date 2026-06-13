/** @odoo-module **/
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
patch(PosOrder.prototype, {
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        if (this.get_partner()) {
            result.headerData.partner = this.get_partner();
        }
         
 
        return result;
    },
 });

patch(PosOrderline.prototype, {
    getDisplayData() {
        const result = super.getDisplayData(...arguments);
        result.barcode = this.product_id?.barcode || "";
        
        const unitPrice = this.get_unit_display_price ? this.get_unit_display_price() : (this.get_unit_price ? this.get_unit_price() : 0);
        result.unitPriceNumber = (typeof unitPrice === "number") ? unitPrice.toFixed(2) : (parseFloat(unitPrice) || 0).toFixed(2);
        
        result.qtyNumber = parseFloat(result.qty) || 0
        return result;
    },
});

patch(Orderline, {
    props: {
        ...Orderline.props,
        line: {
            ...Orderline.props.line,
            shape: {
                ...Orderline.props.line.shape,
                barcode: { type: String, optional: true },
                unitPriceNumber: { type: String, optional: true },
                qtyNumber: { type: Number, optional: true },
            },
        },
    },
});