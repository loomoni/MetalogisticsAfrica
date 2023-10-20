import base64
import locale
from datetime import date
from io import BytesIO

import xlsxwriter
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _
from odoo.tools import datetime


class AccountInvoiceInherit(models.Model):
    _inherit = 'account.invoice'

    file_no = fields.Char(string="File Number")
    awb_bl = fields.Char(string="AWB/BL")
    tansad_no = fields.Char(string="TANSAD No")
    pkg_no = fields.Char(string="Pkg No")
    weight = fields.Char(string="weight")

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


class CustomerInvoiceWizard(models.TransientModel):
    _name = 'customer.invoice.report.wizard'

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
        file_name = _('Customer Invoices ' + str(self.date_from) + ' - ' + str(self.date_to) + ' report.xlsx')
        fp = BytesIO()

        workbook = xlsxwriter.Workbook(fp)
        worksheet = workbook.add_worksheet()
        # Disable gridlines
        # worksheet.hide_gridlines(2)  # 2 means 'both'

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

        worksheet = workbook.add_worksheet(
            'Customer Invoice report ' + str(self.date_from) + ' - ' + str(self.date_to) + ' report.xlsx')

        worksheet.set_row(0, 25)

        worksheet.set_column('A:A', 27)
        worksheet.set_column('B:B', 16)
        worksheet.set_column('B:I', 16)

        if self.date_from and self.date_to:
            row = 0
            col = 0

            worksheet.write(row, 0, 'ContactName', cell_title_text_format)
            worksheet.write(row, 1, 'InvoiceNumber', cell_title_text_format)
            worksheet.write(row, 2, 'Creator', cell_title_text_format)
            worksheet.write(row, 3, 'Invoice Date', cell_title_text_format)
            worksheet.write(row, 4, 'Due Date', cell_title_text_format)
            worksheet.write(row, 5, 'Tax Excluded', cell_title_text_format)
            worksheet.write(row, 6, 'Tax', cell_title_text_format)
            worksheet.write(row, 7, 'Total', cell_title_text_format)
            worksheet.write(row, 8, 'Status', cell_title_text_format)

            all_customers_invoice = self.env['account.invoice'].sudo().search(
                [('date_invoice', '<=', self.date_to), ('date_invoice', '>=', self.date_from)])
            customer_invoice = self.env['account.invoice'].sudo().search([('partner_id', '=', self.customer_name),
                                                                          ('date_invoice', '<=', self.date_to),
                                                                          ('date_invoice', '>=', self.date_from)])

            if customer_invoice:
                print('invoice')
            else:
                for all_invoice in all_customers_invoice:
                    name = all_invoice.partner_id.name
                    inv_number = all_invoice.number
                    sale_person = all_invoice.user_id.name
                    invoice_date = datetime.strftime(all_invoice.date_invoice, '%d/%m/%Y')
                    due_date = datetime.strftime(all_invoice.date_due, '%d/%m/%Y')
                    amount_tax_excluded = all_invoice.amount_untaxed
                    amount_tax = all_invoice.amount_tax
                    total = all_invoice.amount_total
                    status = all_invoice.state

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
