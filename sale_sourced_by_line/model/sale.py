# -*- coding: utf-8 -*-
# Copyright 2013-2014 Camptocamp SA - Guewen Baconnier
# © 2016 Eficent Business and IT Consulting Services S.L.
# © 2016 Serpent Consulting Services Pvt. Ltd.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def _prepare_procurement_group_by_line(self, line):
        vals = super()._prepare_procurement_group_by_line(line)
        # for compatibility with sale_quotation_sourcing
        if line._get_procurement_group_key()[0] == 10:
            if line.warehouse_id:
                vals["name"] += "/" + line.warehouse_id.name
        return vals

    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Default Warehouse",

        help="If no source warehouse is selected on line, "
        "this warehouse is used as default. ",
    )
    # states={"draft": [("readonly", False)], "sent": [("readonly", False)]},


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Source Warehouse",
        readonly=False,
        related='',
        store=True,
        compute_sudo=False,
        help="If a source warehouse is selected, it will be used to define the route. "
             "Otherwise, it will get the warehouse of the sale order.",
    )

    def _compute_qty_at_date(self):
        save_wh = {rec: rec.warehouse_id for rec in self}
        result = super()._compute_qty_at_date()
        for rec in self:
            rec.warehouse_id = save_wh.get(rec, False)
        return result

    def _prepare_procurement_values(self):
        values = super()._prepare_procurement_values()
        self.ensure_one()
        if self.warehouse_id:
            values["warehouse_id"] = self.warehouse_id
        return values

    def _get_procurement_group_key(self):
        priority = 10
        key = super()._get_procurement_group_key()
        if key[0] >= priority:
            return key
        warehouse = self.warehouse_id or self.order_id.warehouse_id
        return priority, warehouse.id
