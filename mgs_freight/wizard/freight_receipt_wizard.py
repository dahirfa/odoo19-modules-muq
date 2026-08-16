from odoo import models, fields, api
from odoo.exceptions import UserError

class FreightReceiptWizard(models.TransientModel):
    _name = 'freight.receipt.wizard'
    _description = 'Freight Receipt Wizard'

    customer_id = fields.Many2one('res.partner', string="Customer")
    date_from = fields.Date(string="From Date", default=fields.Date.today, required=True)
    date_to = fields.Date(string="To Date", default=fields.Date.today)
    
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_to and record.date_from:
                if record.date_to < record.date_from:
                    raise UserError("The To Date cannot be earlier than From Date  Please select a valid range.")
    def print_report(self):
        final_dict = {
            "customer_id": self.customer_id.id,
            "date_from": self.date_from,
            "date_to": self.date_to,
        }

        return (
            self.env.ref(
                "mgs_freight.freight_receipt_report"
            )
            .report_action(self, data=final_dict)
        )

