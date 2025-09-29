from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PlcConfig(models.Model):
    _name = 'plc.config'
    _description = 'PLC Configuration'
    _rec_name = 'name'

    name = fields.Char('Configuration Name', required=True)
    plc_ip = fields.Char('PLC IP Address', required=True, default='192.168.0.1')
    plc_port = fields.Integer('PLC Port', required=True, default=502)
    unit_id = fields.Integer('Unit ID', default=1)

    # Modbus Register Addresses
    cycle_complete_address = fields.Integer('Cycle Complete Address', default=100)
    data_ready_address = fields.Integer('Data Ready Address', default=101)
    part_number_address = fields.Integer('Part Number Start Address', default=200)
    measurement_start_address = fields.Integer('Measurement Data Start Address', default=300)

    # Printer Configuration
    printer_ip = fields.Char('Printer IP Address', default='192.168.1.200')
    printer_port = fields.Integer('Printer Port', default=9100)

    active = fields.Boolean('Active', default=True)

    @api.model
    def get_active_config(self):
        return self.search([('active', '=', True)], limit=1)

    def action_test_connection(self):
        """Test PLC connection"""
        try:
            from pymodbus.client import ModbusTcpClient

            client = ModbusTcpClient(self.plc_ip, port=self.plc_port)
            if client.connect():
                # Try to read a register
                result = client.read_holding_registers(0, 1, unit=self.unit_id)
                client.close()

                if not result.isError():
                    message = "Connection successful!"
                    message_type = 'success'
                else:
                    message = f"Connection error: {result}"
                    message_type = 'warning'
            else:
                message = "Cannot connect to PLC"
                message_type = 'danger'

        except Exception as e:
            message = f"Connection failed: {str(e)}"
            message_type = 'danger'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'PLC Connection Test',
                'message': message,
                'type': message_type,
                'sticky': False,
            }
        }

    def action_start_monitoring(self):
        """Start PLC monitoring"""
        try:
            self.env['plc.communicator'].start_monitoring()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'PLC Monitoring',
                    'message': 'Monitoring started successfully',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'Failed to start monitoring: {str(e)}',
                    'type': 'danger',
                    'sticky': False,
                }
            }