# -*- coding: utf-8 -*-

from odoo.addons.mgs_payment_waafipay.controllers.main import MgsPaymentWaafipay
from werkzeug import urls
import logging
from requests.exceptions import ConnectionError, HTTPError
from odoo.http import request
from odoo import http
import requests
import json

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.payment import utils as payment_utils
from odoo.addons.mgs_payment_waafipay.const import PAYMENT_STATUS_MAPPING

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    waafipay_type = fields.Char(string="Waafipay Type", help="This has no use in Odoo except for debugging.")

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'waafipay_evc':
            return res
        provider_id = self.provider_id
        base_url = provider_id._waafipay_get_api_url()
        reference=self.reference
        partner_phone = self.partner_phone
        
        if partner_phone.startswith("+"):
            partner_phone = partner_phone[1:]
        if partner_phone.startswith("00"):
            partner_phone = partner_phone[2:]
        elif partner_phone.startswith("0"):
            partner_phone = partner_phone[1:]
        partner_phone = partner_phone.replace(" ", "")
        
        # international format
        partner_phone = "252" + partner_phone[-9:]
    
        
        payload = json.dumps({
            "schemaVersion": "1.0",
            "requestId":  "Aaran-%s"%self.id,
            "timestamp": "client_timestamp",
            "channelName": "WEB",
            "serviceName": "API_PURCHASE",

            "serviceParams":
            {
                "merchantUid": provider_id.merchant_uid,
                "apiUserId": provider_id.api_userid,
                "apiKey":  provider_id.api_key,
                "paymentMethod": "MWALLET_ACCOUNT",
                "payerInfo": 
                    {
                        "accountNo": partner_phone
                    },
                "transactionInfo": 
                    {
                        "referenceId":str(reference.replace("/", "").replace("-", "")),
                        "invoiceId": self.id,
                        "amount": self.amount,
                        "currency": "USD",
                        "description": "Order # "+reference
                    }
            }
        })
        response=None
        try:
            _logger.info("Sending Request to %s"%base_url)
            _logger.warning("Sending Request to %s"%payload)
            response = requests.post(base_url, data=payload,  headers = {'Content-Type': 'application/json'}, timeout=60)
        except (ConnectionError, HTTPError):
            raise ValidationError("WaafiPay: Encountered an error")
        if response:
            vals=json.loads(response.text)
            if vals['responseMsg'] == "RCS_SUCCESS":
                return {
                    'api_url': MgsPaymentWaafipay.return_url,
                    'reference': reference,
                    'payment_status':  vals['params']['state'],
                    }
            else:
                _logger.error(vals)
                _logger.error("WaafiPay Transaction Cancelled with response : %s" %str(vals['responseMsg']))
                return {'api_url': MgsPaymentWaafipay.return_url,'cancel_reason':vals['responseMsg'],'reference': reference,'payment_status':'Cancelled'}

    @api.model
    def _get_tx_from_notification_data(self, provider_code, data):
        tx = super()._get_tx_from_notification_data(provider_code, data)
        if provider_code != 'waafipay_evc':
            return tx

        reference = data.get('reference')
        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'waafipay_evc')])
        if not tx:
            raise ValidationError(
                "Waafipay: " + _("No transaction found matching reference %s.", reference)
            )
        return tx
    
    def _process_notification_data(self, data):
        super()._process_notification_data(data)
        if self.provider_code != 'waafipay_evc':
            return
        payment_status = data.get('payment_status')
        if payment_status in PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
        elif payment_status in PAYMENT_STATUS_MAPPING['cancel']:
            self._set_canceled(state_message=data.get('cancel_reason'))
        else:
            _logger.info("received data with invalid payment status: %s", payment_status)
            self._set_error(
                "Waafipay: " + _("Received data with invalid payment status: %s", payment_status)
            )