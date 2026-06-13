from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
class Company(models.Model):
    _inherit = 'res.company'

    mgs_pd_journal_ids = fields.Many2many('account.journal')

class InvRestrict(models.Model):
    _inherit = 'account.move'
    mgs_allow_reset   = fields.Boolean(string="User", compute='_mgs_allow_reset')


    @api.depends('mgs_allow_reset')
    def _mgs_allow_reset(self):
        user_crnt = self.env.user
        if user_crnt.has_group('mgs_inventory_journal_restrict.inventory_restrict'):
            self.mgs_allow_reset = True
        else:
            self.mgs_allow_reset = False
    def button_draft(self):
        for r in self:
            if r.journal_id.id in self.env.company.mgs_pd_journal_ids.ids   and r.mgs_allow_reset==False:
                raise UserError("Action not allowed!")
        return super(InvRestrict, self).button_draft()
    def button_cancel(self):
        for r in self:
            if r.journal_id.id in self.env.company.mgs_pd_journal_ids.ids  and r.mgs_allow_reset==False:
                raise UserError("Action not allowed!")
        return super(InvRestrict, self).button_cancel()
    def unlink(self):
        for r in self :
            if   r.journal_id.id in self.env.company.mgs_pd_journal_ids.ids  and r.mgs_allow_reset==False:
                raise UserError("You can't unlink posted Journal")
        return super(InvRestrict, self).unlink()