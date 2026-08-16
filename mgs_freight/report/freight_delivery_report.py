from odoo import models, fields, api

class FreightDeliveryReport(models.AbstractModel):
    _name = 'report.mgs_freight.delivery_report_template'
    _description = 'Delivery Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        delivery_id = data.get('delivery_id')
        customer_id = data.get('customer_id')
        summary = data.get('summary')
        add_customer = data.get('add_customer')
        status_type = data.get('status_type')

        Delivery = self.env['freight.delivery']
        deliveries = Delivery.browse(delivery_id) if delivery_id else Delivery

        if customer_id and not delivery_id:
            if status_type == "bill":
                
                delivery_lines = self.env['freight.delivery.line'].search([
                    ('receipt_id.customer_id', '=', customer_id),
                    ('delivery_id.state', 'in', [ 'bill'])
                ])
            elif status_type == "confirm":
                delivery_lines = self.env['freight.delivery.line'].search([
                    ('receipt_id.customer_id', '=', customer_id),
                    ('delivery_id.state', 'in', [ 'confirm'])
                ])
            else :
                delivery_lines = self.env['freight.delivery.line'].search([
                    ('receipt_id.customer_id', '=', customer_id),
                    ('delivery_id.state', 'in', [ 'bill','confirm'])
                ])
                
            deliveries = delivery_lines.mapped('delivery_id')

        elif delivery_id:
            deliveries = Delivery.browse(delivery_id)

        delivery_lines = deliveries.mapped('delivery_ids')
        if customer_id:
            delivery_lines = delivery_lines.filtered(lambda l: l.receipt_id.customer_id.id == customer_id)

        customer_name = self.env['res.partner'].browse(customer_id).name if customer_id else False

        if summary:
            total_ctn = sum(delivery_lines.mapped('ctn'))
            total_cbm = sum(delivery_lines.mapped('cbm'))

            return {
                'doc_ids': deliveries.ids,
                'doc_model': 'freight.delivery',
                'docs': deliveries,
                'delivery_lines': delivery_lines,
                'total_ctn': round(total_ctn, 2),
                'total_cbm': round(total_cbm, 2),
                'customer_name': customer_name,
                'summary': summary,
                'add_customer': add_customer,
                'delivery_id': delivery_id,
            }

        else:
            detailed_lines = delivery_lines.mapped('product_ids')
            total_ctn = sum(detailed_lines.mapped('ctn'))
            total_pcs = sum(detailed_lines.mapped('pcs'))
            total_quantities = sum(detailed_lines.mapped('t_qty'))
            total_cbm = sum(detailed_lines.mapped('total_cbm'))

            return {
                'doc_ids': deliveries.ids,
                'doc_model': 'freight.delivery',
                'docs': deliveries,
                'delivery_lines': detailed_lines,
                'customer_name': customer_name,
                'summary': summary,
                'add_customer': add_customer,
                'total_ctn': total_ctn,
                'total_pcs': total_pcs,
                'total_quantities': total_quantities,
                'total_cbm': total_cbm,
                'delivery_id': delivery_id,
            }
