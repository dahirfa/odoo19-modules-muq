# -*- coding: utf-8 -*-

from odoo import models, fields, api
import requests
import json
from datetime import datetime
import logging
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)

class MgsSmsMaliningMassMailog(models.Model):
    _name = 'mgs.mass.mail.log'

    sms_id  = fields.Many2one('mgs.sms',string='SMS',)
    partner_id  = fields.Many2one('res.partner',string='Contact')
    mobile  = fields.Char(string='Contact Mobile',related='partner_id.phone',store=True)
    email  = fields.Char(string='Contact Email',related='partner_id.email',store=True)
    mail_list_id  = fields.Many2one('mgs.mailing.list',string='Mailing Lis')
    msg = fields.Text()
    cron_processed = fields.Boolean(default=False)
    description = fields.Text(string='Reason')
    state = fields.Selection([('sent', 'Sent'), ('queue','In queue'), ('failed', 'Failed')])

class MgsSmsMaliningContact(models.Model):
    _name = 'mgs.mail.contact'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    mobile = fields.Char()
    company_name = fields.Char(string='Company Name')
    email = fields.Char('Email')
    list_ids = fields.Many2many('mgs.mailing.list', 'mgs_mailing_contact_list_rel', 'contact_id', 'list_id', string='Mailing Lists')
    tag_ids = fields.Many2many('res.partner.category', string='Tags')
    active = fields.Boolean(
    default=True
    )
    
class MgsSmsMaliningList(models.Model):
    _name = 'mgs.mailing.list'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    
    name = fields.Char(string='Mailing List', required=True)
    active = fields.Boolean(default=True)
    sms_ids = fields.Many2many('mgs.sms','sms_mgs_mailing_list_rel', 'list_id','sms_id',copy=False)
    
    partner_ids = fields.Many2many('res.partner',string='Mailing Lists', copy=False)


class ResCompany(models.Model):
    _inherit = 'res.company'

    mgs_marketing_sms_username = fields.Char(string='Username')
    mgs_marketing_sms_password = fields.Char(string='Password')
    mgs_marketing_sms_sender_id = fields.Char(string='Sender')

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    mgs_marketing_sms_username = fields.Char(related='company_id.mgs_marketing_sms_username', readonly=False)
    mgs_marketing_sms_password = fields.Char(related='company_id.mgs_marketing_sms_password', readonly=False)
    mgs_marketing_sms_sender_id = fields.Char(related='company_id.mgs_marketing_sms_sender_id', readonly=False)

