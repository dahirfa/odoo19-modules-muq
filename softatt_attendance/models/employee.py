from odoo import _, api, fields, models


class AttendanceEmployeeCodes(models.Model):
    _name = "sa.attendance.employee.code"
    _description = "Employee Code"
    
    employee_id         = fields.Many2one("hr.employee", string="Employee", 
    ondelete='cascade'
    )
    code                = fields.Char(string="Code", required=True, nocopy=True)
    device_id           = fields.Many2one("sa.biometric.device", string="Device", tracking=True, 
    ondelete='cascade')
    company_id              = fields.Many2one('res.company', related='employee_id.company_id', store=True)
    _sql_constraints = [
        ('unique_device_id_code', 'unique(device_id, code)', 'Device and Code must be unique together!')
    ]
        
class AttendanceEmployee(models.Model):
    _inherit = "hr.employee"
    
    attendance_type = fields.Selection([('smart', 'Smart'),('punch', 'Punch Type')], default='punch',required=True)
    code_ids        = fields.One2many('sa.attendance.employee.code', 'employee_id', string='Codes', copy=False)
    sa_timoff_ids  = fields.One2many('sa.employee.timeoff', 'employee_id')
    
# class AttendanceEmployeeBase(models.AbstractModel):
#     _inherit = "hr.employee.base"
    
#     attendance_type = fields.Selection([('smart', 'Smart'),('punch', 'Punch Type')], default='punch',required=True)
#     code_ids        = fields.One2many('sa.attendance.employee.code', 'employee_id', string='Codes', copy=False)
#     sa_timoff_ids  = fields.One2many('sa.employee.timeoff', 'employee_id')
    

class HrEmployeeTimeOff(models.Model):
    _name           = "sa.employee.timeoff"
    _description    = "Employee TimeOff"
    _order          = "start_date DESC"
    
    employee_id = fields.Many2one('hr.employee',string='Employee', required=True)
    start_date  = fields.Date(default= fields.Date().today(), required=True, string="From")
    end_date    = fields.Date(default= fields.Date().today(), required=True, string="To")
    reason      = fields.Text()