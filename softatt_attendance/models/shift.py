from datetime import datetime, timedelta
from odoo import _, api, fields, models
from odoo.tools import date_utils

import logging

_logger = logging.getLogger(__name__)
class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'
    
    next_dayofweek      = fields.Char(compute='_compute_next_dayofweek', store=True)

    @api.depends('dayofweek', 'calendar_id')
    def _compute_next_dayofweek(self):
        for r in self:
            ndow = (int(r.dayofweek) + 1) % 7
            r.next_dayofweek = ndow    
            
            
class ResourceCalendarPeriods(models.Model):
    _name           =  'sa.resource.calendar.periods'
    _description    =  'In/Out Periods'

    name        = fields.Char(required=True)    
    calender_id = fields.Many2one('resource.calendar',string='Calender',)
    hour_from   = fields.Float(string='from', required=True, index=True,
        help="Start and End time of working.\n"
             "A specific value of 24:00 is interpreted as 23:59:59.999999.")
    hour_to     = fields.Float(string='to', required=True)
    dayofweek   = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
        ], 'Day of Week', required=True, index=True, default='0')
    punch_type  = fields.Selection([('in', 'Check In'), ('out', 'Check Out')], required=True)

class ResourceAttendanceTags(models.Model):
    _name           =  'sa.calendar.tag'
    _description    =  'Attendance Tags'

    name        = fields.Selection([
        ('Early', 'Early'),
        ('On-Time', 'On-Time'),
        ('Late', 'Late')], required=True, default="Early")
    
    color       = fields.Integer(string='color',)
    
    calendar_id = fields.Many2one('resource.calendar',string='Calender',)
    hour_from   = fields.Float(string='from', required=True, index=True,
        help="Start and End time of working.\n"
             "A specific value of 24:00 is interpreted as 23:59:59.999999.")
    hour_to     = fields.Float(string='to', required=True)
    dayofweek   = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
        ], 'Day of Week', required=True, index=True, default='0')

class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'
    
    overnight_shift     = fields.Boolean(default=False)
    sa_in_out_periods   = fields.One2many('sa.resource.calendar.periods','calender_id')
    sa_calendar_tag_ids = fields.One2many('sa.calendar.tag','calendar_id')

    

    def _get_next_day(self, dayofweek):
        ndow = (int(dayofweek) + 1) % 7
        next_dayofweek_id = None
        if self.overnight_shift == True:
            line = self.attendance_ids.search([('calendar_id.id','=',self.id), ('dayofweek','=',ndow), ('day_period','=','morning')])
            next_dayofweek_id = line
        return next_dayofweek_id


    def _softatt_get_tags(self, dayofweek, time):
        str_time = time.strftime("%H:%M")
        time_float = date_utils._softatt_time_to_float(str_time)
        tags = self.sa_calendar_tag_ids.search([('hour_from','<=',time_float), ('hour_to','>=',time_float), ('dayofweek','=',dayofweek), ('calendar_id.id','=',self.id)], limit=1)
        if not tags:
            return None
        return tags
        
    def _softatt_get_period_punch(self, dayofweek, time):
        line = None
        str_time = time.strftime("%H:%M")
        time_float = date_utils._softatt_time_to_float(str_time)
        line = self.sa_in_out_periods.search([('hour_from','<=',time_float), ('hour_to','>=',time_float), ('dayofweek','=',dayofweek), ('calender_id.id','=',self.id)], limit=1)
        if not line:
            return None
        return line
    
    
    def _softatt_get_period_punch_shift(self, dayofweek, time):
        line        = None
        str_time    = time.strftime("%H:%M")
        time_float  = date_utils._softatt_time_to_float(str_time)
        line        = self.env['sa.resource.calendar.periods'].search([('hour_from','<=',time_float), ('hour_to','>=',time_float), ('dayofweek','=',dayofweek)])
        if not line:
            return None
        return line
        
        
    def _softatt_get_shift_start_and_end_bot(self, dayofweek, time):
        line = None
        str_time = time.strftime("%H:%M")
        time_float = date_utils._softatt_time_to_float(str_time)
        afm = False
        if not self.overnight_shift:
            line = self.attendance_ids.search([('hour_from','<',time_float), ('hour_to','>',time_float), ('dayofweek','=',dayofweek), ('calendar_id.id','=',self.id), ('day_period','!=','break')])
        else:
            line = self.attendance_ids.search([('hour_from','<',time_float), ('hour_to','>',time_float), ('dayofweek','=',dayofweek), ('day_period','=','afternoon'), ('calendar_id.id','=',self.id)])            
            if not line:
                previous_day = self.attendance_ids.search([('hour_to','>',time_float), ('next_dayofweek','=',dayofweek), ('day_period','=','afternoon'),('calendar_id.id','=',self.id)], limit=1)
                if previous_day:
                    next_day = self._get_next_day(previous_day.dayofweek)
                    if next_day and time_float < next_day.hour_to:
                        line = previous_day
                    if line:
                        afm = True
        if not line:
            _logger.info("--------No matching records-------")
            return None
            
        if not self.overnight_shift:
            shift_start_time    = line.hour_from
            shift_end_time      = line.hour_to 
            s, e = datetime.combine(time.date(), datetime.min.time()) + timedelta(hours=shift_start_time), datetime.combine(time.date(), datetime.min.time()) + timedelta(hours=shift_end_time)
        else:
            shift_start_time    = line.hour_from
            shift_end_time      = self._get_next_day(line.dayofweek).hour_to + 24
            
            if not afm:
                s, e = datetime.combine(time.date(), datetime.min.time()) + timedelta(hours=shift_start_time), datetime.combine(time.date(), datetime.min.time()) + timedelta(hours=shift_end_time)            
            else:
                s, e = datetime.combine(time.date(), datetime.min.time()) + timedelta(hours=shift_start_time), datetime.combine(time.date(), datetime.min.time()) + timedelta(hours=shift_end_time)            
                s, e = s - timedelta(days=1), e - timedelta(days=1)
        return [s, e, line]