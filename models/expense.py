# -*- coding: utf-8 -*-
from odoo import models, fields, api

class Expense(models.Model):
    _name = 'dormexpo.expense'
    _description = 'Expense Record'

    name = fields.Char(string='Description', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    amount = fields.Float(string='Amount', required=True)
    category = fields.Selection([
        ('food', 'Food'),
        ('utilities', 'Utilities'),
        ('maintenance', 'Maintenance'),
        ('other', 'Other'),
    ], string='Category', default='other')
    receipt = fields.Binary(string='Receipt')
    receipt_name = fields.Char(string='Receipt Filename')
