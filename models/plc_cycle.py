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
    
    # CLUTCH Machine Specific Fields
    zero_position = fields.Float(
        string='Zero Position',
        digits=(10, 3),
        default=0.0,
        help="Zero position (default: 0)"
    )
    s1_for = fields.Float(
        string='S1_FOR',
        digits=(10, 3),
        help="S1 forward measurement from D2704"
    )
    s2_for = fields.Float(
        string='S2_FOR',
        digits=(10, 3),
        help="S2 forward measurement from D2708"
    )
    s2_rev = fields.Float(
        string='S2_REV',
        digits=(10, 3),
        default=0.0,
        help="S2 reverse measurement (for future use)"
    )
    s1_rev = fields.Float(
        string='S1_REV',
        digits=(10, 3),
        default=0.0,
        help="S1 reverse measurement (for future use)"
    )
    initial_position_revload = fields.Float(
        string='Initial Position RevLoad',
        digits=(10, 3),
        default=0.0,
        help="Initial position reverse load (for future use)"
    )
    
    # QR Code Match Status
    qr_match_status = fields.Selection([
        ('pending', 'Pending'),
        ('matched', 'Matched'),
        ('not_matched', 'Not Matched')
    ], string='QR Match Status', default='pending')
    qr_scan_datetime = fields.Datetime(
        string='QR Scan DateTime',
        help="When the QR code was scanned and matched"
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
        help="32-character QR code string (also stored in barcode field)"
    )
    
    @api.onchange('qr_code_data')
    def _onchange_qr_code_data(self):
        """Keep barcode in sync with qr_code_data"""
        if self.qr_code_data:
            self.barcode = self.qr_code_data
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
    is_quality_pass = fields.Boolean(
        string='Quality Pass',
        compute='_compute_quality_pass',
        store=True
    )

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
        """
        Generate QR code data in format: Part_no + Revision + Vendor_code + MMYY + Serial_no (32 chars total)
        Format: {part_no}{revision}{vendor_code}{mfg_date}{serial_no}
        """
        self.ensure_one()
        
        # Get QR code components from workstation configuration
        workstation = self.workstation_id
        if not workstation:
            raise UserError(_("Workstation is required to generate QR code"))
        
        part_no = workstation.part_no or ''
        revision = workstation.revision or ''
        vendor_code = workstation.vendor_code or ''
        
        # Generate manufacturing date (MMYY format)
        from datetime import datetime
        now = datetime.now()
        mfg_date = now.strftime('%m%y')  # MMYY format
        
        # Generate serial number (6 digits) from sequence
        serial_no = self.env['ir.sequence'].next_by_code('plc.serial.number') or '000001'
        # Ensure serial number is 6 digits
        serial_no = serial_no.zfill(6)[:6]
        
        # Calculate available length for part_no
        # Total: 32 chars = part_no + revision(1) + vendor_code + mfg_date(4) + serial_no(6)
        # So: part_no + vendor_code = 32 - 1 - 4 - 6 = 21 chars
        # We'll pad/truncate as needed
        
        # Build QR code string
        # Format: Part_no + Revision + Vendor_code + MMYY + Serial_no
        qr_string = f"{part_no}{revision}{vendor_code}{mfg_date}{serial_no}"
        
        # Ensure total length is exactly 32 characters
        if len(qr_string) > 32:
            # Truncate part_no if needed
            available_for_part = 32 - len(revision) - len(vendor_code) - 4 - 6
            if available_for_part > 0:
                part_no = part_no[:available_for_part]
                qr_string = f"{part_no}{revision}{vendor_code}{mfg_date}{serial_no}"
            else:
                # If still too long, truncate from the end
                qr_string = qr_string[:32]
        elif len(qr_string) < 32:
            # Pad with zeros at the end (or pad part_no)
            padding_needed = 32 - len(qr_string)
            qr_string = qr_string + '0' * padding_needed
        
        # Store both the formatted string and JSON data
        # QR code data IS the barcode - they are the same
        self.qr_code_data = qr_string
        self.barcode = qr_string  # Always keep barcode in sync with qr_code_data
        
        # Also store detailed data as JSON for reference
        qr_data_json = {
            'qr_code': qr_string,
            'part_no': part_no,
            'revision': revision,
            'vendor_code': vendor_code,
            'mfg_date': mfg_date,
            'serial_no': serial_no,
            'cycle_number': self.cycle_number,
            'part_name': self.part_name,
            'barcode': self.barcode,
            'cycle_datetime': self.cycle_datetime.isoformat() if self.cycle_datetime else None,
        }
        
        # Store JSON in a separate field or as metadata
        # For now, we'll use qr_code_data for the 32-char string
        # and store JSON separately if needed
        
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
    
    def _auto_print_qr_code(self):
        """Auto-print QR code to Zebra printer after cycle OK"""
        self.ensure_one()
        
        if not self.qr_code_data:
            self.generate_qr_code_data()
        
        if not self.workstation_id:
            _logger.warning("No workstation configured for auto-print")
            return False
        
        workstation = self.workstation_id
        
        # Get printer type - default to USB if not set
        printer_type = workstation.printer_type
        _logger.info(f"[PRINT] Workstation printer_type field value: {repr(printer_type)}")
        
        if not printer_type or printer_type not in ['network', 'usb']:
            # Default to USB if not explicitly set
            printer_type = 'usb'
            _logger.warning(f"[PRINT] ⚠️ Printer type not set or invalid ({repr(printer_type)}), defaulting to USB")
            _logger.warning(f"[PRINT] 💡 Please set 'Printer Type' field to 'USB' in workstation configuration to avoid this warning")
        else:
            _logger.info(f"[PRINT] Using configured printer type: {printer_type}")
        
        _logger.info(f"[PRINT] Selected printer type: {printer_type} for workstation {workstation.name}")
        
        # Generate ZPL command
        zpl_command = self._generate_zpl_command()
        
        if printer_type == 'usb':
            return self._print_via_usb(zpl_command, workstation)
        else:
            return self._print_via_network(zpl_command, workstation)
    
    def _print_via_usb(self, zpl_command, workstation):
        """Print to USB-connected Zebra printer"""
        try:
            import platform
            
            # Check if running on Windows
            if platform.system() != 'Windows':
                _logger.error("USB printing is currently only supported on Windows")
                return False
            
            # Try to import win32print
            try:
                import win32print
                import win32api
            except ImportError:
                _logger.error("win32print module not found. Please install pywin32: pip install pywin32")
                return False
            
            printer_name = workstation.printer_usb_name
            
            # If printer name not specified, try to find Zebra printer
            if not printer_name:
                _logger.info("No printer name specified, attempting to auto-detect Zebra printer...")
                printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
                zebra_printers = [p[2] for p in printers if 'zebra' in p[2].lower() or 'zdesigner' in p[2].lower()]
                
                if zebra_printers:
                    printer_name = zebra_printers[0]
                    _logger.info(f"Auto-detected Zebra printer: {printer_name}")
                else:
                    _logger.error("No Zebra printer found. Please specify printer name in workstation configuration.")
                    return False
            
            _logger.info(f"Printing to USB printer: {printer_name}")
            _logger.info(f"ZPL command length: {len(zpl_command)} bytes")
            
            # Open printer
            try:
                hprinter = win32print.OpenPrinter(printer_name)
            except Exception as e:
                _logger.error(f"Failed to open printer '{printer_name}': {e}")
                _logger.error(f"Available printers: {[p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]}")
                return False
            
            try:
                # Start a print job
                job_info = ("PLC Cycle QR Code", None, "RAW")
                job_id = win32print.StartDocPrinter(hprinter, 1, job_info)
                win32print.StartPagePrinter(hprinter)
                
                # Send ZPL command as raw data
                win32print.WritePrinter(hprinter, zpl_command.encode('utf-8'))
                
                # End print job
                win32print.EndPagePrinter(hprinter)
                win32print.EndDocPrinter(hprinter)
                
                # Mark as printed and save
                self.qr_code_printed = True
                self.env.cr.commit()
                
                _logger.info(f"✅ QR code auto-printed successfully to USB printer '{printer_name}' for cycle {self.cycle_number}")
                _logger.info(f"QR Code Data: {self.qr_code_data}")
                return True
                
            finally:
                win32print.ClosePrinter(hprinter)
                
        except Exception as e:
            _logger.error(f"Error printing to USB printer: {e}", exc_info=True)
            return False
    
    def _print_via_network(self, zpl_command, workstation):
        """Print to network-connected Zebra printer"""
        printer_ip = workstation.printer_ip or '192.168.1.100'
        printer_port = workstation.printer_port or 9100
        
        try:
            import socket
            
            # Send to printer
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            
            try:
                _logger.info(f"Connecting to network printer at {printer_ip}:{printer_port}...")
                sock.connect((printer_ip, printer_port))
                _logger.info(f"Connected to printer, sending ZPL command ({len(zpl_command)} bytes)...")
                sock.send(zpl_command.encode('utf-8'))
                _logger.info(f"ZPL command sent successfully")
                
                # Mark as printed and save
                self.qr_code_printed = True
                self.env.cr.commit()  # Commit the flag change
                _logger.info(f"✅ QR code auto-printed successfully for cycle {self.cycle_number}")
                _logger.info(f"QR Code Data: {self.qr_code_data}")
                return True
            except socket.timeout:
                _logger.error(f"Timeout connecting to printer at {printer_ip}:{printer_port}")
                return False
            except socket.error as e:
                _logger.error(f"Socket error connecting to printer at {printer_ip}:{printer_port}: {e}")
                return False
            finally:
                try:
                    sock.close()
                except:
                    pass
                
        except Exception as e:
            _logger.error(f"Error auto-printing QR code via network: {e}", exc_info=True)
            return False
    
    def _generate_zpl_command(self):
        """Generate ZPL command for Zebra printer using the new template format"""
        # Get QR code components from workstation and cycle
        workstation = self.workstation_id
        if not workstation:
            # Fallback: use cycle data only
            part_no = ''
            revision = ''
            vendor_code = ''
            mfg_date = ''
            serial_no = ''
        else:
            part_no = workstation.part_no or ''
            revision = workstation.revision or ''
            vendor_code = workstation.vendor_code or ''
            
            # Get manufacturing date from cycle datetime (MMYY format)
            if self.cycle_datetime:
                mfg_date = self.cycle_datetime.strftime('%m%y')
            else:
                from datetime import datetime
                mfg_date = datetime.now().strftime('%m%y')
            
            # Extract serial number from QR code data if available
            # QR format: part_no + revision + vendor_code + mfg_date(4) + serial_no(6)
            serial_no = ''
            if self.qr_code_data and len(self.qr_code_data) >= 32:
                # Serial number is last 6 characters
                serial_no = self.qr_code_data[-6:]
            else:
                # Fallback: use cycle number or generate
                serial_no = self.cycle_number.replace('CYC', '').zfill(6)[:6] if self.cycle_number else '000001'
        
        # QR code data (32-char string)
        qr_code = self.qr_code_data or ''
        
        # Part description (use part_name)
        part_desc = self.part_name or ''
        
        # Build ZPL command using the new template
        zpl = f"""^XA
^PW591
^LL300
~SD15

^FO50,60
^BQN,2,5
^FDLA,{qr_code}^FS

^FO220,35^A0N,32,32^FD{part_no}^FS
^FO220,68^A0N,32,32^FD{revision}^FS
^FO220,101^A0N,32,32^FD{vendor_code}^FS
^FO220,134^A0N,32,32^FD{mfg_date}^FS
^FO220,167^A0N,32,32^FD{serial_no}^FS

^FO0,210
^FB591,1,0,C,0
^A0N,32,32
^FD{part_desc}^FS

^FO0,250
^FB591,1,0,C,0
^A0N,32,32
^FD AUTOLINE INDUST LTD ^FS
^XZ"""
        
        return zpl.strip()

    def scan_qr_code(self, scanned_data):
        """Process scanned QR code data (new format: 32-char string)"""
        self.ensure_one()
        try:
            # New format: scanned_data is a 32-character string
            # Compare directly with qr_code_data
            scanned_string = scanned_data.strip()
            
            if not self.qr_code_data:
                self.generate_qr_code_data()
            
            # Verify the scanned data matches this cycle's QR code
            if scanned_string == self.qr_code_data:
                self.qr_code_scanned = True
                self.qr_match_status = 'matched'
                self.scan_datetime = fields.Datetime.now()
                self.qr_scan_datetime = fields.Datetime.now()
                
                return {
                    'status': 'success',
                    'message': _('QR Code matched successfully!'),
                    'cycle_data': {
                        'cycle_number': self.cycle_number,
                        'part_name': self.part_name,
                        'result': self.result,
                        'torque_nm': self.torque_nm,
                        'qr_code': self.qr_code_data,
                    }
                }
            else:
                self.qr_match_status = 'not_matched'
                return {
                    'status': 'error',
                    'message': _('QR Code does not match this cycle! Expected: %s, Got: %s') % (self.qr_code_data, scanned_string)
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
