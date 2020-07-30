from odoo import api, fields, models, _ 
from odoo.osv import expression
from odoo.tools import float_is_zero
from odoo.tools import float_compare, float_round, float_repr
from odoo.tools.misc import formatLang
from odoo.exceptions import UserError, ValidationError

import time
import math
import logging

_logger = logging.getLogger(__name__)
STATES = [('draft', 'Draft'), ('open', 'Open'), ('close', 'Close'), ('reject', 'Reject')]

class vit_giro(models.Model):
    _name = 'vit.giro'
    _rec_name = 'name'
    _description = 'Giro'
    
    # def _get_invoices(self, cr, uid, ids, field, arg, context=None):
    def _get_invoices(self):
        results = {}
        # for giro in self.browse(cr, uid, ids, context=context):
        for giro in self:
            results[giro.id] = ""
            for gi in giro.giro_invoice_ids:
                results[giro.id] += "%s " % (gi.invoice_id.number or "")
        return results

    
    name = fields.Char('Number', help='Nomor Giro', readonly=True, states={'draft': [('readonly', False)]})
    due_date =  fields.Date('Due Date', help='', readonly=True, states={'draft': [('readonly', False)]})
    receive_date = fields.Datetime('Receive Date', help='', readonly=True,
                                    states={'draft': [('readonly', False)]}, default=time.strftime("%Y-%m-%d %H:%M:%S") )
    clearing_date =  fields.Datetime('Clearing Date', help='', readonly=True,
                                        states={'draft': [('readonly', False)]})
    amount = fields.Float('Amount', help='', readonly=True, states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one('res.partner', 'Partner', help='', readonly=True,
                                    states={'draft': [('readonly', False)]})
    journal_id = fields.Many2one('account.journal', 'Bank Journal', domain=[('type', '=', 'bank')], help='',
                                    readonly=True, states={'draft': [('readonly', False)]})
    giro_invoice_ids = fields.One2many('vit.giro_invioce', 'giro_id', readonly=True,
                                        states={'draft': [('readonly', False)]})
    # invoice_names = fields.function(_get_invoices, type='char', string="Allocated Invoices")
    invoice_names = fields.Char(compute='_get_invoices', type='char', string="Allocated Invoices")
    type = fields.Selection(
        [('payment', 'Payment'),
        ('receipt', 'Receipt')],
        # [('purchase', 'Purchase'),
        # ('sale', 'Sale')],
        "Type",
        required=True, readonly=True, states={'draft': [('readonly', False)]}, default='payment' )
    invoice_type = fields.Char('Invoice Type', readonly=True, states={'draft': [('readonly', False)]}, default='in_invoice' )
    state = fields.Selection(string="State", selection=STATES, required=True, readonly=True, default=STATES[0][0])
    # _columns = {
    #     'name': fields.Char('Number', help='Nomor Giro', readonly=True, states={'draft': [('readonly', False)]}),
    #     'due_date': fields.Date('Due Date', help='', readonly=True, states={'draft': [('readonly', False)]}),
    #     'receive_date': fields.Datetime('Receive Date', help='', readonly=True,
    #                                     states={'draft': [('readonly', False)]}),
    #     'clearing_date': fields.Datetime('Clearing Date', help='', readonly=True,
    #                                      states={'draft': [('readonly', False)]}),
    #     'amount': fields.Float('Amount', help='', readonly=True, states={'draft': [('readonly', False)]}),
    #     'partner_id': fields.Many2one('res.partner', 'Partner', help='', readonly=True,
    #                                   states={'draft': [('readonly', False)]}),
    #     'journal_id': fields.Many2one('account.journal', 'Bank Journal', domain=[('type', '=', 'bank')], help='',
    #                                   readonly=True, states={'draft': [('readonly', False)]}),
    #     'giro_invoice_ids': fields.One2many('vit.giro_invioce', 'giro_id', readonly=True,
    #                                         states={'draft': [('readonly', False)]}),
    #     'invoice_names': fields.Function(_get_invoices, type='Char', string="Allocated Invoices"),
    #     'type': fields.Selection([
    #         ('payment', 'Payment'),
    #         ('receipt', 'Receipt')],
    #         "Type",
    #         required=True, readonly=True, states={'draft': [('readonly', False)]}),
    #     'invoice_type': fields.Char('Invoice Type', readonly=True, states={'draft': [('readonly', False)]}),
    #     'state': fields.Selection(string="State", selection=STATES, required=True, readonly=True)
    # }
    
    _sql_constraints = [('name_uniq', 'unique(name)', _('Nomor Giro tidak boleh sama'))]
    
    # def _cek_total(self, cr, uid, ids, context=None):
    def _cek_total(self):
        inv_total = 0.0
        for giro in self:
        # for giro in self.browse(cr, uid, ids, context=context):
            for gi in giro.giro_invoice_ids:
                inv_total += gi.amount
            
            if giro.amount == inv_total:
                return True
        
        return False
    
    _constraints = [(_cek_total, _('Total amount allocated for the invoices must be the same as total Giro amount'),
                     ['amount', 'giro_invoice_ids'])]
    
    # _defaults = {
    #     'state': STATES[0][0],
    #     'receive_date': time.strftime("%Y-%m-%d %H:%M:%S"),
    #     'type': 'payment',
    #     'inv_type': 'in_invoice',
    # }
    
    
    # def action_cancel(self, cr, uid, ids, context=None):
    def action_cancel(self):
        data = {'state': STATES[0][0]}
        # self.write(cr, uid, ids, data, context=context)
        self.write(data)
    
    # def action_confirm(self, cr, uid, ids, context=None):
    def action_confirm(self):
        data = {'state': STATES[1][0]}
        self.write(data)
    
    # def action_clearing(self, cr, uid, ids, context=None):
    def action_clearing(self):
        
        # voucher_obj = self.pool.get('account.voucher')
        # users_obj = self.pool.get('res.users')
        voucher_obj = self.env['account.voucher']
        users_obj = self.env['res.users'] 
        # u1 = users_obj.browse(cr, uid, uid, context=context)
        u1 = users_obj.browse( self.env.user.id )
        company_id = u1.company_id.id
        
        # for giro in self.browse(cr, uid, ids, context=context):
        for giro in self:
            for gi in giro.giro_invoice_ids:
                invoice_id = gi.invoice_id
                partner_id = giro.partner_id.id
                amount = gi.amount
                journal_id = giro.journal_id
                type = giro.type
                name = giro.name
                # vid = voucher_obj.create_payment(cr, uid, invoice_id, partner_id, amount, journal_id, type, name,
                #                                  company_id,
                #                                  context=context)
                vid = voucher_obj.create_payment(invoice_id, partner_id, amount, journal_id, type, name,
                                                 company_id )
                # voucher_obj.payment_confirm(cr, uid, vid, context=context)
                voucher_obj.payment_confirm( vid )
        
        data = {'state': STATES[2][0],
                'clearing_date': time.strftime("%Y-%m-%d %H:%M:%S")}

        # self.write(cr, uid, ids, data, context=context)
        self.write( data )
    
    # def action_reject(self, cr, uid, ids, context=None):
    def action_reject(self):
        data = {'state': STATES[3][0]}
        # self.write(cr, uid, ids, data, context=context)
        self.write(data)

    
    @api.onchange('type')
    def on_change_type(self):
        inv_type = 'in_invoice'
        if self.type == 'payment':
            inv_type = 'in_invoice'
        elif self.type == 'receipt':
            inv_type = 'out_invoice'
        self.invoice_type = inv_type

    # @api.onchange('amount')
    # def on_change_amount(self):
    #     self.amount = 500000
    #     self.name = "tes"
            

class vit_giro_invoice(models.Model):
    _name = 'vit.giro_invioce'
    _description = 'Giro vs Invoice'
    
    giro_id = fields.Many2one('vit.giro', 'Giro', help='')
    invoice_id = fields.Many2one('account.invoice', 'Invoice',
                                    help='Invoice to be paid',
                                    domain=[('state', '=', 'open')])
    amount_invoice = fields.Float('Invoice Amount')
    amount = fields.Float('Amount Allocated')
    # _columns = {
    #     'giro_id': fields.Many2one('vit.giro', 'Giro', help=''),
    #     'invoice_id': fields.Many2one('account.invoice', 'Invoice',
    #                                   help='Invoice to be paid',
    #                                   domain=[('state', '=', 'open')]),
    #     # 'amount_invoice': fields.related("invoice_id", "residual",
    #     #             relation="account.invoice",
    #     #             type="float", string="Invoice Amount", store=True),
    #     'amount_invoice': fields.Float('Invoice Amount'),
    #     'amount': fields.Float('Amount Allocated'),
    # }
    
    @api.onchange('invoice_id')
    def on_change_invoice_id(self):
        self.amount_invoice = self.invoice_id.residual


class account_invoice(models.Model):
    _name = 'account.invoice'
    _inherit = 'account.invoice'
    
    giro_invoice_ids = fields.One2many('vit.giro_invioce', 'invoice_id', string="Giro" )

    # _columns = {
    #     'giro_invoice_ids': fields.One2many('vit.giro_invioce', 'invoice_id', string="Giro"),
    # }
