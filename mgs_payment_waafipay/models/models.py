# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('waafipay_evc', "EVC")], ondelete={'waafipay_evc': 'set default'})
    
    merchant_uid = fields.Char()
    api_userid = fields.Char()
    api_key = fields.Char()

    def _waafipay_get_api_url(self):
        self.ensure_one()

        if self.state == 'enabled':
            return 'https://api.waafipay.com/asm'
        else:
            return 'https://sandbox.waafipay.net/asm'