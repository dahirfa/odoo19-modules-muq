from odoo import _, api, fields, models


class account_move(models.Model):
    _inherit = "account.move"

    mgs_container_type = fields.Selection(
        string="Type",
        selection=[("container", "Container"), ("bill", "Bill")],
        default="container",
        required=True,
        tracking=True
    )

    container_referrence = fields.Char(string="Container", tracking=True)
    bill_referrence = fields.Char(string="Container", tracking=True)



class AccountPaymentInherit(models.Model):
    _inherit = 'account.payment'
    
    
    mgs_partner_bal = fields.Monetary(
        string='Balance', compute="_compute_mgs_partner_bal", store=True)

    @api.depends('partner_id')
    def _compute_mgs_partner_bal(self):
        for r in self:
            r.mgs_partner_bal = 0.0
            if r.partner_id:
                params = [str(r.partner_id.id), 'asset_receivable']
                query = """
                        SELECT COALESCE (sum(debit - credit), 0)
                        FROM account_move_line aml
                        LEFT JOIN account_account as aa ON aml.account_id=aa.id
                        WHERE aml.partner_id = %s
                        AND aa.account_type = %s
                        AND parent_state = 'posted' """
                self.env.cr.execute(query, tuple(params))
                data                = self.env.cr.fetchone()
                r.mgs_partner_bal   = data[0]

    


class ResCompany(models.Model):
    _inherit = 'res.company'

    custom_bank_text = fields.Html("Custom Bank Text")
   
    
    
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    custom_bank_text = fields.Html(related='company_id.custom_bank_text', readonly=False)
    