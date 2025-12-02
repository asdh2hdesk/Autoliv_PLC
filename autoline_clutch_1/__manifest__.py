# -*- coding: utf-8 -*-
{
    'name': 'Autoline CLUTCH',
    'version': '18.0.1.0.6',
    'category': 'Manufacturing',
    'summary': 'Mitsubishi PLC Integration with ModbusTCP, QR Code Printing and Dashboard',
    'description': """
        Autoline PLC Integration Module
        CLUTCH MACHINE
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
        'data/expiry_data.xml',
        'views/plc_cycle_views.xml',
        'views/plc_config_views.xml',
        'views/dashboard_views.xml',
        'views/manual_print.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'autoline_clutch_1/static/src/js/dashboard.js',
            'autoline_clutch_1/static/src/js/plc_monitor.js',
            'autoline_clutch_1/static/src/xml/dashboard.xml',
            'autoline_clutch_1/static/src/css/dashboard.css',
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
