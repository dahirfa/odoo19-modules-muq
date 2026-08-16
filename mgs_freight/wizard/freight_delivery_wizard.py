from odoo import models, fields, api


class FreightDeliveryWizard(models.TransientModel):
    _name = 'freight.delivery.wizard'
    _description = 'Freight Delivery Wizard'

    customer_id = fields.Many2one(
        'res.partner', 
        string="Customer"
        )
    delivery_id = fields.Many2one(
        'freight.delivery', 
        string="Delivery", 
        
        )
    summary = fields.Boolean(
        default=True
    )
    
    add_customer = fields.Boolean(
        string='Add Customer',
    )
    
    status_type = fields.Selection(
        string='Type',
        selection=[('bill', 'Billed'), ('confirm', 'Confirmed'), ('both', 'Both')],
        default="bill"
    )
    
    def print_report(self):
        final_dict = {
            "customer_id": self.customer_id.id,
            "delivery_id": self.delivery_id.id,
            "summary": self.summary,
            "add_customer": self.add_customer,
            "status_type": self.status_type
        }

        return (
            self.env.ref(
                "mgs_freight.freight_delivery_report"
            )
            .report_action(self, data=final_dict)
        )

