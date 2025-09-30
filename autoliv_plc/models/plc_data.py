from odoo import models, fields, api
from datetime import datetime, timedelta
import logging
import threading
import time
import qrcode
import io
import base64
import json
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

_logger = logging.getLogger(__name__)


class PlcData(models.Model):
    _name = 'plc.data'
    _description = 'PLC Data Records'
    _rec_name = 'part_number'
    _order = 'create_date desc'

    part_number = fields.Char('Part Number', required=True)
    barcode = fields.Char('Barcode', required=True)
    cycle_time = fields.Float('Cycle Time (seconds)')
    measurement_data = fields.Text('Measurement Data (JSON)')
    qr_code_data = fields.Text('QR Code Data')
    qr_code_image = fields.Binary('QR Code Image')

    # Status fields
    state = fields.Selection([
        ('draft', 'Draft'),
        ('printed', 'Printed'),
        ('scanned', 'Scanned'),
        ('verified', 'Verified'),
        ('failed', 'Failed')
    ], default='draft', string='Status')

    scanned_barcode = fields.Char('Scanned Barcode')
    scan_timestamp = fields.Datetime('Scan Timestamp')
    verification_result = fields.Boolean('Verification Result')

    # PLC data fields
    plc_timestamp = fields.Datetime('PLC Timestamp')
    operator_id = fields.Char('Operator ID')
    station_id = fields.Char('Station ID')

    @api.model
    def create_from_plc_data(self, plc_data):
        """Create a new record from PLC data"""
        # Generate barcode
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        barcode = f"{plc_data.get('part_number', 'UNKNOWN')}_{timestamp}"

        # Create QR code data
        qr_data = {
            'barcode': barcode,
            'part_number': plc_data.get('part_number'),
            'timestamp': timestamp,
            'station': plc_data.get('station_id'),
            'operator': plc_data.get('operator_id')
        }
        qr_code_string = f"{barcode}|{plc_data.get('part_number')}|{timestamp}"

        # Generate QR code image
        qr_image = self._generate_qr_code(qr_code_string)

        record = self.create({
            'part_number': plc_data.get('part_number'),
            'barcode': barcode,
            'cycle_time': plc_data.get('cycle_time'),
            'measurement_data': str(plc_data.get('measurements', {})),
            'qr_code_data': qr_code_string,
            'qr_code_image': qr_image,
            'plc_timestamp': fields.Datetime.now(),
            'operator_id': plc_data.get('operator_id'),
            'station_id': plc_data.get('station_id'),
            'state': 'draft'
        })

        # Send to printer
        self._send_to_printer(record)

        return record

    def _generate_qr_code(self, data):
        """Generate QR code image"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue())
        return img_str

    def _send_to_printer(self, record):
        """Send label to Zebra printer"""
        try:
            config = self.env['plc.config'].get_active_config()
            if not config:
                _logger.error("No active PLC configuration found")
                return False

            # ZPL (Zebra Programming Language) template
            zpl_template = f"""
^XA
^FO50,50^GFA,1024,1024,16,,{record.qr_code_image.decode() if record.qr_code_image else ''}^FS
^FO200,50^FDPart: {record.part_number}^FS
^FO200,80^FDBarcode: {record.barcode}^FS
^FO200,110^FDTime: {record.plc_timestamp.strftime('%Y-%m-%d %H:%M:%S')}^FS
^FO200,140^FDOperator: {record.operator_id or 'N/A'}^FS
^FO200,170^FDStation: {record.station_id or 'N/A'}^FS
^XZ
"""

            # Send to printer (implement based on your printer communication method)
            self._print_label(zpl_template, config)
            record.state = 'printed'

        except Exception as e:
            _logger.error(f"Error printing label: {e}")
            record.state = 'failed'

    def _print_label(self, zpl_data, config):
        """Send ZPL data to printer"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((config.printer_ip, config.printer_port))
            sock.send(zpl_data.encode())
            sock.close()
            return True
        except Exception as e:
            _logger.error(f"Printer communication error: {e}")
            return False

    def verify_scanned_barcode(self, scanned_barcode):
        """Verify scanned barcode against stored data"""
        self.scanned_barcode = scanned_barcode
        self.scan_timestamp = fields.Datetime.now()

        if self.barcode == scanned_barcode:
            self.verification_result = True
            self.state = 'verified'
            return True
        else:
            self.verification_result = False
            self.state = 'failed'
            return False

    def action_scan_qr(self):
        """Action to trigger QR scanning"""
        return {
            'type': 'ir.actions.client',
            'tag': 'plc_qr_scanner',
            'context': {'active_id': self.id}
        }

    def action_print_label(self):
        """Reprint the label"""
        self._send_to_printer(self)
        return True

    @api.model
    def get_dashboard_stats(self):
        """Get statistics for dashboard"""
        today = fields.Date.today()
        yesterday = today - timedelta(days=1)

        # Today's stats
        today_records = self.search([
            ('create_date', '>=', today),
            ('create_date', '<', today + timedelta(days=1))
        ])

        # Yesterday's stats for comparison
        yesterday_records = self.search([
            ('create_date', '>=', yesterday),
            ('create_date', '<', today)
        ])

        return {
            'today_total': len(today_records),
            'today_verified': len(today_records.filtered(lambda r: r.state == 'verified')),
            'today_failed': len(today_records.filtered(lambda r: r.state == 'failed')),
            'yesterday_total': len(yesterday_records),
            'success_rate': (len(today_records.filtered(lambda r: r.state == 'verified')) / len(
                today_records) * 100) if today_records else 0,
            'recent_records': today_records.read(['part_number', 'barcode', 'state', 'create_date'])[:10]
        }


