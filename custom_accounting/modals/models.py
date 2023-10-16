import base64
import locale
from io import BytesIO

from odoo import fields, models, api


class AccountInvoiceInherit(models.Model):
    _inherit = 'account.invoice'

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
