import base64
import locale
from datetime import date
from io import BytesIO

import xlsxwriter
from dateutil.relativedelta import relativedelta
from docutils.parsers import null
from xlsxwriter.utility import xl_range

from odoo import fields, models, api, _
from odoo.tools import datetime


class AccountInvoiceInherit(models.Model):
    _inherit = 'account.invoice'
    _order = 'id DESC'

    file_no = fields.Char(string="File Number", states={'open': [('readonly', True)]}, )
    awb_bl = fields.Char(string="AWB/BL")
    tansad_no = fields.Char(string="TANSAD No")
    pkg_no = fields.Char(string="Pkg No")
    weight = fields.Char(string="weight")
    delivery_no = fields.Char(string="Delivery Note No.")
    # debt_number = fields.Char(string="Number", compute="debt_compute", store=True)
    # number = fields.Char(string="Number", store=True)
    # move_id = fields.Many2one(comodel_name='account.move', string="Account Move Name")
    #
    # # Define a computed field to set the report name dynamically
    # report_name = fields.Char(
    #     string="Report Name",
    #     compute='_compute_report_name',
    #     store=True
    # )
    #
    # @api.depends('type')
    # def _compute_report_name(self):
    #     for invoice in self:
    #
    #         # Set the string based on the type of the invoice and the presence of origin
    #         if invoice.type == 'out_invoice':
    #             invoice.report_name = 'Invoice: ' + (invoice.number or '')
    #         elif invoice.type == 'out_invoice' and invoice.origin:
    #             invoice.report_name = 'Debit Note: ' + (invoice.number or '')
    #         else:
    #             invoice.report_name = "Report"
    #
    # # Modify the report action to use the computed field
    # def print_custom_report(self):
    #     report_name = self.report_name  # Use the computed report name
    #     action = self.env.ref('custom_accounting.' + report_name, raise_if_not_found=False)
    #     if action:
    #         return action.report_action(self)
    #     else:
    #         return False
    #
    # @api.multi
    # def invoice_report_action(self):
    #     return self.print_custom_report()
    #
    # @api.onchange('number', 'origin')
    # @api.depends('number', 'origin')
    # def debt_compute(self):
    #     for record in self:
    #         if record.origin:
    #             numeric_origin = ''.join(filter(str.isdigit, record.origin))
    #             record.debt_number = f"MADN-{numeric_origin}"
    #             record.number = record.debt_number
    #             # if record.type == 'out_invoice':
    #             #     record.move_id.name = record.debt_number
    #             # break  # Add this line to exit the loop after processing one record
    #         else:
    #             record.debt_number = False
    #
    # @api.multi
    # def action_invoice_open(self):
    #     res = super(AccountInvoiceInherit, self).action_invoice_open()
    #
    #     # Continue with your custom code after the super call
    #     for invoice in self:
    #         if invoice.origin:
    #             invoice.number = invoice.debt_number
    #         else:
    #             invoice.number = invoice.move_id.name
    #     return res

    # @api.multi
    # def name_get(self):
    #     result = []
    #     for invoice in self:
    #         # Set the string based on the type of the invoice and the presence of origin
    #         if invoice.type == 'out_invoice':
    #             name = 'Invoice: ' + (invoice.number or '')
    #         elif invoice.type == 'out_invoice' and invoice.origin:
    #             name = 'Debit Note: ' + (invoice.number or '')
    #         else:
    #             name = invoice.number or ''
    #
    #         result.append((invoice.id, name))
    #     return result

    @api.model
    def company_info(self):
        company = self.env.user.company_id
        logo_data = base64.b64decode(company.logo)
        return {
            'name': company.name,
            'vat': company.vat,
            'vrn': company.company_registry,
            'street': company.street,
            'street2': company.street2,
            'phone': company.phone,
            'email': company.email,
            'website': company.website,
            'logo': BytesIO(logo_data)
        }

    @api.multi
    def print_delivery_note_action(self):
        return self.env.ref('custom_sale.delivery_note_print_pdf_id').report_action(self)

    def get_payment_dates(self):
        payment_dates = []
        for payment in self.payment_ids:
            if payment.payment_date:
                payment_dates.append(payment.payment_date)
        return payment_dates

    def get_payment_amount(self):
        payment_amount = []
        for payment in self.payment_ids:
            if payment.payment_date:
                payment_amount.append(payment.amount)
        return payment_amount

    def format_payment_amount(self, amount):
        return locale.format('%.2f', amount, grouping=True)


