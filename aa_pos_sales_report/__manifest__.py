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
{
    'name': "AA : POS Sales Profit Report",
    'version': "13.0.0.2",
    'summary': "",
    'category': 'Point Of Sale',
    "license": "AGPL-3",
    'description': """
    """,
    'author': "Nilmar Shereef",
    'website': "https://www.linkedin.com/company/aifas-alliance",
    'depends': ['base', 'point_of_sale'],
    'qweb': ['static/src/xml/postickett.xml'],

    'data': [
        'wizard/pos_profit_details.xml',
        'reports/pos_report.xml',
        'reports/pos_session_report_template.xml'
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
