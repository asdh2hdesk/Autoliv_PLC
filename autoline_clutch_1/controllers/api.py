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
    def process_scan_api(self, scanned_data=None, scanner_id=None, workstation_id=None, **kwargs):
        """API endpoint to process QR code scan (new format: 32-char string)"""
        try:
            # Get scanned_data from kwargs or direct parameter
            if not scanned_data and kwargs:
                scanned_data = kwargs.get('scanned_data') or kwargs.get('qr_code') or kwargs.get('data') or ''
            
            if not scanned_data:
                return {'error': _('Missing scanned_data field')}
            
            scanned_string = scanned_data.strip() if isinstance(scanned_data, str) else str(scanned_data).strip()
            
            # Find matching cycle by QR code
            cycle = request.env['plc.cycle'].search([
                ('qr_code_data', '=', scanned_string)
            ], limit=1)
            
            if cycle:
                # Match found - update cycle
                result = cycle.scan_qr_code(scanned_string)
                
                # Also create QR log entry
                log_result = request.env['qr.code.log'].process_scan(
                    scanned_data=scanned_string,
                    scanner_id=scanner_id or kwargs.get('scanner_id'),
                    workstation_id=workstation_id or kwargs.get('workstation_id') or cycle.workstation_id.id
                )
                
                return {
                    'success': True,
                    'match_status': 'matched',
                    'cycle_id': cycle.id,
                    'cycle_number': cycle.cycle_number,
                    'part_name': cycle.part_name,
                    'message': _('QR Code matched successfully!'),
                    'qr_match_status': cycle.qr_match_status,
                }
            else:
                # No match found
                log_result = request.env['qr.code.log'].process_scan(
                    scanned_data=scanned_string,
                    scanner_id=scanner_id or kwargs.get('scanner_id'),
                    workstation_id=workstation_id or kwargs.get('workstation_id')
                )
                
                return {
                    'success': False,
                    'match_status': 'not_found',
                    'message': _('QR Code not found in database'),
                    'scanned_data': scanned_string,
                }
            
        except Exception as e:
            _logger.error(f"Error processing scan via API: {e}")
            return {'error': str(e), 'success': False}
    
    @http.route('/scanner/capture', type='http', auth='public', methods=['GET'], csrf=False)
    def scanner_capture_page(self, **kwargs):
        """Background scanner capture page - stays open and auto-verifies"""
        return request.render('autoline_clutch_1.scanner_capture_page', {})
    
    @http.route('/api/scanner/verify', type='http', auth='public', methods=['POST'], csrf=False)
    def api_scanner_verify(self, **kwargs):
        """API endpoint for automatic scanner verification"""
        try:
            import json
            
            # Get JSON data from request body
            try:
                json_data = json.loads(request.httprequest.data.decode('utf-8'))
                scanned_data = json_data.get('qr_code') or json_data.get('data') or json_data.get('scanned_data') or ''
            except (ValueError, AttributeError, UnicodeDecodeError):
                # Try to get from request params if JSON parsing fails
                scanned_data = request.params.get('qr_code') or request.params.get('data') or request.params.get('scanned_data') or ''
            
            if not scanned_data:
                _logger.warning(f"[AUTO SCANNER] No QR code data provided. Request data: {request.httprequest.data}, Params: {request.params}")
                return request.make_response(
                    json.dumps({'success': False, 'error': 'No QR code data provided'}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            
            scanned_data = scanned_data.strip()
            _logger.info(f"[AUTO SCANNER] Scan received: {scanned_data[:32]}...")
            
            # Get LAST cycle record
            last_cycle = request.env['plc.cycle'].search([
                ('qr_code_data', '!=', False)
            ], order='cycle_datetime desc, id desc', limit=1)
            
            if not last_cycle:
                return request.make_response(
                    json.dumps({
                        'success': False,
                        'match_found': False,
                        'message': 'No cycles found in database',
                        'scanned_data': scanned_data
                    }),
                    headers=[('Content-Type', 'application/json')]
                )
            
            match_found = False
            cycle = None
            
            # Verify against last cycle
            if last_cycle.qr_code_data == scanned_data:
                cycle = last_cycle
                match_found = True
                _logger.info(f"[AUTO SCANNER] ✅ MATCH with last cycle: {last_cycle.cycle_number}")
                
                try:
                    # Create scan log entry first
                    scan_log_vals = {
                        'scanned_data': scanned_data,
                        'scanner_id': 'USB_SCANNER',
                        'workstation_id': cycle.workstation_id.id if cycle.workstation_id else None,
                    }
                    _logger.info(f"[AUTO SCANNER] Creating scan log with data: {scan_log_vals}")
                    
                    scan_log = request.env['qr.code.log'].create(scan_log_vals)
                    _logger.info(f"[AUTO SCANNER] ✅ Created scan log record: ID={scan_log.id}, Reference={scan_log.scan_reference}")
                    
                    # Find matching cycle (this will update the scan_log and cycle)
                    scan_log.find_matching_cycle()
                    _logger.info(f"[AUTO SCANNER] Match status: {scan_log.match_status}, Cycle ID: {scan_log.cycle_id.id if scan_log.cycle_id else None}")
                    
                    # Update cycle scan status
                    if scan_log.cycle_id:
                        scan_log.cycle_id.qr_code_scanned = True
                        scan_log.cycle_id.qr_match_status = 'matched'
                        scan_log.cycle_id.scan_datetime = scan_log.scan_datetime
                        scan_log.cycle_id.qr_scan_datetime = scan_log.scan_datetime
                        _logger.info(f"[AUTO SCANNER] Updated cycle {scan_log.cycle_id.cycle_number} scan status")
                    
                    # Commit the transaction
                    request.env.cr.commit()
                    _logger.info(f"[AUTO SCANNER] ✅ Transaction committed - Scan log ID={scan_log.id}, Status={scan_log.match_status}")
                    
                except Exception as e:
                    _logger.error(f"[AUTO SCANNER] ❌ Error creating scan log: {e}", exc_info=True)
                    request.env.cr.rollback()
                    raise
                
                return request.make_response(
                    json.dumps({
                        'success': True,
                        'match_found': True,
                        'message': '✅ QR Code verified successfully!',
                        'cycle_number': cycle.cycle_number,
                        'part_name': cycle.part_name,
                        'cycle_id': cycle.id,
                        'scanned_data': scanned_data,
                        'last_cycle_qr': last_cycle.qr_code_data,
                        'scan_log_id': scan_log.id
                    }),
                    headers=[('Content-Type', 'application/json')]
                )
            else:
                _logger.warning(f"[AUTO SCANNER] ❌ NO MATCH - Scanned: {scanned_data[:32]}, Expected: {last_cycle.qr_code_data[:32]}")
                
                try:
                    # Create scan log entry even for no match
                    scan_log_vals = {
                        'scanned_data': scanned_data,
                        'scanner_id': 'USB_SCANNER',
                        'workstation_id': None,
                    }
                    _logger.info(f"[AUTO SCANNER] Creating scan log (no match) with data: {scan_log_vals}")
                    
                    scan_log = request.env['qr.code.log'].create(scan_log_vals)
                    _logger.info(f"[AUTO SCANNER] ✅ Created scan log record: ID={scan_log.id}, Reference={scan_log.scan_reference}")
                    
                    scan_log.find_matching_cycle()
                    _logger.info(f"[AUTO SCANNER] Match status: {scan_log.match_status}")
                    
                    # Commit the transaction
                    request.env.cr.commit()
                    _logger.info(f"[AUTO SCANNER] ✅ Transaction committed - Scan log ID={scan_log.id}, Status={scan_log.match_status}")
                    
                except Exception as e:
                    _logger.error(f"[AUTO SCANNER] ❌ Error creating scan log (no match): {e}", exc_info=True)
                    request.env.cr.rollback()
                    raise
                
                return request.make_response(
                    json.dumps({
                        'success': True,
                        'match_found': False,
                        'message': '❌ QR Code does not match last printed cycle',
                        'scanned_data': scanned_data,
                        'last_cycle_qr': last_cycle.qr_code_data,
                        'last_cycle_number': last_cycle.cycle_number,
                        'last_part_name': last_cycle.part_name,
                        'scan_log_id': scan_log.id
                    }),
                    headers=[('Content-Type', 'application/json')]
                )
            
        except Exception as e:
            _logger.error(f"Error in auto scanner verification: {e}", exc_info=True)
            return request.make_response(
                json.dumps({
                    'success': False,
                    'error': str(e)
                }),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
    
    @http.route('/api/plc/scan/usb', type='http', auth='public', methods=['POST', 'GET'], csrf=False)
    def process_scan_usb(self, **kwargs):
        """USB scanner input endpoint - matches against LAST record first"""
        try:
            # Get scanned data from request (GET for direct scanner input, POST for form submission)
            scanned_data = request.params.get('data') or request.params.get('qr_code') or request.httprequest.data.decode('utf-8').strip() if request.httprequest.data else ''
            
            if not scanned_data:
                # Return scanner input page if no data
                return request.render('autoline_clutch_1.scanner_input_page', {})
            
            scanned_data = scanned_data.strip()
            
            # Handle request to get last cycle info only
            if request.params.get('get_last_cycle'):
                last_cycle = request.env['plc.cycle'].search([
                    ('qr_code_data', '!=', False)
                ], order='cycle_datetime desc, id desc', limit=1)
                
                last_cycle_info = None
                if last_cycle:
                    last_cycle_info = {
                        'cycle_number': last_cycle.cycle_number,
                        'qr_code_data': last_cycle.qr_code_data,
                        'part_name': last_cycle.part_name,
                    }
                
                return request.make_response(
                    json.dumps({'last_cycle': last_cycle_info}),
                    headers=[('Content-Type', 'application/json')]
                )
            
            if not scanned_data:
                # Return scanner input page if no data
                return request.render('autoline_clutch_1.scanner_input_page', {})
            
            _logger.info(f"[USB SCAN] Received scan: {scanned_data[:50]}...")
            
            # First, try to find the LAST (most recent) cycle record
            last_cycle = request.env['plc.cycle'].search([
                ('qr_code_data', '!=', False)
            ], order='cycle_datetime desc, id desc', limit=1)
            
            match_found = False
            cycle = None
            
            # Check if scanned data matches the last record
            if last_cycle and last_cycle.qr_code_data == scanned_data:
                cycle = last_cycle
                match_found = True
                _logger.info(f"[USB SCAN] ✅ Match found with LAST record: {last_cycle.cycle_number}")
            else:
                # If not last record, search all records
                cycle = request.env['plc.cycle'].search([
                    ('qr_code_data', '=', scanned_data)
                ], limit=1)
                
                if cycle:
                    match_found = True
                    _logger.info(f"[USB SCAN] ✅ Match found (not last record): {cycle.cycle_number}")
            
            if match_found and cycle:
                # Match found - update cycle
                result = cycle.scan_qr_code(scanned_data)
                
                # Create QR log entry
                log_result = request.env['qr.code.log'].process_scan(
                    scanned_data=scanned_data,
                    scanner_id='USB_SCANNER',
                    workstation_id=cycle.workstation_id.id if cycle.workstation_id else None
                )
                
                # Return success response
                response_data = {
                    'success': True,
                    'match_status': 'matched',
                    'cycle_id': cycle.id,
                    'cycle_number': cycle.cycle_number,
                    'part_name': cycle.part_name,
                    'message': _('✅ QR Code matched successfully with cycle %s!') % cycle.cycle_number,
                    'is_last_record': (cycle.id == last_cycle.id) if last_cycle else False,
                }
                
                # If accessed via browser, return HTML page with result
                if request.httprequest.headers.get('Accept', '').find('text/html') >= 0:
                    return request.render('autoline_clutch_1.scanner_result_page', response_data)
                
                # Otherwise return JSON
                return request.make_response(
                    json.dumps(response_data),
                    headers=[('Content-Type', 'application/json')]
                )
            else:
                # No match found
                log_result = request.env['qr.code.log'].process_scan(
                    scanned_data=scanned_data,
                    scanner_id='USB_SCANNER',
                    workstation_id=None
                )
                
                last_cycle_info = None
                if last_cycle:
                    last_cycle_info = {
                        'cycle_number': last_cycle.cycle_number,
                        'qr_code_data': last_cycle.qr_code_data,
                        'part_name': last_cycle.part_name,
                    }
                
                response_data = {
                    'success': False,
                    'match_status': 'not_found',
                    'message': _('❌ QR Code not found in database'),
                    'scanned_data': scanned_data,
                    'last_cycle': last_cycle_info,
                }
                
                # If accessed via browser, return HTML page with result
                if request.httprequest.headers.get('Accept', '').find('text/html') >= 0:
                    return request.render('autoline_clutch_1.scanner_result_page', response_data)
                
                # Otherwise return JSON
                return request.make_response(
                    json.dumps(response_data),
                    headers=[('Content-Type', 'application/json')]
                )
            
        except Exception as e:
            _logger.error(f"Error processing USB scan: {e}", exc_info=True)
            error_response = {
                'error': str(e),
                'success': False,
                'message': _('Error processing scan: %s') % str(e)
            }
            
            if request.httprequest.headers.get('Accept', '').find('text/html') >= 0:
                return request.render('autoline_clutch_1.scanner_result_page', error_response)
            
            return request.make_response(
                json.dumps(error_response),
                headers=[('Content-Type', 'application/json')],
                status=500
            )

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
            
        except UserError:
            # Re-raise UserError (expiry errors) so Odoo can show popup
            raise
        except Exception as e:
            _logger.error(f"Error getting dashboard data via API: {e}")
            return {'error': str(e)}
    
    @http.route('/api/scanner/recent-scans', type='json', auth='user', methods=['GET'])
    def get_recent_scans_api(self, limit=10):
        """Get recent scan verification results for dashboard"""
        try:
            scans = request.env['dashboard.data'].get_recent_scans(limit=limit)
            return {'scans': scans}
        except UserError:
            # Re-raise UserError (expiry errors) so Odoo can show popup
            raise
        except Exception as e:
            _logger.error(f"Error getting recent scans: {e}")
            return {'error': str(e)}
    
    @http.route('/api/scanner/last-cycle', type='json', auth='public', methods=['GET'], csrf=False)
    def get_last_cycle_api(self):
        """Get last cycle info for scanner verification"""
        try:
            last_cycle = request.env['dashboard.data'].get_last_cycle_info()
            return {'last_cycle': last_cycle}
        except UserError:
            # Re-raise UserError (expiry errors) so Odoo can show popup
            raise
        except Exception as e:
            _logger.error(f"Error getting last cycle: {e}")
            return {'error': str(e)}
