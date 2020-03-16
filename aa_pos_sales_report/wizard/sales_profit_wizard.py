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


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    type = fields.Selection([
        ('consu', 'Consumable'),
        ('product', 'Storable Product'),
        ('service', 'Service')], string='Product Type', default='product', required=True,
        help='A storable product is a product for which you manage stock. The Inventory app has to be installed.\n'
             'A consumable product is a product for which stock is not managed.\n'
             'A service is a non-material product you provide.')


class PosProfitWizard(models.TransientModel):
    _name = 'pos.profit.wizard'
    _description = 'Point of Sale Profit Report'

    def _default_start_date(self):
        """ Find the earliest start_date of the latests sessions """
        # restrict to configs available to the user
        config_ids = self.env['pos.config'].search([]).ids
        # exclude configs has not been opened for 2 days
        self.env.cr.execute("""
            SELECT
            max(start_at) as start,
            config_id
            FROM pos_session
            WHERE config_id = ANY(%s)
            AND start_at > (NOW() - INTERVAL '2 DAYS')
            GROUP BY config_id
        """, (config_ids,))
        latest_start_dates = [res['start'] for res in self.env.cr.dictfetchall()]
        # earliest of the latest sessions
        return latest_start_dates and min(latest_start_dates) or fields.Datetime.now()

    start_date = fields.Datetime(required=True, default=_default_start_date)
    end_date = fields.Datetime(required=True, default=fields.Datetime.now)
    pos_config_ids = fields.Many2many('pos.config', 'pos_profit_configs',
        default=lambda s: s.env['pos.config'].search([]))

    @api.onchange('start_date')
    def _onchange_start_date(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            self.end_date = self.start_date

    @api.onchange('end_date')
    def _onchange_end_date(self):
        if self.end_date and self.end_date < self.start_date:
            self.start_date = self.end_date

    def generate_report(self):
        if (not self.env.company.logo):
            raise UserError(_("You have to set a logo or a layout for your company."))
        elif (not self.env.company.external_report_layout_id):
            raise UserError(_("You have to set your reports's header and footer layout."))
        data = {'date_start': self.start_date, 'date_stop': self.end_date, 'config_ids': self.pos_config_ids.ids}
        return self.env.ref('aa_pos_sales_report.aa_sale_profit_report').report_action([], data=data)