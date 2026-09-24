from odoo import models, fields


class DocumentDesign(models.Model):
    _inherit = 'res.company'

    document_design_text = fields.Text()
    # more_info = fields.Boolean()
    
   

class ResConfigSettingsDocument(models.TransientModel):
    _inherit = 'res.config.settings'

    document_design_text = fields.Text(related="company_id.document_design_text", readonly=False)
    # more_info = fields.Text(related="company_id.more_info", readonly=False)
   