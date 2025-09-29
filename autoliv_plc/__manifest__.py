{
    'name': 'PLC Integration with QR Code',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Connect Odoo 18 to Mitsubishi PLC via Modbus TCP with QR Code generation',
    'description': """
        This module provides:
        - Modbus TCP communication with Mitsubishi PLC
        - Data logging from PLC cycle completion
        - QR code generation and printing to Zebra ZD421
        - QR code scanning and verification
    """,
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/plc_data_views.xml',
        'views/plc_config_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'autoliv_plc/static/src/js/qr_scanner.js',
            'autoliv_plc/static/src/css/plc_integration.css',
            'autoliv_plc/views/plc_dashboard_templates.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
