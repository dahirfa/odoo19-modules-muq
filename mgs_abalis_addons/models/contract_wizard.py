from odoo import fields, models


class ContractWizard(models.TransientModel):
    _inherit = 'contract.wizard'

    customer_id = fields.Many2one(domain=[('user_type', 'in', ['customer', 'customer_owner'])])

    def contract_action(self):
        """Keep the "Tenant & Owner" type: the base wizard resets the tenant to "Customer"."""
        customer_owners = self.customer_id.filtered(lambda p: p.user_type == 'customer_owner')
        res = super().contract_action()
        customer_owners.user_type = 'customer_owner'
        return res
