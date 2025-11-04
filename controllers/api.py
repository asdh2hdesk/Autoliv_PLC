# -*- coding: utf-8 -*-

import json
import logging
from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PlcApiController(http.Controller):

    @http.route('/api/plc/cycle', type='json', auth='user', methods=['POST'])
    def create_cycle(self, **kwargs):
        """API endpoint to create cycle from external system"""
        try:
            # Extract data from request
            cycle_data = request.jsonrequest
            
            # Validate required fields
            required_fields = ['part_name', 'barcode']
            for field in required_fields:
                if field not in cycle_data:
                    return {'error': _('Missing required field: %s') % field}
            
            # Create cycle record
            cycle_vals = {
                'part_name': cycle_data.get('part_name'),
                'barcode': cycle_data.get('barcode'),
                'torque_nm': cycle_data.get('torque_nm', 0.0),
                'initial_position': cycle_data.get('initial_position', 0.0),
                'forward_load_after': cycle_data.get('forward_load_after', 0.0),
                'final_position': cycle_data.get('final_position', 0.0),
                'cycle_time': cycle_data.get('cycle_time', 0.0),
                'result': cycle_data.get('result', 'pending'),
                'workstation_id': cycle_data.get('workstation_id'),
            }
            
            cycle = request.env['plc.cycle'].create(cycle_vals)
            
            # Generate QR code
            cycle.generate_qr_code_data()
            cycle.generate_qr_code_image()
            
            return {
                'success': True,
                'cycle_id': cycle.id,
                'cycle_number': cycle.cycle_number,
                'qr_data': cycle.qr_code_data
            }
            
        except Exception as e:
            _logger.error(f"Error creating cycle via API: {e}")
            return {'error': str(e)}

    @http.route('/api/plc/scan', type='json', auth='user', methods=['POST'])
    def process_scan_api(self, **kwargs):
        """API endpoint to process QR code scan"""
        try:
            scan_data = request.jsonrequest
            
            if 'scanned_data' not in scan_data:
                return {'error': _('Missing scanned_data field')}
            
            result = request.env['qr.code.log'].process_scan(
                scanned_data=scan_data['scanned_data'],
                scanner_id=scan_data.get('scanner_id'),
                workstation_id=scan_data.get('workstation_id')
            )
            
            return result
            
        except Exception as e:
            _logger.error(f"Error processing scan via API: {e}")
            return {'error': str(e)}

    @http.route('/api/plc/print', type='json', auth='user', methods=['POST'])
    def print_qr_api(self, **kwargs):
        """API endpoint to print QR code"""
        try:
            print_data = request.jsonrequest
            
            if 'cycle_id' not in print_data:
                return {'error': _('Missing cycle_id field')}
            
            cycle = request.env['plc.cycle'].browse(print_data['cycle_id'])
            if not cycle.exists():
                return {'error': _('Cycle not found')}
            
            # Generate QR code if not exists
            if not cycle.qr_code_data:
                cycle.generate_qr_code_data()
            if not cycle.qr_code_image:
                cycle.generate_qr_code_image()
            
            # Mark as printed
            cycle.qr_code_printed = True
            
            return {
                'success': True,
                'cycle_id': cycle.id,
                'qr_data': cycle.qr_code_data,
                'print_status': 'ready'
            }
            
        except Exception as e:
            _logger.error(f"Error printing QR code via API: {e}")
            return {'error': str(e)}

    @http.route('/api/plc/status/<int:cycle_id>', type='json', auth='user', methods=['GET'])
    def get_cycle_status(self, cycle_id):
        """Get cycle status"""
        try:
            cycle = request.env['plc.cycle'].browse(cycle_id)
            if not cycle.exists():
                return {'error': _('Cycle not found')}
            
            return {
                'cycle_id': cycle.id,
                'cycle_number': cycle.cycle_number,
                'part_name': cycle.part_name,
                'barcode': cycle.barcode,
                'result': cycle.result,
                'qr_printed': cycle.qr_code_printed,
                'qr_scanned': cycle.qr_code_scanned,
                'cycle_datetime': cycle.cycle_datetime.isoformat(),
                'torque_nm': cycle.torque_nm,
                'cycle_time': cycle.cycle_time,
            }
            
        except Exception as e:
            _logger.error(f"Error getting cycle status: {e}")
            return {'error': str(e)}

    @http.route('/api/plc/workstations', type='json', auth='user', methods=['GET'])
    def get_workstations(self):
        """Get all workstations"""
        try:
            workstations = request.env['plc.workstation'].search([])
            
            workstation_data = []
            for workstation in workstations:
                workstation_data.append({
                    'id': workstation.id,
                    'name': workstation.name,
                    'code': workstation.code,
                    'plc_ip': workstation.plc_ip,
                    'plc_port': workstation.plc_port,
                    'is_active': workstation.is_active,
                    'connection_status': workstation.connection_status,
                    'last_connection': workstation.last_connection.isoformat() if workstation.last_connection else None,
                })
            
            return workstation_data
            
        except Exception as e:
            _logger.error(f"Error getting workstations: {e}")
            return {'error': str(e)}

    @http.route('/api/plc/dashboard', type='json', auth='user', methods=['GET'])
    def get_dashboard_api(self, date_from=None, date_to=None):
        """Get dashboard data via API"""
        try:
            dashboard_data = request.env['dashboard.data'].get_dashboard_metrics(
                date_from=date_from,
                date_to=date_to
            )
            return dashboard_data
            
        except Exception as e:
            _logger.error(f"Error getting dashboard data via API: {e}")
            return {'error': str(e)}
