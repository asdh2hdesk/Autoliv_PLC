# -*- coding: utf-8 -*-

import logging
import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class QrCodeLog(models.Model):
    _name = 'qr.code.log'
    _description = 'QR Code Scan Log'
    _order = 'scan_datetime desc'
    _rec_name = 'scan_reference'

    @api.model
    def search(self, domain, offset=0, limit=None, order=None):
        """Override search to check module expiry"""
        # Check module expiry before allowing access
        self.env['autoline_clutch_1.module_expiry'].check_expiry()
        return super(QrCodeLog, self).search(domain, offset=offset, limit=limit, order=order)

    # Basic Information
    scan_reference = fields.Char(
        string='Scan Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    scanned_data = fields.Text(
        string='Scanned Data',
        required=True,
        help="Raw scanned QR code data"
    )
    scan_datetime = fields.Datetime(
        string='Scan DateTime',
        required=True,
        default=fields.Datetime.now
    )
    
    # Parsed Data
    cycle_number = fields.Char(
        string='Cycle Number',
        help="Extracted cycle number from QR code"
    )
    part_name = fields.Char(
        string='Part Name',
        help="Extracted part name from QR code"
    )
    barcode = fields.Char(
        string='Barcode',
        help="Extracted barcode from QR code"
    )
    cycle_datetime = fields.Datetime(
        string='Cycle DateTime',
        help="Extracted cycle datetime from QR code"
    )
    
    # Matching Information
    cycle_id = fields.Many2one(
        'plc.cycle',
        string='Matched Cycle',
        help="Cycle record that matches this scan"
    )
    match_status = fields.Selection([
        ('matched', 'Matched'),
        ('not_found', 'Not Found'),
        ('invalid_data', 'Invalid Data'),
        ('duplicate', 'Duplicate Scan')
    ], string='Match Status', default='not_found')
    
    # Additional Information
    scanner_id = fields.Char(
        string='Scanner ID',
        help="ID of the scanner device used"
    )
    operator_id = fields.Many2one(
        'res.users',
        string='Operator',
        default=lambda self: self.env.user
    )
    workstation_id = fields.Many2one(
        'plc.workstation',
        string='Workstation',
        help="Workstation where scan occurred"
    )
    notes = fields.Text(string='Notes')
    match_message = fields.Text(
        string='Match Message',
        readonly=True,
        help="Message about the scan match result"
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Create QR code log records with batch support"""
        for vals in vals_list:
            if vals.get('scan_reference', _('New')) == _('New'):
                vals['scan_reference'] = self.env['ir.sequence'].next_by_code('qr.code.log') or _('New')
            
            # Parse scanned data
            if vals.get('scanned_data'):
                parsed_data = self._parse_scanned_data(vals['scanned_data'])
                vals.update(parsed_data)
            
            # Ensure scan_datetime is set
            if not vals.get('scan_datetime'):
                vals['scan_datetime'] = fields.Datetime.now()
        
        records = super(QrCodeLog, self).create(vals_list)
        _logger.info(f"[QR LOG] Created {len(records)} scan log record(s)")
        return records

    def _parse_scanned_data(self, scanned_data):
        """Parse scanned QR code data (new format: 32-char string)"""
        # New format is a 32-character string, not JSON
        # Try to parse as JSON first (for backward compatibility)
        try:
            data = json.loads(scanned_data)
            return {
                'cycle_number': data.get('cycle_number'),
                'part_name': data.get('part_name'),
                'barcode': data.get('barcode'),
                'cycle_datetime': data.get('cycle_datetime'),
            }
        except (json.JSONDecodeError, TypeError):
            # Not JSON, treat as 32-character string format
            # Store as-is, will be matched directly with qr_code_data
            return {}

    def find_matching_cycle(self):
        """Find matching cycle record (new format: match by qr_code_data string)"""
        self.ensure_one()
        
        if not self.scanned_data:
            self.match_status = 'invalid_data'
            self.match_message = "No scanned data provided"
            _logger.warning(f"[QR LOG] No scanned data for log ID {self.id}")
            return False
        
        scanned_string = self.scanned_data.strip()
        _logger.info(f"[QR LOG] Finding match for scanned data: {scanned_string[:32]}... (Log ID: {self.id})")
        
        # Try to find cycle by QR code data (32-char string)
        cycle = self.env['plc.cycle'].search([
            ('qr_code_data', '=', scanned_string)
        ], limit=1)
        
        if cycle:
            _logger.info(f"[QR LOG] Found matching cycle: {cycle.cycle_number} (ID: {cycle.id})")
            
            # Check if already scanned
            existing_scan = self.env['qr.code.log'].search([
                ('cycle_id', '=', cycle.id),
                ('match_status', '=', 'matched'),
                ('id', '!=', self.id)
            ], limit=1)
            
            if existing_scan:
                self.match_status = 'duplicate'
                self.match_message = f"Duplicate scan of cycle {cycle.cycle_number}"
                self.notes = f"Duplicate scan of cycle {cycle.cycle_number}"
                _logger.warning(f"[QR LOG] Duplicate scan detected for cycle {cycle.cycle_number}")
                return False
            
            self.cycle_id = cycle.id
            self.match_status = 'matched'
            self.match_message = f"Successfully matched with cycle {cycle.cycle_number}"
            
            # Update cycle record
            cycle.qr_code_scanned = True
            cycle.qr_match_status = 'matched'
            cycle.scan_datetime = self.scan_datetime
            cycle.qr_scan_datetime = self.scan_datetime
            
            _logger.info(f"[QR LOG] ✅ Matched and updated cycle {cycle.cycle_number}")
            return True
        else:
            _logger.warning(f"[QR LOG] No cycle found matching QR code: {scanned_string[:32]}...")
            
            # Try old format matching (by cycle_number or barcode) for backward compatibility
            if self.cycle_number or self.barcode:
                domain = []
                if self.cycle_number:
                    domain.append(('cycle_number', '=', self.cycle_number))
                if self.barcode:
                    domain.append(('barcode', '=', self.barcode))
                
                if domain:
                    cycle = self.env['plc.cycle'].search(domain, limit=1)
                    if cycle:
                        self.cycle_id = cycle.id
                        self.match_status = 'matched'
                        self.match_message = f"Successfully matched with cycle {cycle.cycle_number}"
                        cycle.qr_code_scanned = True
                        cycle.scan_datetime = self.scan_datetime
                        _logger.info(f"[QR LOG] Matched via old format: cycle {cycle.cycle_number}")
                        return True
            
            self.match_status = 'not_found'
            self.match_message = "No matching cycle found in database"
            _logger.warning(f"[QR LOG] ❌ No match found for scan log ID {self.id}")
            return False

    def action_find_match(self):
        """Action to find matching cycle"""
        self.ensure_one()
        if self.find_matching_cycle():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Match Found'),
                    'message': _('QR code successfully matched with cycle %s') % self.cycle_id.cycle_number,
                    'type': 'success',
                }
            }
        else:
            message = _('No matching cycle found')
            if self.match_status == 'duplicate':
                message = _('This QR code has already been scanned')
            elif self.match_status == 'invalid_data':
                message = _('Invalid QR code data format')
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Match'),
                    'message': message,
                    'type': 'warning',
                }
            }

    @api.model
    def process_scan(self, scanned_data, scanner_id=None, workstation_id=None):
        """Process a new QR code scan"""
        vals = {
            'scanned_data': scanned_data,
            'scanner_id': scanner_id,
            'workstation_id': workstation_id,
        }
        
        scan_log = self.create(vals)
        scan_log.find_matching_cycle()
        
        return {
            'scan_log_id': scan_log.id,
            'match_status': scan_log.match_status,
            'cycle_id': scan_log.cycle_id.id if scan_log.cycle_id else None,
            'message': self._get_status_message(scan_log.match_status)
        }

    def _get_status_message(self, status):
        """Get status message for scan result"""
        messages = {
            'matched': _('QR code successfully matched!'),
            'not_found': _('No matching cycle found in database.'),
            'invalid_data': _('Invalid QR code data format.'),
            'duplicate': _('This QR code has already been scanned.'),
        }
        return messages.get(status, _('Unknown status'))

    @api.model
    def get_scan_statistics(self, date_from=None, date_to=None):
        """Get scan statistics for dashboard"""
        domain = []
        if date_from:
            domain.append(('scan_datetime', '>=', date_from))
        if date_to:
            domain.append(('scan_datetime', '<=', date_to))
        
        scans = self.search(domain)
        
        return {
            'total_scans': len(scans),
            'matched_scans': len(scans.filtered(lambda s: s.match_status == 'matched')),
            'not_found_scans': len(scans.filtered(lambda s: s.match_status == 'not_found')),
            'invalid_data_scans': len(scans.filtered(lambda s: s.match_status == 'invalid_data')),
            'duplicate_scans': len(scans.filtered(lambda s: s.match_status == 'duplicate')),
            'match_rate': (len(scans.filtered(lambda s: s.match_status == 'matched')) / len(scans) * 100) if scans else 0,
        }
