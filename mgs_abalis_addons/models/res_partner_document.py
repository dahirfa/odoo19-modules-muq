from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResPartnerDocument(models.Model):
    _name = 'res.partner.document'
    _description = 'Partner Identity Document'
    _rec_name = 'id_card_number'
    _order = 'valid_to desc, id desc'

    id_card_number = fields.Char(
        string='ID Card Number',
        help="Number printed on the identity document.",
    )
    document_type = fields.Selection(
        selection=[
            ('national_id', 'National ID'),
            ('passport', 'Passport'),
            ('driving_license', 'Driving License'),
            ('residence_permit', 'Residence Permit'),
            ('other', 'Other'),
        ],
        string='Document Type',
        required=True,
        default='national_id',
        help="Kind of identity document.",
    )
    valid_from = fields.Date(string='Valid From', help="Date the document was issued.")
    valid_to = fields.Date(string='Valid To', help="Date the document expires.")
    name = fields.Char(string='Name', help="Full name as written on the document.")
    gender = fields.Selection(
        selection=[('male', 'Male'), ('female', 'Female')],
        string='Gender',
        help="Gender as written on the document.",
    )
    date_of_birth = fields.Date(string='Date of Birth', help="Date of birth as written on the document.")
    issuing_authority = fields.Char(string='Issuing Authority', help="Authority that issued the document.")
    country_id = fields.Many2one(
        comodel_name='res.country',
        string='Country',
        help="Country that issued the document.",
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner',
        required=True,
        index=True,
        ondelete='cascade',
    )

    @api.constrains('valid_from', 'valid_to')
    def _check_validity_dates(self):
        for record in self:
            if record.valid_from and record.valid_to and record.valid_to < record.valid_from:
                raise ValidationError(self.env._("A document's Valid To date cannot be before its Valid From date."))
