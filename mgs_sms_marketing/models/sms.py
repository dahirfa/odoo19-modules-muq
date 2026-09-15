import threading
from odoo import models


class AfricasTalkingSMS(models.Model):
    _inherit = 'sms.sms'

    def send(self, unlink_failed=False, unlink_sent=True, auto_commit=False, raise_exception=False):
        is_message_overwrite = self.env['ir.config_parameter'].sudo().get_param('mgs_sms_marketing.overwrite_odoo_sms')

        for batch_ids in self._split_batch():
            if not is_message_overwrite:
                self.browse(batch_ids)._send(unlink_failed=unlink_failed, unlink_sent=unlink_sent, raise_exception=raise_exception)
            else:
                self.browse(batch_ids).send_mgs_sms()
            if auto_commit is True and not getattr(threading.current_thread(), 'testing', False):
                self._cr.commit()
    def send_mgs_sms(self):
        mgs_sms_obj=self.env['mgs.sms']
        model_obj=self.env['ir.model'].sudo().search([('model','=',self._inherit)]).id
        for rec_id in self:
            try:
                sms_record=mgs_sms_obj.create_mgs_sms('To '+rec_id.number,rec_id.body,rec_id.number,rec_id.partner_id.id,model_obj)
                if sms_record:
                    try:
                        response = sms_record.action_send_mgs_sms()
                        self.state= 'sent' if response=='the sms was sent successfully' else 'canceled'
                    except Exception as e:
                        continue
            except Exception as e:
                continue