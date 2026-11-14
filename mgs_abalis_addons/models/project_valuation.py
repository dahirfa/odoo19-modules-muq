from odoo import models


class ProjectRentValuationMixin(models.AbstractModel):
    """Rent valuation shared by projects and subprojects.

    For a Rent valuation, only properties with a running (active) rent contract count:
    * Total Value of Project: sum of the prices of those properties;
    * Total Collection: rent paid on their running contracts;
    * Scope of Collection: rent invoiced but not yet paid on those contracts.
    Deposits and every other payment type are left out of the collections.
    """
    _name = 'mgs.project.rent.valuation.mixin'
    _description = 'Project Rent Valuation'

    def _get_rent_valuation_property_domain(self):
        """Domain of the rent properties valued by this (sub)project."""
        raise NotImplementedError()

    def _apply_rent_valuation(self):
        Property = self.env['property.details'].sudo()
        Tenancy = self.env['tenancy.details'].sudo()
        for rec in self.filtered(lambda r: r.sale_lease == 'rent'):
            properties = Property.search(rec._get_rent_valuation_property_domain())
            active_contracts = Tenancy.search([
                ('property_id', 'in', properties.ids),
                ('contract_type', '=', 'running_contract'),
            ])
            invoiced, paid = active_contracts._get_rent_collection()
            rec.total_values = sum(active_contracts.property_id.mapped('price'))
            rec.total_collection = paid
            rec.scope_of_collection = invoiced - paid


class PropertyProject(models.Model):
    _name = 'property.project'
    _inherit = ['property.project', 'mgs.project.rent.valuation.mixin']

    def _get_rent_valuation_property_domain(self):
        self.ensure_one()
        domain = [('property_project_id', '=', self.id), ('sale_lease', '=', 'for_tenancy')]
        if self.is_sub_project:
            domain.append(('subproject_id', 'in', self.sub_project_ids.ids))
        return domain

    def _compute_properties_statics(self):
        super()._compute_properties_statics()
        self._apply_rent_valuation()


class PropertySubProject(models.Model):
    _name = 'property.sub.project'
    _inherit = ['property.sub.project', 'mgs.project.rent.valuation.mixin']

    def _get_rent_valuation_property_domain(self):
        self.ensure_one()
        return [('subproject_id', '=', self.id), ('sale_lease', '=', 'for_tenancy')]

    def compute_properties_statics(self):
        super().compute_properties_statics()
        self._apply_rent_valuation()
