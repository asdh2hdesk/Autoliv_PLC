# -*- coding: utf-8 -*-
{
    'name': 'AutoLiv PLC Integration',
    'version': '18.0.1.0.6',
    'category': 'Manufacturing',
    'summary': 'Mitsubishi PLC Integration with ModbusTCP, QR Code Printing and Dashboard',
    'description': """
        AutoLiv PLC Integration Module
        =============================
        
        This module provides:
        * ModbusTCP communication with Mitsubishi PLC
        * Real-time data logging from PLC cycles
        * QR code generation and printing via Zebra printer
        * QR code scanning and matching
        * Modern dashboard for tracking parts, OK/NOK status
        * Real-time monitoring and analytics
    """,
    'author': 'RAKESH ASD',
    'website': 'https://www.asdsoftwares.com',
    'depends': [
        'base',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/sequence.xml',
        'data/cron_data.xml',
        'views/plc_cycle_views.xml',
        'views/plc_config_views.xml',
        'views/dashboard_views.xml',
        'views/menu_views.xml',
        'views/print_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'autoliv_plc/static/src/js/dashboard.js',
            'autoliv_plc/static/src/js/plc_monitor.js',
            'autoliv_plc/static/src/xml/dashboard.xml',
            'autoliv_plc/static/src/css/dashboard.css',
        ],
    },
    'external_dependencies': {
        'python': [
            'pymodbus',
            'qrcode',
            'Pillow',
            'requests',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
