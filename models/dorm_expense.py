from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import base64


class DormExpenseCategory(models.Model):
    """Expense categories for better organization"""
    _name = 'dorm.expense.category'
    _description = 'Dorm Expense Category'
    _order = 'sequence, name'

    name = fields.Char(string='Category Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    color = fields.Integer(string='Color Index')
    icon = fields.Char(string='Icon Class', help='Font Awesome icon class')
    active = fields.Boolean(default=True)
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Category code must be unique!')
    ]


class DormExpense(models.Model):
    """Main expense tracking model"""
    _name = 'dorm.expense'
    _description = 'Dorm Expense'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, create_date desc'
    _rec_name = 'description'

    # Basic Information
    description = fields.Char(
        string='Description',
        required=True,
        tracking=True,
        help='Brief description of the expense'
    )

    date = fields.Date(
        string='Expense Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        index=True
    )

    amount = fields.Monetary(
        string='Amount',
        required=True,
        currency_field='currency_id',
        tracking=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    category_id = fields.Many2one(
        'dorm.expense.category',
        string='Category',
        required=True,
        tracking=True,
        ondelete='restrict'
    )

    # Receipt Management
    receipt = fields.Binary(
        string='Receipt',
        attachment=True,
        help='Upload receipt image or PDF'
    )

    receipt_filename = fields.Char(string='Receipt Filename')

    receipt_preview = fields.Image(
        string='Receipt Preview',
        compute='_compute_receipt_preview',
        store=True
    )

    # User and Access Control
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
        index=True
    )

    is_shared = fields.Boolean(
        string='Shared',
        default=False,
        tracking=True,
        help='If checked, this expense can be viewed by other users'
    )

    shared_with_ids = fields.Many2many(
        'res.users',
        'dorm_expense_shared_users_rel',
        'expense_id',
        'user_id',
        string='Shared With Users'
    )

    # Additional Information
    notes = fields.Text(string='Notes')

    tags = fields.Char(string='Tags', help='Comma-separated tags for filtering')

    location = fields.Char(string='Location', help='Where the expense occurred')

    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('mobile', 'Mobile Payment'),
        ('transfer', 'Bank Transfer'),
        ('other', 'Other')
    ], string='Payment Method', default='card', tracking=True)

    # Status and Workflow
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid')
    ], string='Status', default='draft', tracking=True, required=True)

    # System Fields
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    active = fields.Boolean(default=True)

    # Computed Fields
    month = fields.Char(
        string='Month',
        compute='_compute_period',
        store=True,
        index=True
    )

    year = fields.Char(
        string='Year',
        compute='_compute_period',
        store=True,
        index=True
    )

    week = fields.Char(
        string='Week',
        compute='_compute_period',
        store=True
    )

    amount_display = fields.Char(
        string='Amount Display',
        compute='_compute_amount_display'
    )

    days_ago = fields.Integer(
        string='Days Ago',
        compute='_compute_days_ago'
    )

    # Computed Fields Implementation
    @api.depends('date')
    def _compute_period(self):
        for record in self:
            if record.date:
                record.month = record.date.strftime('%B %Y')
                record.year = str(record.date.year)
                record.week = f"Week {record.date.isocalendar()[1]}, {record.date.year}"
            else:
                record.month = False
                record.year = False
                record.week = False

    @api.depends('receipt', 'receipt_filename')
    def _compute_receipt_preview(self):
        for record in self:
            if record.receipt and record.receipt_filename:
                # Check if it's an image file
                if any(ext in record.receipt_filename.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                    record.receipt_preview = record.receipt
                else:
                    record.receipt_preview = False
            else:
                record.receipt_preview = False

    @api.depends('amount', 'currency_id')
    def _compute_amount_display(self):
        for record in self:
            if record.amount and record.currency_id:
                record.amount_display = f"{record.currency_id.symbol}{record.amount:.2f}"
            else:
                record.amount_display = "$0.00"

    @api.depends('date')
    def _compute_days_ago(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.date:
                delta = today - record.date
                record.days_ago = delta.days
            else:
                record.days_ago = 0

    # Constraints
    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_("Amount must be greater than zero."))
            if record.amount > 999999.99:
                raise ValidationError(_("Amount seems unusually high. Please verify."))

    @api.constrains('date')
    def _check_date(self):
        for record in self:
            if record.date > fields.Date.context_today(self):
                raise ValidationError(_("Expense date cannot be in the future."))
            # Warn if expense is too old (more than 1 year)
            one_year_ago = fields.Date.context_today(self) - timedelta(days=365)
            if record.date < one_year_ago:
                raise ValidationError(_("Expense date is more than 1 year old. Please verify."))

    # CRUD Operations
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Auto-set user_id if not provided
            if 'user_id' not in vals:
                vals['user_id'] = self.env.user.id

        expenses = super().create(vals_list)

        # Send notification
        for expense in expenses:
            expense.message_post(
                body=_("Expense created: %s for %s") % (expense.description, expense.amount_display)
            )

        return expenses

    def write(self, vals):
        result = super().write(vals)

        # Log significant changes
        if 'amount' in vals or 'state' in vals:
            for record in self:
                record.message_post(
                    body=_("Expense updated: %s") % record.description
                )

        return result

    def unlink(self):
        # Prevent deletion of approved expenses
        if any(expense.state in ['approved', 'paid'] for expense in self):
            raise UserError(_("Cannot delete approved or paid expenses."))

        return super().unlink()

    # Workflow Actions
    def action_submit(self):
        """Submit expense for approval"""
        self.write({'state': 'submitted'})
        self.message_post(body=_("Expense submitted for approval"))
        return True

    def action_approve(self):
        """Approve expense (requires manager role)"""
        self.write({'state': 'approved'})
        self.message_post(body=_("Expense approved"))
        # Send notification to user
        self.user_id.notify_success(
            message=_("Your expense '%s' has been approved") % self.description
        )
        return True

    def action_reject(self):
        """Reject expense"""
        self.write({'state': 'rejected'})
        self.message_post(body=_("Expense rejected"))
        return True

    def action_reset_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})
        return True

    def action_mark_paid(self):
        """Mark expense as paid"""
        self.write({'state': 'paid'})
        self.message_post(body=_("Expense marked as paid"))
        return True

    # Business Logic Methods
    def action_view_receipt(self):
        """Open receipt in full view"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/dorm.expense/{self.id}/receipt/{self.receipt_filename}',
            'target': 'new',
        }

    def action_duplicate(self):
        """Duplicate expense"""
        self.ensure_one()
        new_expense = self.copy({
            'description': f"{self.description} (Copy)",
            'date': fields.Date.context_today(self),
            'state': 'draft',
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'dorm.expense',
            'view_mode': 'form',
            'res_id': new_expense.id,
            'target': 'current',
        }

    @api.model
    def get_monthly_stats(self, user_id=None, month=None, year=None):
        """Get monthly expense statistics"""
        if not user_id:
            user_id = self.env.user.id

        if not month:
            month = datetime.now().month
        if not year:
            year = datetime.now().year

        domain = [
            ('user_id', '=', user_id),
            ('date', '>=', f"{year}-{month:02d}-01"),
            ('date', '<=', f"{year}-{month:02d}-31"),
            ('state', '!=', 'rejected')
        ]

        expenses = self.search(domain)

        total = sum(expenses.mapped('amount'))
        by_category = {}
        for expense in expenses:
            cat_name = expense.category_id.name
            by_category[cat_name] = by_category.get(cat_name, 0) + expense.amount

        return {
            'total': total,
            'count': len(expenses),
            'average': total / len(expenses) if expenses else 0,
            'by_category': by_category,
            'top_category': max(by_category.items(), key=lambda x: x[1])[0] if by_category else None,
        }


class DormExpenseReport(models.AbstractModel):
    """Report model for analytics"""
    _name = 'report.dorm_expo.expense_report'
    _description = 'Dorm Expense Report'

    def _get_report_values(self, docids, data=None):
        docs = self.env['dorm.expense'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'dorm.expense',
            'docs': docs,
            'data': data,
        }
