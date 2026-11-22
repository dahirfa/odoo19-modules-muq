from odoo import fields, models
from odoo.exceptions import UserError


class FreightReceiptPrintWizard(models.TransientModel):
    _name = 'freight.receipt.print.wizard'
    _description = 'Freight Receipt Print Wizard'

    receipt_id = fields.Many2one(
        comodel_name='freight.receipts',
        string='Receipt',
        required=True,
        readonly=True,
        ondelete='cascade',
    )
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
    )

    def action_print(self):
        self.ensure_one()
        lines = self.receipt_id.freight_receipt_ids.filtered(
            lambda line: line.receiver_date == self.date
        )
        if not lines:
            raise UserError(self.env._(
                "There are no receipt lines dated %(date)s on this receipt.",
                date=self.date,
            ))
        # The web client drops docids from the report URL whenever `data` is
        # set, so the receipt ids must travel inside `data` itself.
        data = {
            'receipt_ids': self.receipt_id.ids,
            'date': fields.Date.to_string(self.date),
        }
        return self.env.ref(
            'mgs_freight.freight_consignment_note_report'
        ).report_action(self.receipt_id, data=data)
