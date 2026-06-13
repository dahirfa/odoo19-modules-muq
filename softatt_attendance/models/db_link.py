from odoo import models, fields, api
from odoo.exceptions import  ValidationError

class saAttendanceServers(models.Model):
    _name = 'sa.db_link.server'
    _description = 'Configration For DB-Link servers'


    name = fields.Char(string='DB Alias(lower case)',required=True)
    db_name = fields.Char(string='Db name',required=True)
    ip_address = fields.Char(readonly=False,required=True)
    current_user = fields.Char(readonly=False,required=True)
    port = fields.Char(readonly=False,required=True)
    user_name = fields.Char(readonly=False, string="DB-USER",required=True)
    password = fields.Char(readonly=False,password=True,required=True)
    registered = fields.Boolean(readonly=True)
    
    @api.onchange('name')
    def onchange_name(self):
        if self.name:
            name=self.name
            if '-' in name:
                name = name.replace('-','_')
            if ' ' in name:
                name = name.replace(' ','_')
                
            self.name = name.lower()

    def register_server(self):
        for rec in self:
            try:
                query=f"""
                    CREATE EXTENSION IF NOT EXISTS  dblink;
                    SELECT dblink_connect('host={rec.ip_address} port={rec.port} user={rec.user_name} password={rec.password} dbname={rec.db_name}');
                    CREATE FOREIGN DATA WRAPPER {rec.name} VALIDATOR postgresql_fdw_validator;
                    CREATE SERVER IF NOT EXISTS {rec.name} FOREIGN DATA WRAPPER {rec.name} OPTIONS (hostaddr '{rec.ip_address}',  port '{rec.port}' , dbname '{rec.db_name}');
                    CREATE USER MAPPING IF NOT EXISTS FOR {rec.current_user} SERVER {rec.name}  OPTIONS (user '{rec.user_name}' , password '{rec.password}');
                    SELECT dblink_connect('{rec.name}');
                    SELECT dblink_disconnect();
                """
                rec.env.cr.execute(query)
                res = rec.env.cr.fetchone()
            except Exception as e:
                raise ValidationError(str(e))

            if res[0] == 'OK':
                rec.registered=True
            else:
                raise ValidationError(str(res))