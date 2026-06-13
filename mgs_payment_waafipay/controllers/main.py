# -*- coding: utf-8 -*-
import logging
import pprint

import requests
from requests.exceptions import ConnectionError, HTTPError
from werkzeug import urls

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

class MgsPaymentWaafipay(http.Controller):
    return_url = '/payment/waafipay-evc/'
    
    @http.route(return_url, type='http',auth='public',methods=['POST','GET'], csrf=False, save_session=False)
    def waafipay_return_from_redirect(self, **data):
        if not data:
            pass
        else:
            request.env['payment.transaction'].sudo()._handle_notification_data('waafipay_evc', data)
        return request.redirect('/payment/status')