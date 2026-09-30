from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    delivery_order_report_logo = fields.Image(
        string='Delivery Order Report Logo',
        max_width=1920,
        max_height=1920,
        help="Header image printed on the Delivery Order and Container Control reports. "
             "Upload a single image combining every branding element of the header. "
             "The standard company logo is not used by these reports and stays unchanged.",
    )
    
    delivery_address = fields.Text(
        string='Delivery Order Address'
    )
