# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class InheritAgedPartnerBalanceCustomHandler(models.AbstractModel):
    _inherit = 'account.aged.partner.balance.report.handler'
                    
    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        interval = options.get('aging_interval', 30)
        for column in options['columns']:
            if column['expression_label'].startswith('period'):
                period_number = int(column['expression_label'].replace('period', ''))

                if period_number == 0:
                    column['name'] = ''
                elif period_number == 1:
                    column['name'] = '0-30'
                elif period_number == 2:
                    column['name'] = '31-60'
                elif period_number == 3:
                    column['name'] = '61-90'
                elif period_number == 4:
                    column['name'] = '91-120'
                else:
                    column['name'] = _('Older')




