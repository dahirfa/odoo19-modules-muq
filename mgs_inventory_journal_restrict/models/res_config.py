from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mgs_journal_ids = fields.Many2many(related="company_id.mgs_pd_journal_ids", readonly=False)

    # @api.model
    # def set_values(self):
    #     res = super(ResConfigSettings, self).set_values()
    #     self.env['ir.config_parameter'].sudo().set_param('mgs_inventory_journal_restrict.mgs_journal_ids',
    #                                                      self.mgs_journal_ids.ids)