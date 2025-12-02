# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from odoo import models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ModuleExpiry(models.AbstractModel):
    """Utility model for checking module expiry"""
    _name = 'autoline_brake_atmt.module_expiry'
    _description = 'Module Expiry Utility'

    @api.model
    def check_expiry(self):
        """Check if module has expired and raise exception if expired"""
        module_name = 'autoline_brake_atmt'
        expiry_param_key = f'{module_name}.expiry_date'
        
        # Get expiry date from system parameter
        expiry_date_str = self.env['ir.config_parameter'].sudo().get_param(expiry_param_key)
        
        # If no expiry date is set, allow access (graceful handling)
        if not expiry_date_str:
            _logger.warning(f"Expiry date not configured for module {module_name}")
            return True
        
        try:
            # Parse expiry date (format: YYYY-MM-DD)
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
            current_date = datetime.now().date()
            
            # Log for debugging
            _logger.info(f"Module {module_name} expiry check: Current Date={current_date}, Expiry Date={expiry_date}")
            
            # Check if expired (use >= to block on expiry date itself)
            if current_date >= expiry_date:
                _logger.warning(f"Module {module_name} has EXPIRED! Current Date={current_date}, Expiry Date={expiry_date}")
                raise UserError(_(
                    "⚠️ MODULE EXPIRED ⚠️\n\n"
                    "This module has expired and access is now blocked.\n\n"
                    "Expiry Date: %s\n"
                    "Current Date: %s\n\n"
                    "Please contact your administrator to renew the license."
                ) % (expiry_date_str, current_date.strftime('%Y-%m-%d')))
            
            return True
            
        except ValueError as e:
            _logger.error(f"Invalid expiry date format for {module_name}: {expiry_date_str}. Error: {e}")
            # If date format is invalid, allow access but log warning
            return True
    
    @api.model
    def get_expiry_date(self):
        """Get expiry date from system parameter"""
        module_name = 'autoline_brake_atmt'
        expiry_param_key = f'{module_name}.expiry_date'
        return self.env['ir.config_parameter'].sudo().get_param(expiry_param_key)
    
    @api.model
    def is_expired(self):
        """Check if module is expired (returns boolean, doesn't raise exception)"""
        try:
            self.check_expiry()
            return False
        except UserError:
            return True


