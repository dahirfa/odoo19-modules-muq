# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountReconcileWizard(models.TransientModel):
    _inherit = 'account.reconcile.wizard'

    def reconcile(self):
        # Check if all move lines belong to the same partner and same account
        partner_name = self.move_line_ids.mapped('partner_id')
        partner_acc = self.move_line_ids.mapped('account_id')
        if len(partner_name) > 1 or len(partner_acc) > 1:
            raise UserError(_("All move lines must belong to the same partner and account."))

        # Call the original reconcile method
        return super(AccountReconcileWizard, self).reconcile()