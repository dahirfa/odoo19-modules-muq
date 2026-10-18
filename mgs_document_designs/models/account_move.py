from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_name_invoice_report(self):
        # Swap only the generic invoice layout; localizations that ship their
        # own legal invoice template keep it.
        name = super()._get_name_invoice_report()
        if name == 'account.report_invoice_document':
            return 'mgs_document_designs.report_invoice_document'
        return name
