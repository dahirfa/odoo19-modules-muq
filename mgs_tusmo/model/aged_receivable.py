from odoo import models

class AgedReceivableReportHandler(models.AbstractModel):
    _inherit = "account.aged.receivable.report.handler"

    def _aged_partner_report_custom_engine_common(
        self,
        options,
        internal_type,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
    ):
        res = super()._aged_partner_report_custom_engine_common(
            options,
            internal_type,
            current_groupby,
            next_groupby,
            offset=offset,
            limit=limit,
        )

        # Total line
        if not current_groupby:
            res["phone"] = ""
            return res

        new_res = []

        for grouping_key, values in res:
            values = dict(values)

            # Show phone only on the partner row
            if current_groupby == "partner_id":
                partner = self.env["res.partner"].browse(grouping_key)
                values["phone"] = partner.phone or ""
            else:
                # Invoice / Journal Item rows
                values["phone"] = ""

            new_res.append((grouping_key, values))

        return new_res