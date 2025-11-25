# -*- coding: utf-8 -*-

import logging
import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PlcPrintWizard(models.TransientModel):
    _name = 'plc.print.wizard'
    _description = 'PLC Print QR Code Wizard'

    cycle_id = fields.Many2one(
        'plc.cycle',
        string='Cycle',
        required=True
    )
    printer_ip = fields.Char(
        string='Printer IP Address',
        default='192.168.1.100',
        help="IP address of the Zebra printer"
    )
    printer_port = fields.Integer(
        string='Printer Port',
        default=9100,
        help="Port for Zebra printer communication"
    )
    copies = fields.Integer(
        string='Number of Copies',
        default=1,
        help="Number of copies to print"
    )
    label_size = fields.Selection([
        ('2x1', '2" x 1"'),
        ('3x1', '3" x 1"'),
        ('4x2', '4" x 2"'),
        ('custom', 'Custom Size')
    ], string='Label Size', default='3x1')
    custom_width = fields.Integer(
        string='Custom Width (mm)',
        help="Custom label width in millimeters"
    )
    custom_height = fields.Integer(
        string='Custom Height (mm)',
        help="Custom label height in millimeters"
    )
    
    # Display fields
    cycle_number = fields.Char(
        string='Cycle Number',
        related='cycle_id.cycle_number',
        readonly=True
    )
    part_name = fields.Char(
        string='Part Name',
        related='cycle_id.part_name',
        readonly=True
    )
    barcode = fields.Char(
        string='Barcode',
        related='cycle_id.barcode',
        readonly=True
    )
    qr_data_preview = fields.Text(
        string='QR Data Preview',
        compute='_compute_qr_data_preview'
    )

    @api.depends('cycle_id')
    def _compute_qr_data_preview(self):
        for record in self:
            if record.cycle_id and record.cycle_id.qr_code_data:
                try:
                    qr_data = json.loads(record.cycle_id.qr_code_data)
                    preview = json.dumps(qr_data, indent=2)
                    record.qr_data_preview = preview
                except:
                    record.qr_data_preview = record.cycle_id.qr_code_data
            else:
                record.qr_data_preview = ''

    def action_print(self):
        """Print QR code label"""
        self.ensure_one()
        
        if not self.cycle_id:
            raise UserError(_('No cycle selected'))
        
        # Generate QR code if not exists
        if not self.cycle_id.qr_code_data:
            self.cycle_id.generate_qr_code_data()
        if not self.cycle_id.qr_code_image:
            self.cycle_id.generate_qr_code_image()
        
        try:
            # Generate ZPL command for Zebra printer
            zpl_command = self._generate_zpl_command()
            
            # Send to printer
            success = self._send_to_printer(zpl_command)
            
            if success:
                # Mark as printed
                self.cycle_id.qr_code_printed = True
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Print Successful'),
                        'message': _('QR code label printed successfully!'),
                        'type': 'success',
                    }
                }
            else:
                raise UserError(_('Failed to send print job to printer'))
                
        except Exception as e:
            _logger.error(f"Error printing QR code: {e}")
            raise UserError(_('Error printing QR code: %s') % str(e))

    def _generate_zpl_command(self):
        """Generate ZPL command for Zebra printer (new format: 32-char string)"""
        cycle = self.cycle_id
        
        # Get label dimensions
        if self.label_size == 'custom':
            width = self.custom_width
            height = self.custom_height
        else:
            size_map = {
                '2x1': (50, 25),  # 2" x 1" in mm
                '3x1': (75, 25),  # 3" x 1" in mm
                '4x2': (100, 50), # 4" x 2" in mm
            }
            width, height = size_map.get(self.label_size, (75, 25))
        
        # Convert mm to dots (203 DPI)
        width_dots = int(width * 8)  # 203 DPI = 8 dots/mm
        height_dots = int(height * 8)
        
        # QR code data (32-char string)
        qr_data = cycle.qr_code_data or ''
        
        # Generate ZPL command
        zpl = f"""^XA
^PW{width_dots}
^LL{height_dots}
^FO20,20^BY3
^BQN,2,3
^FDQA,{qr_data}^FS
^FO20,{height_dots-50}^A0N,20,20
^FD{cycle.cycle_number}^FS
^FO20,{height_dots-30}^A0N,15,15
^FD{cycle.part_name}^FS
^FO20,{height_dots-10}^A0N,12,12
^FD{qr_data}^FS
^XZ"""
        
        return zpl.strip()

    def _send_to_printer(self, zpl_command):
        """Send ZPL command to Zebra printer"""
        try:
            import socket
            
            # Create socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # 5 second timeout
            
            # Connect to printer
            sock.connect((self.printer_ip, self.printer_port))
            
            # Send ZPL command
            for _ in range(self.copies):
                sock.send(zpl_command.encode('utf-8'))
            
            # Close connection
            sock.close()
            
            return True
            
        except Exception as e:
            _logger.error(f"Error sending to printer: {e}")
            return False

    def action_preview(self):
        """Preview the label design"""
        self.ensure_one()
        
        if not self.cycle_id:
            raise UserError(_('No cycle selected'))
        
        # Generate QR code if not exists
        if not self.cycle_id.qr_code_data:
            self.cycle_id.generate_qr_code_data()
        if not self.cycle_id.qr_code_image:
            self.cycle_id.generate_qr_code_image()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Label Preview'),
            'res_model': 'plc.print.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('autoline_brake_atmt.view_print_wizard_preview').id,
            'target': 'new',
        }

    def action_test_connection(self):
        """Test printer connection"""
        self.ensure_one()
        
        try:
            import socket
            
            # Create socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # 5 second timeout
            
            # Try to connect
            sock.connect((self.printer_ip, self.printer_port))
            sock.close()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Successful'),
                    'message': _('Printer connection test successful!'),
                    'type': 'success',
                }
            }
            
        except Exception as e:
            _logger.error(f"Printer connection test failed: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Failed'),
                    'message': _('Unable to connect to printer: %s') % str(e),
                    'type': 'danger',
                }
            }