class PlcCommunicator(models.TransientModel):
    _name = 'plc.communicator'
    _description = 'PLC Communication Handler'

    @api.model
    def start_monitoring(self):
        """Start PLC monitoring in background"""
        threading.Thread(target=self._monitor_plc, daemon=True).start()

    def _monitor_plc(self):
        """Monitor PLC for cycle completion"""
        while True:
            try:
                config = self.env['plc.config'].get_active_config()
                if not config:
                    time.sleep(5)
                    continue

                client = ModbusTcpClient(config.plc_ip, port=config.plc_port)

                if client.connect():
                    # Check cycle complete signal
                    result = client.read_holding_registers(
                        config.cycle_complete_address, 1, slave=config.unit_id
                    )

                    if result.registers[0] == 1:  # Cycle complete
                        # Read PLC data
                        plc_data = self._read_plc_data(client, config)

                        # Create record in Odoo
                        with self.env.cr.savepoint():
                            self.env['plc.data'].create_from_plc_data(plc_data)

                        # Reset cycle complete flag
                        client.write_register(
                            config.cycle_complete_address, 0, slave=config.unit_id
                        )

                    client.close()

            except Exception as e:
                _logger.error(f"PLC monitoring error: {e}")

            time.sleep(1)  # Check every second

    def _read_plc_data(self, client, config):
        """Read all required data from PLC"""
        try:
            # Read part number (assuming it's stored as ASCII in holding registers)
            part_result = client.read_holding_registers(
                config.part_number_address, 10, slave=config.unit_id
            )
            part_number = ''.join(chr(reg) for reg in part_result.registers if reg != 0)

            # Read measurement data
            measurement_result = client.read_holding_registers(
                config.measurement_start_address, 20, slave=config.unit_id
            )

            # Read other data (cycle time, operator, station)
            cycle_time_result = client.read_holding_registers(400, 2, slave=config.unit_id)
            cycle_time = (cycle_time_result.registers[0] << 16 | cycle_time_result.registers[1]) / 100.0

            operator_result = client.read_holding_registers(410, 5, slave=config.unit_id)
            operator_id = ''.join(chr(reg) for reg in operator_result.registers if reg != 0)

            station_result = client.read_holding_registers(420, 5, slave=config.unit_id)
            station_id = ''.join(chr(reg) for reg in station_result.registers if reg != 0)

            return {
                'part_number': part_number.strip(),
                'cycle_time': cycle_time,
                'measurements': measurement_result.registers,
                'operator_id': operator_id.strip(),
                'station_id': station_id.strip(),
            }

        except Exception as e:
            _logger.error(f"Error reading PLC data: {e}")
            return {}

    @api.model
    def get_connection_status(self):
        """Check if PLC connection is active"""
        config = self.env['plc.config'].get_active_config()
        if not config:
            return {'status': 'no_config', 'message': 'No active configuration'}

        try:
            client = ModbusTcpClient(config.plc_ip, port=config.plc_port)

            if client.connect():
                client.close()
                return {'status': 'connected', 'message': 'PLC connected'}
            else:
                return {'status': 'disconnected', 'message': 'PLC disconnected'}

        except Exception as e:
            return {'status': 'error', 'message': f'Connection error: {str(e)}'}

    def _handle_plc_error(self, error_msg):
        """Handle PLC communication errors"""
        _logger.error(f"PLC Error: {error_msg}")

        # Create error log record
        self.env['plc.error.log'].create({
            'error_message': error_msg,
            'error_time': fields.Datetime.now(),
            'error_type': 'communication'
        })


# Error logging model
class PlcErrorLog(models.Model):
    _name = 'plc.error.log'
    _description = 'PLC Error Logs'
    _order = 'error_time desc'

    error_message = fields.Text('Error Message', required=True)
    error_time = fields.Datetime('Error Time', required=True)
    error_type = fields.Selection([
        ('communication', 'Communication'),
        ('data', 'Data Processing'),
        ('printer', 'Printer'),
        ('qr', 'QR Code')
    ], string='Error Type', default='communication')
    resolved = fields.Boolean('Resolved', default=False)