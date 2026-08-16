from odoo import models, fields, api,_
from odoo.exceptions import UserError, ValidationError
class TransferFreightLineWizard(models.TransientModel):
    _name = 'freight.line.transfer.wizard'
    _description = 'Transfer Freight Receipt Lines'

    receipt_id = fields.Many2one('freight.receipts', string='From Customer', readonly=True)
    new_receipt_id = fields.Many2one('freight.receipts', string='To Customer', required=True)
    line_ids = fields.Many2many('freight.receipt.line', string='Lines to Transfer',domain="[('receipt_id', '=', receipt_id)]",)

    def action_transfer_lines(self):
        invalid_lines = self.line_ids.filtered(lambda l: l.ctn_delivered >= 1)
        if invalid_lines:
            product_names = ", ".join(invalid_lines.mapped(lambda l: l.product_id.display_name))
            raise UserError(_(
                "You cannot transfer the following products because they already have delivered cartons:\n%s"
            ) % product_names)

        for line in self.line_ids:
            line.receipt_id = self.new_receipt_id

        return {'type': 'ir.actions.act_window_close'}