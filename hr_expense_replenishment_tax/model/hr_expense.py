#!/usr/bin/python
# -*- encoding: utf-8 -*-
###############################################################################
#    Module Writen to OpenERP, Open Source Management Solution
#    Copyright (C) OpenERP Venezuela (<http://openerp.com.ve>).
#    All Rights Reserved
############# Credits #########################################################
#    Coded by: Katherine Zaoral          <kathy@vauxoo.com>
#    Planified by: Humberto Arocha       <hbto@vauxoo.com>
#    Audited by: Humberto Arocha         <hbto@vauxoo.com>
###############################################################################
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
###############################################################################
import time
from openerp.osv import fields, osv
from openerp import netsvc
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _

class hr_expense_expense(osv.Model):
    _inherit = "hr.expense.expense"
    _columns =  {
            'fully_applied_vat':fields.boolean('Fully Applied VAT',
                help=('Indicates if VAT has been computed in this expense')), 
            }

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default.update({'fully_applied_vat': False,
                        })
        return super(hr_expense_expense, self).copy(cr, uid, id, default,
                        context=context)
    def payment_reconcile(self, cr, uid, ids, context=None):
        """ It reconcile the expense advance and expense invoice account move
        lines.
        """
        context = context or {}
        res = super(hr_expense_expense, self).payment_reconcile(cr, uid, ids,
                                                            context=context)
        self.create_her_tax(cr, uid, ids, res, context=context)
        return res

    def create_her_tax(self, cr, uid, ids, aml={}, context=None):
        aml_obj = self.pool.get('account.move.line')
        acc_voucher_obj = self.pool.get('account.voucher')
        context = context or {}
        ids= isinstance(ids,(int,long)) and [ids] or ids
        exp = self.browse(cr, uid, ids, context=context)[0]

        company_currency = self._get_company_currency(cr, uid,
                            exp.id, context)

        current_currency = self._get_current_currency(cr, uid,
                            exp.id, context)

        if exp.fully_applied_vat:
            return True
        self.unlink_move_tax(cr, uid, exp, context=context)
        for invoice in exp.invoice_ids:
            for tax in invoice.tax_line:
                if tax.tax_id.tax_voucher_ok:
                    account_tax_voucher = tax.tax_id.account_paid_voucher_id.id
                    account_tax_collected = tax.tax_id.account_collected_id.id
                    factor = acc_voucher_obj.get_percent_pay_vs_invoice(cr, uid,
                        tax.amount, tax.amount, context=context)
                    move_lines_tax = acc_voucher_obj.\
                                            _preparate_move_line_tax(cr, uid,
                        account_tax_voucher,
                        account_tax_collected, exp.account_move_id.id,
                        'payment', invoice.partner_id.id,
                        exp.account_move_id.period_id.id,
                        exp.account_move_id.journal_id.id,
                        exp.account_move_id.date, company_currency,
                        tax.amount, tax.amount,
                        current_currency,
                        False, tax.name, tax.account_analytic_id and\
                            tax.account_analytic_id.id or False,
                        tax.base_amount, factor, context=context)
                        
                    for move_line_tax in move_lines_tax:
                        move_create = aml_obj.create(cr ,uid, move_line_tax,
                                                context=context)
        exp.write({'fully_applied_vat':True})
        return True

    def _get_company_currency(self, cr, uid, exp_id, context=None):
        return self.pool.get('hr.expense.expense').browse(cr,
            uid, exp_id,
            context).account_move_id.journal_id.company_id.currency_id.id

    def _get_current_currency(self, cr, uid, exp_id, context=None):
        exp = self.pool.get('hr.expense.expense').browse(cr, uid, exp_id,
                                                                    context)
        return exp.currency_id.id or\
                self._get_company_currency(cr ,uid, exp_id, context)

    def unlink_move_tax(self, cr, uid, exp, context={}):
        aml_obj = self.pool.get('account.move.line')
        acc_tax_v = []
        acc_tax_c = []
        for invoice in exp.invoice_ids:
            for tax in invoice.tax_line:
                if tax.tax_id.tax_voucher_ok:
                    acc_tax_v.append(tax.tax_id.account_paid_voucher_id.id)
                    acc_tax_c.append(tax.tax_id.account_collected_id.id)
        acc_inv_tax = list( set( acc_tax_v + acc_tax_c ) )
        move_ids = aml_obj.search(cr, uid, [
                ('move_id', '=', exp.account_move_id.id),
                ('account_id', 'in', ( acc_inv_tax ))
        ])
        aml_obj.unlink(cr, uid, move_ids)
        return True
    