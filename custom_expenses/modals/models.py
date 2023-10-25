from odoo import fields, models, api, _


class HrExpensesInherit(models.Model):
    _inherit = 'hr.expense'

    file_number = fields.Char(string="File Number")
