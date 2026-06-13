# -*- coding: utf-8 -*-

from odoo import models


class MgsHrJournalPartner(models.Model):
    _inherit = 'hr.payslip'

    def set_move_partner(self):
        for r in self:
            move_id     =   r.move_id
            partner_id  =   r.employee_id.address_id or None
            if move_id and partner_id:
                lines   =   move_id.line_ids.filtered(lambda line: not line.partner_id)
                lines.write({'partner_id':partner_id.id})
    
    def action_payslip_done(self):
        result = super(MgsHrJournalPartner,self).action_payslip_done()
        self.set_move_partner()
        return result
