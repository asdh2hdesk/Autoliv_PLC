# -*- coding: utf-8 -*-

import logging
import json
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PlcCycle(models.Model):
    _name = 'plc.cycle'
    _description = 'PLC Cycle Data'
    _order = 'cycle_datetime desc'
    _rec_name = 'cycle_number'

    # Basic Information
    cycle_number = fields.Char(
        string='Cycle Number',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    part_name = fields.Char(
        string='Part Name',
        required=True,
        help="Name of the part being processed"
    )
    barcode = fields.Char(
        string='Barcode',
        required=True,
        help="Unique barcode for this cycle"
    )
    cycle_datetime = fields.Datetime(
        string='Cycle DateTime',
        required=True,
        default=fields.Datetime.now
    )
    
    # PLC Data Fields
    torque_nm = fields.Float(
        string='Torque (Nm)',
        digits=(10, 2),
        help="Torque measurement in Newton-meters"
    )
    initial_position = fields.Float(
        string='Initial Position',
        digits=(10, 3),
        help="Initial position measurement"
    )
    forward_load_after = fields.Float(
        string='Forward Load After (mm)',
        digits=(10, 3),
        help="Forward load measurement after operation"
    )
    final_position = fields.Float(
        string='Final Position',
        digits=(10, 3),
        help="Final position measurement"
    )
    cycle_time = fields.Float(
        string='Cycle Time (s)',
        digits=(10, 3),
        help="Total cycle time in seconds"
    )
    
    # Status and Results
    result = fields.Selection([
        ('ok', 'OK'),
        ('nok', 'NOK'),
        ('pending', 'Pending')
    ], string='Result', default='pending', required=True)
    
    # QR Code Information
    qr_code_data = fields.Text(
        string='QR Code Data',
        help="JSON data encoded in QR code"
    )
    qr_code_image = fields.Binary(
        string='QR Code Image',
        attachment=True
    )
    qr_code_printed = fields.Boolean(
        string='QR Code Printed',
        default=False
    )
    qr_code_scanned = fields.Boolean(
        string='QR Code Scanned',
        default=False
    )
    scan_datetime = fields.Datetime(
        string='Scan DateTime',
        help="When the QR code was scanned"
    )
    
    # Additional Information
    operator_id = fields.Many2one(
        'res.users',
        string='Operator',
        default=lambda self: self.env.user
    )
    workstation_id = fields.Many2one(
        'plc.workstation',
        string='Workstation',
        help="PLC workstation configuration"
    )
    notes = fields.Text(string='Notes')
    
    # Computed Fields
    cycle_duration = fields.Float(
        string='Cycle Duration (min)',
        compute='_compute_cycle_duration',
        store=True
    )
    is_quality_pass = fields.Boolean(
        string='Quality Pass',
        compute='_compute_quality_pass',
        store=True
    )

    @api.depends('cycle_time')
    def _compute_cycle_duration(self):
        for record in self:
            record.cycle_duration = record.cycle_time / 60.0 if record.cycle_time else 0.0

    @api.depends('result')
    def _compute_quality_pass(self):
        for record in self:
            record.is_quality_pass = record.result == 'ok'

    @api.model_create_multi
    def create(self, vals_list):
        """Create PLC cycle records with batch support"""
        for vals in vals_list:
            if vals.get('cycle_number', _('New')) == _('New'):
                vals['cycle_number'] = self.env['ir.sequence'].next_by_code('plc.cycle') or _('New')
        return super(PlcCycle, self).create(vals_list)

    def generate_qr_code_data(self):
        """Generate QR code data as JSON string"""
        self.ensure_one()
        qr_data = {
            'cycle_number': self.cycle_number,
            'part_name': self.part_name,
            'barcode': self.barcode,
            'cycle_datetime': self.cycle_datetime.isoformat(),
            'torque_nm': self.torque_nm,
            'initial_position': self.initial_position,
            'forward_load_after': self.forward_load_after,
            'final_position': self.final_position,
            'cycle_time': self.cycle_time,
            'result': self.result,
            'operator': self.operator_id.name,
        }
        self.qr_code_data = json.dumps(qr_data)
        return self.qr_code_data

    def generate_qr_code_image(self):
        """Generate QR code image"""
        try:
            import qrcode
            from io import BytesIO
            import base64
            
            if not self.qr_code_data:
                self.generate_qr_code_data()
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(self.qr_code_data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue())
            
            self.qr_code_image = img_str
            return True
        except ImportError:
            raise UserError(_("Please install qrcode and Pillow libraries: pip install qrcode Pillow"))
        except Exception as e:
            _logger.error(f"Error generating QR code: {e}")
            raise UserError(_("Error generating QR code: %s") % str(e))

    def print_qr_code(self):
        """Print QR code using Zebra printer"""
        self.ensure_one()
        if not self.qr_code_data:
            self.generate_qr_code_data()
        
        # This will be implemented with Zebra printer integration
        return {
            'type': 'ir.actions.act_window',
            'name': _('Print QR Code'),
            'res_model': 'plc.print.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_cycle_id': self.id}
        }

    def scan_qr_code(self, scanned_data):
        """Process scanned QR code data"""
        self.ensure_one()
        try:
            scanned_json = json.loads(scanned_data)
            
            # Verify the scanned data matches this cycle
            if (scanned_json.get('cycle_number') == self.cycle_number and
                scanned_json.get('barcode') == self.barcode):
                
                self.qr_code_scanned = True
                self.scan_datetime = fields.Datetime.now()
                
                return {
                    'status': 'success',
                    'message': _('QR Code matched successfully!'),
                    'cycle_data': {
                        'cycle_number': self.cycle_number,
                        'part_name': self.part_name,
                        'result': self.result,
                        'torque_nm': self.torque_nm,
                    }
                }
            else:
                return {
                    'status': 'error',
                    'message': _('QR Code does not match this cycle!')
                }
        except json.JSONDecodeError:
            return {
                'status': 'error',
                'message': _('Invalid QR Code data format!')
            }
        except Exception as e:
            _logger.error(f"Error processing scanned QR code: {e}")
            return {
                'status': 'error',
                'message': _('Error processing QR code: %s') % str(e)
            }

    @api.model
    def get_dashboard_data(self, date_from=None, date_to=None):
        """Get data for dashboard"""
        domain = []
        if date_from:
            domain.append(('cycle_datetime', '>=', date_from))
        if date_to:
            domain.append(('cycle_datetime', '<=', date_to))
        
        cycles = self.search(domain)
        
        return {
            'total_cycles': len(cycles),
            'ok_cycles': len(cycles.filtered(lambda c: c.result == 'ok')),
            'nok_cycles': len(cycles.filtered(lambda c: c.result == 'nok')),
            'pending_cycles': len(cycles.filtered(lambda c: c.result == 'pending')),
            'qr_printed': len(cycles.filtered(lambda c: c.qr_code_printed)),
            'qr_scanned': len(cycles.filtered(lambda c: c.qr_code_scanned)),
            'avg_cycle_time': sum(cycles.mapped('cycle_time')) / len(cycles) if cycles else 0,
        }

    def action_mark_ok(self):
        """Mark cycle as OK"""
        self.write({'result': 'ok'})

    def action_mark_nok(self):
        """Mark cycle as NOK"""
        self.write({'result': 'nok'})

    def action_print_qr(self):
        """Action to print QR code"""
        return self.print_qr_code()

    def action_scan_qr(self):
        """Action to scan QR code"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Scan QR Code'),
            'res_model': 'plc.scan.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_cycle_id': self.id}
        }
