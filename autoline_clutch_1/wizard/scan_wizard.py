# -*- coding: utf-8 -*-

import logging
import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PlcScanWizard(models.TransientModel):
    _name = 'plc.scan.wizard'
    _description = 'PLC Scan QR Code Wizard'

    cycle_id = fields.Many2one(
        'plc.cycle',
        string='Cycle',
        help="Cycle to match against (optional)"
    )
    scanned_data = fields.Text(
        string='Scanned Data',
        required=True,
        help="Raw scanned QR code data"
    )
    scanner_id = fields.Char(
        string='Scanner ID',
        help="ID of the scanner device used"
    )
    workstation_id = fields.Many2one(
        'plc.workstation',
        string='Workstation',
        help="Workstation where scan occurred"
    )
    
    # Parsed data
    parsed_cycle_number = fields.Char(
        string='Parsed Cycle Number',
        compute='_compute_parsed_data',
        readonly=True
    )
    parsed_part_name = fields.Char(
        string='Parsed Part Name',
        compute='_compute_parsed_data',
        readonly=True
    )
    parsed_barcode = fields.Char(
        string='Parsed Barcode',
        compute='_compute_parsed_data',
        readonly=True
    )
    parsed_datetime = fields.Datetime(
        string='Parsed DateTime',
        compute='_compute_parsed_data',
        readonly=True
    )
    
    # Match results
    match_status = fields.Selection([
        ('not_processed', 'Not Processed'),
        ('matched', 'Matched'),
        ('not_found', 'Not Found'),
        ('invalid_data', 'Invalid Data'),
        ('duplicate', 'Duplicate Scan')
    ], string='Match Status', default='not_processed', readonly=True)
    
    matched_cycle_id = fields.Many2one(
        'plc.cycle',
        string='Matched Cycle',
        readonly=True
    )
    match_message = fields.Text(
        string='Match Message',
        readonly=True
    )

    @api.depends('scanned_data')
    def _compute_parsed_data(self):
        for record in self:
            if record.scanned_data:
                try:
                    data = json.loads(record.scanned_data)
                    record.parsed_cycle_number = data.get('cycle_number')
                    record.parsed_part_name = data.get('part_name')
                    record.parsed_barcode = data.get('barcode')
                    record.parsed_datetime = data.get('cycle_datetime')
                except json.JSONDecodeError:
                    record.parsed_cycle_number = False
                    record.parsed_part_name = False
                    record.parsed_barcode = False
                    record.parsed_datetime = False
            else:
                record.parsed_cycle_number = False
                record.parsed_part_name = False
                record.parsed_barcode = False
                record.parsed_datetime = False

    def action_process_scan(self):
        """Process the scanned QR code"""
        self.ensure_one()
        
        if not self.scanned_data:
            raise UserError(_('No scanned data provided'))
        
        try:
            # Create scan log
            scan_log_vals = {
                'scanned_data': self.scanned_data,
                'scanner_id': self.scanner_id,
                'workstation_id': self.workstation_id.id if self.workstation_id else None,
            }
            
            scan_log = self.env['qr.code.log'].create(scan_log_vals)
            
            # Find matching cycle
            if scan_log.find_matching_cycle():
                self.match_status = 'matched'
                self.matched_cycle_id = scan_log.cycle_id.id
                self.match_message = _('QR code successfully matched with cycle %s') % scan_log.cycle_id.cycle_number
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Match Found'),
                        'message': self.match_message,
                        'type': 'success',
                    }
                }
            else:
                self.match_status = scan_log.match_status
                self.matched_cycle_id = False
                self.match_message = scan_log._get_status_message(scan_log.match_status)
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('No Match'),
                        'message': self.match_message,
                        'type': 'warning',
                    }
                }
                
        except Exception as e:
            _logger.error(f"Error processing scan: {e}")
            self.match_status = 'invalid_data'
            self.match_message = _('Error processing scan: %s') % str(e)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': self.match_message,
                    'type': 'danger',
                }
            }

    def action_view_matched_cycle(self):
        """View the matched cycle"""
        self.ensure_one()
        
        if not self.matched_cycle_id:
            raise UserError(_('No matched cycle found'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Matched Cycle'),
            'res_model': 'plc.cycle',
            'res_id': self.matched_cycle_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_scan_log(self):
        """View the scan log"""
        self.ensure_one()
        
        scan_log = self.env['qr.code.log'].search([
            ('scanned_data', '=', self.scanned_data)
        ], limit=1)
        
        if not scan_log:
            raise UserError(_('No scan log found'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Scan Log'),
            'res_model': 'qr.code.log',
            'res_id': scan_log.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_clear_data(self):
        """Clear the scanned data"""
        self.ensure_one()
        
        self.write({
            'scanned_data': '',
            'match_status': 'not_processed',
            'matched_cycle_id': False,
            'match_message': '',
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Scan QR Code'),
            'res_model': 'plc.scan.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
