from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _get_rendering_context(self, report, docids, data):
        data = super()._get_rendering_context(report, docids, data)
        # The customer portal asks for a PROFORMA as soon as no PDF is stored.
        if self.env.context.get('proforma_invoice') and report.model == 'account.move':
            moves = self.env['account.move'].browse(docids)
            if moves and all(move._mgs_is_pos_invoice_without_stored_pdf() for move in moves):
                data['proforma'] = False
        return data
