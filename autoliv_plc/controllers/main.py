from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class PLCController(http.Controller):

    @http.route('/plc/scan_qr', type='json', auth='user', methods=['POST'])
    def scan_qr_code(self, **kw):
        """Handle QR code scanning"""
        try:
            scanned_data = request.jsonrequest.get('scanned_data')
            record_id = request.jsonrequest.get('record_id')

            if not scanned_data or not record_id:
                return {'success': False, 'message': 'Missing required data'}

            record = request.env['plc.data'].browse(int(record_id))
            if not record.exists():
                return {'success': False, 'message': 'Record not found'}

            # Extract barcode from scanned data
            barcode = scanned_data.split('|')[0] if '|' in scanned_data else scanned_data

            success = record.verify_scanned_barcode(barcode)

            return {
                'success': success,
                'message': 'Verification successful' if success else 'Barcode mismatch',
                'state': record.state
            }

        except Exception as e:
            _logger.error(f"QR scan error: {e}")
            return {'success': False, 'message': str(e)}

    @http.route('/plc/start_monitoring', type='json', auth='user', methods=['POST'])
    def start_plc_monitoring(self, **kw):
        """Start PLC monitoring"""
        try:
            request.env['plc.communicator'].start_monitoring()
            return {'success': True, 'message': 'PLC monitoring started'}
        except Exception as e:
            _logger.error(f"Error starting PLC monitoring: {e}")
            return {'success': False, 'message': str(e)}