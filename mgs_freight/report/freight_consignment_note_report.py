from odoo import api, fields, models
from odoo.exceptions import UserError


class FreightConsignmentNoteReport(models.AbstractModel):
    _name = 'report.mgs_freight.consignment_note_template'
    _description = 'Freight Shipping Consignment Note'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        if not data.get('date'):
            raise UserError(self.env._(
                "Print the consignment note from the Print Receipt button on the receipt."
            ))
        date = fields.Date.to_date(data['date'])
        receipts = self.env['freight.receipts'].browse(data.get('receipt_ids') or docids)
        if not receipts:
            raise UserError(self.env._("No receipt was selected to print."))

        shipping_labels = dict(
            receipts._fields['shipping_type']._description_selection(self.env)
        )
        notes = []
        for receipt in receipts:
            lines = receipt.freight_receipt_ids.filtered(
                lambda line: line.receiver_date == date
            ).sorted('id')
            notes.append({
                'receipt': receipt,
                'shipping_label': shipping_labels.get(receipt.shipping_type, ''),
                'lines': lines,
                'total_pcs': sum(lines.mapped('ctn')),
                'total_weight': sum(lines.mapped('t_weight')),
                'total_cbm': sum(lines.mapped('t_cmb')),
            })

        return {
            'doc_ids': receipts.ids,
            'doc_model': 'freight.receipts',
            'docs': receipts,
            'notes': notes,
            'date': date,
        }
