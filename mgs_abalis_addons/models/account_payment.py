from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    property_id = fields.Many2one(
        comodel_name='property.details',
        string='Property',
        help='Selecting a property fills in the tenant of its latest running rent contract as the customer.',
        tracking=True
    )

    @api.onchange('property_id')
    def _onchange_property_id_set_tenant(self):
        """Set the customer to the tenant of the property's latest running contract."""
        if not self.property_id or self.partner_type != 'customer':
            return
        contract = self.env['tenancy.details'].search([
            ('property_id', '=', self.property_id.id),
            ('contract_type', '=', 'running_contract'),
            ('tenancy_id', '!=', False),
        ], order='start_date desc, id desc', limit=1)
        if contract:
            self.partner_id = contract.tenancy_id
