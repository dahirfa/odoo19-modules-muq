from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    def action_open_change_password_wizard(self):
        self.ensure_one()
        user = self.env['res.users'].search([('partner_id', '=', self.id)], limit=1)
        if user:
            wizard = self.env['change.password.wizard'].create({
                'user_ids': [(0, 0, {
                    'user_id': user.id,
                    'user_login': user.login,
                })]
            })
            return {
                'name': 'Change Password',
                'type': 'ir.actions.act_window',
                'res_model': 'change.password.wizard',
                'res_id': wizard.id,
                'view_mode': 'form',
                'target': 'new',
            }
        return {'type': 'ir.actions.act_window_close'}
    
    