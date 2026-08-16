from odoo import models, fields, api

class FreightReceiptReport(models.AbstractModel):
    _name = 'report.mgs_freight.receipt_report_template'
    _description = 'Freight Receipt Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        customer_id = data.get('customer_id')
        customer = self.env['res.partner'].browse(data.get('customer_id'))
        customer_name = customer.name
        
        domain = []
        
        if customer_id:
            domain.append(('receipt_id.customer_id.id', '=', customer_id))
        
        if date_from:
            domain.append(('receiver_date', '>=', date_from))
        
        if date_to:
            domain.append(('receiver_date', '<=', date_to))
        
        receipt_lines = self.env['freight.receipt.line'].search(domain)
        # Calculate totals
        total_ctn = round(sum(receipt_lines.mapped('ctn')), 2)
        total_pcs = round(sum(receipt_lines.mapped('pcs')), 2)
        total_t_qty = round(sum(receipt_lines.mapped('t_qty')), 2)
        total_cbm = round(sum(receipt_lines.mapped('cbm')), 2)
        total_t_cmb = round(sum(receipt_lines.mapped('t_cmb')), 2)
        total_weight_kg = round(sum(receipt_lines.mapped('weight_kg')), 2)
        total_t_weight = round(sum(receipt_lines.mapped('t_weight')), 2)
        return {
            'doc_ids': docids,
            'doc_model': 'freight.receipt.wizard',
            'docs': data,  
            'receipt_lines': receipt_lines,
            "customer_name":customer_name,
            'total_ctn': total_ctn,
            'total_pcs': total_pcs,
            'total_t_qty': total_t_qty,
            'total_cbm': total_cbm,
            'total_t_cmb': total_t_cmb,
            'total_weight_kg': total_weight_kg,
            'total_t_weight': total_t_weight
        }

        
       
        
    
    
    