from odoo import models, api
import ast

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def _query_get(self, domain=None):
        self.check_access_rights('read')

        context = dict(self._context or {})
        domain = domain or []
        if not isinstance(domain, (list, tuple)):
            domain = ast.literal_eval(domain)

        date_field = 'aml.date'

        # Apply date filters
        if context.get('date_to'):
            domain += [(date_field, '<=', context['date_to'])]
        if context.get('date_from'):
            if not context.get('strict_range'):
                domain += [
                    '|',
                    (date_field, '>=', context['date_from']),
                    ('account_id.include_initial_balance', '=', True)
                ]
            elif context.get('initial_bal'):
                domain += [(date_field, '<', context['date_from'])]
            else:
                domain += [(date_field, '>=', context['date_from'])]

        # Apply company filters with alias to avoid ambiguity
        # company_field = 'aml.company_id'  # Use alias for the company field
        # if context.get('company_id'):
        #     domain += [(company_field, '=', context['company_id'])]
        # elif context.get('allowed_company_ids'):
        #     domain += [(company_field, 'in', self.env.companies.ids)]
        # else:
        #     domain += [(company_field, '=', self.env.company.id)]

        # Apply additional context filters
        if context.get('state') and context['state'].lower() != 'all':
            domain += [('aml.parent_state', '=', context['state'])]
        if context.get('reconcile_date'):
            domain += [
                '|',
                ('aml.reconciled', '=', False),
                '|',
                ('aml.matched_debit_ids.max_date', '>', context['reconcile_date']),
                ('aml.matched_credit_ids.max_date', '>', context['reconcile_date'])
            ]
        filters = {
            'account_tag_ids': 'aml.account_id.tag_ids',
            'account_ids': 'aml.account_id',
            'analytic_tag_ids': 'aml.analytic_tag_ids',
            'analytic_account_ids': 'aml.analytic_account_id',
            'partner_ids': 'aml.partner_id',
            'partner_categories': 'aml.partner_id.category_id',
        }
        for key, field in filters.items():
            if context.get(key):
                domain += [(field, 'in', context[key].ids)]

        # Add mandatory filters
        domain += [
            ('aml.display_type', 'not in', ('line_section', 'line_note')),
            ('aml.parent_state', '!=', 'cancel'),
        ]

        # Build the WHERE clause manually
        where_clauses = []
        params = []
        for condition in domain:
            if isinstance(condition, tuple) and len(condition) == 3:
                field, operator, value = condition
                where_clauses.append(f"{field} {operator} %s")
                params.append(value)
            elif isinstance(condition, str):  # Handle OR operators like '|'
                where_clauses.append(condition)

        # Combine the WHERE clauses
        where_clause = " AND ".join(where_clauses)

        # Generate the final query parts
        tables = "account_move_line aml"  # Main table for the query with alias
        return tables, where_clause, params