class TotalIncomeWizard(models.TransientModel):
    _name = 'total.income.report.wizard'

    customer_id = fields.Many2one('res.partner', string='Customer', required=False, domain="[('customer', '=', True)]")
    customer_name = fields.Integer(string='Customer name', related='customer_id.id')
    date_from = fields.Date(string='Date From', required=True,
                            default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date(string='Date To', required=True,
                          default=lambda self: fields.Date.to_string(
                              (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    state = fields.Selection([("draft", "Draft"), ("open", "Open"), ("paid", "Paid")])

    @api.multi
    def get_report(self):
        file_name = _('Total Income From ' + str(self.date_from) + ' - ' + str(self.date_to) + ' report.xlsx')
        fp = BytesIO()

        workbook = xlsxwriter.Workbook(fp)
        worksheet = workbook.add_worksheet('Income report')
        # Disable gridlines
        worksheet.hide_gridlines(2)  # 2 means 'both'

        heading_company_format = workbook.add_format({
            # 'bold': True,
            'font_size': 7,
            'font_name': 'Arial',
            # 'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        })
        heading_company_format.set_border()
        cell_title_text_format_contact = workbook.add_format({'align': 'left',
                                                              'bold': True,
                                                              'font_name': 'Calibri',
                                                              'size': 12,
                                                              'fg_color': '#FFCC00',
                                                              })
        cell_title_text_format_contact.set_border()
        cell_title_text_format = workbook.add_format({'align': 'center',
                                                      'bold': True,
                                                      'font_name': 'Calibri',
                                                      'size': 12,
                                                      'fg_color': '#FFCC00',
                                                      })
        cell_title_text_format.set_border()

        cell_body_text_format = workbook.add_format({'align': 'center',
                                                     'font_name': 'Calibri',
                                                     'size': 11,
                                                     })
        cell_body_text_format.set_border()
        cell_body_text_format_contact = workbook.add_format({'align': 'left',
                                                             'font_name': 'Calibri',
                                                             'size': 11,
                                                             })
        cell_body_text_format_contact.set_border()
        cell_body_number_format = workbook.add_format({'align': 'right',
                                                       'bold': False,
                                                       'size': 11,
                                                       'num_format': '#,###0.00'})
        cell_body_number_format.set_border()

        cell_result_body_number_format = workbook.add_format({'align': 'right',
                                                              'bold': True,
                                                              'size': 13,
                                                              'fg_color': '#FFCC00',
                                                              'num_format': '#,###0.00'})
        cell_result_body_number_format.set_border()

        worksheet.set_row(0, 25)

        worksheet.set_column('A:A', 27)
        worksheet.set_column('B:B', 16)
        worksheet.set_column('B:I', 16)

        if self.date_from and self.date_to:
            row = 0
            col = 0

            worksheet.write(row, 0, 'Contact Name', cell_title_text_format)
            worksheet.write(row, 1, 'Invoice Number', cell_title_text_format)
            worksheet.write(row, 2, 'Operator', cell_title_text_format)
            worksheet.write(row, 3, 'Invoice Date', cell_title_text_format)
            worksheet.write(row, 4, 'Due Date', cell_title_text_format)
            worksheet.write(row, 5, 'Tax Excluded', cell_title_text_format)
            worksheet.write(row, 6, 'Tax', cell_title_text_format)
            worksheet.write(row, 7, 'Total', cell_title_text_format)
            worksheet.write(row, 8, 'Amount Due', cell_title_text_format)
            worksheet.write(row, 9, 'Status', cell_title_text_format)

            all_customers_invoice = self.env['account.invoice'].sudo().search(
                [('date_invoice', '<=', self.date_to), ('date_invoice', '>=', self.date_from),
                 ('partner_id.customer', '=', True)])
            customer_invoice = self.env['account.invoice'].sudo().search([('partner_id', '=', self.customer_name),
                                                                          ('date_invoice', '<=', self.date_to),
                                                                          ('date_invoice', '>=', self.date_from),
                                                                          ('partner_id.customer', '=', True),
                                                                          ])
            state_invoice = self.env['account.invoice'].sudo().search([('state', '=', self.state),
                                                                       ('date_invoice', '<=', self.date_to),
                                                                       ('date_invoice', '>=', self.date_from),
                                                                       ('partner_id.customer', '=', True)])
            customer_and_state_invoice = self.env['account.invoice'].sudo().search([('state', '=', self.state),
                                                                                    ('partner_id', '=',
                                                                                     self.customer_name),
                                                                                    (
                                                                                        'date_invoice', '<=',
                                                                                        self.date_to),
                                                                                    ('date_invoice', '>=',
                                                                                     self.date_from),
                                                                                    ('partner_id.customer', '=', True)])

            if customer_and_state_invoice:
                for invoice in customer_and_state_invoice:
                    name = invoice.partner_id.name
                    if invoice.origin:
                        inv_number = invoice.number
                    else:
                        inv_number = invoice.number
                    sale_person = invoice.user_id.name
                    invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
                    due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
                    if invoice.origin:
                        amount_tax_excluded = 0 - invoice.amount_untaxed
                    else:
                        amount_tax_excluded = invoice.amount_untaxed
                    amount_tax = invoice.amount_tax
                    if invoice.origin:
                        total = 0 - invoice.amount_total
                    else:
                        total = invoice.amount_total
                    amount_due = invoice.residual
                    status = invoice.state

                    worksheet.write(row + 1, col, name or '', cell_body_text_format_contact)
                    worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 8, amount_due or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 9, status or '', cell_body_text_format)

                    row = row + 1

                worksheet.set_row(row + 1, 23)
                worksheet.write(row + 1, 5, f'=SUM({xl_range(1, col + 5, row, col + 5)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 6, f'=SUM({xl_range(1, col + 6, row, col + 6)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 7, f'=SUM({xl_range(1, col + 7, row, col + 7)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 8, f'=SUM({xl_range(1, col + 8, row, col + 8)})',
                                cell_result_body_number_format)

            elif customer_invoice:
                for invoice in customer_invoice:
                    name = invoice.partner_id.name
                    if invoice.origin:
                        inv_number = invoice.number
                    else:
                        inv_number = invoice.number
                    sale_person = invoice.user_id.name
                    invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
                    due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
                    if invoice.origin:
                        amount_tax_excluded = 0 - invoice.amount_untaxed
                    else:
                        amount_tax_excluded = invoice.amount_untaxed
                    amount_tax = invoice.amount_tax
                    if invoice.origin:
                        total = 0 - invoice.amount_total
                    else:
                        total = invoice.amount_total
                    amount_due = invoice.residual
                    status = invoice.state

                    worksheet.write(row + 1, col, name or '', cell_body_text_format_contact)
                    worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 8, amount_due or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 9, status or '', cell_body_text_format)

                    row = row + 1

                worksheet.set_row(row + 1, 23)
                worksheet.write(row + 1, 5, f'=SUM({xl_range(1, col + 5, row, col + 5)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 6, f'=SUM({xl_range(1, col + 6, row, col + 6)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 7, f'=SUM({xl_range(1, col + 7, row, col + 7)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 8, f'=SUM({xl_range(1, col + 8, row, col + 8)})',
                                cell_result_body_number_format)
            elif state_invoice:
                for invoice in state_invoice:
                    name = invoice.partner_id.name
                    if invoice.origin:
                        inv_number = invoice.number
                    else:
                        inv_number = invoice.number
                    sale_person = invoice.user_id.name
                    invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
                    due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
                    if invoice.origin:
                        amount_tax_excluded = 0 - invoice.amount_untaxed
                    else:
                        amount_tax_excluded = invoice.amount_untaxed
                    amount_tax = invoice.amount_tax
                    if invoice.origin:
                        total = 0 - invoice.amount_total
                    else:
                        total = invoice.amount_total
                    amount_due = invoice.residual
                    status = invoice.state

                    worksheet.write(row + 1, col, name or '', cell_body_text_format_contact)
                    worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 8, amount_due or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 9, status or '', cell_body_text_format)

                    row = row + 1

                worksheet.set_row(row + 1, 23)
                worksheet.write(row + 1, 5, f'=SUM({xl_range(1, col + 5, row, col + 5)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 6, f'=SUM({xl_range(1, col + 6, row, col + 6)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 7, f'=SUM({xl_range(1, col + 7, row, col + 7)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 8, f'=SUM({xl_range(1, col + 8, row, col + 8)})',
                                cell_result_body_number_format)

            else:
                for invoice in all_customers_invoice:
                    name = invoice.partner_id.name
                    if invoice.origin:
                        inv_number = invoice.number
                    else:
                        inv_number = invoice.number
                    sale_person = invoice.user_id.name
                    invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
                    due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
                    if invoice.origin:
                        amount_tax_excluded = 0 - invoice.amount_untaxed
                    else:
                        amount_tax_excluded = invoice.amount_untaxed
                    amount_tax = invoice.amount_tax
                    if invoice.origin:
                        total = 0 - invoice.amount_total
                    else:
                        total = invoice.amount_total
                    amount_due = invoice.residual
                    status = invoice.state

                    worksheet.write(row + 1, col, name or '', cell_body_text_format_contact)
                    worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 8, amount_due or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 9, status or '', cell_body_text_format)

                    row = row + 1

                worksheet.set_row(row + 1, 23)
                worksheet.write(row + 1, 5, f'=SUM({xl_range(1, col + 5, row, col + 5)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 6, f'=SUM({xl_range(1, col + 6, row, col + 6)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 7, f'=SUM({xl_range(1, col + 7, row, col + 7)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 8, f'=SUM({xl_range(1, col + 8, row, col + 8)})',
                                cell_result_body_number_format)

        workbook.close()
        file_download = base64.b64encode(fp.getvalue())
        fp.close()

        self = self.with_context(default_name=file_name, default_file_download=file_download)

        return {
            'name': 'Income Report Download',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'total.income.report.excel',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self._context,
        }


class TotalIncomeReportExcel(models.TransientModel):
    _name = 'total.income.report.excel'
    _description = "Icome report report excel table"

    name = fields.Char('File Name', size=256, readonly=True)
    file_download = fields.Binary('Download Invoices', readonly=True)


class CashDepositWizard(models.TransientModel):
    _name = 'deposit.report.wizard'

    account_id = fields.Many2one('account.account', string='Account', required=True)
    # account_name = fields.Integer(string='Account name', related='account_id.id')
    date_from = fields.Date(string='Date From', required=True,
                            default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date(string='Date To', required=True,
                          default=lambda self: fields.Date.to_string(
                              (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    state = fields.Selection([("draft", "Draft"), ("open", "Open"), ("paid", "Paid")])

    @api.multi
    def get_report(self):
        file_name = _('Cash Deposit From ' + str(self.date_from) + ' - ' + str(self.date_to) + ' report.xlsx')
        fp = BytesIO()

        workbook = xlsxwriter.Workbook(fp)
        worksheet = workbook.add_worksheet('Deposit report')
        # Disable gridlines
        worksheet.hide_gridlines(2)  # 2 means 'both'

        heading_company_format = workbook.add_format({
            # 'bold': True,
            'font_size': 7,
            'font_name': 'Arial',
            # 'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        })
        heading_company_format.set_border()
        cell_title_text_format_contact = workbook.add_format({'align': 'left',
                                                              'bold': True,
                                                              'font_name': 'Calibri',
                                                              'size': 12,
                                                              'fg_color': '#FFCC00',
                                                              })
        cell_title_text_format_contact.set_border()
        cell_title_text_format = workbook.add_format({'align': 'center',
                                                      'bold': True,
                                                      'font_name': 'Calibri',
                                                      'size': 12,
                                                      'fg_color': '#FFCC00',
                                                      })
        cell_title_text_format.set_border()

        cell_body_text_format = workbook.add_format({'align': 'center',
                                                     'font_name': 'Calibri',
                                                     'size': 11,
                                                     })
        cell_body_text_format.set_border()
        cell_body_text_format_contact = workbook.add_format({'align': 'left',
                                                             'font_name': 'Calibri',
                                                             'size': 11,
                                                             })
        cell_body_text_format_contact.set_border()
        cell_body_number_format = workbook.add_format({'align': 'right',
                                                       'bold': False,
                                                       'size': 11,
                                                       'num_format': '#,###0.00'})
        cell_body_number_format.set_border()

        cell_result_body_number_format = workbook.add_format({'align': 'right',
                                                              'bold': True,
                                                              'size': 13,
                                                              'fg_color': '#FFCC00',
                                                              'num_format': '#,###0.00'})
        cell_result_body_number_format.set_border()

        worksheet.set_row(0, 25)

        worksheet.set_column('A:A', 16)
        worksheet.set_column('B:B', 16)
        worksheet.set_column('B:I', 16)

        if self.date_from and self.date_to:
            row = 0
            col = 0

            worksheet.write(row, 0, 'Date', cell_title_text_format)
            worksheet.write(row, 1, 'Amount', cell_title_text_format)
            worksheet.write(row, 2, 'Status', cell_title_text_format)

            all_posited_deposit = self.env['account.move'].sudo().search([('date', '<=', self.date_to),
                                                                          ('date', '>=', self.date_from),
                                                                          ])

            if all_posited_deposit:
                for cash_deposit in all_posited_deposit:
                    for line in cash_deposit.line_ids:
                        if line.debit > 0 and line.account_id.id == self.account_id.id:
                            posted_date = datetime.strftime(cash_deposit.date, '%d-%m-%Y')
                            # for amount in all_posited_deposit.line_ids:
                            amount_deposited = line.debit
                            status = cash_deposit.state

                            worksheet.write(row + 1, col, posted_date or '', cell_body_text_format)
                            worksheet.write(row + 1, col + 1, amount_deposited or '', cell_body_number_format)
                            worksheet.write(row + 1, col + 2, status or '', cell_body_text_format)
                            row = row + 1
                            # row1 = row + 1

                worksheet.set_row(row + 1, 23)
                worksheet.write(row + 1, 1, f'=SUM({xl_range(1, col + 1, row, col + 1)})',
                                cell_result_body_number_format)

            # if customer_and_state_invoice:
            #     for invoice in customer_and_state_invoice:
            #         name = invoice.partner_id.name
            #         if invoice.origin:
            #             inv_number = invoice.debt_number
            #         else:
            #             inv_number = invoice.number
            #         sale_person = invoice.user_id.name
            #         invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
            #         due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
            #         if invoice.origin:
            #             amount_tax_excluded = 0 - invoice.amount_untaxed
            #         else:
            #             amount_tax_excluded = invoice.amount_untaxed
            #         amount_tax = invoice.amount_tax
            #         if invoice.origin:
            #             total = 0 - invoice.amount_total
            #         else:
            #             total = invoice.amount_total
            #         amount_due = invoice.residual
            #         status = invoice.state
            #
            #         worksheet.write(row + 1, col, name or '', cell_body_text_format_contact)
            #         worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 8, amount_due or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 9, status or '', cell_body_text_format)
            #
            #         row = row + 1
            #
            #     worksheet.set_row(row + 1, 23)
            #     worksheet.write(row + 1, 5, f'=SUM({xl_range(1, col + 5, row, col + 5)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 6, f'=SUM({xl_range(1, col + 6, row, col + 6)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 7, f'=SUM({xl_range(1, col + 7, row, col + 7)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 8, f'=SUM({xl_range(1, col + 8, row, col + 8)})',
            #                     cell_result_body_number_format)
            #
            # elif customer_invoice:
            #     for invoice in customer_invoice:
            #         name = invoice.partner_id.name
            #         if invoice.origin:
            #             inv_number = invoice.debt_number
            #         else:
            #             inv_number = invoice.number
            #         sale_person = invoice.user_id.name
            #         invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
            #         due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
            #         if invoice.origin:
            #             amount_tax_excluded = 0 - invoice.amount_untaxed
            #         else:
            #             amount_tax_excluded = invoice.amount_untaxed
            #         amount_tax = invoice.amount_tax
            #         if invoice.origin:
            #             total = 0 - invoice.amount_total
            #         else:
            #             total = invoice.amount_total
            #         amount_due = invoice.residual
            #         status = invoice.state
            #
            #         worksheet.write(row + 1, col, name or '', cell_body_text_format_contact)
            #         worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 8, amount_due or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 9, status or '', cell_body_text_format)
            #
            #         row = row + 1
            #
            #     worksheet.set_row(row + 1, 23)
            #     worksheet.write(row + 1, 5, f'=SUM({xl_range(1, col + 5, row, col + 5)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 6, f'=SUM({xl_range(1, col + 6, row, col + 6)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 7, f'=SUM({xl_range(1, col + 7, row, col + 7)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 8, f'=SUM({xl_range(1, col + 8, row, col + 8)})',
            #                     cell_result_body_number_format)
            # elif state_invoice:
            #     for invoice in state_invoice:
            #         name = invoice.partner_id.name
            #         if invoice.origin:
            #             inv_number = invoice.debt_number
            #         else:
            #             inv_number = invoice.number
            #         sale_person = invoice.user_id.name
            #         invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
            #         due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
            #         if invoice.origin:
            #             amount_tax_excluded = 0 - invoice.amount_untaxed
            #         else:
            #             amount_tax_excluded = invoice.amount_untaxed
            #         amount_tax = invoice.amount_tax
            #         if invoice.origin:
            #             total = 0 - invoice.amount_total
            #         else:
            #             total = invoice.amount_total
            #         amount_due = invoice.residual
            #         status = invoice.state
            #
            #         worksheet.write(row + 1, col, name or '', cell_body_text_format_contact)
            #         worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 8, amount_due or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 9, status or '', cell_body_text_format)
            #
            #         row = row + 1
            #
            #     worksheet.set_row(row + 1, 23)
            #     worksheet.write(row + 1, 5, f'=SUM({xl_range(1, col + 5, row, col + 5)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 6, f'=SUM({xl_range(1, col + 6, row, col + 6)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 7, f'=SUM({xl_range(1, col + 7, row, col + 7)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 8, f'=SUM({xl_range(1, col + 8, row, col + 8)})',
            #                     cell_result_body_number_format)
            #
            # else:
            #     for invoice in all_customers_invoice:
            #         name = invoice.partner_id.name
            #         if invoice.origin:
            #             inv_number = invoice.debt_number
            #         else:
            #             inv_number = invoice.number
            #         sale_person = invoice.user_id.name
            #         invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
            #         due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
            #         if invoice.origin:
            #             amount_tax_excluded = 0 - invoice.amount_untaxed
            #         else:
            #             amount_tax_excluded = invoice.amount_untaxed
            #         amount_tax = invoice.amount_tax
            #         if invoice.origin:
            #             total = 0 - invoice.amount_total
            #         else:
            #             total = invoice.amount_total
            #         amount_due = invoice.residual
            #         status = invoice.state
            #
            #         worksheet.write(row + 1, col, name or '', cell_body_text_format_contact)
            #         worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 8, amount_due or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 9, status or '', cell_body_text_format)
            #
            #         row = row + 1
            #
            #     worksheet.set_row(row + 1, 23)
            #     worksheet.write(row + 1, 5, f'=SUM({xl_range(1, col + 5, row, col + 5)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 6, f'=SUM({xl_range(1, col + 6, row, col + 6)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 7, f'=SUM({xl_range(1, col + 7, row, col + 7)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 8, f'=SUM({xl_range(1, col + 8, row, col + 8)})',
            #                     cell_result_body_number_format)

        workbook.close()
        file_download = base64.b64encode(fp.getvalue())
        fp.close()

        self = self.with_context(default_name=file_name, default_file_download=file_download)

        return {
            'name': 'Cash Deposited Report Download',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'cash.deposit.report.excel',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self._context,
        }


class CashDepositExcel(models.TransientModel):
    _name = 'cash.deposit.report.excel'
    _description = "Cash Deposited report excel table"

    name = fields.Char('File Name', size=256, readonly=True)
    file_download = fields.Binary('Download Invoices', readonly=True)


class ExpensesReportWizard(models.TransientModel):
    _name = 'expense.report.wizard'

    customer_id = fields.Many2one('hr.employee', string='Employee', required=False)
    customer_name = fields.Integer(string='Employee name', related='customer_id.id')
    date_from = fields.Date(string='Date From', required=True,
                            default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date(string='Date To', required=True,
                          default=lambda self: fields.Date.to_string(
                              (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    state = fields.Selection([("draft", "Draft"), ("open", "Open"), ("paid", "Paid")])

    @api.multi
    def get_report(self):
        file_name = _('Expenses Report From ' + str(self.date_from) + ' - ' + str(self.date_to) + ' report.xlsx')
        fp = BytesIO()

        workbook = xlsxwriter.Workbook(fp)
        worksheet = workbook.add_worksheet('Expenses report')
        # Disable gridlines
        worksheet.hide_gridlines(2)  # 2 means 'both'

        heading_company_format = workbook.add_format({
            # 'bold': True,
            'font_size': 7,
            'font_name': 'Arial',
            # 'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        })
        heading_company_format.set_border()
        cell_title_text_format_contact = workbook.add_format({'align': 'left',
                                                              'bold': True,
                                                              'font_name': 'Calibri',
                                                              'size': 12,
                                                              'fg_color': '#FFCC00',
                                                              })
        cell_title_text_format_contact.set_border()
        cell_title_text_format_main = workbook.add_format({'align': 'center',
                                                           'bold': True,
                                                           'font_name': 'Calibri',
                                                           'size': 12,
                                                           'fg_color': '#FFCC00',
                                                           })
        cell_title_text_format_main.set_border()
        cell_title_text_format = workbook.add_format({'align': 'center',
                                                      'bold': True,
                                                      'font_name': 'Calibri',
                                                      'size': 12,

                                                      })
        cell_title_text_format.set_border()
        cell_title_text_format_number = workbook.add_format({'align': 'right',
                                                             'bold': True,
                                                             'font_name': 'Calibri',
                                                             'size': 12,
                                                             })
        cell_title_text_format_number.set_border()

        cell_body_text_format_number = workbook.add_format({'align': 'right',
                                                            'font_name': 'Calibri',
                                                            'size': 11,
                                                            'num_format': '#,###0.00'
                                                            })
        cell_body_text_format_number.set_border()
        cell_body_text_format = workbook.add_format({'align': 'center',
                                                     'font_name': 'Calibri',
                                                     'size': 11,
                                                     })
        cell_body_text_format.set_border()
        cell_body_text_format_contact = workbook.add_format({'align': 'left',
                                                             'font_name': 'Calibri',
                                                             'size': 11,
                                                             })
        cell_body_text_format_contact.set_border()
        cell_body_number_format = workbook.add_format({'align': 'right',
                                                       'bold': False,
                                                       'size': 11,
                                                       'num_format': '#,###0.00'})
        cell_body_number_format.set_border()

        cell_result_body_number_format = workbook.add_format({'align': 'right',
                                                              'bold': True,
                                                              'size': 13,
                                                              'fg_color': '#FFCC00',
                                                              'num_format': '#,###0.00'})
        cell_result_body_number_format.set_border()

        worksheet.set_row(1, 25)

        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:C', 16)
        worksheet.set_column('D:D', 50)
        worksheet.set_column('B:I', 16)

        if self.date_from and self.date_to:
            row = 2
            col = 0

            worksheet.merge_range('A2:H2', 'METALOGISTICS PETTY CASH ACCOUNT ', cell_title_text_format_main)
            worksheet.write(row, 0, 'DATE', cell_title_text_format)
            worksheet.write(row, 1, 'RECEIPT', cell_title_text_format)
            worksheet.write(row, 2, 'NAME', cell_title_text_format)
            worksheet.write(row, 3, 'PARTICULARS', cell_title_text_format)
            worksheet.write(row, 4, 'VOUCHER NO.', cell_title_text_format)
            worksheet.write(row, 5, 'QTY', cell_title_text_format)
            worksheet.write(row, 6, 'PRICE', cell_title_text_format_number)
            worksheet.write(row, 7, 'AMOUNT', cell_title_text_format_number)

            all_expenses = self.env['hr.expense'].sudo().search(
                [('date', '<=', self.date_to), ('date', '>=', self.date_from)])

            employee_expense = self.env['hr.expense'].sudo().search([('employee_id', '=', self.customer_name),
                                                                     ('date', '<=', self.date_to),
                                                                     ('date', '>=', self.date_from),
                                                                     ])
            state_invoice = self.env['account.invoice'].sudo().search([('state', '=', self.state),
                                                                       ('date', '<=', self.date_to),
                                                                       ('date', '>=', self.date_from),
                                                                       ('partner_id.customer', '=', True)])
            customer_and_state_invoice = self.env['account.invoice'].sudo().search([('state', '=', self.state),
                                                                                    ('partner_id', '=',
                                                                                     self.customer_name),
                                                                                    (
                                                                                        'date_invoice', '<=',
                                                                                        self.date_to),
                                                                                    ('date_invoice', '>=',
                                                                                     self.date_from),
                                                                                    ('partner_id.customer', '=', True)])

            if employee_expense:
                for expense in employee_expense:
                    request_date = datetime.strftime(expense.date, '%d.%m.%Y')
                    # receipt = expense.product_id.name
                    employee_name = expense.employee_id.name
                    particular = expense.product_id.name
                    qty = expense.quantity
                    unit_price = expense.unit_amount
                    amount = expense.total_amount

                    worksheet.write(row + 1, col, request_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 1, '' or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 2, employee_name or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 3, particular or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 4, 'v' or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 5, qty or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 6, unit_price or '', cell_body_text_format_number)
                    worksheet.write(row + 1, col + 7, amount or '', cell_body_text_format_number)

                    row = row + 1

            else:
                for expense in all_expenses:
                    request_date = datetime.strftime(expense.date, '%d.%m.%Y')
                    # receipt = expense.product_id.name
                    employee_name = expense.employee_id.name
                    particular = expense.product_id.name
                    qty = expense.quantity
                    unit_price = expense.unit_amount
                    amount = expense.total_amount

                    worksheet.write(row + 1, col, request_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 1, '' or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 2, employee_name or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 3, particular or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 4, 'v' or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 5, qty or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 6, unit_price or '', cell_body_text_format_number)
                    worksheet.write(row + 1, col + 7, amount or '', cell_body_text_format_number)

                    row = row + 1

            worksheet.write(row + 1, 7, f'=SUM({xl_range(1, col + 7, row, col + 7)})',
                            cell_result_body_number_format)

            # if customer_and_state_invoice:
            #     for invoice in customer_and_state_invoice:
            #         name = invoice.partner_id.name
            #         if invoice.origin:
            #             inv_number = invoice.debt_number
            #         else:
            #             inv_number = invoice.number
            #         sale_person = invoice.user_id.name
            #         invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
            #         due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
            #         if invoice.origin:
            #             amount_tax_excluded = 0 - invoice.amount_untaxed
            #         else:
            #             amount_tax_excluded = invoice.amount_untaxed
            #         amount_tax = invoice.amount_tax
            #         if invoice.origin:
            #             total = 0 - invoice.amount_total
            #         else:
            #             total = invoice.amount_total
            #         amount_due = invoice.residual
            #         status = invoice.state
            #
            #         worksheet.write(row + 1, col, name or '', cell_body_text_format_contact)
            #         worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 8, amount_due or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 9, status or '', cell_body_text_format)
            #
            #         row = row + 1
            #
            #     worksheet.set_row(row + 1, 23)
            #     worksheet.write(row + 1, 5, f'=SUM({xl_range(1, col + 5, row, col + 5)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 6, f'=SUM({xl_range(1, col + 6, row, col + 6)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 7, f'=SUM({xl_range(1, col + 7, row, col + 7)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 8, f'=SUM({xl_range(1, col + 8, row, col + 8)})',
            #                     cell_result_body_number_format)
            #
            # elif customer_invoice:
            #     for invoice in customer_invoice:
            #         name = invoice.partner_id.name
            #         if invoice.origin:
            #             inv_number = invoice.debt_number
            #         else:
            #             inv_number = invoice.number
            #         sale_person = invoice.user_id.name
            #         invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
            #         due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
            #         if invoice.origin:
            #             amount_tax_excluded = 0 - invoice.amount_untaxed
            #         else:
            #             amount_tax_excluded = invoice.amount_untaxed
            #         amount_tax = invoice.amount_tax
            #         if invoice.origin:
            #             total = 0 - invoice.amount_total
            #         else:
            #             total = invoice.amount_total
            #         amount_due = invoice.residual
            #         status = invoice.state
            #
            #         worksheet.write(row + 1, col, name or '', cell_body_text_format_contact)
            #         worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 8, amount_due or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 9, status or '', cell_body_text_format)
            #
            #         row = row + 1
            #
            #     worksheet.set_row(row + 1, 23)
            #     worksheet.write(row + 1, 5, f'=SUM({xl_range(1, col + 5, row, col + 5)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 6, f'=SUM({xl_range(1, col + 6, row, col + 6)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 7, f'=SUM({xl_range(1, col + 7, row, col + 7)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 8, f'=SUM({xl_range(1, col + 8, row, col + 8)})',
            #                     cell_result_body_number_format)
            # elif state_invoice:
            #     for invoice in state_invoice:
            #         name = invoice.partner_id.name
            #         if invoice.origin:
            #             inv_number = invoice.debt_number
            #         else:
            #             inv_number = invoice.number
            #         sale_person = invoice.user_id.name
            #         invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
            #         due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
            #         if invoice.origin:
            #             amount_tax_excluded = 0 - invoice.amount_untaxed
            #         else:
            #             amount_tax_excluded = invoice.amount_untaxed
            #         amount_tax = invoice.amount_tax
            #         if invoice.origin:
            #             total = 0 - invoice.amount_total
            #         else:
            #             total = invoice.amount_total
            #         amount_due = invoice.residual
            #         status = invoice.state
            #
            #         worksheet.write(row + 1, col, name or '', cell_body_text_format_contact)
            #         worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 8, amount_due or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 9, status or '', cell_body_text_format)
            #
            #         row = row + 1
            #
            #     worksheet.set_row(row + 1, 23)
            #     worksheet.write(row + 1, 5, f'=SUM({xl_range(1, col + 5, row, col + 5)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 6, f'=SUM({xl_range(1, col + 6, row, col + 6)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 7, f'=SUM({xl_range(1, col + 7, row, col + 7)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 8, f'=SUM({xl_range(1, col + 8, row, col + 8)})',
            #                     cell_result_body_number_format)
            #
            # else:
            #     for invoice in all_customers_invoice:
            #         name = invoice.partner_id.name
            #         if invoice.origin:
            #             inv_number = invoice.debt_number
            #         else:
            #             inv_number = invoice.number
            #         sale_person = invoice.user_id.name
            #         invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
            #         due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
            #         if invoice.origin:
            #             amount_tax_excluded = 0 - invoice.amount_untaxed
            #         else:
            #             amount_tax_excluded = invoice.amount_untaxed
            #         amount_tax = invoice.amount_tax
            #         if invoice.origin:
            #             total = 0 - invoice.amount_total
            #         else:
            #             total = invoice.amount_total
            #         amount_due = invoice.residual
            #         status = invoice.state
            #
            #         worksheet.write(row + 1, col, name or '', cell_body_text_format_contact)
            #         worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
            #         worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 8, amount_due or '', cell_body_number_format)
            #         worksheet.write(row + 1, col + 9, status or '', cell_body_text_format)
            #
            #         row = row + 1
            #
            #     worksheet.set_row(row + 1, 23)
            #     worksheet.write(row + 1, 5, f'=SUM({xl_range(1, col + 5, row, col + 5)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 6, f'=SUM({xl_range(1, col + 6, row, col + 6)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 7, f'=SUM({xl_range(1, col + 7, row, col + 7)})',
            #                     cell_result_body_number_format)
            #     worksheet.write(row + 1, 8, f'=SUM({xl_range(1, col + 8, row, col + 8)})',
            #                     cell_result_body_number_format)

        workbook.close()
        file_download = base64.b64encode(fp.getvalue())
        fp.close()

        self = self.with_context(default_name=file_name, default_file_download=file_download)

        return {
            'name': 'Expense Report Download',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'expenses.report.excel',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self._context,
        }


class ExpensesReportExcel(models.TransientModel):
    _name = 'expenses.report.excel'
    _description = "Expenses report report excel table"

    name = fields.Char('File Name', size=256, readonly=True)
    file_download = fields.Binary('Download Expense Report', readonly=True)


class CustomerInvoiceWizard(models.TransientModel):
    _name = 'customer.invoice.report.wizard'

    customer_id = fields.Many2one('res.partner', string='Customer', required=False, domain="[('customer', '=', True)]")
    customer_name = fields.Integer(string='Customer name', related='customer_id.id')
    date_from = fields.Date(string='Date From', required=True,
                            default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date(string='Date To', required=True,
                          default=lambda self: fields.Date.to_string(
                              (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    state = fields.Selection([("draft", "Draft"), ("open", "Open")])

    @api.multi
    def get_report(self):
        file_name = _('Customer Invoices ' + str(self.date_from) + ' - ' + str(self.date_to) + ' report.xlsx')
        fp = BytesIO()

        workbook = xlsxwriter.Workbook(fp)
        worksheet = workbook.add_worksheet('Customer Invoice report')
        # Disable gridlines
        worksheet.hide_gridlines(2)  # 2 means 'both'

        heading_company_format = workbook.add_format({
            # 'bold': True,
            'font_size': 7,
            'font_name': 'Arial',
            # 'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        })
        heading_company_format.set_border()
        cell_title_text_format_contact = workbook.add_format({'align': 'left',
                                                              'font_name': 'Calibri',
                                                              'size': 11,
                                                              })
        cell_title_text_format_contact.set_border()
        cell_title_text_format = workbook.add_format({'align': 'center',
                                                      'bold': True,
                                                      'font_name': 'Calibri',
                                                      'size': 12,
                                                      'fg_color': '#FFCC00',
                                                      })
        cell_title_text_format.set_border()

        cell_body_text_format = workbook.add_format({'align': 'center',
                                                     'font_name': 'Calibri',
                                                     'size': 11,
                                                     })
        cell_body_text_format.set_border()
        cell_body_number_format = workbook.add_format({'align': 'right',
                                                       'bold': False,
                                                       'size': 11,
                                                       'num_format': '#,###0.00'})
        cell_body_number_format.set_border()

        cell_result_body_number_format = workbook.add_format({'align': 'right',
                                                              'bold': True,
                                                              'size': 13,
                                                              'fg_color': '#FFCC00',
                                                              'num_format': '#,###0.00'})
        cell_result_body_number_format.set_border()

        worksheet.set_row(0, 25)

        worksheet.set_column('A:A', 27)
        worksheet.set_column('B:B', 16)
        worksheet.set_column('B:I', 16)

        if self.date_from and self.date_to:
            row = 0
            col = 0

            worksheet.write(row, 0, 'Contact Name', cell_title_text_format)
            worksheet.write(row, 1, 'Invoice Number', cell_title_text_format)
            worksheet.write(row, 2, 'Operator', cell_title_text_format)
            worksheet.write(row, 3, 'Invoice Date', cell_title_text_format)
            worksheet.write(row, 4, 'Due Date', cell_title_text_format)
            worksheet.write(row, 5, 'Tax Excluded', cell_title_text_format)
            worksheet.write(row, 6, 'Tax', cell_title_text_format)
            worksheet.write(row, 7, 'Total', cell_title_text_format)
            worksheet.write(row, 8, 'Amount Due', cell_title_text_format)
            worksheet.write(row, 9, 'Status', cell_title_text_format)

            all_customers_invoice = self.env['account.invoice'].sudo().search(
                [('date_invoice', '<=', self.date_to), ('date_invoice', '>=', self.date_from),
                 ('partner_id.customer', '=', True), ('state', 'in', ('draft', 'open'))])
            customer_invoice = self.env['account.invoice'].sudo().search([('partner_id', '=', self.customer_name),
                                                                          ('date_invoice', '<=', self.date_to),
                                                                          ('date_invoice', '>=', self.date_from),
                                                                          ('partner_id.customer', '=', True),
                                                                          ('state', 'in', ('draft', 'open'))
                                                                          ])
            state_invoice = self.env['account.invoice'].sudo().search([('state', '=', self.state),
                                                                       ('date_invoice', '<=', self.date_to),
                                                                       ('date_invoice', '>=', self.date_from)])
            customer_and_state_invoice = self.env['account.invoice'].sudo().search([('state', '=', self.state),
                                                                                    ('partner_id', '=',
                                                                                     self.customer_name),
                                                                                    (
                                                                                        'date_invoice', '<=',
                                                                                        self.date_to),
                                                                                    ('date_invoice', '>=',
                                                                                     self.date_from),
                                                                                    ('partner_id.customer', '=', True)])

            if customer_and_state_invoice:
                for invoice in customer_and_state_invoice:
                    name = invoice.partner_id.name
                    if invoice.origin:
                        inv_number = invoice.number
                    else:
                        inv_number = invoice.number
                    sale_person = invoice.user_id.name
                    invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
                    due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
                    amount_tax_excluded = invoice.amount_untaxed
                    amount_tax = invoice.amount_tax
                    total = invoice.amount_total
                    amount_due = invoice.residual
                    status = invoice.state

                    worksheet.write(row + 1, col, name or '', cell_title_text_format_contact)
                    worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 8, amount_due or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 9, status or '', cell_body_text_format)

                    row = row + 1

            elif customer_invoice:
                for invoice in customer_invoice:
                    name = invoice.partner_id.name
                    if invoice.origin:
                        inv_number = invoice.number
                    else:
                        inv_number = invoice.number
                    sale_person = invoice.user_id.name
                    invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
                    due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
                    amount_tax_excluded = invoice.amount_untaxed
                    amount_tax = invoice.amount_tax
                    total = invoice.amount_total
                    amount_due = invoice.residual
                    status = invoice.state

                    worksheet.write(row + 1, col, name or '', cell_title_text_format_contact)
                    worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 8, amount_due or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 9, status or '', cell_body_text_format)

                    row = row + 1

            elif state_invoice:
                for invoice in state_invoice:
                    name = invoice.partner_id.name
                    if invoice.origin:
                        inv_number = invoice.number
                    else:
                        inv_number = invoice.number
                    sale_person = invoice.user_id.name
                    invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
                    due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
                    amount_tax_excluded = invoice.amount_untaxed
                    amount_tax = invoice.amount_tax
                    total = invoice.amount_total
                    amount_due = invoice.residual
                    status = invoice.state

                    worksheet.write(row + 1, col, name or '', cell_title_text_format_contact)
                    worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 8, amount_due or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 9, status or '', cell_body_text_format)

                    row = row + 1

            else:
                for invoice in all_customers_invoice:
                    name = invoice.partner_id.name
                    if invoice.origin:
                        inv_number = invoice.number
                    else:
                        inv_number = invoice.number
                    sale_person = invoice.user_id.name
                    invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
                    due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
                    amount_tax_excluded = invoice.amount_untaxed
                    amount_tax = invoice.amount_tax
                    total = invoice.amount_total
                    amount_due = invoice.residual
                    status = invoice.state

                    worksheet.write(row + 1, col, name or '', cell_title_text_format_contact)
                    worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 8, amount_due or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 9, status or '', cell_body_text_format)

                    row = row + 1

            worksheet.set_row(row + 1, 23)
            worksheet.write(row + 1, 5, f'=SUM({xl_range(1, col + 5, row, col + 5)})',
                            cell_result_body_number_format)
            worksheet.write(row + 1, 6, f'=SUM({xl_range(1, col + 6, row, col + 6)})',
                            cell_result_body_number_format)
            worksheet.write(row + 1, 7, f'=SUM({xl_range(1, col + 7, row, col + 7)})',
                            cell_result_body_number_format)
            worksheet.write(row + 1, 8, f'=SUM({xl_range(1, col + 8, row, col + 8)})',
                            cell_result_body_number_format)

        workbook.close()
        file_download = base64.b64encode(fp.getvalue())
        fp.close()

        self = self.with_context(default_name=file_name, default_file_download=file_download)

        return {
            'name': 'Invoice Report Download',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'customer.invoice.report.excel',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self._context,
        }


class CustomerInvoiceReportExcel(models.TransientModel):
    _name = 'customer.invoice.report.excel'
    _description = "customer invoice report excel table"

    name = fields.Char('File Name', size=256, readonly=True)
    file_download = fields.Binary('Download Invoices', readonly=True)


class DebitNoteWizard(models.TransientModel):
    _name = 'debit.note.report.wizard'

    customer_id = fields.Many2one('res.partner', string='Customer', required=False, domain="[('customer', '=', True)]")
    customer_name = fields.Integer(string='Customer name', related='customer_id.id')
    date_from = fields.Date(string='Date From', required=True,
                            default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date(string='Date To', required=True,
                          default=lambda self: fields.Date.to_string(
                              (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    state = fields.Selection([("draft", "Draft"), ("open", "Open"), ("paid", "Paid")])

    @api.multi
    def get_report(self):
        file_name = _('Debit Note ' + str(self.date_from) + ' - ' + str(self.date_to) + ' report.xlsx')
        fp = BytesIO()

        workbook = xlsxwriter.Workbook(fp)
        worksheet = workbook.add_worksheet('Debit Note  report')
        # Disable gridlines
        worksheet.hide_gridlines(2)  # 2 means 'both'

        heading_company_format = workbook.add_format({
            # 'bold': True,
            'font_size': 7,
            'font_name': 'Arial',
            # 'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        })
        heading_company_format.set_border()
        cell_title_text_format = workbook.add_format({'align': 'center',
                                                      'bold': True,
                                                      'font_name': 'Calibri',
                                                      'size': 12,
                                                      'fg_color': '#FFCC00',
                                                      })
        cell_title_text_format.set_border()

        cell_body_text_format_contact = workbook.add_format({'align': 'left',
                                                             'font_name': 'Calibri',
                                                             'size': 11,
                                                             })
        cell_body_text_format_contact.set_border()
        cell_body_text_format = workbook.add_format({'align': 'center',
                                                     'font_name': 'Calibri',
                                                     'size': 11,
                                                     })
        cell_body_text_format.set_border()
        cell_body_number_format = workbook.add_format({'align': 'right',
                                                       'bold': False,
                                                       'size': 11,
                                                       'num_format': '#,###0.00'})
        cell_body_number_format.set_border()

        cell_result_body_number_format = workbook.add_format({'align': 'right',
                                                              'bold': True,
                                                              'size': 13,
                                                              'fg_color': '#FFCC00',
                                                              'num_format': '#,###0.00'})
        cell_result_body_number_format.set_border()

        worksheet.set_row(0, 25)

        worksheet.set_column('A:A', 27)
        worksheet.set_column('B:B', 16)
        worksheet.set_column('B:I', 16)

        if self.date_from and self.date_to:
            row = 0
            col = 0

            worksheet.write(row, 0, 'Contact Name', cell_title_text_format)
            worksheet.write(row, 1, 'Invoice Number', cell_title_text_format)
            worksheet.write(row, 2, 'Operator', cell_title_text_format)
            worksheet.write(row, 3, 'Invoice Date', cell_title_text_format)
            worksheet.write(row, 4, 'Due Date', cell_title_text_format)
            worksheet.write(row, 5, 'Tax Excluded', cell_title_text_format)
            worksheet.write(row, 6, 'Tax', cell_title_text_format)
            worksheet.write(row, 7, 'Total', cell_title_text_format)
            worksheet.write(row, 8, 'Status', cell_title_text_format)

            all_customers_invoice = self.env['account.invoice'].sudo().search(
                [('date_invoice', '<=', self.date_to), ('date_invoice', '>=', self.date_from),
                 ('partner_id.customer', '=', True)])
            customer_invoice = self.env['account.invoice'].sudo().search([('partner_id', '=', self.customer_name),
                                                                          ('date_invoice', '<=', self.date_to),
                                                                          ('date_invoice', '>=', self.date_from),
                                                                          ('partner_id.customer', '=', True),
                                                                          ])
            state_invoice = self.env['account.invoice'].sudo().search([('state', '=', self.state),
                                                                       ('date_invoice', '<=', self.date_to),
                                                                       ('date_invoice', '>=', self.date_from),
                                                                       ('partner_id.customer', '=', True)])
            customer_and_state_invoice = self.env['account.invoice'].sudo().search([('state', '=', self.state),
                                                                                    ('partner_id', '=',
                                                                                     self.customer_name),
                                                                                    (
                                                                                        'date_invoice', '<=',
                                                                                        self.date_to),
                                                                                    ('date_invoice', '>=',
                                                                                     self.date_from),
                                                                                    ('partner_id.customer', '=', True)])

            if customer_and_state_invoice:
                for invoice in customer_and_state_invoice:
                    if invoice.origin:
                        name = invoice.partner_id.name
                        inv_number = invoice.number
                        sale_person = invoice.user_id.name
                        invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
                        due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
                        amount_tax_excluded = invoice.amount_untaxed
                        amount_tax = invoice.amount_tax
                        total = invoice.amount_total
                        status = invoice.state

                        worksheet.write(row + 1, col, name or '', cell_body_text_format_contact)
                        worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
                        worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
                        worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
                        worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
                        worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
                        worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
                        worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
                        worksheet.write(row + 1, col + 8, status or '', cell_body_text_format)

                        row = row + 1

                worksheet.set_row(row + 1, 23)
                worksheet.write(row + 1, 5, f'=SUM({xl_range(1, col + 5, row, col + 5)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 6, f'=SUM({xl_range(1, col + 6, row, col + 6)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 7, f'=SUM({xl_range(1, col + 7, row, col + 7)})',
                                cell_result_body_number_format)

            elif customer_invoice:
                for invoice in customer_invoice:
                    if invoice.origin:
                        name = invoice.partner_id.name
                        inv_number = invoice.number
                        sale_person = invoice.user_id.name
                        invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
                        due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
                        amount_tax_excluded = invoice.amount_untaxed
                        amount_tax = invoice.amount_tax
                        total = invoice.amount_total
                        status = invoice.state

                        worksheet.write(row + 1, col, name or '', cell_body_text_format_contact)
                        worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
                        worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
                        worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
                        worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
                        worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
                        worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
                        worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
                        worksheet.write(row + 1, col + 8, status or '', cell_body_text_format)

                        row = row + 1

                worksheet.set_row(row + 1, 23)
                worksheet.write(row + 1, 5, f'=SUM({xl_range(1, col + 5, row, col + 5)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 6, f'=SUM({xl_range(1, col + 6, row, col + 6)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 7, f'=SUM({xl_range(1, col + 7, row, col + 7)})',
                                cell_result_body_number_format)
            elif state_invoice:
                for invoice in state_invoice:
                    if invoice.origin:
                        name = invoice.partner_id.name
                        inv_number = invoice.number
                        sale_person = invoice.user_id.name
                        invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
                        due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
                        amount_tax_excluded = invoice.amount_untaxed
                        amount_tax = invoice.amount_tax
                        total = invoice.amount_total
                        status = invoice.state

                        worksheet.write(row + 1, col, name or '', cell_body_text_format_contact)
                        worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
                        worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
                        worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
                        worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
                        worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
                        worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
                        worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
                        worksheet.write(row + 1, col + 8, status or '', cell_body_text_format)

                        row = row + 1

                worksheet.set_row(row + 1, 23)
                worksheet.write(row + 1, 5, f'=SUM({xl_range(1, col + 5, row, col + 5)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 6, f'=SUM({xl_range(1, col + 6, row, col + 6)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 7, f'=SUM({xl_range(1, col + 7, row, col + 7)})',
                                cell_result_body_number_format)

            else:
                for invoice in all_customers_invoice:
                    if invoice.origin:
                        name = invoice.partner_id.name
                        inv_number = invoice.number
                        sale_person = invoice.user_id.name
                        invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
                        due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
                        amount_tax_excluded = invoice.amount_untaxed
                        amount_tax = invoice.amount_tax
                        total = invoice.amount_total
                        status = invoice.state

                        worksheet.write(row + 1, col, name or '', cell_body_text_format_contact)
                        worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
                        worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
                        worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
                        worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
                        worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
                        worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
                        worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
                        worksheet.write(row + 1, col + 8, status or '', cell_body_text_format)
                        row = row + 1

                worksheet.set_row(row + 1, 23)
                worksheet.write(row + 1, 5, f'=SUM({xl_range(1, col + 5, row, col + 5)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 6, f'=SUM({xl_range(1, col + 6, row, col + 6)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 7, f'=SUM({xl_range(1, col + 7, row, col + 7)})',
                                cell_result_body_number_format)

        workbook.close()
        file_download = base64.b64encode(fp.getvalue())
        fp.close()

        self = self.with_context(default_name=file_name, default_file_download=file_download)

        return {
            'name': 'Debit Note Report Download',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'debit.note.report.excel',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self._context,
        }


class DebitNoteReportExcel(models.TransientModel):
    _name = 'debit.note.report.excel'
    _description = "Debit Note report excel table"

    name = fields.Char('File Name', size=256, readonly=True)
    file_download = fields.Binary('Download Invoices', readonly=True)


class SupplierBillsWizard(models.TransientModel):
    _name = 'supplier.bills.report.wizard'

    supplier_id = fields.Many2one('res.partner', string='Supplier', required=False, domain="[('supplier', '=', True)]")
    supplier_name = fields.Integer(string='Supplier name', related='supplier_id.id')
    date_from = fields.Date(string='Date From', required=True,
                            default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date(string='Date To', required=True,
                          default=lambda self: fields.Date.to_string(
                              (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    state = fields.Selection([("draft", "Draft"), ("open", "Open"), ("paid", "Paid")])

    @api.multi
    def get_report(self):
        file_name = _('Supplier bills ' + str(self.date_from) + ' - ' + str(self.date_to) + ' report.xlsx')
        fp = BytesIO()

        workbook = xlsxwriter.Workbook(fp)
        worksheet = workbook.add_worksheet('Supplier bills report')
        # Disable gridlines
        worksheet.hide_gridlines(2)  # 2 means 'both'

        heading_company_format = workbook.add_format({
            # 'bold': True,
            'font_size': 7,
            'font_name': 'Arial',
            # 'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        })
        heading_company_format.set_border()
        cell_title_text_format = workbook.add_format({'align': 'center',
                                                      'bold': True,
                                                      'font_name': 'Calibri',
                                                      'size': 12,
                                                      'fg_color': '#FFCC00',
                                                      })
        cell_title_text_format.set_border()

        cell_body_text_format = workbook.add_format({'align': 'center',
                                                     'font_name': 'Calibri',
                                                     'size': 11,
                                                     })
        cell_body_text_format.set_border()
        cell_body_number_format = workbook.add_format({'align': 'right',
                                                       'bold': False,
                                                       'size': 11,
                                                       'num_format': '#,###0.00'})
        cell_body_number_format.set_border()

        cell_result_body_number_format = workbook.add_format({'align': 'right',
                                                              'bold': True,
                                                              'size': 13,
                                                              'fg_color': '#FFCC00',
                                                              'num_format': '#,###0.00'})
        cell_result_body_number_format.set_border()

        worksheet.set_row(0, 25)

        worksheet.set_column('A:A', 27)
        worksheet.set_column('B:B', 16)
        worksheet.set_column('B:I', 16)

        if self.date_from and self.date_to:
            row = 0
            col = 0

            worksheet.write(row, 0, 'Contact Name', cell_title_text_format)
            worksheet.write(row, 1, 'Bill number', cell_title_text_format)
            worksheet.write(row, 2, 'Operator', cell_title_text_format)
            worksheet.write(row, 3, 'Bill Date', cell_title_text_format)
            worksheet.write(row, 4, 'Due Date', cell_title_text_format)
            worksheet.write(row, 5, 'Tax Excluded', cell_title_text_format)
            worksheet.write(row, 6, 'Tax', cell_title_text_format)
            worksheet.write(row, 7, 'Total', cell_title_text_format)
            worksheet.write(row, 8, 'Status', cell_title_text_format)

            all_customers_invoice = self.env['account.invoice'].sudo().search(
                [('date_invoice', '<=', self.date_to), ('date_invoice', '>=', self.date_from),
                 ('partner_id.supplier', '=', True)])
            supplier_bills = self.env['account.invoice'].sudo().search([('partner_id', '=', self.supplier_name),
                                                                        ('date_invoice', '<=', self.date_to),
                                                                        ('date_invoice', '>=', self.date_from),
                                                                        ('partner_id.supplier', '=', True)])
            state_bills = self.env['account.invoice'].sudo().search([('state', '=', self.state),
                                                                     ('date_invoice', '<=', self.date_to),
                                                                     ('date_invoice', '>=', self.date_from),
                                                                     ('partner_id.supplier', '=', True)])
            supplier_and_state_bill = self.env['account.invoice'].sudo().search([('state', '=', self.state),
                                                                                 ('partner_id', '=',
                                                                                  self.supplier_name),
                                                                                 (
                                                                                     'date_invoice', '<=',
                                                                                     self.date_to),
                                                                                 ('date_invoice', '>=',
                                                                                  self.date_from),
                                                                                 ('partner_id.supplier', '=', True)])

            if supplier_and_state_bill:
                for invoice in supplier_and_state_bill:
                    name = invoice.partner_id.name
                    inv_number = invoice.number
                    sale_person = invoice.user_id.name
                    invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
                    due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
                    amount_tax_excluded = invoice.amount_untaxed
                    amount_tax = invoice.amount_tax
                    total = invoice.amount_total
                    status = invoice.state

                    worksheet.write(row + 1, col, name or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 8, status or '', cell_body_text_format)

                    row = row + 1

                worksheet.set_row(row + 1, 23)
                worksheet.write(row + 1, 5, f'=SUM({xl_range(1, col + 5, row, col + 5)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 6, f'=SUM({xl_range(1, col + 6, row, col + 6)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 7, f'=SUM({xl_range(1, col + 7, row, col + 7)})',
                                cell_result_body_number_format)

            elif supplier_bills:
                for invoice in supplier_bills:
                    name = invoice.partner_id.name
                    inv_number = invoice.number
                    sale_person = invoice.user_id.name
                    invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
                    due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
                    amount_tax_excluded = invoice.amount_untaxed
                    amount_tax = invoice.amount_tax
                    total = invoice.amount_total
                    status = invoice.state

                    worksheet.write(row + 1, col, name or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 8, status or '', cell_body_text_format)

                    row = row + 1

                worksheet.set_row(row + 1, 23)
                worksheet.write(row + 1, 5, f'=SUM({xl_range(1, col + 5, row, col + 5)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 6, f'=SUM({xl_range(1, col + 6, row, col + 6)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 7, f'=SUM({xl_range(1, col + 7, row, col + 7)})',
                                cell_result_body_number_format)
            elif state_bills:
                for invoice in state_bills:
                    name = invoice.partner_id.name
                    inv_number = invoice.number
                    sale_person = invoice.user_id.name
                    invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
                    due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
                    amount_tax_excluded = invoice.amount_untaxed
                    amount_tax = invoice.amount_tax
                    total = invoice.amount_total
                    status = invoice.state

                    worksheet.write(row + 1, col, name or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 8, status or '', cell_body_text_format)

                    row = row + 1

                worksheet.set_row(row + 1, 23)
                worksheet.write(row + 1, 5, f'=SUM({xl_range(1, col + 5, row, col + 5)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 6, f'=SUM({xl_range(1, col + 6, row, col + 6)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 7, f'=SUM({xl_range(1, col + 7, row, col + 7)})',
                                cell_result_body_number_format)

            else:
                for invoice in all_customers_invoice:
                    name = invoice.partner_id.name
                    inv_number = invoice.number
                    sale_person = invoice.user_id.name
                    invoice_date = datetime.strftime(invoice.date_invoice, '%d/%m/%Y')
                    due_date = datetime.strftime(invoice.date_due, '%d/%m/%Y')
                    amount_tax_excluded = invoice.amount_untaxed
                    amount_tax = invoice.amount_tax
                    total = invoice.amount_total
                    status = invoice.state

                    worksheet.write(row + 1, col, name or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 1, inv_number or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 2, sale_person or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 3, invoice_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 4, due_date or '', cell_body_text_format)
                    worksheet.write(row + 1, col + 5, amount_tax_excluded or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 6, amount_tax or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 7, total or '', cell_body_number_format)
                    worksheet.write(row + 1, col + 8, status or '', cell_body_text_format)

                    row = row + 1

                worksheet.set_row(row + 1, 23)
                worksheet.write(row + 1, 5, f'=SUM({xl_range(1, col + 5, row, col + 5)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 6, f'=SUM({xl_range(1, col + 6, row, col + 6)})',
                                cell_result_body_number_format)
                worksheet.write(row + 1, 7, f'=SUM({xl_range(1, col + 7, row, col + 7)})',
                                cell_result_body_number_format)

        workbook.close()
        file_download = base64.b64encode(fp.getvalue())
        fp.close()

        self = self.with_context(default_name=file_name, default_file_download=file_download)

        return {
            'name': 'Invoice Report Download',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'customer.invoice.report.excel',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self._context,
        }


class SupplierBillReportExcel(models.TransientModel):
    _name = 'supplier.bill.report.excel'
    _description = "supplier bill report excel table"

    name = fields.Char('File Name', size=256, readonly=True)
    file_download = fields.Binary('Download Invoices', readonly=True)
