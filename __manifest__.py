{
    'name': 'DormEXPO',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Manage your dorm budget and track expenses',
    'description': """
        DormEXPO - Dorm Expense Tracker
        ================================
        * Track daily dorm expenses
        * Categorize spending (food, transport, books, etc.)
        * Upload and attach receipts
        * Visual expense analytics and charts
        * Monthly budget tracking
        * Export expense reports
        * Multi-user support with privacy controls
    """,
    'author': 'Your Name',
    'website': 'https://www.dormexpo.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
        'web_dashboard',
    ],
    'data': [
        'security/dorm_expense_security.xml',
        'security/ir.model.access.csv',
        'data/dorm_expense_categories.xml',
        'views/dorm_expense_views.xml',
        'views/dorm_expense_menus.xml',
        'report/expense_report_template.xml',
        'wizard/expense_report_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'dorm_expo/static/src/css/dorm_expo.css',
            'dorm_expo/static/src/js/expense_dashboard.js',
        ],
    },
    'demo': [
        'data/dorm_expense_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
