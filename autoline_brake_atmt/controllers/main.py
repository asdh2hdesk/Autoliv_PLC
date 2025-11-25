# -*- coding: utf-8 -*-

import json
import logging
from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PlcDashboardController(http.Controller):

    @http.route('/plc/dashboard', type='http', auth='user', website=True)
    def dashboard(self, **kwargs):
        """Main dashboard page"""
        return request.render('autoline_brake_atmt.dashboard_template', {})

    @http.route('/plc/scan', type='http', auth='user', website=True)
    def scan_page(self, **kwargs):
        """QR code scanning page"""
        return request.render('autoline_brake_atmt.scan_template', {})

    @http.route('/plc/monitor', type='http', auth='user', website=True)
    def monitor_page(self, **kwargs):
        """Real-time monitoring page"""
        return request.render('autoline_brake_atmt.monitor_template', {})

    @http.route('/plc/print/<int:cycle_id>', type='http', auth='user', website=True)
    def print_qr_code(self, cycle_id, **kwargs):
        """Print QR code for cycle"""
        try:
            cycle = request.env['plc.cycle'].browse(cycle_id)
            if not cycle.exists():
                return request.render('autoline_brake_atmt.error_template', {
                    'error': _('Cycle not found')
                })
            
            # Generate QR code if not exists
            if not cycle.qr_code_data:
                cycle.generate_qr_code_data()
            if not cycle.qr_code_image:
                cycle.generate_qr_code_image()
            
            # Mark as printed
            cycle.qr_code_printed = True
            
            return request.render('autoline_brake_atmt.print_template', {
                'cycle': cycle,
                'qr_data': cycle.qr_code_data
            })
            
        except Exception as e:
            _logger.error(f"Error printing QR code: {e}")
            return request.render('autoline_brake_atmt.error_template', {
                'error': _('Error printing QR code: %s') % str(e)
            })

    @http.route('/plc/scan/process', type='json', auth='user', methods=['POST'])
    def process_scan(self, scanned_data, scanner_id=None, workstation_id=None):
        """Process scanned QR code data"""
        try:
            result = request.env['qr.code.log'].process_scan(
                scanned_data=scanned_data,
                scanner_id=scanner_id,
                workstation_id=workstation_id
            )
            return result
        except Exception as e:
            _logger.error(f"Error processing scan: {e}")
            return {
                'scan_log_id': None,
                'match_status': 'error',
                'cycle_id': None,
                'message': _('Error processing scan: %s') % str(e)
            }

    @http.route('/plc/dashboard/data', type='json', auth='user', methods=['POST'])
    def get_dashboard_data(self, date_from=None, date_to=None):
        """Get dashboard data via AJAX"""
        try:
            dashboard_data = request.env['dashboard.data'].get_dashboard_metrics(
                date_from=date_from,
                date_to=date_to
            )
            return dashboard_data
        except Exception as e:
            _logger.error(f"Error getting dashboard data: {e}")
            return {'error': str(e)}

    @http.route('/plc/dashboard/hourly', type='json', auth='user', methods=['POST'])
    def get_hourly_data(self, date_from=None, date_to=None):
        """Get hourly data for charts"""
        try:
            hourly_data = request.env['dashboard.data'].get_hourly_data(
                date_from=date_from,
                date_to=date_to
            )
            return hourly_data
        except Exception as e:
            _logger.error(f"Error getting hourly data: {e}")
            return {'error': str(e)}

    @http.route('/plc/dashboard/workstations', type='json', auth='user', methods=['POST'])
    def get_workstation_data(self, date_from=None, date_to=None):
        """Get workstation data"""
        try:
            workstation_data = request.env['dashboard.data'].get_workstation_data(
                date_from=date_from,
                date_to=date_to
            )
            return workstation_data
        except Exception as e:
            _logger.error(f"Error getting workstation data: {e}")
            return {'error': str(e)}

    @http.route('/plc/dashboard/recent', type='json', auth='user', methods=['POST'])
    def get_recent_cycles(self, limit=10):
        """Get recent cycles"""
        try:
            recent_data = request.env['dashboard.data'].get_recent_cycles(limit=limit)
            return recent_data
        except Exception as e:
            _logger.error(f"Error getting recent cycles: {e}")
            return {'error': str(e)}

    @http.route('/plc/dashboard/alerts', type='json', auth='user', methods=['POST'])
    def get_alerts(self):
        """Get system alerts"""
        try:
            alerts = request.env['dashboard.data'].get_alerts()
            return alerts
        except Exception as e:
            _logger.error(f"Error getting alerts: {e}")
            return {'error': str(e)}

    @http.route('/plc/plc/read', type='json', auth='user', methods=['POST'])
    def read_plc_data(self, workstation_id):
        """Read data from PLC"""
        try:
            workstation = request.env['plc.workstation'].browse(workstation_id)
            if not workstation.exists():
                return {'error': _('Workstation not found')}
            
            cycle = workstation.create_cycle_from_plc()
            if cycle:
                return {
                    'success': True,
                    'cycle_id': cycle.id,
                    'cycle_number': cycle.cycle_number,
                    'message': _('Cycle data read successfully')
                }
            else:
                return {
                    'success': False,
                    'message': _('No cycle data available from PLC')
                }
        except Exception as e:
            _logger.error(f"Error reading PLC data: {e}")
            return {'error': str(e)}

    @http.route('/plc/plc/test', type='json', auth='user', methods=['POST'])
    def test_plc_connection(self, workstation_id):
        """Test PLC connection"""
        try:
            workstation = request.env['plc.workstation'].browse(workstation_id)
            if not workstation.exists():
                return {'error': _('Workstation not found')}
            
            result = workstation.test_connection()
            return {
                'success': True,
                'message': _('Connection test completed')
            }
        except Exception as e:
            _logger.error(f"Error testing PLC connection: {e}")
            return {'error': str(e)}
