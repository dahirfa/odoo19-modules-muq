# -*- coding: utf-8 -*-

from odoo import models

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def send_mgs_sms(self):
        mgs_sms_obj = self.env['mgs.sms']

        model_id = self.env['ir.model'].sudo().search(
            [('model', '=', self._name)],
            limit=1
        ).id

        company = self.env.company

        for rec in self:
            # Only send SMS for customer inbound payments
            if rec.partner_type != 'customer' or rec.payment_type != 'inbound':
                continue

            # Check partner phone number
            if not rec.partner_id.phone:
                rec.message_post(
                    body='SMS not sent: This partner has no phone number attached.'
                )
                continue

            payment_no = rec.name
            remaining_balance = rec.mgs_partner_bal - rec.amount

            msg = (
                f"Macmiil waxaad bixisay ${rec.amount:,.2f}. "
                f"Baaqiga kugu harsan waa ${remaining_balance:,.2f}. "
                "Mahadsanid."
            )

            if not (
                company.mgs_marketing_sms_username
                and company.mgs_marketing_sms_password
            ):
                rec.message_post(
                    body='SMS not sent: SMS credentials are not configured.'
                )
                continue

            sms_record = mgs_sms_obj.sudo().create_mgs_sms(
                payment_no,
                msg,
                rec.partner_id.phone,
                rec.partner_id.id,
                model_id
            )

            if not sms_record:
                continue

            try:
                response = sms_record.action_send_mgs_sms()
                rec.message_post(body=response)
            except Exception as e:
                rec.message_post(
                    body=f"SMS error: {str(e)}"
                )

    def action_post(self):
        res = super(AccountPayment, self).action_post()
        self.sudo().send_mgs_sms()
        return res

class InheritFreightDelivery(models.Model):
    _inherit = 'freight.delivery'

    def send_delivery_sms(self):
        mgs_sms_obj = self.env['mgs.sms']
        model_id = self.env['ir.model'].sudo().search(
            [('model', '=', self._name)], limit=1
        ).id

        company = self.env.company
        missing_phone_partners = []

        for rec in self:
            for line in rec.delivery_ids:
                partner = line.receipt_id.customer_id

                if not partner:
                    continue

                if not partner.phone:
                    missing_phone_partners.append(partner.name)
                    continue

                msg = f"WARGELIN: Macmiilkeena sharafta leh waxaan ku ogeysiineeynaa in uu yimid Container {rec.container_no}, waxan kaa codsaneynaa in aad Alaabtaada si dhaqso ah u soodoonato,Waad Ku Mahadsantahay doorashada aad na dooratay inan kuu adeegno."

                if company.mgs_marketing_sms_username and company.mgs_marketing_sms_password:
                    sms_record = mgs_sms_obj.sudo().create_mgs_sms(
                        rec.name,
                        msg,
                        partner.phone,
                        partner.id,
                        model_id
                    )
                    if sms_record:
                        try:
                            response = sms_record.action_send_mgs_sms()
                            
                        except Exception as e:
                            rec.message_post(
                                body=f"SMS error for {partner.name}: {str(e)}"
                            )

        #partners without phone numbers
        if missing_phone_partners:
            self.message_post(
                body=(
                    "SMS NOT sent. These partners have no mobile number:"
                    + ", ".join(missing_phone_partners)
                )
            )
