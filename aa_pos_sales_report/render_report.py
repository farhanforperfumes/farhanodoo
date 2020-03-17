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
import logging
from datetime import timedelta
from functools import partial

import psycopg2
import pytz
from itertools import groupby
from operator import itemgetter
from odoo import api, fields, models, tools, _
from odoo.tools import float_is_zero
from odoo.exceptions import UserError
from odoo.http import request
from odoo.osv.expression import AND
import base64


class POSSalesProfitReport(models.AbstractModel):

    _name = 'report.aa_pos_sales_report.report_profit_saledetails'
    _description = 'POS Sales Profit Report'


    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, pos = False, session_ids=False):
        """ Serialise the orders of the requested time period, configs and sessions.
        :param date_start: The dateTime to start, default today 00:00:00.
        :type date_start: str.
        :param date_stop: The dateTime to stop, default date_start + 23:59:59.
        :type date_stop: str.
        :param config_ids: Pos Config id's to include.
        :type config_ids: list of numbers.
        :param session_ids: Pos Config id's to include.
        :type session_ids: list of numbers.
        :returns: dict -- Serialised sales.
        """
        domain = [('state', 'in', ['paid','invoiced','done'])]
        branches = ''
        for each_pos in pos:
            branches += each_pos.name

        if (session_ids):
            domain = AND([domain, [('session_id', 'in', session_ids)]])
        else:
            if date_start:
                date_start = fields.Datetime.from_string(date_start)
            else:
                # start by default today 00:00:00
                user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
                today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
                date_start = today.astimezone(pytz.timezone('UTC'))

            if date_stop:
                date_stop = fields.Datetime.from_string(date_stop)
                # avoid a date_stop smaller than date_start
                if (date_stop < date_start):
                    date_stop = date_start + timedelta(days=1, seconds=-1)
            else:
                # stop by default today 23:59:59
                date_stop = date_start + timedelta(days=1, seconds=-1)

            domain = AND([domain,
                [('date_order', '>=', fields.Datetime.to_string(date_start)),
                ('date_order', '<=', fields.Datetime.to_string(date_stop))]
            ])

            if config_ids:
                domain = AND([domain, [('config_id', 'in', config_ids)]])
        orders = self.env['pos.order'].search(domain)

        user_currency = self.env.company.currency_id

        total = 0.0
        products_sold = {}
        taxes = {}
        lines_list = []
        for order in orders:
            if user_currency != order.pricelist_id.currency_id:
                total += order.pricelist_id.currency_id._convert(
                    order.amount_total, user_currency, order.company_id, order.date_order or fields.Date.today())
            else:
                total += order.amount_total
            currency = order.session_id.currency_id

            for line in order.lines:
                lines_list.append(line.id)
                key = (line.product_id, line.price_unit, line.discount)
                products_sold.setdefault(key, 0.0)
                products_sold[key] += line.qty

                if line.tax_ids_after_fiscal_position:
                    line_taxes = line.tax_ids_after_fiscal_position.compute_all(
                        line.price_unit * (1 - (line.discount or 0.0) / 100.0), currency, line.qty,
                        product=line.product_id, partner=line.order_id.partner_id or False)
                    for tax in line_taxes['taxes']:
                        taxes.setdefault(tax['id'], {'name': tax['name'], 'tax_amount': 0.0, 'base_amount': 0.0})
                        taxes[tax['id']]['tax_amount'] += tax['amount']
                        taxes[tax['id']]['base_amount'] += tax['base']
                else:
                    taxes.setdefault(0, {'name': _('No Taxes'), 'tax_amount': 0.0, 'base_amount': 0.0})
                    taxes[0]['base_amount'] += line.price_subtotal_incl
        if lines_list:
            self.env.cr.execute("""
                                            SELECT line.id,line.product_id,line.qty,line.price_unit,line.discount,
                                            line.price_subtotal, ROUND(line.price_subtotal_incl, 3 ) AS tax_price_tot
                                            FROM pos_order_line AS line
                                            WHERE line.id IN %s
                                        """, (tuple(lines_list),))
        all_lines = self.env.cr.dictfetchall()

        for one_l in all_lines:
            domain = [('id', '=', one_l['id'])]
            line_obj = self.env['pos.order.line'].search(domain)

            line_tax__list = []
            for line_tax_id in line_obj.tax_ids_after_fiscal_position:
                line_tax__list.append(line_tax_id.name)

            one_l['tax'] = line_tax__list
            one_l['product_cost'] = line_obj.product_id.standard_price * line_obj.qty
            one_l['barcode'] = line_obj.product_id.barcode or '--'
            one_l['product_name'] = line_obj.product_id.name or '--'

            if one_l['discount'] == 0:
                one_l['profit'] = one_l['price_subtotal'] - one_l['product_cost']

        res = {}
        for item in all_lines:
            res.setdefault(item['product_id'], []).append(item)

        dict_keys = res.keys()
        pid = False
        product_bar = False
        product_name = False
        sum_qty = 0
        sum_price_subtotal = 0
        sum_product_cost = 0
        sum_tax_price_tot = 0
        sum_tax = []
        sum_profit = 0
        vat_amnt = 0
        product_data = []

        for d_key in dict_keys:
            for lines in res[d_key]:
                pid = lines['id']
                product_name = lines['product_name']
                product_bar = lines['barcode']
                sum_qty += lines['qty']
                sum_price_subtotal += lines['price_subtotal']
                sum_product_cost += lines['product_cost']
                sum_tax_price_tot += lines['tax_price_tot']
                sum_profit += lines['profit']
                vat_amnt += user_currency.round(lines['tax_price_tot'] - lines['price_subtotal'])

                for each_tax in lines['tax']:
                    if each_tax not in sum_tax:
                        sum_tax.append(each_tax)
            str_tax = ''
            if sum_tax:
                str_tax = ' '.join([str(elem) for elem in sum_tax])

            data_pack = {
                'id': pid,
                'product_name': product_name,
                'product_bar': product_bar,
                'sum_qty': sum_qty,
                'sum_price_subtotal': sum_price_subtotal,
                'sum_product_cost': sum_product_cost,
                'sum_tax_price_tot': sum_tax_price_tot,
                'sum_tax': str_tax,
                'vat_amnt': vat_amnt,
                'sum_profit': sum_profit
            }
            pid = False
            product_bar = False
            product_name = False
            sum_qty = 0
            sum_price_subtotal = 0
            sum_product_cost = 0
            sum_tax_price_tot = 0
            sum_tax = []
            sum_profit = 0
            vat_amnt = 0
            product_data.append(data_pack)
        payment_ids = self.env["pos.payment"].search([('pos_order_id', 'in', orders.ids)]).ids

        if payment_ids:
            self.env.cr.execute("""
                                SELECT method.name, sum(amount) total
                                FROM pos_payment AS payment,
                                     pos_payment_method AS method
                                WHERE payment.payment_method_id = method.id
                                    AND payment.id IN %s
                                GROUP BY method.name
                            """, (tuple(payment_ids),))
            payments = self.env.cr.dictfetchall()

        else:
            payments = []
        complete_dict = {
            'currency_precision': user_currency.decimal_places,
            'total_paid': user_currency.round(total),
            'payments': payments,
            'company_name': self.env.company.name,
            'branches': branches,
            'taxes': list(taxes.values()),
            'lines': product_data
        }
        return complete_dict

    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        configs = self.env['pos.config'].browse(data['config_ids'])
        data.update(self.get_sale_details(data['date_start'], data['date_stop'], configs.ids, configs))
        return data
