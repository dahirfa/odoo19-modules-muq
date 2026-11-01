from odoo import api, models

PROPERTY_TYPES = ['land', 'residential', 'commercial', 'industrial']


class PropertyDetails(models.Model):
    _inherit = 'property.details'

    @api.model
    def get_property_stats(self, landlord_ids=None):
        """Dashboard statistics, optionally restricted to the given landlords.

        Without landlords the original computation is used unchanged. With
        landlords, every value returned by the original method is computed on
        the records of those landlords only, plus ``mgs_filter_ids`` used by
        the dashboard to open the matching records from a card.
        """
        landlord_ids = [int(landlord_id) for landlord_id in landlord_ids or []]
        if not landlord_ids:
            return super().get_property_stats()
        return self._mgs_get_landlord_property_stats(landlord_ids)

    def _mgs_get_landlord_property_stats(self, landlord_ids):
        """Same keys and value formats as ``get_property_stats``, filtered by landlord"""
        company_domain = [('company_id', 'in', self.env.companies.ids)]
        landlord_domain = [('landlord_id', 'in', landlord_ids)]
        property_domain = company_domain + landlord_domain
        tenancy_domain = company_domain + [('property_landlord_id', 'in', landlord_ids)]
        rent_invoice_domain = company_domain + landlord_domain
        sale_domain = company_domain + landlord_domain
        sale_move_domain = company_domain + [('sold_id.landlord_id', 'in', landlord_ids)]

        # Property Stages & Types
        property = self.env['property.details']
        property_sudo = property.sudo()
        stage_counts = {
            stage: property_sudo.search_count([('stage', '=', stage)] + property_domain)
            for stage in ['available', 'booked', 'on_lease', 'sale', 'sold']
        }
        type_counts = [
            property_sudo.search_count([('type', '=', property_type)] + property_domain)
            for property_type in PROPERTY_TYPES
        ]
        property_type = [['Land', 'Residential', 'Commercial', 'Industrial'], type_counts]
        property_stage = [
            ['Available Properties', 'Sold Properties', 'Booked Properties', 'On Sale', 'On Lease'],
            [stage_counts['available'], stage_counts['sold'], stage_counts['booked'],
             stage_counts['sale'], stage_counts['on_lease']]]
        currency_symbol = self.env.company.currency_id.symbol

        # Rent Contract
        rent_contract = self.env['tenancy.details'].sudo()
        contract_counts = {
            contract_type: rent_contract.search_count(
                [('contract_type', '=', contract_type)] + tenancy_domain)
            for contract_type in ['new_contract', 'running_contract', 'expire_contract',
                                  'close_contract']
        }
        extend_contract = rent_contract.search_count([('is_extended', '=', True)] + tenancy_domain)
        full_tenancy_total = sum(self.env['rent.invoice'].search(
            ['|', ('type', '=', 'rent'), ('type', '=', 'full_rent')] + rent_invoice_domain).mapped(
            'rent_invoice_id').mapped('amount_total'))
        pending_invoice = self.env['rent.invoice'].search_count(
            [('payment_state', '=', 'not_paid')] + rent_invoice_domain)

        # Sale Contract
        sale_contract = self.env['property.vendor'].sudo()
        booked = sale_contract.search_count([('stage', '=', 'booked')] + sale_domain)
        sale_sold = sale_contract.search_count([('stage', '=', 'sold')] + sale_domain)
        refund = sale_contract.search_count([('stage', '=', 'refund')] + sale_domain)
        sold_total = sum(
            sale_contract.search([('stage', '=', 'sold')] + sale_domain).mapped('sale_price'))
        pending_invoice_sale = self.env['account.move'].search_count(
            [('sold_id', '!=', False), ('payment_state', '=', 'not_paid')] + sale_move_domain)

        # Region, Project, Sub Project, Properties
        projects = self.env['property.project'].search(company_domain + landlord_domain)
        subprojects = self.env['property.sub.project'].search(company_domain + landlord_domain)
        properties = property.search(property_domain)
        regions = properties.region_id | projects.region_id | subprojects.region_id

        # Customer & Landlord
        contract_partners = (rent_contract.search(tenancy_domain).tenancy_id
                             | sale_contract.search(sale_domain).customer_id)
        customers = contract_partners.filtered(lambda partner: partner.user_type == 'customer')
        landlord_count = self.env['res.partner'].sudo().search_count(
            [('id', 'in', landlord_ids), ('user_type', '=', 'landlord')])

        return {
            # Property
            'avail_property': stage_counts['available'],
            'booked_property': stage_counts['booked'],
            'lease_property': stage_counts['on_lease'],
            'sale_property': stage_counts['sale'],
            'sold_property': stage_counts['sold'],
            # Rent Contract
            'draft_contract': contract_counts['new_contract'],
            'running_contract': contract_counts['running_contract'],
            'expire_contract': contract_counts['expire_contract'],
            'extend_contract': extend_contract,
            'close_contract': contract_counts['close_contract'],
            'pending_invoice': pending_invoice,
            'rent_total': str(
                round(full_tenancy_total, 2)) + ' ' + currency_symbol if currency_symbol else "",
            # Sale Contract
            'booked': booked,
            'sale_sold': sale_sold,
            'refund': refund,
            'sold_total': str(
                round(sold_total, 2)) + ' ' + currency_symbol if currency_symbol else "",
            'pending_invoice_sale': pending_invoice_sale,
            # Customer & Landlord
            'customer_count': len(customers),
            'landlord_count': landlord_count,
            # Region, Project, Sub Project, Properties
            'region_count': len(regions),
            'project_count': len(projects),
            'subproject_count': len(subprojects),
            'total_property': len(properties),
            # Graph
            'property_type': property_type,
            'property_stage': property_stage,
            'property_map_data': self._mgs_get_property_map_data(property_domain),
            'due_paid_amount': self._mgs_due_paid_amount(sale_move_domain, rent_invoice_domain),
            'tenancy_top_broker': self._mgs_get_top_broker(tenancy_domain, sale_domain),
            # Records behind the cards that are not filtered by a landlord field
            'mgs_filter_ids': {
                'region_ids': regions.ids,
                'customer_ids': customers.ids,
            },
        }

    def _mgs_get_top_broker(self, tenancy_domain, sale_domain):
        """Landlord filtered version of ``get_top_broker``"""
        broker_tenancy = {}
        broker_sold = {}
        for broker, count in self.env['tenancy.details']._read_group(
                [('is_any_broker', '=', True)] + tenancy_domain,
                ['broker_id'],
                ['__count'], limit=5):
            if broker:
                broker_tenancy[broker.sudo().name] = count
        for broker, count in self.env['property.vendor']._read_group(
                [('is_any_broker', '=', True), ('stage', '=', 'sold')] + sale_domain,
                ['broker_id'],
                ['__count'], limit=5):
            if broker:
                broker_sold[broker.sudo().name] = count

        brokers_tenancy_list = dict(
            sorted(broker_tenancy.items(), key=lambda x: x[1], reverse=True))
        broker_sold_list = dict(
            sorted(broker_sold.items(), key=lambda x: x[1], reverse=True))
        return [list(brokers_tenancy_list.keys()), list(brokers_tenancy_list.values()),
                list(broker_sold_list.keys()),
                list(broker_sold_list.values())]

    def _mgs_due_paid_amount(self, sale_move_domain, rent_invoice_domain):
        """Landlord filtered version of ``due_paid_amount``"""
        sold_moves = self.env['account.move'].sudo().search(
            [('sold_id', '!=', False), ('sold_id.stage', '=', 'sold')] + sale_move_domain)
        sold = {
            'Due': sum(sold_moves.filtered(
                lambda move: move.payment_state == 'not_paid').mapped('amount_total')),
            'Paid': sum(sold_moves.filtered(
                lambda move: move.payment_state == 'paid').mapped('amount_total')),
        }
        rent_invoices = self.env['rent.invoice'].sudo().search(rent_invoice_domain)
        tenancy = {
            'Due': sum(rec.rent_invoice_id.amount_total for rec in rent_invoices
                       if rec.payment_state == 'not_paid'),
            'Paid': sum(rec.rent_invoice_id.amount_total for rec in rent_invoices
                        if rec.payment_state == 'paid'),
        }
        return [list(sold.keys()), list(sold.values()), list(tenancy.keys()),
                list(tenancy.values())]

    def _mgs_get_property_map_data(self, property_domain):
        """Landlord filtered version of ``get_property_map_data``"""
        data = []
        properties = self.env['property.details'].sudo().search(property_domain)
        for prop in properties.filtered(lambda prop: prop.latitude and prop.longitude):
            address_parts = []
            if prop.street:
                address_parts.append(prop.street)
            if prop.city_id and prop.city_id.name:
                address_parts.append(prop.city_id.name)

            address_line = ", ".join(address_parts)
            name_line = prop.name or ""

            if address_line:
                line_length = max(len(name_line), len(address_line)) * 2
                title = f"{name_line}\n{'-' * line_length}\n{address_line}"
            else:
                title = name_line
            data.append({
                'title': title,
                'latitude': prop.latitude,
                'longitude': prop.longitude,
                'status': prop.stage,
            })
        return data
