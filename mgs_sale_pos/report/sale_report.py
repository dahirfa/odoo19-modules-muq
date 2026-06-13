from odoo import models  # type: ignore
import re
import logging

_logger = logging.getLogger(__name__)


class MgsSaleReport(models.AbstractModel):
    _inherit = "report.mgs_sale.sale_report"

    def _sale_query(self, where_clause="", pos_where=None):
        """Extend base _sale_query to accept an explicit pos_where built by the
        wizard. If pos_where is None we fall back to the conservative converter.
        """
        sale_query = super()._sale_query(where_clause)

        currency_table = self.env["res.currency"]._get_simple_currency_table(
            self.env.companies
        )
        currency_table = self.env.cr.mogrify(currency_table).decode(
            self.env.cr.connection.encoding
        )

        # Simplified POS SELECT to match the sale structure
        pos_select = f"""
            SELECT 
                MIN(l.id) AS id,
                l.product_id AS product_id,
                pt.uom_id AS product_uom_id,
                CASE WHEN l.product_id IS NOT NULL THEN SUM(l.qty * 1.0 * u.factor / COALESCE(NULLIF(pt.uom_id,0),1)) ELSE 0 END AS product_uom_qty,
                CASE WHEN l.product_id IS NOT NULL THEN SUM(0.0) ELSE 0 END AS qty_delivered,
                CASE WHEN l.product_id IS NOT NULL THEN SUM(0.0) ELSE 0 END AS qty_invoiced,
                CASE WHEN l.product_id IS NOT NULL THEN SUM(0.0) ELSE 0 END AS qty_to_invoice,
                CASE WHEN l.product_id IS NOT NULL THEN SUM( (l.price_subtotal_incl) / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END * CASE COALESCE(account_currency_table.rate, 0) WHEN 0 THEN 1.0 ELSE account_currency_table.rate END ) ELSE 0 END AS price_total,
                CASE WHEN l.product_id IS NOT NULL THEN SUM( (l.price_subtotal) / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END * CASE COALESCE(account_currency_table.rate, 0) WHEN 0 THEN 1.0 ELSE account_currency_table.rate END ) ELSE 0 END AS price_subtotal,
                COUNT(*) AS nbr,
                s.name AS name,
                s.date_order AS date,
                s.state AS state,
                s.partner_id AS partner_id,
                s.user_id AS user_id,
                s.company_id AS company_id,
                pt.categ_id AS categ_id,
                NULL::int AS pricelist_id,
                NULL::int AS team_id,
                p.product_tmpl_id,
                partner.commercial_partner_id AS commercial_partner_id,
                {self.env.company.currency_id.id} AS currency_id,
                -- Your additional columns for POS
                partner.name AS partner_name,
                pt.name ->>'en_US' AS product_name,
                COALESCE(SUM(0.0), 0) AS cost,
                SUM(0.0) AS margin,
                NULL AS client_order_ref
        """

        pos_from = f"""
            FROM 
                pos_order_line l
                INNER JOIN pos_order s ON (s.id = l.order_id)
                LEFT JOIN product_product p ON (l.product_id = p.id)
                LEFT JOIN product_template pt ON (p.product_tmpl_id = pt.id)
                LEFT JOIN product_category pc ON pt.categ_id = pc.id
                LEFT JOIN product_category parent_pc ON pc.parent_id = parent_pc.id
                LEFT JOIN uom_uom u ON (u.id = pt.uom_id)
                LEFT JOIN res_partner partner ON (s.partner_id = partner.id)
                JOIN {currency_table} ON account_currency_table.company_id = s.company_id
        """

        # Use the pos_where provided by the wizard when available (preferred)
        if pos_where is None:
            pos_where = self._convert_where_clause_for_pos(where_clause)
        where_pos_full = "s.state IN ('paid', 'done')"
        if pos_where:
            where_pos_full += " " + pos_where

        pos_group_by = """
            GROUP BY 
                l.product_id,
                pt.uom_id,
                s.name,
                s.date_order,
                s.state,
                s.partner_id,
                s.user_id,
                s.company_id,
                pt.categ_id,
                p.product_tmpl_id,
                partner.commercial_partner_id,
                partner.name,
                pt.name
        """

        pos_query = pos_select + pos_from + " WHERE " + where_pos_full + pos_group_by
        return sale_query + "\nUNION ALL\n" + pos_query

    def _convert_where_clause_for_pos(self, where_clause):
        """
        Conservative conversion of sale WHERE -> POS WHERE.
        Remove only filters that don't apply to POS - keep product, partner, and user filters.
        """
        if not where_clause:
            return ""

        converted = where_clause

        # 1. canonicalize whitespace
        converted = " ".join(converted.split())

        # 2. replace product alias t. -> pt.
        converted = re.sub(r"\bt\.", "pt.", converted)

        # 3. Remove ONLY filters that don't apply to POS:
        #    KEEP: date, company, category, parent_category, product, partner, user
        #    REMOVE: team, currency, pricelist, tags, sale-specific states

        # Remove team_id filters (POS doesn't have sales teams)
        converted = re.sub(
            r"\bAND\s+s\.team_id\s*=\s*%s\b", "", converted, flags=re.IGNORECASE
        )
        converted = re.sub(
            r"\bs\.team_id\s*=\s*%s\b", "TRUE", converted, flags=re.IGNORECASE
        )

        # Remove currency filters (POS uses company currency)
        converted = re.sub(
            r"\bAND\s+s\.currency_id\s*=\s*%s\b", "", converted, flags=re.IGNORECASE
        )
        converted = re.sub(
            r"\bs\.currency_id\s*=\s*%s\b", "TRUE", converted, flags=re.IGNORECASE
        )

        # Remove tag filters (POS doesn't have sale order tags)
        converted = re.sub(
            r"\bAND\s+tag\.id\s*=\s*%s\b", "", converted, flags=re.IGNORECASE
        )
        converted = re.sub(
            r"\btag\.id\s*=\s*%s\b", "TRUE", converted, flags=re.IGNORECASE
        )
        converted = re.sub(
            r"\bAND\s+tag\.id\s+IN\s+%s\b", "", converted, flags=re.IGNORECASE
        )
        converted = re.sub(
            r"\btag\.id\s+IN\s+%s\b", "TRUE", converted, flags=re.IGNORECASE
        )

        # Remove state filter (POS uses different states)
        converted = re.sub(
            r"\bAND\s+s\.state\s*=\s*'sale'\b", "", converted, flags=re.IGNORECASE
        )
        converted = re.sub(
            r"\bs\.state\s*=\s*'sale'\b", "TRUE", converted, flags=re.IGNORECASE
        )

        # Remove invoice_status fields (POS doesn't have invoice status)
        converted = re.sub(r"\bs\.invoice_status\b", "TRUE", converted)
        converted = re.sub(r"\bl\.invoice_status\b", "TRUE", converted)

        # Clean up any resulting double ANDs or trailing AND
        converted = re.sub(r"\bAND\s+AND\b", "AND", converted, flags=re.IGNORECASE)
        converted = re.sub(r"\s+", " ", converted)  # Normalize whitespace
        converted = re.sub(r"\s+AND\s*$", "", converted)  # Remove trailing AND

        # If the clause starts with AND, keep that (the caller expects it), otherwise prefix AND
        converted = converted.strip()
        if converted and not converted.lower().startswith("and"):
            converted = "AND " + converted

        return converted
