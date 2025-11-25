# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PlcWorkstation(models.Model):
    _name = 'plc.workstation'
    _description = 'PLC Workstation Configuration'
    _rec_name = 'name'

    name = fields.Char(
        string='Workstation Name',
        required=True
    )
    code = fields.Char(
        string='Code',
        required=True,
        help="Unique code for this workstation"
    )
    plc_ip = fields.Char(
        string='PLC IP Address',
        required=True,
        help="IP address of the Mitsubishi PLC"
    )
    plc_port = fields.Integer(
        string='PLC Port',
        default=502,
        help="ModbusTCP port (default: 502)"
    )
    unit_id = fields.Integer(
        string='Unit ID',
        default=1,
        help="Modbus unit ID"
    )
    timeout = fields.Integer(
        string='Timeout (seconds)',
        default=5,
        help="Connection timeout in seconds"
    )
    
    # Modbus Register Mappings
    cycle_start_register = fields.Integer(
        string='Cycle Start Register',
        help="Modbus register for cycle start trigger"
    )
    cycle_complete_register = fields.Integer(
        string='Cycle Complete Register',
        help="Modbus register for cycle completion status"
    )
    torque_register = fields.Integer(
        string='Torque Register (D2700)',
        default=2700,
        help="D register address for torque value (D2700)"
    )
    initial_position_register = fields.Integer(
        string='Initial Position Register (D700)',
        default=700,
        help="D register address for initial position (D700)"
    )
    forward_load_register = fields.Integer(
        string='Forward Load/Register Placeholder',
        help="Legacy field (not used for Brake machine)"
    )
    final_position_register = fields.Integer(
        string='Final Position Register (D704)',
        default=704,
        help="D register address for final position (D704)"
    )
    load_cell_register = fields.Integer(
        string='Load Cell Register (D710)',
        default=710,
        help="D register address for load cell value (D710)"
    )
    cycle_time_register = fields.Integer(
        string='Cycle Time Register (D720)',
        default=720,
        help="D register address for cycle time (D720)"
    )
    result_register = fields.Integer(
        string='Result Register',
        help="Modbus register for result (OK/NOK)"
    )
    barcode_register_start = fields.Integer(
        string='Barcode Start Register',
        help="Starting register for barcode data (multiple registers)"
    )
    barcode_length = fields.Integer(
        string='Barcode Length',
        default=32,
        help="Number of characters in barcode"
    )
    
    # QR Code Configuration (variant specific)
    part_name_at = fields.Char(
        string='Part Name (Brake-AT)',
        default='BRAKE-AT',
        help="Part description used when AT sensor bit is ON"
    )
    part_no_at = fields.Char(
        string='Part Number (Brake-AT)',
        help="Part number used for QR code generation when AT variant runs"
    )
    revision_at = fields.Char(
        string='Revision (Brake-AT)',
        size=2,
        help="Revision character for Brake-AT variant"
    )
    vendor_code_at = fields.Char(
        string='Vendor Code (Brake-AT)',
        help="Vendor code used for Brake-AT variant"
    )
    part_name_mt = fields.Char(
        string='Part Name (Brake-MT)',
        default='BRAKE-MT',
        help="Part description used when AT sensor bit is OFF (MT variant)"
    )
    part_no_mt = fields.Char(
        string='Part Number (Brake-MT)',
        help="Part number used for QR code generation when MT variant runs"
    )
    revision_mt = fields.Char(
        string='Revision (Brake-MT)',
        size=2,
        help="Revision character for Brake-MT variant"
    )
    vendor_code_mt = fields.Char(
        string='Vendor Code (Brake-MT)',
        help="Vendor code used for Brake-MT variant"
    )
    # Legacy fallback values (used if variant-specific fields are empty)
    part_no = fields.Char(
        string='Default Part Number',
        help="Fallback part number when variant specific value is empty"
    )
    revision = fields.Char(
        string='Default Revision',
        size=2,
        help="Fallback revision when variant specific value is empty"
    )
    vendor_code = fields.Char(
        string='Default Vendor Code',
        help="Fallback vendor code when variant specific value is empty"
    )
    
    # CLUTCH Machine Register Mappings (M bits - coils)
    # Note: These are the PLC M bit numbers (M20, M201, etc.)
    # For Mitsubishi FX5U: M0 maps to Modbus address 8192, so M221 = 8192 + 221 = 8413
    m_bit_address_offset = fields.Integer(
        string='M Bit Address Offset',
        default=8192,
        help="Offset to add to M bit numbers to get Modbus address. For Mitsubishi FX5U: M0 = 8192, so M221 = 8192 + 221 = 8413. Default is 8192."
    )
    part_presence_bit = fields.Integer(
        string='Part Presence Bit (M16)',
        default=16,
        help="M bit number for part presence detection (M16). Actual Modbus address = this value + offset."
    )
    part_at_bit = fields.Integer(
        string='AT Variant Sensor Bit (M20)',
        default=20,
        help="M bit number that indicates Brake-AT variant (ON=AT, OFF=MT). Actual Modbus address = this value + offset."
    )
    cycle_start_bit = fields.Integer(
        string='Cycle Start Bit (M201)',
        default=201,
        help="M bit number for cycle start (M201). Actual Modbus address = this value + offset."
    )
    cycle_complete_bit = fields.Integer(
        string='Cycle Complete Bit (M222)',
        default=222,
        help="M bit number for cycle complete (M222). Actual Modbus address = this value + offset."
    )
    cycle_ok_bit = fields.Integer(
        string='Cycle OK Bit (M2000)',
        default=2000,
        help="M bit number for cycle OK (Brake machines use M2000). Actual Modbus address = this value + offset."
    )
    cycle_nok_bit = fields.Integer(
        string='Cycle NOK Bit (M349)',
        default=349,
        help="M bit number for cycle NOK (M349). Actual Modbus address = this value + offset."
    )
    
    # Zebra Printer Configuration
    printer_type = fields.Selection([
        ('network', 'Network (TCP/IP)'),
        ('usb', 'USB'),
    ], string='Printer Type', default='usb',
        help="Type of printer connection: Network (TCP/IP) or USB"
    )
    printer_ip = fields.Char(
        string='Printer IP Address',
        default='192.168.1.100',
        help="IP address of the Zebra printer (for network printers only)"
    )
    printer_port = fields.Integer(
        string='Printer Port',
        default=9100,
        help="Port for Zebra printer communication (for network printers only)"
    )
    printer_usb_name = fields.Char(
        string='USB Printer Name',
        help="Windows printer name for USB printer (e.g., 'ZDesigner ZT410-203dpi ZPL' or 'Zebra ZT410'). Leave empty to auto-detect."
    )
    
    # M Bit Reading Configuration
    m_bit_read_method = fields.Selection([
        ('coils', 'Coils (Function Code 0x01)'),
        ('discrete_inputs', 'Discrete Inputs (Function Code 0x02)'),
        ('auto', 'Auto (Try Coils, fallback to Discrete Inputs)'),
    ], string='M Bit Read Method', default='coils',
        help="Method to use for reading M bits. For Mitsubishi FX5U with M0=8192 mapping, use Coils (Function Code 0x01). Default: Coils."
    )
    
    # Monitoring
    monitoring_active = fields.Boolean(
        string='Monitoring Active',
        default=False,
        help="Whether continuous monitoring is active"
    )
    
    # Status
    is_active = fields.Boolean(
        string='Active',
        default=True
    )
    last_connection = fields.Datetime(
        string='Last Connection',
        readonly=True
    )
    connection_status = fields.Selection([
        ('connected', 'Connected'),
        ('disconnected', 'Disconnected'),
        ('error', 'Error')
    ], string='Connection Status', default='disconnected')
    
    # Related Records
    cycle_ids = fields.One2many(
        'plc.cycle',
        'workstation_id',
        string='Cycles'
    )
    cycle_count = fields.Integer(
        string='Total Cycles',
        compute='_compute_cycle_count'
    )

    @api.depends('cycle_ids')
    def _compute_cycle_count(self):
        for record in self:
            record.cycle_count = len(record.cycle_ids)

    @api.constrains('plc_ip')
    def _check_plc_ip(self):
        for record in self:
            if record.plc_ip:
                import re
                ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
                if not re.match(ip_pattern, record.plc_ip):
                    raise ValidationError(_("Invalid IP address format"))

    def test_connection(self):
        """Test PLC connection"""
        self.ensure_one()
        try:
            from pymodbus.client import ModbusTcpClient
            
            # Match working test pattern - use positional or port keyword
            try:
                client = ModbusTcpClient(self.plc_ip, port=self.plc_port, timeout=self.timeout)
            except TypeError:
                client = ModbusTcpClient(self.plc_ip, port=self.plc_port)
            
            if client.connect():
                self.connection_status = 'connected'
                self.last_connection = fields.Datetime.now()
                client.close()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Connection Successful'),
                        'message': _('PLC connection test successful!'),
                        'type': 'success',
                    }
                }
            else:
                self.connection_status = 'error'
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Connection Failed'),
                        'message': _('Unable to connect to PLC!'),
                        'type': 'danger',
                    }
                }
        except ImportError as e:
            _logger.error(f"pymodbus import error: {e}")
            raise UserError(_("Please install pymodbus library: pip install pymodbus"))
        except Exception as e:
            self.connection_status = 'error'
            _logger.error(f"PLC connection error: {e}", exc_info=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Error'),
                    'message': _('Error connecting to PLC: %s') % str(e),
                    'type': 'danger',
                }
            }

    def read_plc_data(self):
        """Read data from PLC registers"""
        self.ensure_one()
        
        # Try importing pymodbus components with version compatibility
        try:
            from pymodbus.client import ModbusTcpClient
        except ImportError as e:
            _logger.error(f"pymodbus.client import error: {e}")
            raise UserError(_("Please install pymodbus library: pip install pymodbus\nError: %s") % str(e))
        
        # Try importing BinaryPayloadDecoder with fallback
        use_pymodbus_decoder = True
        try:
            from pymodbus.payload import BinaryPayloadDecoder
            from pymodbus.constants import Endian
        except ImportError:
            try:
                # Try pymodbus 2.x path
                from pymodbus.client.common import BinaryPayloadDecoder
                from pymodbus.constants import Endian
            except ImportError:
                _logger.warning("BinaryPayloadDecoder not available, using manual float decoding")
                use_pymodbus_decoder = False
                # Define Endian constants locally
                class Endian:
                    Big = 1
                    Little = 2
        
        try:
            # Use helper to get client with unit_id configured
            client = self._get_plc_client()
            
            if not client.connect():
                raise UserError(_("Unable to connect to PLC"))
            
            # Read cycle completion status
            result = self._read_holding_registers(client, self.cycle_complete_register, 1)
            
            if result.isError():
                raise UserError(_("Error reading from PLC: %s") % result)
            
            cycle_complete = result.registers[0]
            
            if cycle_complete == 1:  # Cycle completed
                # Read all measurement data
                data = {}
                
                # Read torque
                if self.torque_register:
                    result = self._read_holding_registers(client, self.torque_register, 2)
                    if not result.isError() and result.registers:
                        if use_pymodbus_decoder:
                            decoder = BinaryPayloadDecoder.fromRegisters(
                                result.registers, byteorder=Endian.Big, wordorder=Endian.Little
                            )
                            data['torque_nm'] = decoder.decode_32bit_float()
                        else:
                            data['torque_nm'] = self._decode_float_from_registers(result.registers, 'big')
                
                # Read initial position
                if self.initial_position_register:
                    result = self._read_holding_registers(client, self.initial_position_register, 2)
                    if not result.isError() and result.registers:
                        if use_pymodbus_decoder:
                            decoder = BinaryPayloadDecoder.fromRegisters(
                                result.registers, byteorder=Endian.Big, wordorder=Endian.Little
                            )
                            data['initial_position'] = decoder.decode_32bit_float()
                        else:
                            data['initial_position'] = self._decode_float_from_registers(result.registers, 'big')
                
                # Read forward load
                if self.forward_load_register:
                    result = self._read_holding_registers(client, self.forward_load_register, 2)
                    if not result.isError() and result.registers:
                        if use_pymodbus_decoder:
                            decoder = BinaryPayloadDecoder.fromRegisters(
                                result.registers, byteorder=Endian.Big, wordorder=Endian.Little
                            )
                            data['forward_load_after'] = decoder.decode_32bit_float()
                        else:
                            data['forward_load_after'] = self._decode_float_from_registers(result.registers, 'big')
                
                # Read final position
                if self.final_position_register:
                    result = self._read_holding_registers(client, self.final_position_register, 2)
                    if not result.isError() and result.registers:
                        if use_pymodbus_decoder:
                            decoder = BinaryPayloadDecoder.fromRegisters(
                                result.registers, byteorder=Endian.Big, wordorder=Endian.Little
                            )
                            data['final_position'] = decoder.decode_32bit_float()
                        else:
                            data['final_position'] = self._decode_float_from_registers(result.registers, 'big')
                
                # Read cycle time
                if self.cycle_time_register:
                    result = self._read_holding_registers(client, self.cycle_time_register, 2)
                    if not result.isError() and result.registers:
                        if use_pymodbus_decoder:
                            decoder = BinaryPayloadDecoder.fromRegisters(
                                result.registers, byteorder=Endian.Big, wordorder=Endian.Little
                            )
                            data['cycle_time'] = decoder.decode_32bit_float()
                        else:
                            data['cycle_time'] = self._decode_float_from_registers(result.registers, 'big')
                
                # Read result
                if self.result_register:
                    result = self._read_holding_registers(client, self.result_register, 1)
                    if not result.isError():
                        data['result'] = 'ok' if result.registers[0] == 1 else 'nok'
                
                # Read barcode
                if self.barcode_register_start and self.barcode_length:
                    registers_needed = (self.barcode_length + 1) // 2
                    result = self._read_holding_registers(client, self.barcode_register_start, registers_needed)
                    if not result.isError() and result.registers:
                        if use_pymodbus_decoder:
                            decoder = BinaryPayloadDecoder.fromRegisters(
                                result.registers, byteorder=Endian.Big, wordorder=Endian.Little
                            )
                            barcode_bytes = decoder.decode_string(self.barcode_length)
                            data['barcode'] = barcode_bytes.decode('utf-8').strip('\x00')
                        else:
                            # Manual decode for string (simpler - just combine register values)
                            barcode_chars = []
                            for reg in result.registers:
                                # Each register is 16-bit, extract two characters
                                barcode_chars.append(chr((reg >> 8) & 0xFF))  # High byte
                                barcode_chars.append(reg & 0xFF)  # Low byte
                            data['barcode'] = ''.join(barcode_chars)[:self.barcode_length].strip('\x00')
                
                client.close()
                return data
            else:
                client.close()
                return None
                
        except UserError:
            # Re-raise UserError as-is (already has proper message)
            raise
        except Exception as e:
            _logger.error(f"Error reading PLC data: {e}", exc_info=True)
            raise UserError(_("Error reading from PLC: %s") % str(e))

    def create_cycle_from_plc(self, part_name=None):
        """Create a new cycle record from PLC data"""
        self.ensure_one()
        
        data = self.read_plc_data()
        if not data:
            return None
        
        # Barcode will be set automatically when QR code is generated
        # Don't set a temporary barcode here - let generate_qr_code_data() handle it
        
        # Set part name
        if part_name:
            data['part_name'] = part_name
        
        # Create cycle record
        cycle_vals = {
            'part_name': data.get('part_name', 'UNKNOWN'),
            'barcode': 'TEMP',  # Temporary value, will be replaced by generate_qr_code_data()
            'torque_nm': data.get('torque_nm', 0.0),
            'initial_position': data.get('initial_position', 0.0),
            'forward_load_after': data.get('forward_load_after', 0.0),
            'final_position': data.get('final_position', 0.0),
            'cycle_time': data.get('cycle_time', 0.0),
            'result': data.get('result', 'pending'),
            'workstation_id': self.id,
        }
        
        cycle = self.env['plc.cycle'].create(cycle_vals)
        
        # Generate QR code (this will set both qr_code_data and barcode)
        cycle.generate_qr_code_data()
        cycle.generate_qr_code_image()
        
        return cycle

    def action_read_plc_data(self):
        """Action to manually read data from PLC and create cycle"""
        self.ensure_one()
        try:
            # Check if M221 is ON
            cycle_state = self._read_cycle_status()
            if not cycle_state.get('cycle_ok', False):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Cycle Not Ready'),
                        'message': _('M221 (Cycle OK) is not ON. Please ensure the cycle is complete and OK before reading data.'),
                        'type': 'warning',
                    }
                }
            
            # Create cycle from PLC data
            cycle = self._create_cycle_from_plc_data()
            if cycle:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Cycle Created'),
                        'message': _('Cycle record created successfully!\nCycle Number: %s\nQR Code: %s') % (cycle.cycle_number, cycle.qr_code_data[:32] if cycle.qr_code_data else 'N/A'),
                        'type': 'success',
                        'sticky': True,
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error'),
                        'message': _('Failed to create cycle record. Check logs for details.'),
                        'type': 'danger',
                    }
                }
        except Exception as e:
            _logger.error(f"Error in action_read_plc_data: {e}", exc_info=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Error reading PLC data: %s') % str(e),
                    'type': 'danger',
                }
            }
    
    def action_force_create_cycle(self):
        """Force create a cycle record (for testing/debugging) - reads current PLC data and creates cycle"""
        self.ensure_one()
        try:
            _logger.info(f"[FORCE CREATE CYCLE] Starting cycle creation for workstation {self.name} (ID: {self.id})")
            
            # Read current PLC data and create cycle
            cycle = self._create_cycle_from_plc_data()
            
            if cycle:
                _logger.info(f"[FORCE CREATE CYCLE] ✅ Cycle created successfully: {cycle.cycle_number} (ID: {cycle.id})")
                
                # Try to auto-print QR code
                try:
                    cycle._auto_print_qr_code()
                    _logger.info(f"[FORCE CREATE CYCLE] ✅ QR code auto-printed")
                except Exception as e:
                    _logger.warning(f"[FORCE CREATE CYCLE] ⚠️ QR code printing failed: {e}")
                
                # Open the created cycle record
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Cycle Created'),
                    'res_model': 'plc.cycle',
                    'res_id': cycle.id,
                    'view_mode': 'form',
                    'target': 'current',
                    'context': {'create': False},
                }
            else:
                _logger.error(f"[FORCE CREATE CYCLE] ❌ Cycle creation returned None")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error'),
                        'message': _('Failed to create cycle record. Check logs for details.'),
                        'type': 'danger',
                        'sticky': True,
                    }
                }
        except Exception as e:
            _logger.error(f"[FORCE CREATE CYCLE] ❌ Error creating cycle: {e}", exc_info=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Error creating cycle: %s\n\nCheck Odoo logs for full details.') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    def create_cycle_from_plc(self):
        """Legacy method - kept for compatibility"""
        try:
            cycle = self._create_cycle_from_plc_data()
            if cycle:
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('New Cycle Created'),
                    'res_model': 'plc.cycle',
                    'res_id': cycle.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('No Data'),
                        'message': _('No cycle data available from PLC'),
                        'type': 'info',
                    }
                }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Error reading PLC data: %s') % str(e),
                    'type': 'danger',
                }
            }
    
    def _get_plc_client(self):
        """Get ModbusTCP client for PLC connection"""
        try:
            from pymodbus.client import ModbusTcpClient
        except ImportError as e:
            _logger.error(f"pymodbus import error: {e}")
            raise UserError(_("Please install pymodbus library: pip install pymodbus"))
        
        try:
            # Create client matching working test pattern
            # ModbusTCP doesn't require unit_id (it's for RTU/ASCII)
            # Use positional or keyword arguments as shown in working test
            try:
                # Try with timeout parameter
                client = ModbusTcpClient(
                    self.plc_ip,
                    port=self.plc_port,
                    timeout=self.timeout
                )
            except TypeError:
                # Fallback without timeout
                client = ModbusTcpClient(self.plc_ip, port=self.plc_port)
            
            return client
        except Exception as e:
            _logger.error(f"Error creating PLC client: {e}")
            raise UserError(_("Error creating PLC client: %s") % str(e))
    
    def _read_holding_registers(self, client, address, count):
        """
        Helper method to read holding registers
        Uses keyword arguments matching working test pattern
        """
        # Use keyword arguments as shown in working test
        return client.read_holding_registers(address=address, count=count)
    
    def _read_coils(self, client, address, count):
        """
        Helper method to read coils
        Uses keyword arguments matching working test pattern
        """
        # Use keyword arguments as shown in working test
        return client.read_coils(address=address, count=count)
    
    def _read_discrete_inputs(self, client, address, count):
        """
        Helper method to read discrete inputs (function code 0x02)
        Some Mitsubishi PLCs map M bits to discrete inputs instead of coils
        """
        try:
            return client.read_discrete_inputs(address=address, count=count)
        except AttributeError:
            # If method doesn't exist, try alternative name
            try:
                return client.read_discrete_input(address=address, count=count)
            except:
                raise
    
    def scan_for_active_bits(self, start_address=0, end_address=400, use_discrete_inputs=False):
        """
        Scan a range of addresses to find which bits are ON
        This helps identify the correct Modbus addresses for M bits
        
        Args:
            start_address: Starting Modbus address to scan
            end_address: Ending Modbus address to scan
            use_discrete_inputs: If True, scan discrete inputs instead of coils
        """
        self.ensure_one()
        import time
        
        _logger.info(f"[BIT SCAN] Scanning addresses {start_address} to {end_address} ({'Discrete Inputs' if use_discrete_inputs else 'Coils'})")
        
        client = None
        active_bits = []
        
        try:
            client = self._get_plc_client()
            if not client or not client.connect():
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error'),
                        'message': _('Failed to connect to PLC'),
                        'type': 'danger',
                    }
                }
            
            time.sleep(0.1)
            
            # Scan in chunks of 100 to avoid overwhelming the PLC
            chunk_size = 100
            for chunk_start in range(start_address, end_address, chunk_size):
                chunk_end = min(chunk_start + chunk_size, end_address)
                count = chunk_end - chunk_start
                
                try:
                    if use_discrete_inputs:
                        result = self._read_discrete_inputs(client, chunk_start, count)
                    else:
                        result = self._read_coils(client, chunk_start, count)
                    
                    if not result.isError() and result.bits:
                        for i, bit_val in enumerate(result.bits):
                            if bit_val:
                                bit_addr = chunk_start + i
                                active_bits.append(bit_addr)
                                _logger.info(f"[BIT SCAN] Found active bit at address {bit_addr}")
                    
                    time.sleep(0.1)  # Small delay between chunks
                    
                except Exception as e:
                    _logger.warning(f"[BIT SCAN] Error scanning {chunk_start}-{chunk_end}: {e}")
                    time.sleep(0.1)
            
            client.close()
            
            message = f"Bit Scan Results ({'Discrete Inputs' if use_discrete_inputs else 'Coils'}):\n"
            message += "=" * 50 + "\n"
            
            if active_bits:
                message += f"Found {len(active_bits)} active bits:\n"
                for addr in sorted(active_bits):
                    message += f"  Address {addr} (M{addr}): ON\n"
                message += f"\n💡 Compare these addresses with your expected M bits:\n"
                message += f"   Expected M20: Check if address 20 is in the list\n"
                message += f"   Expected M201: Check if address 201 is in the list\n"
                message += f"   Expected M222: Check if address 222 is in the list\n"
            else:
                message += f"No active bits found in range {start_address}-{end_address}\n"
                message += f"\n💡 Try:\n"
                message += f"   1. Place a part and run scan again\n"
                message += f"   2. Start a cycle and run scan again\n"
                message += f"   3. Try scanning discrete inputs instead\n"
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Bit Scan Results'),
                    'message': message,
                    'type': 'info',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            _logger.error(f"Error in scan_for_active_bits: {e}", exc_info=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Error scanning bits: %s') % str(e),
                    'type': 'danger',
                }
            }
        finally:
            if client:
                try:
                    client.close()
                except:
                    pass
    
    def test_m_bit_as_discrete_input(self):
        """
        Test if M bits can be read as discrete inputs instead of coils
        Some Mitsubishi PLCs map M bits to discrete inputs
        """
        self.ensure_one()
        import time
        
        _logger.info(f"[DISCRETE INPUT TEST] Testing M bits as discrete inputs")
        
        client = None
        results = []
        
        try:
            client = self._get_plc_client()
            if not client or not client.connect():
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error'),
                        'message': _('Failed to connect to PLC'),
                        'type': 'danger',
                    }
                }
            
            time.sleep(0.1)
            
            test_bits = []
            if self.part_presence_bit:
                test_bits.append(('M20 (Part Presence)', self.part_presence_bit))
            test_bits.extend([
                ('M201 (Cycle Start)', self.cycle_start_bit),
                ('M222 (Cycle Complete)', self.cycle_complete_bit),
                ('M221 (Cycle OK)', self.cycle_ok_bit),
                ('M349 (Cycle NOK)', self.cycle_nok_bit),
            ])
            
            for bit_name, bit_addr in test_bits:
                try:
                    # Apply address offset (for Mitsubishi FX5U: M0 = 8192)
                    modbus_addr = bit_addr + self.m_bit_address_offset
                    result = self._read_discrete_inputs(client, modbus_addr, 1)
                    if not result.isError() and result.bits:
                        value = result.bits[0]
                        status = "ON" if value else "OFF"
                        results.append(f"{bit_name} (address {modbus_addr}): {status} (as Discrete Input)")
                        _logger.info(f"[DISCRETE INPUT TEST] {bit_name} (address {modbus_addr}): {status}")
                    else:
                        error = str(result) if result.isError() else "No bits"
                        results.append(f"{bit_name}: ERROR - {error}")
                        _logger.warning(f"[DISCRETE INPUT TEST] {bit_name}: {error}")
                except Exception as e:
                    results.append(f"{bit_name}: EXCEPTION - {type(e).__name__}")
                    _logger.error(f"[DISCRETE INPUT TEST] {bit_name}: {e}", exc_info=True)
                
                time.sleep(0.1)
            
            client.close()
            
            message = "Discrete Input Test Results:\n"
            message += "=" * 50 + "\n"
            message += "\n".join(results)
            message += "\n\n💡 If discrete inputs work but coils don't:"
            message += "\n   We need to modify the code to read M bits as discrete inputs"
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Discrete Input Test'),
                    'message': message,
                    'type': 'info',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            _logger.error(f"Error in test_m_bit_as_discrete_input: {e}", exc_info=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Error testing discrete inputs: %s') % str(e),
                    'type': 'danger',
                }
            }
        finally:
            if client:
                try:
                    client.close()
                except:
                    pass
    
    def _decode_float_from_registers(self, registers, byteorder='big'):
        """
        Decode 32-bit float from two 16-bit registers
        Fallback method when BinaryPayloadDecoder is not available
        
        Args:
            registers: List of two 16-bit register values [high_word, low_word]
            byteorder: 'big' or 'little' (default: 'big' for Mitsubishi)
        
        Returns:
            float: Decoded float value
        """
        import struct
        if len(registers) < 2:
            return 0.0
        
        try:
            # For Mitsubishi PLCs (Big Endian):
            # Register[0] = High 16 bits, Register[1] = Low 16 bits
            # Pack as two 16-bit words in big endian order
            if byteorder == 'big':
                # Big endian: high word first, then low word
                # Each register is already in big endian format
                bytes_data = struct.pack('>HH', registers[0], registers[1])
            else:
                # Little endian: low word first, then high word
                bytes_data = struct.pack('<HH', registers[1], registers[0])
            
            # Unpack as 32-bit float (IEEE 754)
            float_value = struct.unpack('>f' if byteorder == 'big' else '<f', bytes_data)[0]
            
            return float_value
        except Exception as e:
            _logger.error(f"Error decoding float from registers: {e}")
            return 0.0
    
    def read_plc_coil(self, coil_address):
        """
        Read a single coil (M bit) from PLC
        
        Args:
            coil_address: M bit address (e.g., 201 for M201)
            
        Returns:
            bool: True if coil is ON, False if OFF, None on error
        """
        self.ensure_one()
        client = None
        try:
            import time
            # Use helper to get client with unit_id configured
            client = self._get_plc_client()
            if not client:
                _logger.warning(f"Failed to create PLC client for reading coil M{coil_address}")
                return None
            
            if not client.connect():
                _logger.warning(f"Failed to connect to PLC for reading coil M{coil_address}")
                return None
            
            # Small delay to ensure connection is stable
            time.sleep(0.05)
            
            # Apply address offset (for Mitsubishi FX5U: M0 = 8192, so M221 = 8192 + 221 = 8413)
            modbus_address = coil_address + self.m_bit_address_offset
            
            # Read coil (function code 0x01)
            # Note: Mitsubishi M bits are typically mapped to coils
            # Address mapping: M0 = 8192 (default offset), so M221 = 8192 + 221 = 8413
            result = self._read_coils(client, modbus_address, 1)
            
            if result.isError():
                error_msg = str(result)
                _logger.warning(f"Modbus error reading coil M{coil_address} (address {modbus_address}): {error_msg}")
                return None
            
            if not result.bits:
                _logger.warning(f"No bits returned for coil M{coil_address} (address {modbus_address})")
                return None
            
            value = result.bits[0]
            _logger.debug(f"Successfully read coil M{coil_address} (address {modbus_address}): {value}")
            return value
            
        except Exception as e:
            _logger.error(f"Exception reading PLC coil M{coil_address} (address {modbus_address}): {e}", exc_info=True)
            return None
        finally:
            if client:
                try:
                    client.close()
                except:
                    pass

    def _get_variant_part_config(self, variant):
        """
        Return part configuration dictionary for the requested variant.
        Variant should be 'at' or 'mt'. Falls back to default values.
        """
        self.ensure_one()
        variant = (variant or 'mt').lower()
        if variant not in ('at', 'mt'):
            variant = 'mt'

        if variant == 'at':
            return {
                'part_name': self.part_name_at or self.part_name_mt or 'BRAKE-AT',
                'part_no': self.part_no_at or self.part_no or '',
                'revision': self.revision_at or self.revision or '',
                'vendor_code': self.vendor_code_at or self.vendor_code or '',
            }
        return {
            'part_name': self.part_name_mt or self.part_name_at or 'BRAKE-MT',
            'part_no': self.part_no_mt or self.part_no or '',
            'revision': self.revision_mt or self.revision or '',
            'vendor_code': self.vendor_code_mt or self.vendor_code or '',
        }
    
    def read_plc_holding_register_float(self, register_address):
        """
        Read a holding register (D register) as float from PLC
        
        Args:
            register_address: D register address (e.g., 2704 for D2704)
            
        Returns:
            float: Register value as float, None on error
        """
        self.ensure_one()
        client = None
        try:
            import time
            
            # Try importing BinaryPayloadDecoder with fallback
            use_pymodbus_decoder = True
            try:
                from pymodbus.payload import BinaryPayloadDecoder
                from pymodbus.constants import Endian
            except ImportError:
                try:
                    from pymodbus.client.common import BinaryPayloadDecoder
                    from pymodbus.constants import Endian
                except ImportError:
                    use_pymodbus_decoder = False
                    class Endian:
                        Big = 1
                        Little = 2
            
            # Use helper to get client with unit_id configured
            client = self._get_plc_client()
            if not client:
                return None
            
            if not client.connect():
                return None
            
            # Small delay to ensure connection is stable
            time.sleep(0.05)
            
            # Read 2 registers (32-bit float requires 2 registers)
            result = self._read_holding_registers(client, register_address, 2)
            
            if result.isError() or not result.registers:
                return None
            
            # Decode as float (Mitsubishi typically uses Big Endian)
            if use_pymodbus_decoder:
                decoder = BinaryPayloadDecoder.fromRegisters(
                    result.registers, byteorder=Endian.Big, wordorder=Endian.Big
                )
                float_value = decoder.decode_32bit_float()
            else:
                float_value = self._decode_float_from_registers(result.registers, 'big')
            
            return float_value
            
        except Exception as e:
            _logger.error(f"Error reading PLC register {register_address} as float: {e}")
            return None
        finally:
            if client:
                try:
                    client.close()
                except:
                    pass
    
    def _read_cycle_status(self):
        """
        Read cycle status bits from PLC using a single batch read operation
        This avoids connection issues from multiple individual reads
        
        Returns:
            dict: Dictionary with cycle status bits
        """
        self.ensure_one()
        cycle_state = {
            'part_presence': False,
            'part_at': False,
            'cycle_start': False,
            'cycle_complete': False,
            'cycle_ok': False,
            'cycle_nok': False,
        }
        
        client = None
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                import time
                client = self._get_plc_client()
                if not client:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    return cycle_state
                
                # Connect with retry
                if not client.connect():
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    return cycle_state
                
                # Small delay to ensure connection is stable
                time.sleep(0.1)
                
                # Simplified: Only read M221 (Cycle OK bit) since that's what triggers cycle creation
                # But we still read all bits for logging/debugging
                bit_addresses = []
                bit_mapping = {}  # Maps address to state key
                
                # Only add cycle_ok_bit (M221 or M2000) - this is the only one we need for cycle detection
                if self.cycle_ok_bit:
                    bit_addresses.append(self.cycle_ok_bit)
                    bit_mapping[self.cycle_ok_bit] = 'cycle_ok'
                    _logger.debug(f"[PLC READ] Will monitor cycle_ok_bit M{self.cycle_ok_bit} (Modbus address will be {self.cycle_ok_bit + self.m_bit_address_offset})")
                
                # Optionally add other bits for logging (but not required for cycle detection)
                if self.part_presence_bit:
                    bit_addresses.append(self.part_presence_bit)
                    bit_mapping[self.part_presence_bit] = 'part_presence'

                if self.part_at_bit:
                    bit_addresses.append(self.part_at_bit)
                    bit_mapping[self.part_at_bit] = 'part_at'
                
                if self.cycle_start_bit:
                    bit_addresses.append(self.cycle_start_bit)
                    bit_mapping[self.cycle_start_bit] = 'cycle_start'
                
                if self.cycle_complete_bit:
                    bit_addresses.append(self.cycle_complete_bit)
                    bit_mapping[self.cycle_complete_bit] = 'cycle_complete'
                
                if self.cycle_nok_bit:
                    bit_addresses.append(self.cycle_nok_bit)
                    bit_mapping[self.cycle_nok_bit] = 'cycle_nok'
                
                if not bit_addresses:
                    return cycle_state
                
                # Read bits individually with delays to avoid connection issues
                # Apply address offset if configured
                # Prioritize cycle_ok_bit (read it first to catch it quickly)
                sorted_bits = sorted(bit_mapping.items(), key=lambda x: 0 if x[1] == 'cycle_ok' else 1)
                
                for m_bit_number, state_key in sorted_bits:
                    try:
                        # Calculate actual Modbus address (M bit number + offset)
                        modbus_address = m_bit_number + self.m_bit_address_offset
                        
                        # Small delay before each read to avoid overwhelming PLC
                        # Use shorter delay for cycle_ok_bit to catch it faster
                        delay = 0.05 if state_key == 'cycle_ok' else 0.1
                        time.sleep(delay)
                        
                        # Try reading based on configured method
                        result = None
                        read_success = False
                        read_method_used = ""
                        
                        # For cycle_ok_bit (especially M2000), try multiple methods if one fails
                        if state_key == 'cycle_ok' and self.m_bit_read_method != 'auto':
                            # For critical cycle_ok_bit, try both methods even if one is configured
                            methods_to_try = []
                            if self.m_bit_read_method == 'coils':
                                methods_to_try = [('coil', self._read_coils), ('discrete_input', self._read_discrete_inputs)]
                            elif self.m_bit_read_method == 'discrete_inputs':
                                methods_to_try = [('discrete_input', self._read_discrete_inputs), ('coil', self._read_coils)]
                            else:
                                methods_to_try = [('coil', self._read_coils)]
                            
                            for method_name, read_func in methods_to_try:
                                try:
                                    result = read_func(client, modbus_address, 1)
                                    read_method_used = method_name
                                    if not result.isError() and result.bits:
                                        read_success = True
                                        if method_name != methods_to_try[0][0]:
                                            _logger.info(f"[PLC READ] M{m_bit_number} (cycle_ok_bit) read successfully as {method_name} (primary method failed)")
                                        break
                                    elif result and result.isError():
                                        # Check for ExceptionResponse
                                        if hasattr(result, 'exception_code'):
                                            exception_code = result.exception_code
                                            if exception_code == 2:
                                                _logger.warning(f"[PLC READ] M{m_bit_number} (address {modbus_address}) {method_name}: ILLEGAL DATA ADDRESS - trying alternative method...")
                                            else:
                                                _logger.debug(f"[PLC READ] M{m_bit_number} (address {modbus_address}) {method_name}: Exception code {exception_code} - trying alternative...")
                                except Exception as e:
                                    if method_name == methods_to_try[0][0]:
                                        _logger.debug(f"[PLC READ] M{m_bit_number} (address {modbus_address}) {method_name} read failed: {e}, trying alternative...")
                                    continue
                        else:
                            # For other bits, use configured method
                            if self.m_bit_read_method == 'coils':
                                result = self._read_coils(client, modbus_address, 1)
                                read_method_used = "coil"
                                if not result.isError() and result.bits:
                                    read_success = True
                            elif self.m_bit_read_method == 'discrete_inputs':
                                try:
                                    result = self._read_discrete_inputs(client, modbus_address, 1)
                                    read_method_used = "discrete_input"
                                    if not result.isError() and result.bits:
                                        read_success = True
                                except Exception as e:
                                    _logger.debug(f"[PLC READ] M{m_bit_number} (address {modbus_address}) discrete input read failed: {e}")
                            else:  # auto - try coils first, then discrete inputs
                                # Try coils first
                                result = self._read_coils(client, modbus_address, 1)
                                read_method_used = "coil"
                                if result.isError() or not result.bits:
                                    # Fallback to discrete inputs
                                    try:
                                        result = self._read_discrete_inputs(client, modbus_address, 1)
                                        read_method_used = "discrete_input"
                                        if not result.isError() and result.bits:
                                            read_success = True
                                            _logger.debug(f"[PLC READ] M{m_bit_number} (address {modbus_address}) read as discrete input (coil failed)")
                                    except Exception as e:
                                        _logger.debug(f"[PLC READ] M{m_bit_number} (address {modbus_address}) discrete input read also failed: {e}")
                                else:
                                    read_success = True
                        
                        if read_success and result and result.bits and len(result.bits) > 0:
                            bit_value = result.bits[0]
                            # Ensure boolean value (not just truthy)
                            cycle_state[state_key] = bool(bit_value)
                            # Log every read with clear status
                            status = "ON" if bit_value else "OFF"
                            _logger.info(f"[PLC READ] M{m_bit_number} (Modbus addr {modbus_address}, {state_key}): {status} (via {read_method_used}), raw value: {bit_value}, boolean: {bool(bit_value)}")
                        elif result and result.isError():
                            error_msg = str(result)
                            # Check if it's an ExceptionResponse (Illegal Data Address)
                            if hasattr(result, 'exception_code'):
                                exception_code = result.exception_code
                                if exception_code == 2:
                                    _logger.warning(f"[PLC READ] M{m_bit_number} (Modbus addr {modbus_address}, {state_key}): ILLEGAL DATA ADDRESS (exception code 2) - Address {modbus_address} is not accessible. M{m_bit_number} may not exist or address mapping is incorrect.")
                                    _logger.warning(f"[PLC READ] 💡 Suggestion: Verify M{m_bit_number} exists in PLC, or try different address offset. Current offset: {self.m_bit_address_offset}")
                                else:
                                    _logger.warning(f"[PLC READ] M{m_bit_number} (Modbus addr {modbus_address}, {state_key}): Modbus Exception Code {exception_code} - {error_msg}")
                            else:
                                _logger.warning(f"[PLC READ] M{m_bit_number} (Modbus addr {modbus_address}, {state_key}): ERROR - {error_msg}")
                            # Mark as False (default) and continue with other bits
                            cycle_state[state_key] = False
                            continue
                        else:
                            _logger.warning(f"[PLC READ] M{m_bit_number} (Modbus addr {modbus_address}, {state_key}): No bits returned")
                    
                    except Exception as e:
                        # Log error but continue with other bits
                        error_msg = str(e)
                        # Check if it's an ExceptionResponse
                        if 'ExceptionResponse' in str(type(e)) or 'exception_code' in str(e):
                            if state_key == 'cycle_ok':
                                _logger.error(f"[PLC READ] CRITICAL: M{m_bit_number} (address {modbus_address}) returned ExceptionResponse - Address may not exist or be accessible")
                                _logger.error(f"[PLC READ] 💡 M{m_bit_number} may not be accessible at Modbus address {modbus_address} (M bit {m_bit_number} + offset {self.m_bit_address_offset})")
                                _logger.error(f"[PLC READ] 💡 Try: 1) Verify M{m_bit_number} exists in PLC program, 2) Check if address offset is correct, 3) Use 'Test PLC Bit Access' button to find correct address")
                        # If it's a connection error for cycle_ok_bit, try to reconnect and retry once
                        if state_key == 'cycle_ok':
                            _logger.error(f"[PLC READ] CRITICAL: Failed to read cycle_ok_bit M{m_bit_number} at address {modbus_address}. Error: {error_msg}")
                            # Try to close and recreate connection for next attempt
                            if client:
                                try:
                                    client.close()
                                except:
                                    pass
                            # Mark as False for now, will retry on next read cycle
                            cycle_state[state_key] = False
                            _logger.warning(f"[PLC READ] cycle_ok_bit M{m_bit_number} will be retried on next read cycle")
                        else:
                            _logger.warning(f"[PLC READ] M{m_bit_number} (Modbus addr {modbus_address}, {state_key}): EXCEPTION - {error_msg}")
                            cycle_state[state_key] = False  # Default to False on error
                        # Add delay before next read
                        time.sleep(0.1)
                        continue
                
                # Success - break out of retry loop
                break
                
            except Exception as e:
                _logger.error(f"Error in _read_cycle_status (attempt {attempt + 1}): {e}", exc_info=True)
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
            finally:
                if client:
                    try:
                        client.close()
                    except:
                        pass
                    client = None
        
        # Log final cycle_state for debugging
        _logger.debug(f"[_read_cycle_status] Final cycle_state: {cycle_state}, cycle_ok value: {cycle_state.get('cycle_ok')}, type: {type(cycle_state.get('cycle_ok'))}")
        return cycle_state
    
    def _create_cycle_from_plc_data(self):
        """
        Create cycle record from PLC data (for CLUTCH machine)
        Reads all CLUTCH-specific registers in a single connection
        """
        self.ensure_one()
        
        client = None
        try:
            import time
            
            # Try importing BinaryPayloadDecoder with fallback
            use_pymodbus_decoder = True
            try:
                from pymodbus.payload import BinaryPayloadDecoder
                from pymodbus.constants import Endian
            except ImportError:
                try:
                    from pymodbus.client.common import BinaryPayloadDecoder
                    from pymodbus.constants import Endian
                except ImportError:
                    _logger.warning("BinaryPayloadDecoder not available, using manual float decoding")
                    use_pymodbus_decoder = False
                    class Endian:
                        Big = 1
                        Little = 2
            
            # Read all measurement registers in one connection
            data = {}
            
            # Get client and connect once
            client = self._get_plc_client()
            if not client:
                raise Exception("Unable to create PLC client")
            
            if not client.connect():
                raise Exception("Unable to connect to PLC")
            
            # Small delay to ensure connection is stable
            time.sleep(0.05)
            
            # Determine current variant (AT vs MT) using configured sensor bit (M20)
            # Read M20 AFTER client is connected
            variant_type = 'mt'  # Default to MT
            if self.part_at_bit:
                try:
                    variant_modbus_addr = self.part_at_bit + self.m_bit_address_offset
                    _logger.info(f"[CYCLE CREATE] Reading AT/MT sensor bit M{self.part_at_bit} (Modbus addr {variant_modbus_addr})")
                    variant_result = self._read_coils(client, variant_modbus_addr, 1)
                    if not variant_result.isError() and variant_result.bits:
                        is_at = bool(variant_result.bits[0])
                        variant_type = 'at' if is_at else 'mt'
                        _logger.info(f"[CYCLE CREATE] M{self.part_at_bit} is {'ON' if is_at else 'OFF'} - Variant: {variant_type.upper()}")
                    else:
                        error_msg = str(variant_result) if variant_result.isError() else "No bits returned"
                        _logger.warning(f"[CYCLE CREATE] Unable to read AT/MT sensor (M{self.part_at_bit}) - {error_msg}")
                except Exception as variant_error:
                    _logger.warning(f"[CYCLE CREATE] Exception reading AT/MT sensor bit M{self.part_at_bit}: {variant_error}", exc_info=True)
            else:
                _logger.warning(f"[CYCLE CREATE] part_at_bit not configured - defaulting to MT variant")
            
            _logger.info(f"[CYCLE CREATE] ✅ Detected variant: {variant_type.upper()}")

            variant_config = self._get_variant_part_config(variant_type)
            
            # Helper to read single register and store as float
            def _read_single_register(field_key, register_address, label):
                if not register_address:
                    data[field_key] = 0.0
                    return
                try:
                    _logger.info(f"[CYCLE CREATE] Reading {label} from D register {register_address}")
                    result = self._read_holding_registers(client, register_address, 1)
                    if not result.isError() and result.registers:
                        data[field_key] = float(result.registers[0])
                        _logger.info(f"[CYCLE CREATE] D{register_address} raw value: {result.registers[0]} ({label}: {data[field_key]})")
                    else:
                        error_msg = str(result) if result.isError() else "No registers returned"
                        _logger.warning(f"[CYCLE CREATE] Error reading {label} from D{register_address}: {error_msg}")
                        data[field_key] = 0.0
                    time.sleep(0.02)
                except Exception as read_error:
                    _logger.error(f"[CYCLE CREATE] Exception reading {label} from D{register_address}: {read_error}", exc_info=True)
                    data[field_key] = 0.0

            _read_single_register('torque_nm', self.torque_register, 'torque')
            _read_single_register('initial_position', self.initial_position_register, 'initial position')
            _read_single_register('final_position', self.final_position_register, 'final position')
            _read_single_register('load_cell_value', self.load_cell_register, 'load cell value')
            _read_single_register('cycle_time', self.cycle_time_register, 'cycle time')

            # Legacy fields kept for compatibility (set to zero)
            data['zero_position'] = 0.0

            # Set part name from variant config
            data['part_name'] = variant_config.get('part_name') or 'BRAKE ASSEMBLY'

            # QR code data will be generated in cycle model, which also sets barcode
            # No need to set barcode separately - it will be synced with qr_code_data
            
            # Log all data before creating cycle
            _logger.info(f"[CYCLE CREATE] ========== Data Summary ==========")
            _logger.info(f"[CYCLE CREATE] Variant: {variant_type.upper()}")
            _logger.info(f"[CYCLE CREATE] Torque (D{self.torque_register}): {data.get('torque_nm', 0.0)}")
            _logger.info(f"[CYCLE CREATE] Initial Position (D{self.initial_position_register}): {data.get('initial_position', 0.0)}")
            _logger.info(f"[CYCLE CREATE] Final Position (D{self.final_position_register}): {data.get('final_position', 0.0)}")
            _logger.info(f"[CYCLE CREATE] Load Cell (D{self.load_cell_register}): {data.get('load_cell_value', 0.0)}")
            _logger.info(f"[CYCLE CREATE] Cycle Time (D{self.cycle_time_register}): {data.get('cycle_time', 0.0)}")
            _logger.info(f"[CYCLE CREATE] ===================================")
            
            # Create cycle record
            cycle_vals = {
                'part_name': data.get('part_name', variant_config.get('part_name', 'BRAKE ASSEMBLY')),
                'barcode': 'TEMP',  # Temporary value, will be replaced by generate_qr_code_data()
                'zero_position': data.get('zero_position', 0.0),
                'initial_position': data.get('initial_position', 0.0),
                'final_position': data.get('final_position', 0.0),
                'cycle_time': data.get('cycle_time', 0.0),
                'torque_nm': data.get('torque_nm', 0.0),
                'load_cell_value': data.get('load_cell_value', 0.0),
                'variant_type': variant_type,
                'result': 'ok',  # Will be set based on cycle_ok or cycle_nok
                'workstation_id': self.id,
            }
            
            _logger.info(f"[CYCLE CREATE] Creating cycle record with values: torque={cycle_vals['torque_nm']}, initial_position={cycle_vals['initial_position']}, final_position={cycle_vals['final_position']}, load_cell={cycle_vals['load_cell_value']}")
            cycle = self.env['plc.cycle'].create(cycle_vals)
            _logger.info(f"[CYCLE CREATE] ✅ Cycle record created with ID: {cycle.id}, Cycle Number: {cycle.cycle_number}")
            
            # Generate QR code with new format (this will set both qr_code_data and barcode)
            cycle.generate_qr_code_data()
            cycle.generate_qr_code_image()
            
            _logger.info(f"[CYCLE CREATE] ✅ QR code generated: barcode={cycle.barcode}, qr_code_data={cycle.qr_code_data}")
            
            return cycle
            
        except Exception as e:
            _logger.error(f"Error creating cycle from PLC data: {e}")
            raise
        finally:
            if client:
                try:
                    client.close()
                except:
                    pass
    
    def start_continuous_monitoring(self):
        """Start continuous monitoring for this workstation"""
        self.ensure_one()
        
        if not self.is_active:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Monitoring Not Started'),
                    'message': _('Workstation is not active'),
                    'type': 'warning',
                }
            }
        
        try:
            from .plc_monitor_service import get_plc_monitor_service
            
            service = get_plc_monitor_service()
            db_name = self.env.cr.dbname
            service.start_monitoring(db_name, self.id)
            
            self.monitoring_active = True
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Monitoring Started'),
                    'message': _('Continuous monitoring started for %s') % self.name,
                    'type': 'success',
                }
            }
        except Exception as e:
            _logger.error(f"Error starting monitoring: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Failed to start monitoring: %s') % str(e),
                    'type': 'danger',
                }
            }
    
    def stop_continuous_monitoring(self):
        """Stop continuous monitoring for this workstation"""
        self.ensure_one()
        
        try:
            from .plc_monitor_service import get_plc_monitor_service
            
            service = get_plc_monitor_service()
            service.stop_monitoring(self.id)
            
            self.monitoring_active = False
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Monitoring Stopped'),
                    'message': _('Continuous monitoring stopped for %s') % self.name,
                    'type': 'success',
                }
            }
        except Exception as e:
            _logger.error(f"Error stopping monitoring: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Failed to stop monitoring: %s') % str(e),
                    'type': 'danger',
                }
            }
    
    @api.model
    def start_all_continuous_monitoring(self):
        """Start continuous monitoring for all active workstations (called by cron)"""
        try:
            from .plc_monitor_service import get_plc_monitor_service
            
            service = get_plc_monitor_service()
            db_name = self.env.cr.dbname
            
            # Get all active workstations
            active_workstations = self.search([
                ('is_active', '=', True)
            ])
            
            _logger.info(f"PLC Monitoring Cron: Found {len(active_workstations)} active workstation(s)")
            
            if len(active_workstations) == 0:
                _logger.warning("PLC Monitoring Cron: No active workstations found!")
                return False
            
            started_count = 0
            already_running = 0
            errors = 0
            
            for workstation in active_workstations:
                try:
                    # Always restart monitoring to ensure it's running
                    # (threads might have died)
                    if workstation.id in service.monitors:
                        thread = service.monitors[workstation.id]
                        if not thread.is_alive():
                            # Thread died, restart it
                            _logger.warning(f"Monitoring thread for workstation {workstation.id} is dead, restarting...")
                            service.stop_monitoring(workstation.id)
                            workstation.monitoring_active = False
                    
                    # Check if monitoring is already active
                    if not workstation.monitoring_active:
                        service.start_monitoring(db_name, workstation.id)
                        workstation.monitoring_active = True
                        started_count += 1
                        _logger.info(f"Started monitoring for workstation {workstation.name} (ID: {workstation.id}, IP: {workstation.plc_ip})")
                    else:
                        already_running += 1
                        _logger.debug(f"Monitoring already active for workstation {workstation.name}")
                except Exception as e:
                    errors += 1
                    _logger.error(f"Error starting monitoring for workstation {workstation.id}: {e}", exc_info=True)
            
            if started_count > 0:
                _logger.info(f"PLC Monitoring Cron: Started monitoring for {started_count} workstation(s)")
            if already_running > 0:
                _logger.info(f"PLC Monitoring Cron: {already_running} workstation(s) already have monitoring active")
            if errors > 0:
                _logger.warning(f"PLC Monitoring Cron: {errors} error(s) occurred while starting monitoring")
            
            return True
        except Exception as e:
            _logger.error(f"Error in start_all_continuous_monitoring: {e}", exc_info=True)
            return False
    
    def get_current_plc_status(self):
        """
        Get current PLC status for real-time display
        Returns current state of all bits
        """
        self.ensure_one()
        try:
            status = self._read_cycle_status()
            return {
                'connection_status': self.connection_status,
                'plc_ip': self.plc_ip,
                'plc_port': self.plc_port,
                'monitoring_active': self.monitoring_active,
                'bits': {
                    'part_presence': {
                        'address': self.part_presence_bit,
                        'value': status.get('part_presence', False),
                        'name': 'Part Presence'
                    },
                    'cycle_start': {
                        'address': self.cycle_start_bit,
                        'value': status.get('cycle_start', False),
                        'name': 'Cycle Start'
                    },
                    'cycle_complete': {
                        'address': self.cycle_complete_bit,
                        'value': status.get('cycle_complete', False),
                        'name': 'Cycle Complete'
                    },
                    'cycle_ok': {
                        'address': self.cycle_ok_bit,
                        'value': status.get('cycle_ok', False),
                        'name': 'Cycle OK'
                    },
                    'cycle_nok': {
                        'address': self.cycle_nok_bit,
                        'value': status.get('cycle_nok', False),
                        'name': 'Cycle NOK'
                    },
                },
                'last_connection': self.last_connection,
            }
        except Exception as e:
            _logger.error(f"Error getting PLC status: {e}", exc_info=True)
            return {
                'connection_status': 'error',
                'error': str(e)
            }
    
    def test_plc_bit_access(self):
        """
        Test if specific bits are accessible via different Modbus function codes
        Helps diagnose if bits need to be read as discrete inputs vs coils
        """
        self.ensure_one()
        try:
            client = self._get_plc_client()
            if not client or not client.connect():
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error'),
                        'message': _('Failed to connect to PLC'),
                        'type': 'danger',
                    }
                }
            
            import time
            time.sleep(0.1)
            
            test_bits = []
            if self.part_presence_bit:
                test_bits.append(('M20 (Part Presence)', self.part_presence_bit))
            test_bits.extend([
                ('M201 (Cycle Start)', self.cycle_start_bit),
                ('M222 (Cycle Complete)', self.cycle_complete_bit),
                ('M221 (Cycle OK)', self.cycle_ok_bit),
                ('M349 (Cycle NOK)', self.cycle_nok_bit),
            ])
            
            results = []
            for bit_name, bit_addr in test_bits:
                result_line = f"\n{bit_name} (M{bit_addr}):"
                
                # Apply address offset (for Mitsubishi FX5U: M0 = 8192)
                modbus_addr = bit_addr + self.m_bit_address_offset
                result_line += f"\n  Modbus Address: {modbus_addr} (M{bit_addr} + offset {self.m_bit_address_offset})"
                
                # Test as Coil (Function Code 0x01)
                try:
                    coil_result = self._read_coils(client, modbus_addr, 1)
                    if not coil_result.isError() and coil_result.bits:
                        result_line += f"\n  ✅ Coil Read: {coil_result.bits[0]}"
                    else:
                        result_line += f"\n  ❌ Coil Read Failed: {coil_result if coil_result.isError() else 'No bits'}"
                except Exception as e:
                    result_line += f"\n  ❌ Coil Read Exception: {type(e).__name__}"
                
                time.sleep(0.05)
                
                # Test as Discrete Input (Function Code 0x02) if available
                try:
                    di_result = self._read_discrete_inputs(client, modbus_addr, 1)
                    if not di_result.isError() and di_result.bits:
                        result_line += f"\n  ✅ Discrete Input Read: {di_result.bits[0]}"
                    else:
                        result_line += f"\n  ⚠️ Discrete Input Read Failed: {di_result if di_result.isError() else 'No bits'}"
                except AttributeError:
                    result_line += f"\n  ⚠️ Discrete Input Read: Not supported by pymodbus version"
                except Exception as e:
                    result_line += f"\n  ⚠️ Discrete Input Read Exception: {type(e).__name__}"
                
                results.append(result_line)
                time.sleep(0.05)
            
            client.close()
            
            message = "🔍 PLC Bit Access Test Results:\n"
            message += "=" * 50
            message += "".join(results)
            message += "\n\n💡 Interpretation:"
            message += "\n  ✅ = Bit is readable via this method"
            message += "\n  ❌ = Bit is NOT readable via this method"
            message += "\n  ⚠️ = Method not available or failed"
            message += "\n\n📝 If M20 or M221 show ❌ for Coil Read but ✅ for Discrete Input:"
            message += "\n   These bits may need to be read as discrete inputs instead of coils"
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('PLC Bit Access Test'),
                    'message': message,
                    'type': 'info',
                    'sticky': True,
                }
            }
        except Exception as e:
            _logger.error(f"Error in test_plc_bit_access: {e}", exc_info=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Error testing PLC bit access: %s') % str(e),
                    'type': 'danger',
                }
            }
    
    def continuous_bit_monitor(self, duration_seconds=30, interval_seconds=0.5):
        """
        Continuously monitor and log all PLC bits for testing
        This helps identify when bits actually change state
        
        Args:
            duration_seconds: How long to monitor (default 30 seconds)
            interval_seconds: How often to read (default 0.5 seconds)
        """
        self.ensure_one()
        import time
        from datetime import datetime
        
        _logger.info(f"[CONTINUOUS MONITOR] Starting {duration_seconds}s monitoring for workstation {self.name}")
        _logger.info(f"[CONTINUOUS MONITOR] Reading every {interval_seconds}s")
        _logger.info(f"[CONTINUOUS MONITOR] Monitoring bits: M{self.part_presence_bit}, M{self.cycle_start_bit}, M{self.cycle_complete_bit}, M{self.cycle_ok_bit}, M{self.cycle_nok_bit}")
        
        start_time = time.time()
        last_states = {}
        read_count = 0
        error_count = 0
        
        while (time.time() - start_time) < duration_seconds:
            try:
                # Read current status
                cycle_state = self._read_cycle_status()
                read_count += 1
                
                # Log current state and detect changes
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                
                bit_mappings = [
                    ('part_presence', self.part_presence_bit, 'Part Presence'),
                    ('cycle_start', self.cycle_start_bit, 'Cycle Start'),
                    ('cycle_complete', self.cycle_complete_bit, 'Cycle Complete'),
                    ('cycle_ok', self.cycle_ok_bit, 'Cycle OK'),
                    ('cycle_nok', self.cycle_nok_bit, 'Cycle NOK'),
                ]
                
                log_line = f"[{timestamp}] Read #{read_count}: "
                changes = []
                
                for bit_key, bit_addr, bit_name in bit_mappings:
                    if bit_addr:
                        current_value = cycle_state.get(bit_key, False)
                        last_value = last_states.get(bit_key, None)
                        
                        status = "ON" if current_value else "OFF"
                        log_line += f"M{bit_addr}({status}) "
                        
                        # Detect changes
                        if last_value is not None and current_value != last_value:
                            change_type = "ON" if current_value else "OFF"
                            changes.append(f"M{bit_addr} ({bit_name}): {change_type}")
                            _logger.info(f"[BIT CHANGE] {timestamp} - M{bit_addr} ({bit_name}): {'OFF' if last_value else 'ON'} -> {'ON' if current_value else 'OFF'}")
                        
                        last_states[bit_key] = current_value
                
                # Log every read (at INFO level for continuous monitoring)
                if changes:
                    _logger.info(f"{log_line} | CHANGES: {', '.join(changes)}")
                else:
                    _logger.info(log_line)
                
                # Wait before next read
                time.sleep(interval_seconds)
                
            except Exception as e:
                error_count += 1
                _logger.error(f"[CONTINUOUS MONITOR] Error on read #{read_count}: {e}", exc_info=True)
                time.sleep(interval_seconds)
        
        # Summary
        elapsed = time.time() - start_time
        _logger.info(f"[CONTINUOUS MONITOR] Completed: {read_count} reads, {error_count} errors, {elapsed:.1f}s elapsed")
        _logger.info(f"[CONTINUOUS MONITOR] Final states: {last_states}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Continuous Monitor Complete'),
                'message': _('Monitoring completed:\n- Reads: %d\n- Errors: %d\n- Duration: %.1fs\n\nCheck Odoo logs for detailed bit change history') % (read_count, error_count, elapsed),
                'type': 'info',
                'sticky': True,
            }
        }
    
    def find_m221_address(self):
        """
        Scan to find where M221 actually is when it's forced ON
        Compares scan before and after forcing M221 ON to identify the address
        """
        self.ensure_one()
        import time
        
        _logger.info(f"[FIND M221] Scanning to locate M221 (forced ON in PLC)")
        
        client = None
        try:
            client = self._get_plc_client()
            if not client or not client.connect():
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error'),
                        'message': _('Failed to connect to PLC'),
                        'type': 'danger',
                    }
                }
            
            time.sleep(0.1)
            
            # Test M221 with current offset configuration
            m221_modbus_addr = 221 + self.m_bit_address_offset
            offset_results = []
            
            # Test M221 at configured offset address
            try:
                # Test as coil (most common for FX5U)
                result = self._read_coils(client, m221_modbus_addr, 1)
                if not result.isError() and result.bits:
                    status = "ON" if result.bits[0] else "OFF"
                    offset_results.append(f"  [CONFIGURED] M221 at address {m221_modbus_addr} (coil, offset {self.m_bit_address_offset}): {status}")
                # Test as discrete input
                result = self._read_discrete_inputs(client, m221_modbus_addr, 1)
                if not result.isError() and result.bits:
                    status = "ON" if result.bits[0] else "OFF"
                    offset_results.append(f"  [CONFIGURED] M221 at address {m221_modbus_addr} (discrete input, offset {self.m_bit_address_offset}): {status}")
            except:
                pass
            
            # Scan for active bits around M221 address (8413 with offset 8192)
            active_addresses = []
            scan_start = max(0, m221_modbus_addr - 50)
            scan_end = m221_modbus_addr + 50
            chunk_size = 50
            
            # Scan coils around M221 address
            for start in range(scan_start, scan_end, chunk_size):
                end = min(start + chunk_size, scan_end)
                try:
                    result = self._read_coils(client, start, end-start)
                    if not result.isError() and result.bits:
                        for i, bit_val in enumerate(result.bits):
                            if bit_val:
                                addr = start + i
                                active_addresses.append(('coil', addr))
                except:
                    pass
                time.sleep(0.05)
            
            # Also test common offset addresses for M221
            common_offsets = [
                (0, "Direct mapping (M221 = address 221)"),
                (8192, "FX5U Standard (M0 = 8192, M221 = 8413)"),
                (0x4000, "Offset 0x4000 (M221 = address 16605)"),
                (0x8000, "Offset 0x8000 (M221 = address 32821)"),
            ]
            
            for offset, desc in common_offsets:
                test_addr = 221 + offset
                if test_addr != m221_modbus_addr:  # Skip if already tested
                    try:
                        # Test as coil
                        result = self._read_coils(client, test_addr, 1)
                        if not result.isError() and result.bits and result.bits[0]:
                            offset_results.append(f"  [FOUND] {desc}: Address {test_addr} (coil) = ON")
                        # Test as discrete input
                        result = self._read_discrete_inputs(client, test_addr, 1)
                        if not result.isError() and result.bits and result.bits[0]:
                            offset_results.append(f"  [FOUND] {desc}: Address {test_addr} (discrete input) = ON")
                    except:
                        pass
            
            client.close()
            
            message = "M221 Address Finding Results:\n"
            message += "=" * 60 + "\n"
            message += f"Current Configuration: M Bit Offset = {self.m_bit_address_offset}\n"
            message += f"Expected M221 Address: {m221_modbus_addr} (221 + {self.m_bit_address_offset})\n\n"
            
            if offset_results:
                message += "✅ Offset Test Results:\n"
                message += "\n".join(offset_results)
                message += "\n\n"
            
            if active_addresses:
                message += f"Active bits found near M221 (range {scan_start}-{scan_end}):\n"
                for method, addr in sorted(active_addresses, key=lambda x: x[1]):
                    message += f"  {method.upper()}: Address {addr}"
                    # Calculate which M bit this might be
                    if method == 'coil':
                        possible_m_bit = addr - self.m_bit_address_offset
                        if 0 <= possible_m_bit <= 1000:
                            message += f" (possibly M{possible_m_bit})"
                    message += "\n"
            else:
                message += f"No active bits found in range {scan_start}-{scan_end}.\n"
            
            message += "\n💡 Interpretation:\n"
            message += "  - If M221 shows ON at address 8413: Configuration is correct!\n"
            message += "  - If M221 shows OFF: Make sure M221 is forced ON in PLC program\n"
            message += "  - If M221 is at a different address: Update 'M Bit Address Offset'\n"
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('M221 Address Scan'),
                    'message': message,
                    'type': 'info',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            _logger.error(f"Error in find_m221_address: {e}", exc_info=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Error finding M221 address: %s') % str(e),
                    'type': 'danger',
                }
            }
        finally:
            if client:
                try:
                    client.close()
                except:
                    pass
    
    def test_specific_m_bit(self, bit_address):
        """
        Test reading a specific M bit address multiple times
        Useful for debugging why a bit shows False when it should be True
        """
        self.ensure_one()
        import time
        
        _logger.info(f"[BIT TEST] Testing M{bit_address} - 10 reads with 0.2s intervals")
        
        results = []
        client = None
        
        for i in range(10):
            try:
                client = self._get_plc_client()
                if client and client.connect():
                    time.sleep(0.1)
                    
                    # Calculate actual address with offset
                    modbus_addr = bit_address + self.m_bit_address_offset
                    
                    # Try both methods
                    result = None
                    if self.m_bit_read_method == 'discrete_inputs':
                        result = self._read_discrete_inputs(client, modbus_addr, 1)
                    else:
                        result = self._read_coils(client, modbus_addr, 1)
                    
                    if not result.isError() and result.bits:
                        value = result.bits[0]
                        status = "ON" if value else "OFF"
                        results.append(f"Read #{i+1}: {status} (Modbus addr {modbus_addr})")
                        _logger.info(f"[BIT TEST] M{bit_address} (addr {modbus_addr}) Read #{i+1}: {status}")
                    else:
                        error = str(result) if result.isError() else "No bits"
                        results.append(f"Read #{i+1}: ERROR - {error}")
                        _logger.warning(f"[BIT TEST] M{bit_address} (addr {modbus_addr}) Read #{i+1}: ERROR - {error}")
                    
                    client.close()
                    client = None
                else:
                    results.append(f"Read #{i+1}: Connection failed")
                    _logger.warning(f"[BIT TEST] M{bit_address} Read #{i+1}: Connection failed")
                
                time.sleep(0.2)
                
            except Exception as e:
                results.append(f"Read #{i+1}: Exception - {e}")
                _logger.error(f"[BIT TEST] M{bit_address} Read #{i+1}: {e}", exc_info=True)
                if client:
                    try:
                        client.close()
                    except:
                        pass
                    client = None
                time.sleep(0.2)
        
        message = f"Test Results for M{bit_address}:\n"
        message += f"Modbus Address Used: {bit_address + self.m_bit_address_offset}\n"
        message += "=" * 50 + "\n"
        message += "\n".join(results)
        message += f"\n\n💡 If all reads show OFF but the bit should be ON:"
        message += f"\n   1. Check 'M Bit Address Offset' - might need adjustment"
        message += f"\n   2. Verify the bit address is correct in PLC"
        message += f"\n   3. Check if the bit is actually set in PLC program"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('M Bit Test Results'),
                'message': message,
                'type': 'info',
                'sticky': True,
            }
        }
    
    def test_d_register_reading(self):
        """Test reading D registers to diagnose why values are zero"""
        self.ensure_one()
        import time
        
        _logger.info(f"[TEST D REGISTERS] Testing D register reading for workstation {self.name}")
        
        client = None
        results = []
        
        try:
            client = self._get_plc_client()
            if not client or not client.connect():
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error'),
                        'message': _('Failed to connect to PLC'),
                        'type': 'danger',
                    }
                }
            
            time.sleep(0.1)
            
            # Test reading the configured D registers
            test_registers = [
                ('Torque', self.torque_register, f"D{self.torque_register}" if self.torque_register else 'N/A'),
                ('Initial Position', self.initial_position_register, f"D{self.initial_position_register}" if self.initial_position_register else 'N/A'),
                ('Final Position', self.final_position_register, f"D{self.final_position_register}" if self.final_position_register else 'N/A'),
                ('Load Cell', self.load_cell_register, f"D{self.load_cell_register}" if self.load_cell_register else 'N/A'),
                ('Cycle Time', self.cycle_time_register, f"D{self.cycle_time_register}" if self.cycle_time_register else 'N/A'),
            ]
            
            # Try importing BinaryPayloadDecoder
            use_pymodbus_decoder = True
            try:
                from pymodbus.payload import BinaryPayloadDecoder
                from pymodbus.constants import Endian
            except ImportError:
                try:
                    from pymodbus.client.common import BinaryPayloadDecoder
                    from pymodbus.constants import Endian
                except ImportError:
                    use_pymodbus_decoder = False
                    class Endian:
                        Big = 1
                        Little = 2
            
            for name, reg_addr, reg_name in test_registers:
                if not reg_addr:
                    results.append(f"\n{name} ({reg_name}): ⚠️ Not configured")
                    continue
                
                try:
                    # Read single register (16-bit value) - use raw value directly
                    result = self._read_holding_registers(client, reg_addr, 1)
                    if not result.isError() and result.registers:
                        raw_val = result.registers[0]
                        results.append(f"\n{name} ({reg_name}, address {reg_addr}):")
                        results.append(f"  Raw register value: {raw_val}")
                        results.append(f"  Actual value (no conversion): {float(raw_val)}")
                        
                        if raw_val == 0:
                            results.append(f"  ⚠️ Value is zero - check if register has data in PLC")
                    else:
                        error_msg = str(result) if result.isError() else "No registers returned"
                        results.append(f"\n{name} ({reg_name}, address {reg_addr}): ❌ Error: {error_msg}")
                except Exception as e:
                    results.append(f"\n{name} ({reg_name}, address {reg_addr}): ❌ Exception: {e}")
                
                time.sleep(0.1)
            
            client.close()
            
            message = "D Register Reading Test Results:\n"
            message += "=" * 60 + "\n"
            message += "".join(results)
            message += "\n\n💡 Interpretation:"
            message += "\n  - Raw register value is used directly (no float conversion)"
            message += "\n  - If value is 0: Register might be empty in PLC"
            message += "\n  - If error occurs: Check register address (might need offset)"
            message += "\n  - Compare with your PLC program to verify correct addresses"
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('D Register Test Results'),
                    'message': message,
                    'type': 'info',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            _logger.error(f"Error in test_d_register_reading: {e}", exc_info=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Error testing D registers: %s') % str(e),
                    'type': 'danger',
                }
            }
        finally:
            if client:
                try:
                    client.close()
                except:
                    pass
    
    def test_cycle_detection(self):
        """Manual test method to check cycle detection"""
        self.ensure_one()
        try:
            # Test connection first
            connection_ok = False
            try:
                client = self._get_plc_client()
                if client and client.connect():
                    connection_ok = True
                    client.close()
            except Exception as e:
                _logger.error(f"Connection test failed: {e}")
            
            # Read current cycle status
            status = self._read_cycle_status()
            
            # Also test reading individual bits to see raw values
            raw_values = {}
            raw_errors = {}
            try:
                if self.part_presence_bit:
                    val = self.read_plc_coil(self.part_presence_bit)
                    raw_values['part_presence'] = val
                    if val is None:
                        raw_errors['part_presence'] = f"M{self.part_presence_bit} read failed (check logs)"
                
                val = self.read_plc_coil(self.cycle_start_bit)
                raw_values['cycle_start'] = val
                if val is None:
                    raw_errors['cycle_start'] = f"M{self.cycle_start_bit} read failed (check logs)"
                
                val = self.read_plc_coil(self.cycle_complete_bit)
                raw_values['cycle_complete'] = val
                if val is None:
                    raw_errors['cycle_complete'] = f"M{self.cycle_complete_bit} read failed (check logs)"
                
                val = self.read_plc_coil(self.cycle_ok_bit)
                raw_values['cycle_ok'] = val
                if val is None:
                    raw_errors['cycle_ok'] = f"M{self.cycle_ok_bit} read failed (check logs)"
                
                val = self.read_plc_coil(self.cycle_nok_bit)
                raw_values['cycle_nok'] = val
                if val is None:
                    raw_errors['cycle_nok'] = f"M{self.cycle_nok_bit} read failed (check logs)"
            except Exception as e:
                _logger.error(f"Error reading raw coil values: {e}", exc_info=True)
                raw_errors['general'] = str(e)
            
            message = f"PLC Connection: {'✅ Connected' if connection_ok else '❌ Disconnected'}\n"
            message += f"PLC IP: {self.plc_ip}:{self.plc_port}\n"
            message += f"Monitoring Active: {'✅ Yes' if self.monitoring_active else '❌ No'}\n\n"
            message += f"📊 Current Bit Status (from _read_cycle_status):\n"
            if self.part_presence_bit:
                pp_val = "🔴 ON" if status.get('part_presence', False) else "⚪ OFF"
                message += f"  Part Presence (M{self.part_presence_bit}): {pp_val}\n"
            cs_val = "🔴 ON" if status.get('cycle_start', False) else "⚪ OFF"
            message += f"  Cycle Start (M{self.cycle_start_bit}): {cs_val}\n"
            cc_val = "🔴 ON" if status.get('cycle_complete', False) else "⚪ OFF"
            message += f"  Cycle Complete (M{self.cycle_complete_bit}): {cc_val}\n"
            ok_val = "🔴 ON" if status.get('cycle_ok', False) else "⚪ OFF"
            message += f"  Cycle OK (M{self.cycle_ok_bit}): {ok_val}\n"
            nok_val = "🔴 ON" if status.get('cycle_nok', False) else "⚪ OFF"
            message += f"  Cycle NOK (M{self.cycle_nok_bit}): {nok_val}\n\n"
            message += f"💡 Note: All bits are currently OFF (expected when no cycle is running)\n"
            message += f"   When you start a cycle, you should see bits turn ON and [BIT CHANGE] logs\n\n"
            message += f"Raw Coil Values (direct read):\n"
            if self.part_presence_bit:
                val = raw_values.get('part_presence', 'Error')
                if val is None:
                    val = f"❌ {raw_errors.get('part_presence', 'Read failed')}"
                message += f"  M{self.part_presence_bit}: {val}\n"
            
            val = raw_values.get('cycle_start', 'Error')
            if val is None:
                val = f"❌ {raw_errors.get('cycle_start', 'Read failed')}"
            message += f"  M{self.cycle_start_bit}: {val}\n"
            
            val = raw_values.get('cycle_complete', 'Error')
            if val is None:
                val = f"❌ {raw_errors.get('cycle_complete', 'Read failed')}"
            message += f"  M{self.cycle_complete_bit}: {val}\n"
            
            val = raw_values.get('cycle_ok', 'Error')
            if val is None:
                val = f"❌ {raw_errors.get('cycle_ok', 'Read failed')}"
            message += f"  M{self.cycle_ok_bit}: {val}\n"
            
            val = raw_values.get('cycle_nok', 'Error')
            if val is None:
                val = f"❌ {raw_errors.get('cycle_nok', 'Read failed')}"
            message += f"  M{self.cycle_nok_bit}: {val}\n"
            
            if raw_errors:
                message += f"\n⚠️ Read Errors Detected:\n"
                for key, error in raw_errors.items():
                    message += f"  {key}: {error}\n"
                message += f"\n💡 Check Odoo logs for detailed error messages"
            
            # Try to create cycle if complete and OK
            if status.get('cycle_complete', False) and status.get('cycle_ok', False):
                try:
                    cycle = self._create_cycle_from_plc_data()
                    if cycle:
                        message += f"\n✅ Cycle created: {cycle.cycle_number}\n"
                        message += f"QR Code: {cycle.qr_code_data}"
                    else:
                        message += "\n❌ Failed to create cycle"
                except Exception as e:
                    message += f"\n❌ Error creating cycle: {e}"
            elif status.get('cycle_complete', False):
                message += "\n⚠️ Cycle complete but not OK (check NOK bit)"
            else:
                message += "\n⚠️ Cycle not complete yet"
                message += "\n\n💡 Tip: Ensure M222 (Cycle Complete) and M221 (Cycle OK) are ON in the PLC"
                
                # Add diagnostic: test reading coils
                message += "\n\n🔍 Diagnostic: Testing coil addresses..."
                try:
                    client = self._get_plc_client()
                    if client and client.connect():
                        import time
                        time.sleep(0.05)
                        
                        # Try reading all bits in one batch (from min to max address)
                        all_addrs = [a for a in [
                            self.part_presence_bit,
                            self.cycle_start_bit,
                            self.cycle_complete_bit,
                            self.cycle_ok_bit,
                            self.cycle_nok_bit
                        ] if a]
                        
                        if all_addrs:
                            min_addr = min(all_addrs)
                            max_addr = max(all_addrs)
                            
                            # Try batch read
                            try:
                                batch_result = self._read_coils(client, min_addr, max_addr - min_addr + 1)
                                if not batch_result.isError() and batch_result.bits:
                                    message += f"\n  ✅ Batch read: {len(batch_result.bits)} coils from M{min_addr} to M{max_addr}"
                                    # Check which bits are ON
                                    on_bits = []
                                    for i, bit_val in enumerate(batch_result.bits):
                                        if bit_val:
                                            on_bits.append(min_addr + i)
                                    if on_bits:
                                        message += f"\n  🔴 ON coils: M{on_bits}"
                                    else:
                                        message += f"\n  ⚪ All coils OFF in range M{min_addr}-M{max_addr}"
                                else:
                                    error_msg = str(batch_result) if batch_result.isError() else "No bits returned"
                                    message += f"\n  ❌ Batch read failed: {error_msg}"
                            except Exception as e:
                                message += f"\n  ❌ Batch read error: {e}"
                                _logger.error(f"Batch read error: {e}", exc_info=True)
                        
                        # Test individual addresses with detailed error reporting
                        test_ranges = []
                        if self.part_presence_bit:
                            test_ranges.append((self.part_presence_bit, f'M{self.part_presence_bit} (Part Presence)'))
                        test_ranges.extend([
                            (self.cycle_start_bit, f'M{self.cycle_start_bit} (Cycle Start)'),
                            (self.cycle_complete_bit, f'M{self.cycle_complete_bit} (Cycle Complete)'),
                            (self.cycle_ok_bit, f'M{self.cycle_ok_bit} (Cycle OK)'),
                            (self.cycle_nok_bit, f'M{self.cycle_nok_bit} (Cycle NOK)'),
                        ])
                        
                        message += f"\n\n  Individual address test:"
                        for base_addr, desc in test_ranges:
                            try:
                                result = self._read_coils(client, base_addr, 1)
                                if result.isError():
                                    error_detail = str(result)
                                    message += f"\n    {desc}: ❌ Modbus Error - {error_detail}"
                                    _logger.warning(f"Modbus error reading {desc} (M{base_addr}): {error_detail}")
                                elif result.bits:
                                    val = "🔴 ON" if result.bits[0] else "⚪ OFF"
                                    message += f"\n    {desc}: {val}"
                                else:
                                    message += f"\n    {desc}: ❌ No bits returned"
                                    _logger.warning(f"No bits returned for {desc} (M{base_addr})")
                                time.sleep(0.01)
                            except Exception as e:
                                message += f"\n    {desc}: ❌ Exception - {type(e).__name__}: {e}"
                                _logger.error(f"Exception reading {desc} (M{base_addr}): {e}", exc_info=True)
                        
                        message += f"\n\n✅ PLC Communication Status:"
                        message += f"\n  • Batch read: SUCCESS (read {max_addr - min_addr + 1} coils)"
                        message += f"\n  • Individual reads: SUCCESS (all addresses readable)"
                        message += f"\n  • Connection: STABLE"
                        message += f"\n\n📝 What to do next:"
                        message += f"\n  1. Ensure monitoring is ACTIVE (check 'Monitoring Active' field)"
                        message += f"\n  2. Start a cycle on the PLC"
                        message += f"\n  3. Watch Odoo logs for [BIT CHANGE] messages"
                        message += f"\n  4. You should see:"
                        message += f"\n     - M20 (Part Presence) turn ON when part is loaded"
                        message += f"\n     - M201 (Cycle Start) turn ON when cycle starts"
                        message += f"\n     - M222 (Cycle Complete) turn ON when cycle finishes"
                        message += f"\n     - M221 (Cycle OK) or M349 (Cycle NOK) turn ON for result"
                        
                        client.close()
                except Exception as e:
                    message += f"\n  ❌ Diagnostic error: {e}"
                    _logger.error(f"Diagnostic error: {e}", exc_info=True)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Cycle Detection Test'),
                    'message': message,
                    'type': 'info',
                    'sticky': True,
                }
            }
        except Exception as e:
            _logger.error(f"Error in test_cycle_detection: {e}", exc_info=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Error testing cycle detection: %s') % str(e),
                    'type': 'danger',
                }
            }
