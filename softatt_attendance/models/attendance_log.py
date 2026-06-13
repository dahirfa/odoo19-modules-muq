from odoo import _, api, fields, models
import requests
import pytz
from datetime import datetime, timedelta, time
import json
import logging
from odoo.exceptions import UserError, ValidationError


_logger = logging.getLogger(__name__)

class ConfPunchState(models.Model):
    _name = 'sa.punch.state'
    _description = 'Punch State'
    
    code        = fields.Integer()
    punch_type  = fields.Selection([('in', 'Check In'), ('out', 'Check Out')])
    company_id = fields.Many2one(comodel_name='res.company', required=True, index=True, default=lambda self: self.env.company)
    

class saAttendanceLog(models.Model):
    _name           = "sa.attendance.log"
    _description    = "sa Attendance Log"
    _order          = "punch_time desc"

    hubid                   = fields.Integer(string="ATT ID")
    punch_time              = fields.Datetime(string="Punch Time", required=True, tracking=True)
    punch_state             = fields.Char(required=True)
    check_in_check_out      = fields.Char(store=True, string="Check In/Check Out")
    employee_id             = fields.Many2one("hr.employee", string="Employee", tracking=True)
    department_id           = fields.Many2one(related="employee_id.department_id", readonly=True, store=True)
    device_code             = fields.Integer(string="Device ID", tracking=True)
    code                    = fields.Char(string="Code")
    location_alias          = fields.Char(string="Location Alias",)
    location_id             = fields.Many2one(related="employee_id.work_location_id", string="Location", tracking=True, store=True)
    db_name                 = fields.Char()
    company_id              = fields.Many2one('res.company', related='employee_id.company_id', store=True, readonly=True)
    dayofweek               = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
        ], 'Day of Week', store=True, index=True, default='0', compute="_compute_dayofweek")


    @api.depends('punch_time')
    def _compute_dayofweek(self):
        for record in self:
            if record.punch_time:
                # Directly use the day of the week index (0=Monday, 1=Tuesday, ..., 6=Sunday)
                day_of_week = record.punch_time.weekday()
                record.dayofweek = str(day_of_week)
                
    def action_compute_employees(self):
        employees = self.env["sa.attendance.employee.code"]
        for r in self:
            employee_id = employees.search([("code", "=", r.code),("device_id.externalid", "=", r.device_code),],limit=1,).employee_id
            if employee_id:
                r.employee_id = employee_id.id
            else:
                r.employee_id = None

    # for punch_type Based attendance calculation
    def _process_hr_attendance_punch(self, attendance_obj, punch_states):
        employee_id = self.employee_id.id
        punch_state = punch_states.search([('code','=',int(self.punch_state))], limit=1).punch_type
        if not punch_state:
            self.check_in_check_out = "Undefined Punch"
            return
        punch_time = self.punch_time
        try:
            oatt_domain=[('employee_id.id','=',employee_id),('check_in','!=',False),('check_out', '=', False)]
            open_att=attendance_obj.search(oatt_domain, limit=1)
            if punch_state == "in":
                self.check_in_check_out = "Check In"
                if not open_att:
                    attendance_obj.create({'employee_id':employee_id,'check_in':punch_time})
                    
                if open_att and punch_time >= open_att.check_in + timedelta(hours=20):
                    open_att.check_out = open_att.check_in
                    attendance_obj.create({'employee_id':employee_id,'check_in':punch_time})
                else:
                    return
                
            if punch_state == "out":
                self.check_in_check_out = "Check Out"
                if open_att:
                    open_att.write({'check_out': punch_time})
        except Exception as e:
            return
        
    # for smart attendance calculation
    def _process_hr_attendance(self, obj, target_timezone):
        punch_time      = self.punch_time.astimezone(target_timezone).replace(tzinfo=None)
        employee        = self.employee_id
        employee_id     = employee.id
        working_hours   = employee.resource_calendar_id
        punch_state     = working_hours._softatt_get_period_punch(str(punch_time.weekday()), punch_time.time())
        if not punch_state:
            self.check_in_check_out = "Undefined Punch"
            return
        punch_state     = punch_state.punch_type
        punch_time      = self.punch_time
        try:
            oatt_domain=[('employee_id.id','=',employee_id),('check_in','!=',False),('check_out', '=', False)]
            open_att=obj.search(oatt_domain, limit=1)
            if punch_state == "in":
                self.check_in_check_out = "Check In"
                if not open_att:
                    obj.create({'employee_id':employee_id,'check_in':punch_time})
                if open_att and punch_time >= open_att.check_in + timedelta(hours=20):
                    open_att.check_out = open_att.check_in
                    obj.create({'employee_id':employee_id,'check_in':punch_time})
                else:
                    return
            if punch_state == "out":
                self.check_in_check_out = "Check Out"
                if open_att:
                    open_att.write({'check_out': punch_time})
        except Exception as e:
            return

    # def action_update_hr_attendance(self):
    #     self.action_compute_employees()
    #     obj = self.env["hr.attendance"]
    #     punch_states = self.env["sa.punch.state"]
    #     recs = self.filtered(lambda x: x.employee_id).sorted(key=lambda x: x.punch_time)
    #     for r in recs:
    #         target_timezone = pytz.timezone(self.env.user.tz)
    #         try:
    #             if r.employee_id.attendance_type == 'smart':
    #                 r._process_hr_attendance(obj, target_timezone)
    #             else:
    #                 r._process_hr_attendance_punch(obj, punch_states)
    #         except:
    #             continue
    

    def action_update_hr_attendance(self):
        self.action_compute_employees()
        obj = self.env["hr.attendance"]
        punch_states = self.env["sa.punch.state"]
        recs = self.filtered(lambda x: x.employee_id).sorted(key=lambda x: x.punch_time)

        # Ensure the timezone is valid
        user_tz = self.env.user.tz or 'UTC'  # Default to 'UTC' if tz is False/None
        try:
            target_timezone = pytz.timezone(user_tz)
        except pytz.UnknownTimeZoneError:
            target_timezone = pytz.timezone('UTC')  # Fallback to UTC in case of an invalid timezone

        for r in recs:
            try:
                if r.employee_id.attendance_type == 'smart':
                    r._process_hr_attendance(obj, target_timezone)
                else:
                    r._process_hr_attendance_punch(obj, punch_states)
            except Exception as e:
                _logger.error(f"Error processing attendance for {r.employee_id.name}: {e}")
                continue


    def _is_same_server_logs(self):
        return False
    
    def get_transactions(self):
        if self._is_same_server_logs():
            self._same_server_transactions()
            return
        mode = self.env['ir.config_parameter'].sudo().get_param('softatt_attendance.softatt_comm_mode')
        if mode == 'api':
            self._api_transactions()
        if mode == 'dblink':
            device_codes = self.env["sa.biometric.device"].search([]).mapped("externalid")
            self._dblink_transactions(device_codes)
        
    def _dblink_transactions(self, device_codes=()):
        linked_servers=self.env['sa.db_link.server'].sudo().search([('registered','=',True)])
        query = ""
        count_server_ids=len(linked_servers.sudo().read(['name']))
        count=0
        codes = f"({str(device_codes)[1:-1]})"
        for server in linked_servers:
            count+=1
            
            query += f"""
				SELECT
                    DATA.id,
                    DATA.area,
                    DATA.emp_code,
                    DATA.device_id,
                    DATA.punch_time,
                    DATA.punch_state,
                    DATA.db_name
				FROM public.dblink
				    ('{server.name}',
                            'SELECT 
                                t.id,
                                d.name as area,
                                device_id,
                                emp_code,
                                punch_time,
                                punch_state,
                                current_database()
                            FROM public.sa_biometric_att t
                            LEFT JOIN sa_biometric_device d ON(d.id=t.device_id) 
                            WHERE device_id in {codes}') AS DATA
                                
                                (id integer,
                                area CHARACTER VARYING,
                                device_id integer,
                                emp_code CHARACTER VARYING,
                                punch_time timestamp,
                                punch_state CHARACTER VARYING,
                                db_name CHARACTER VARYING)
				LEFT JOIN (
                            SELECT db_name, hubid, device_code 
                            FROM sa_attendance_log smal 
                            WHERE smal.device_code in {codes}) AS mal 
                    ON mal.hubid=Data.id AND mal.db_name=Data.db_name
				WHERE mal.hubid is NULL
			"""
   
            if count_server_ids > count:
                query +=""" UNION """
            else:
                query +=""" ORDER BY punch_time,punch_state LIMIT 500;"""
        self._process_sql_logs(query)
        
        
    def _process_sql_logs(self, query):
        self.env.cr.execute(query)
        transactions    = self.env.cr.dictfetchall()
        devices         = self.env['sa.biometric.device']
        attendance_log  = self
        logs            = []
        for line in transactions:
            device_id = devices.search([("externalid", "=", line["device_id"])],limit=1)
            logs.append({"hubid"           : line["id"],
                        "location_alias"   : line["area"],
                        "code"             : line["emp_code"],
                        "device_code"      : line["device_id"],
                        "punch_time"       : line["punch_time"],
                        "punch_state"      : line["punch_state"],
                        "db_name"          : line["db_name"],
                        "company_id"       : device_id.company_id.id if device_id else None,
                        })
        log = attendance_log.sudo().create(logs)
        log.action_update_hr_attendance()
    
    def _api_transactions(self):
        conf_param  = self.env['ir.config_parameter']
        session_id  = conf_param._softatt_authenticate()
        url         = conf_param.sudo().get_param('softatt_attendance.att_server_url')
        limit       = conf_param.sudo().get_param('softatt_attendance.att_limit')
        self.env.cr.execute("SELECT max(hubid) as max_id FROM sa_attendance_log")
        max_id      = self.env.cr.dictfetchone()['max_id'] or 0
        full_url    = "%s/attendence/transactions/%s/%s"%(url,max_id,limit)
        headers     = {"Cookie": 'session_id=%s'%session_id}
        request     = requests.request("GET", full_url, headers=headers, data={})
        response    = json.loads(request.text)
        _logger.info(full_url)
        res                 = response.get('transactions')
        attendance_log      = self
        employees           = self.env["sa.attendance.employee.code"]
        logs                = []
        for line in res:
            emp_code_id     = employees.search([
                ("code", "=", line["emp_code"]),
                ("device_id.externalid", "=", line["device_id"])],limit=1)
            logs.append({
                'hubid'         :line['id'],
                'location_alias':line['area'],
                'code'          :line['emp_code'],
                'device_code'   :line['device_id'],
                'punch_time'    :line['punch_time'],
                'punch_state'   :line['punch_state'],
                'employee_id'   :emp_code_id.employee_id.id if emp_code_id else None,
               
                })
      

        log = attendance_log.sudo().create(logs)
        log.action_update_hr_attendance()
    
    def _same_server_transactions(self):
        return
        
    def download_latest_logs(self):
        self.get_transactions()
