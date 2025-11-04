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
        string='Torque Register',
        help="Modbus register for torque value"
    )
    initial_position_register = fields.Integer(
        string='Initial Position Register',
        help="Modbus register for initial position"
    )
    forward_load_register = fields.Integer(
        string='Forward Load Register',
        help="Modbus register for forward load"
    )
    final_position_register = fields.Integer(
        string='Final Position Register',
        help="Modbus register for final position"
    )
    cycle_time_register = fields.Integer(
        string='Cycle Time Register',
        help="Modbus register for cycle time"
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
        default=20,
        help="Number of characters in barcode"
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
            
            client = ModbusTcpClient(
                host=self.plc_ip,
                port=self.plc_port,
                timeout=self.timeout
            )
            
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
        except ImportError:
            raise UserError(_("Please install pymodbus library: pip install pymodbus"))
        except Exception as e:
            self.connection_status = 'error'
            _logger.error(f"PLC connection error: {e}")
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
        try:
            from pymodbus.client import ModbusTcpClient
            from pymodbus.payload import BinaryPayloadDecoder
            from pymodbus.constants import Endian
            
            client = ModbusTcpClient(
                host=self.plc_ip,
                port=self.plc_port,
                timeout=self.timeout
            )
            
            if not client.connect():
                raise UserError(_("Unable to connect to PLC"))
            
            # Read cycle completion status
            result = client.read_holding_registers(
                self.cycle_complete_register, 1, unit=self.unit_id
            )
            
            if result.isError():
                raise UserError(_("Error reading from PLC: %s") % result)
            
            cycle_complete = result.registers[0]
            
            if cycle_complete == 1:  # Cycle completed
                # Read all measurement data
                data = {}
                
                # Read torque
                if self.torque_register:
                    result = client.read_holding_registers(
                        self.torque_register, 2, unit=self.unit_id
                    )
                    if not result.isError():
                        decoder = BinaryPayloadDecoder.fromRegisters(
                            result.registers, byteorder=Endian.Big, wordorder=Endian.Big
                        )
                        data['torque_nm'] = decoder.decode_32bit_float()
                
                # Read initial position
                if self.initial_position_register:
                    result = client.read_holding_registers(
                        self.initial_position_register, 2, unit=self.unit_id
                    )
                    if not result.isError():
                        decoder = BinaryPayloadDecoder.fromRegisters(
                            result.registers, byteorder=Endian.Big, wordorder=Endian.Big
                        )
                        data['initial_position'] = decoder.decode_32bit_float()
                
                # Read forward load
                if self.forward_load_register:
                    result = client.read_holding_registers(
                        self.forward_load_register, 2, unit=self.unit_id
                    )
                    if not result.isError():
                        decoder = BinaryPayloadDecoder.fromRegisters(
                            result.registers, byteorder=Endian.Big, wordorder=Endian.Big
                        )
                        data['forward_load_after'] = decoder.decode_32bit_float()
                
                # Read final position
                if self.final_position_register:
                    result = client.read_holding_registers(
                        self.final_position_register, 2, unit=self.unit_id
                    )
                    if not result.isError():
                        decoder = BinaryPayloadDecoder.fromRegisters(
                            result.registers, byteorder=Endian.Big, wordorder=Endian.Big
                        )
                        data['final_position'] = decoder.decode_32bit_float()
                
                # Read cycle time
                if self.cycle_time_register:
                    result = client.read_holding_registers(
                        self.cycle_time_register, 2, unit=self.unit_id
                    )
                    if not result.isError():
                        decoder = BinaryPayloadDecoder.fromRegisters(
                            result.registers, byteorder=Endian.Big, wordorder=Endian.Big
                        )
                        data['cycle_time'] = decoder.decode_32bit_float()
                
                # Read result
                if self.result_register:
                    result = client.read_holding_registers(
                        self.result_register, 1, unit=self.unit_id
                    )
                    if not result.isError():
                        data['result'] = 'ok' if result.registers[0] == 1 else 'nok'
                
                # Read barcode
                if self.barcode_register_start and self.barcode_length:
                    registers_needed = (self.barcode_length + 1) // 2
                    result = client.read_holding_registers(
                        self.barcode_register_start, registers_needed, unit=self.unit_id
                    )
                    if not result.isError():
                        decoder = BinaryPayloadDecoder.fromRegisters(
                            result.registers, byteorder=Endian.Big, wordorder=Endian.Big
                        )
                        barcode_bytes = decoder.decode_string(self.barcode_length)
                        data['barcode'] = barcode_bytes.decode('utf-8').strip('\x00')
                
                client.close()
                return data
            else:
                client.close()
                return None
                
        except ImportError:
            raise UserError(_("Please install pymodbus library: pip install pymodbus"))
        except Exception as e:
            _logger.error(f"Error reading PLC data: {e}")
            raise UserError(_("Error reading from PLC: %s") % str(e))

    def create_cycle_from_plc(self, part_name=None):
        """Create a new cycle record from PLC data"""
        self.ensure_one()
        
        data = self.read_plc_data()
        if not data:
            return None
        
        # Generate barcode if not provided
        if 'barcode' not in data or not data['barcode']:
            data['barcode'] = self.env['ir.sequence'].next_by_code('plc.barcode') or 'AUTO'
        
        # Set part name
        if part_name:
            data['part_name'] = part_name
        
        # Create cycle record
        cycle_vals = {
            'part_name': data.get('part_name', 'UNKNOWN'),
            'barcode': data.get('barcode', ''),
            'torque_nm': data.get('torque_nm', 0.0),
            'initial_position': data.get('initial_position', 0.0),
            'forward_load_after': data.get('forward_load_after', 0.0),
            'final_position': data.get('final_position', 0.0),
            'cycle_time': data.get('cycle_time', 0.0),
            'result': data.get('result', 'pending'),
            'workstation_id': self.id,
        }
        
        cycle = self.env['plc.cycle'].create(cycle_vals)
        
        # Generate QR code
        cycle.generate_qr_code_data()
        cycle.generate_qr_code_image()
        
        return cycle

    def action_read_plc_data(self):
        """Action to read data from PLC"""
        try:
            cycle = self.create_cycle_from_plc()
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
