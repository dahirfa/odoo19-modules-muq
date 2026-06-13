from odoo import models, api, fields, _
from odoo.exceptions import UserError
import random

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    barcode_before_converted_to_gtin14 = fields.Char(
        string='Barcode Before Conversion',
        readonly=True
    )

    def _is_valid_gtin14(self, barcode):
        if not barcode or len(barcode) != 14 or not barcode.isdigit():
            return False
        total = sum(
            int(d) * (3 if i % 2 == 0 else 1)
            for i, d in enumerate(reversed(barcode[:-1]))
        )
        return (10 - (total % 10)) % 10 == int(barcode[-1])

    def _generate_unique_gtin14(self, exclude_id=None, max_attempts=1000):
        for _ in range(max_attempts):
            payload = str(random.randint(0, 9999999999999)).zfill(13)
            total = sum(
                int(d) * (3 if i % 2 == 0 else 1)
                for i, d in enumerate(reversed(payload))
            )
            check_digit = (10 - (total % 10)) % 10
            candidate = payload + str(check_digit)
            domain = [('barcode', '=', candidate)]
            if exclude_id:
                domain.append(('id', '!=', exclude_id))
            if not self.env[self._name].sudo().search(domain, limit=1):
                return candidate
        raise UserError(_("Unable to generate unique GTIN-14 after %d attempts") % max_attempts)

    def _fix_barcode_length(self):
        for rec in self:
            if not rec.barcode or rec._is_valid_gtin14(rec.barcode):
                continue
            old_barcode = rec.barcode
            rec.barcode_before_converted_to_gtin14 = old_barcode
            rec.barcode = rec._generate_unique_gtin14(exclude_id=rec.id)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.filtered('barcode')._fix_barcode_length()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'barcode' in vals and not self.env.context.get('_fixing_barcode'):
            to_fix = self.filtered(
                lambda r: r.barcode and not r._is_valid_gtin14(r.barcode)
            )
            if to_fix:
                to_fix.with_context(_fixing_barcode=True)._fix_barcode_length()
        return res