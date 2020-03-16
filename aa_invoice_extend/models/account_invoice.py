# -*- coding: utf-8 -*-
##############################################################################
#
#    An Aifas Alliance Odoo Module
#
#    Copyright (C) 2020-TODAY Aifas Alliance (https://www.linkedin.com/company/aifas-alliance).
#    Author: Aifas Alliance (https://www.linkedin.com/company/aifas-alliance).
#    Contact : allianceaifas@gmail.com
#
#    you can modify it under the terms of the GNU Affero
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (AGPL v3) along with this program.
#    If not, see <https://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountInvoiceLine(models.Model):
    _inherit = 'account.move.line'

    price_subtotal_tax = fields.Float(compute='_compute_price_tax_line', string='Total Inc VAT',
                                      store=True)

    @api.depends('price_unit', 'discount', 'tax_ids', 'quantity',
                 'product_id', 'move_id.partner_id', 'move_id.currency_id')
    def _compute_price_tax_line(self):
        for rec in self:
            price = rec.price_unit * (1 - (rec.discount or 0.0) / 100.0)
            taxes = rec.tax_ids.compute_all(price, rec.currency_id, rec.quantity, product=rec.product_id,
                                            partner=rec.move_id.partner_id)
            rec.price_subtotal_tax = taxes['total_included']

            if rec.move_id:
                rec.price_subtotal_tax = rec.move_id.currency_id.round(rec.price_subtotal_tax)


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    remarks = fields.Text("Remarks")
    supplier_ref = fields.Char(string="Supplier Ref")
    supplier_ref_date = fields.Date(string="Supplier Ref Date")
    buyer_order_no = fields.Char(string="Buyer's Order No")
    buyer_order_date = fields.Date(string="Buyer's Order Date")
    dispatch_doc_no = fields.Many2one('stock.picking', string="Despatch Doc No",
                                      domain="[('picking_type_code', '=', 'outgoing')]")
    dispatch_doc_date = fields.Date(string="Despatch Doc Date")
    dispatch_through = fields.Char(string="Despatch Through")
    dispatch_destination = fields.Char(string="Despatch Destination")

    @api.onchange('dispatch_doc_no')
    def _onchange_dispatch_doc_no(self):
        if self.dispatch_doc_no and self.dispatch_doc_no.scheduled_date:
            self.dispatch_doc_date = self.dispatch_doc_no.scheduled_date

