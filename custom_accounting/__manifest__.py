# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Custom Accounting',
    'version': '12.0.0.0.0',
    'category': 'Accounting',
    'summary': 'Custom Accounting and Invoice',
    'sequence': '8',
    'author': 'Loomoni Morwo',
    'website': 'http://loomoni.com',
    'depends': ['account'],
    'demo': [],
    'data': [
        'reports/reports.xml',
        'reports/template.xml',
        'views/views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
}