class MgsSms(models.Model):
    _name = 'mgs.sms'
    _description = 'mgs sms'
    _rec_name = 'source_name'
    _order = 'datetime DESC'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    datetime = fields.Datetime(default= fields.Datetime.now())
    message = fields.Text()
    mobile = fields.Char()
    partner_id = fields.Many2one('res.partner')
    model_id = fields.Many2one('ir.model', string="Model")
    source_name = fields.Char()
    response = fields.Text()
    state = fields.Selection([('sent', 'Sent'), ('failed', 'Failed')])
    is_mass_sms = fields.Boolean(string='Mass ?')
    mail_list_ids = fields.Many2many('mgs.mailing.list','sms_mgs_mailing_list_rel','sms_id', 'list_id')
    mass_mail_log_ids = fields.One2many('mgs.mass.mail.log', 'sms_id', string='Mass Mail')
    sent_count = fields.Integer(compute='_count_log')
    failed_count = fields.Integer(compute='_count_log')
    queue_count = fields.Integer(compute='_count_log')
    company_id = fields.Many2one(
        'res.company', 
        string='Company',
        default=lambda self: self.env.company
    )
    
    @api.depends('mass_mail_log_ids')
    def _count_log(self):
        for r in self:
            r.sent_count=len(r.mass_mail_log_ids.filtered(lambda log: log.state=='sent'))
            r.failed_count=len(r.mass_mail_log_ids.filtered(lambda log: log.state=='failed'))
            r.queue_count=len(r.mass_mail_log_ids.filtered(lambda log: log.state=='queue'))
    
    def action_open_log_queue(self):
        action = self.env.ref('mgs_sms_marketing.mgs_mass_mail_log_action')
        result = action.sudo().read()[0]
        result['context']={}
        result['domain'] = "[('sms_id', '=', %s),('state','=','queue')]"%str(self.id)
        result['context']['create'] = False
        return result
    

    def action_open_log_sent(self):
        action = self.env.ref('mgs_sms_marketing.mgs_mass_mail_log_action')
        result = action.sudo().read()[0]
        result['context']={}
        result['domain'] = "[('sms_id', '=', %s),('state','=','sent')]"%str(self.id)
        result['context']['create'] = False
        return result
    

    def action_open_log_failed(self):
        action = self.env.ref('mgs_sms_marketing.mgs_mass_mail_log_action')
        result = action.sudo().read()[0]
        result['context']={}
        
        result['domain'] = "[('sms_id', '=', %s),('state','=','failed')]"%str(self.id)
        result['context']['create'] = False
        return result
    
    @api.model
    def create_mgs_sms(self, name, msg, to, partner, model):
        mgs_sms_obj = self.env['mgs.sms']
        sms_record = mgs_sms_obj.create({
            'source_name': name,
            'message': msg,
            'mobile': to,
            'partner_id': partner,
            'model_id': model,
            'datetime': datetime.now()})
        return sms_record



    def get_token(self):
        
        company = self.env.company
        username = company.mgs_marketing_sms_username
        password = company.mgs_marketing_sms_password
        if username and password:
            payload = {
                "grant_type": "password",
                "username": username,
                "password": password,
            }
            response = requests.request("POST", 'https://smsapi.hormuud.com/token', data=payload,headers={'content-type': "application/x-www-form-urlencoded"})
            resp_dict1 = json.loads(response.text)
            if not  resp_dict1.get('access_token', False):
                _logger.error("resp_dict1")
                return None
            return  resp_dict1['access_token']
    
            
    @api.model
    def _process_queue(self, batch=60):
        company = self.env.company
        # sender = self.env['ir.config_parameter'].sudo().get_param('mgs_sms_marketing.mgs_marketing_sms_sender_id')
        sender = company.mgs_marketing_sms_sender_id
        queue=self.env['mgs.mass.mail.log'].search([('state','=','queue'),('cron_processed','=',False)],limit=batch+1)
        need_cron_trigger = len(queue) > batch
        if need_cron_trigger:
            queue = queue[:batch]
        access_token=self.get_token()
        if not access_token:
            raise ValidationError('Failed to obtain access token')
        queue.write({'cron_processed':True})
        self.env.cr.commit()
        for sms in queue:
            try:
                payload = {"senderid": sender,"mobile": sms.mobile,"message" : sms.sms_id.message}
                respObj= self.sms_api(access_token,payload)
                if respObj['ResponseMessage'] != 'SUCCESS!.':
                    sms.write({'state':'failed','description':respObj['Data']})
                    self.env.cr.commit()
                else:
                    sms.write({'state':'sent'})
                    self.env.cr.commit()
            except Exception as e:
                self.env.cr.rollback()
                sms.write({'state':'failed','description':str(e)})
                self.env.cr.commit()
        if need_cron_trigger:
            self.env.ref('mgs_sms_marketing.mgs_sms_cron')._trigger()






        
    def sms_api(self,token,payload):
        sendsmsResp = requests.request("POST", 'https://smsapi.hormuud.com/api/SendSMS', data=json.dumps(payload),headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
        respObj = json.loads(sendsmsResp.text)
        return respObj
    
    def action_send_mgs_sms_batch(self,messeges,msg):
        param_obj = self.env['ir.config_parameter']
        # sender = param_obj.sudo().get_param('mgs_sms_marketing.mgs_marketing_sms_sender_id')
        company = self.env.company
        sender = company.mgs_marketing_sms_sender_id
        access_token = self.get_token()
        log_object=self.env['mgs.mass.mail.log']
        if not access_token:
            self.message_post(body='Failed to obtain access token')
            return

        
        for rec in messeges:
            payload = {"senderid": sender,"mobile": rec['mobile'],"message" : msg}
            respObj= self.sms_api(access_token,payload)
            Data=respObj['Data']
            if respObj['ResponseMessage'] != 'SUCCESS!.':
                log_object.create({'contact_id' : rec['contact_id'],'sms_id':rec['sms_id'],'mail_list_id': rec['mail_list_id'],'state':'failed','description':Data})
            else:
                log_object.create({'contact_id' : rec['contact_id'],'sms_id':rec['sms_id'],'mail_list_id': rec['mail_list_id'],'state':'sent'})
        if len(self.mass_mail_log_ids.filtered(lambda log: log.state=='sent')) > 0:
            return 'sent'
        else:
            return 'failed'
        
    
    def action_send(self):
        log_model = self.env['mgs.mass.mail.log'].sudo()

        for sms in self:
            
            if not sms.is_mass_sms:
                continue 

            # Collect partners from mailing lists
            partners = sms.mail_list_ids.partner_ids.filtered(lambda p: p.active)

            unique = {}
            no_phone_partners = []

            for p in partners:
                if p.phone:
                    if p.phone not in unique:
                        unique[p.mobile] = p
                else:
                    no_phone_partners.append(p)

            queue_vals = []

            # Partners with mobile → queue state
            for phone, partner in unique.items():
                queue_vals.append({
                    'sms_id': sms.id,
                    'partner_id': partner.id,
                    'msg': sms.message,
                    'mobile': phone,
                    'state': 'queue',
                    'cron_processed': False,
                    'mail_list_id': sms.mail_list_ids.filtered(lambda l: partner in l.partner_ids)[0].id if sms.mail_list_ids else False,
                })

            # Partners without mobile → failed state so you can see them
            for partner in no_phone_partners:
                queue_vals.append({
                    'sms_id': sms.id,
                    'partner_id': partner.id,
                    'msg': sms.message,
                    'mobile': False,
                    'state': 'failed',
                    'description': "No mobile number",
                    'cron_processed': True,  # mark processed so cron doesn't retry
                    'mail_list_id': sms.mail_list_ids[0].id if sms.mail_list_ids else False,
                })

            # Create all log records at once
            log_model.create(queue_vals)

        # Send queued SMS immediately
        self._process_queue()



    def action_send_mgs_sms(self):
        if not self.mobile:
            self.message_post(body='This partner has no mobile number')
            return 'This partner has no mobile number'
        company = self.env.company
        sender = company.mgs_marketing_sms_sender_id
        access_token=self.get_token()
        if not access_token:
            self.message_post(body='Failed to obtain access token')
            return
        payload = {"senderid": sender,"mobile": self.mobile,"message":self.message}
        try:
            respObj = self.sms_api(access_token,payload)
            Data=respObj['Data']
            self.write({'response': Data})
            if respObj['ResponseMessage'] != 'SUCCESS!.':
                self.message_post(body="Failed to send the sms message to :" + str(self.mobile) +" | Description: "+ Data['Description'])
                self.write({'state': 'failed'})
                return 'failed to send sms'
            else:
                self.write({'state': 'sent'})
                self.message_post(body="Successfully sent sms message to :"+ str(self.mobile))
                return 'the sms was sent successfully'
        except Exception as e:
            self.message_post(body=e)
            return 'failed to send sms'



