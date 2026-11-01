from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_property_project(self):
        self.ensure_one()
        return self.move_id.tenancy_id.property_project_id

    @api.depends('move_id.tenancy_id.property_project_id.income_account_id')
    def _compute_account_id(self):
        # Posted lines keep their account: a recompute (e.g. a project changing its
        # income account) must not touch accounting entries already validated.
        posted_lines = self.filtered(lambda line: line.parent_state == 'posted')
        for line in posted_lines:
            line.account_id = line.account_id
        draft_lines = self - posted_lines
        super(AccountMoveLine, draft_lines)._compute_account_id()
        for line in draft_lines:
            if line.display_type != 'product' or not line.move_id.is_sale_document(include_receipts=True):
                continue
            income_account = line._get_property_project().income_account_id
            if income_account and income_account.company_ids & line.company_id.parent_ids:
                line.account_id = income_account

    @api.depends('move_id.tenancy_id.property_project_id.analytic_account_id')
    def _compute_analytic_distribution(self):
        # Posted lines keep their distribution: their analytic lines already exist and
        # a recompute (e.g. a project changing analytic account) must not touch them.
        posted_lines = self.filtered(lambda line: line.parent_state == 'posted')
        for line in posted_lines:
            line.analytic_distribution = line.analytic_distribution
        super(AccountMoveLine, self - posted_lines)._compute_analytic_distribution()

    def _related_analytic_distribution(self):
        # EXTENDS 'account'
        vals = super()._related_analytic_distribution()
        analytic_account = self._get_property_project().analytic_account_id
        if analytic_account and (
            not analytic_account.company_id or analytic_account.company_id in self.company_id.parent_ids
        ):
            vals |= {str(analytic_account.id): 100}
        return vals
