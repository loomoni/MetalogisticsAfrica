from odoo import fields, models, api, _


class HrExpensesInherit(models.Model):
    _inherit = 'hr.expense'

    file_number = fields.Char(string="File Number")


class HrExpensesSheetInherit(models.Model):
    _inherit = 'hr.expense.sheet'

    # @api.multi
    # def action_submit_sheet(self):
    #     res = super(HrExpensesSheetInherit, self).action_submit_sheet()
    #
    #     mail_template = self.env.ref('custom_expenses.country_manager_notification_email')
    #     mail_template.send_mail(self.id, force_send=True)
    #
    #     return res
