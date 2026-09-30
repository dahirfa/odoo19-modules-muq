from odoo import fields, models
from odoo.exceptions import UserError


class ContainerControlReportWizard(models.TransientModel):
    _name = 'container.control.report.wizard'
    _description = 'Container Control Report Wizard'

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    consignee_id = fields.Many2one(
        comodel_name='res.partner',
        string='Consignee',
        required=True,
        help="Only the containers of this consignee are printed.",
    )
    report_type = fields.Selection(
        selection=[
            ('summary', 'Summary'),
            ('detail', 'Detail'),
        ],
        string='Report Type',
        required=True,
        default='summary',
        help="Summary prints one line per container. Detail prints the full container control file.",
    )

    def _get_containers(self):
        """Containers of the selected consignee, in container number order."""
        self.ensure_one()
        return self.env['container.control'].search(
            [
                ('consignee_id', '=', self.consignee_id.id),
                ('company_id', '=', self.company_id.id),
            ],
            order='container_number',
        )

    def action_print_report(self):
        self.ensure_one()
        if not self._get_containers():
            raise UserError(self.env._(
                "There is no container for %s.", self.consignee_id.display_name))
        report_xml_id = (
            'mgs_container_control.container_control_summary_report_action'
            if self.report_type == 'summary'
            else 'mgs_container_control.container_control_detail_report_action'
        )
        return self.env.ref(report_xml_id).report_action(self)
