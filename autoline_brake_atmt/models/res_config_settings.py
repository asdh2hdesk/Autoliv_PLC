# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    expiry_date = fields.Date(
        string='Module Expiry Date',
        compute='_compute_expiry_date',
        inverse='_inverse_expiry_date',
        readonly=False,
        help="Set the expiry date for this module. The module will be blocked after this date."
    )
    expiry_date_str = fields.Char(
        string='Module Expiry Date (String)',
        config_parameter='autoline_brake_atmt.expiry_date'
    )

    @api.depends('expiry_date_str')
    def _compute_expiry_date(self):
        """Convert string date from config parameter to Date field"""
        for setting in self:
            if setting.expiry_date_str:
                try:
                    setting.expiry_date = fields.Date.to_date(setting.expiry_date_str)
                except (ValueError, TypeError):
                    setting.expiry_date = False
            else:
                setting.expiry_date = False

    def _inverse_expiry_date(self):
        """Convert Date field to string and store in config parameter"""
        for setting in self:
            if setting.expiry_date:
                setting.expiry_date_str = fields.Date.to_string(setting.expiry_date)
            else:
                setting.expiry_date_str = False

