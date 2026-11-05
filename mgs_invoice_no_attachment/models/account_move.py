from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _generate_and_send(self, force_synchronous=True, allow_fallback_pdf=True, **custom_settings):
        if self.env.context.get('mgs_pos_skip_invoice_documents'):
            # The PDF can be rendered again on demand, an electronic document cannot be skipped.
            move_send = self.env['account.move.send']
            self = self.filtered(
                lambda move: move_send._get_default_extra_edis(move)
                or move_send._get_default_invoice_edi_format(
                    move, sending_methods=move_send._get_default_sending_methods(move),
                )
            )
        return super()._generate_and_send(
            force_synchronous=force_synchronous,
            allow_fallback_pdf=allow_fallback_pdf,
            **custom_settings,
        )

    def _mgs_is_pos_invoice_without_stored_pdf(self):
        self.ensure_one()
        move = self.sudo()
        return (
            move.state == 'posted'
            and move.is_sale_document()
            and not move.invoice_pdf_report_id
            and bool(move.pos_order_ids)
        )

    def _get_invoice_pdf_proforma(self):
        # Core falls back on a PROFORMA when no PDF is stored, which is wrong for a posted POS invoice.
        self.ensure_one()
        if not self._mgs_is_pos_invoice_without_stored_pdf():
            return super()._get_invoice_pdf_proforma()
        report = self.env['account.move.send']._get_default_pdf_report_id(self)
        report_model = self.env['ir.actions.report']
        content, report_type = report_model._pre_render_qweb_pdf(report.report_name, self.ids)
        content_by_id = report_model._get_splitted_report(report.report_name, content, report_type)
        return {
            'filename': self._get_invoice_report_filename(report=report),
            'filetype': 'pdf',
            'content': content_by_id[self.id],
        }
