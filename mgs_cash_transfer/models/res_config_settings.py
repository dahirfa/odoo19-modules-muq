from odoo import models, fields
from odoo.exceptions import UserError

class ResCompany(models.Model):
    _inherit = 'res.company'

    mgs_transfer_journal_id = fields.Many2one('account.journal', string='Transfer Journal', domain=[('type', '=', 'general')])

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mgs_transfer_journal_id = fields.Many2one(related='company_id.mgs_transfer_journal_id', string='Transfer Journal', readonly=False, domain=[('type', '=', 'general')], check_company=True)
