# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DashboardData(models.Model):
    _name = 'dashboard.data'
    _description = 'Dashboard Data Model'
    _auto = False

    # This is a virtual model for dashboard data aggregation
    # It doesn't create actual database tables

    def _format_datetime(self, dt, fmt='%Y-%m-%d %H:%M:%S'):
        """Format datetime to user timezone and return formatted string."""
        if not dt:
            return ''
        localized_dt = fields.Datetime.context_timestamp(self, dt)
        if fmt == 'iso':
            return localized_dt.strftime('%Y-%m-%dT%H:%M:%S')
        return localized_dt.strftime(fmt)

    @api.model
    def get_dashboard_metrics(self, date_from=None, date_to=None):
        """Get comprehensive dashboard metrics"""
        # Convert string dates to datetime objects if provided
        if date_from:
            if isinstance(date_from, str):
                # Try parsing common datetime formats
                try:
                    # Try Odoo format: 'YYYY-MM-DD HH:MM:SS'
                    date_from = datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        # Try ISO format: 'YYYY-MM-DDTHH:MM:SS'
                        date_from = datetime.fromisoformat(date_from.replace(' ', 'T'))
                    except ValueError:
                        # Try date only: 'YYYY-MM-DD'
                        date_from = datetime.strptime(date_from, '%Y-%m-%d')
            # Convert datetime to string for Odoo domain (Odoo expects string format)
            if isinstance(date_from, datetime):
                date_from = fields.Datetime.to_string(date_from)
        else:
            date_from = fields.Datetime.to_string(fields.Datetime.now() - timedelta(days=30))
        
        if date_to:
            if isinstance(date_to, str):
                # Try parsing common datetime formats
                try:
                    # Try Odoo format: 'YYYY-MM-DD HH:MM:SS'
                    date_to = datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        # Try ISO format: 'YYYY-MM-DDTHH:MM:SS'
                        date_to = datetime.fromisoformat(date_to.replace(' ', 'T'))
                    except ValueError:
                        # Try date only: 'YYYY-MM-DD' - set to end of day
                        date_to = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
            # Ensure date_to includes the full day (end of day) if it's at midnight
            if isinstance(date_to, datetime):
                if date_to.hour == 0 and date_to.minute == 0 and date_to.second == 0:
                    date_to = date_to + timedelta(days=1) - timedelta(seconds=1)
                date_to = fields.Datetime.to_string(date_to)
        else:
            date_to = fields.Datetime.to_string(fields.Datetime.now())
        
        # Get cycle data - Odoo domain works with string dates in 'YYYY-MM-DD HH:MM:SS' format
        cycle_domain = [
            ('cycle_datetime', '>=', date_from),
            ('cycle_datetime', '<=', date_to)
        ]
        cycles = self.env['plc.cycle'].search(cycle_domain)
        
        # Get scan data
        scan_domain = [
            ('scan_datetime', '>=', date_from),
            ('scan_datetime', '<=', date_to)
        ]
        scans = self.env['qr.code.log'].search(scan_domain)
        
        # Calculate metrics
        total_cycles = len(cycles)
        ok_cycles = len(cycles.filtered(lambda c: c.result == 'ok'))
        nok_cycles = len(cycles.filtered(lambda c: c.result == 'nok'))
        pending_cycles = len(cycles.filtered(lambda c: c.result == 'pending'))
        
        qr_printed = len(cycles.filtered(lambda c: c.qr_code_printed))
        qr_scanned = len(cycles.filtered(lambda c: c.qr_code_scanned))
        
        total_scans = len(scans)
        matched_scans = len(scans.filtered(lambda s: s.match_status == 'matched'))
        
        # Calculate rates
        quality_rate = (ok_cycles / total_cycles * 100) if total_cycles > 0 else 0
        print_rate = (qr_printed / total_cycles * 100) if total_cycles > 0 else 0
        scan_rate = (qr_scanned / total_cycles * 100) if total_cycles > 0 else 0
        match_rate = (matched_scans / total_scans * 100) if total_scans > 0 else 0
        
        # Calculate averages
        avg_cycle_time = sum(cycles.mapped('cycle_time')) / total_cycles if total_cycles > 0 else 0
        avg_torque = sum(cycles.mapped('torque_nm')) / total_cycles if total_cycles > 0 else 0
        
        return {
            'date_from': date_from,
            'date_to': date_to,
            'total_cycles': total_cycles,
            'ok_cycles': ok_cycles,
            'nok_cycles': nok_cycles,
            'pending_cycles': pending_cycles,
            'quality_rate': round(quality_rate, 2),
            'qr_printed': qr_printed,
            'qr_scanned': qr_scanned,
            'print_rate': round(print_rate, 2),
            'scan_rate': round(scan_rate, 2),
            'total_scans': total_scans,
            'matched_scans': matched_scans,
            'match_rate': round(match_rate, 2),
            'avg_cycle_time': round(avg_cycle_time, 2),
            'avg_torque': round(avg_torque, 2),
        }
    
    @api.model
    def get_recent_scans(self, limit=10):
        """Get recent scan verification results for dashboard"""
        scans = self.env['qr.code.log'].search([
            ('scan_datetime', '!=', False)
        ], order='scan_datetime desc', limit=limit)
        
        scan_list = []
        for scan in scans:
            scan_list.append({
                'id': scan.id,
                'scan_reference': scan.scan_reference,
                'scanned_data': scan.scanned_data[:32] if scan.scanned_data else '',
                'scan_datetime': self._format_datetime(scan.scan_datetime),
                'match_status': scan.match_status,
                'cycle_number': scan.cycle_id.cycle_number if scan.cycle_id else '',
                'part_name': scan.cycle_id.part_name if scan.cycle_id else '',
                'match_message': scan.match_message or '',
            })
        
        return scan_list
    
    @api.model
    def get_last_cycle_info(self):
        """Get last printed cycle information for scanner verification"""
        last_cycle = self.env['plc.cycle'].search([
            ('qr_code_data', '!=', False)
        ], order='cycle_datetime desc, id desc', limit=1)
        
        if not last_cycle:
            return None
        
        return {
            'cycle_number': last_cycle.cycle_number,
            'part_name': last_cycle.part_name,
            'qr_code_data': last_cycle.qr_code_data,
            'cycle_datetime': self._format_datetime(last_cycle.cycle_datetime),
            'qr_code_printed': last_cycle.qr_code_printed,
            'qr_code_scanned': last_cycle.qr_code_scanned,
            'qr_match_status': last_cycle.qr_match_status,
        }

    @api.model
    def get_hourly_data(self, date_from=None, date_to=None):
        """Get hourly production data for charts"""
        if not date_from:
            date_from = fields.Datetime.now() - timedelta(days=7)
        if not date_to:
            date_to = fields.Datetime.now()
        
        cycles = self.env['plc.cycle'].search([
            ('cycle_datetime', '>=', date_from),
            ('cycle_datetime', '<=', date_to)
        ])
        
        # Group by hour
        hourly_data = {}
        for cycle in cycles:
            localized_dt = fields.Datetime.context_timestamp(self, cycle.cycle_datetime)
            hour_key = localized_dt.strftime('%Y-%m-%dT%H:00:00')
            if hour_key not in hourly_data:
                hourly_data[hour_key] = {
                    'total': 0,
                    'ok': 0,
                    'nok': 0,
                    'pending': 0
                }
            
            hourly_data[hour_key]['total'] += 1
            hourly_data[hour_key][cycle.result] += 1
        
        # Convert to list for chart
        chart_data = []
        for hour, data in sorted(hourly_data.items()):
            chart_data.append({
                'hour': hour,
                'total': data['total'],
                'ok': data['ok'],
                'nok': data['nok'],
                'pending': data['pending']
            })
        
        return chart_data

    @api.model
    def get_workstation_data(self, date_from=None, date_to=None):
        """Get data by workstation"""
        if not date_from:
            date_from = fields.Datetime.now() - timedelta(days=30)
        if not date_to:
            date_to = fields.Datetime.now()
        
        workstations = self.env['plc.workstation'].search([])
        workstation_data = []
        
        for workstation in workstations:
            cycles = self.env['plc.cycle'].search([
                ('workstation_id', '=', workstation.id),
                ('cycle_datetime', '>=', date_from),
                ('cycle_datetime', '<=', date_to)
            ])
            
            total = len(cycles)
            ok = len(cycles.filtered(lambda c: c.result == 'ok'))
            nok = len(cycles.filtered(lambda c: c.result == 'nok'))
            
            workstation_data.append({
                'workstation': workstation.name,
                'total': total,
                'ok': ok,
                'nok': nok,
                'quality_rate': round((ok / total * 100) if total > 0 else 0, 2)
            })
        
        return workstation_data

    @api.model
    def get_recent_cycles(self, limit=10):
        """Get recent cycles for dashboard"""
        cycles = self.env['plc.cycle'].search([], limit=limit, order='cycle_datetime desc')
        
        recent_data = []
        for cycle in cycles:
            recent_data.append({
                'id': cycle.id,
                'cycle_number': cycle.cycle_number,
                'part_name': cycle.part_name,
                'barcode': cycle.qr_code_data or cycle.barcode or '',
                'qr_code_data': cycle.qr_code_data or cycle.barcode or '',
                'cycle_datetime': self._format_datetime(cycle.cycle_datetime, fmt='iso'),
                'result': cycle.result,
                'torque_nm': cycle.torque_nm,
                'initial_position': cycle.initial_position,
                'final_position': cycle.final_position,
                'load_cell_value': cycle.load_cell_value,
                'cycle_time': cycle.cycle_time,
                'qr_printed': cycle.qr_code_printed,
                'qr_scanned': cycle.qr_code_scanned,
                'qr_match_status': cycle.qr_match_status,
                'operator': cycle.operator_id.name if cycle.operator_id else '',
                'workstation': cycle.workstation_id.name if cycle.workstation_id else '',
            })
        
        return recent_data

    @api.model
    def get_alerts(self):
        """Get system alerts for dashboard"""
        alerts = []
        
        # Check for disconnected workstations
        disconnected_workstations = self.env['plc.workstation'].search([
            ('is_active', '=', True),
            ('connection_status', '!=', 'connected')
        ])
        
        for workstation in disconnected_workstations:
            alerts.append({
                'type': 'warning',
                'title': _('Workstation Disconnected'),
                'message': _('Workstation %s is not connected') % workstation.name,
                'workstation_id': workstation.id
            })
        
        # Check for pending cycles older than 1 hour
        old_pending = self.env['plc.cycle'].search([
            ('result', '=', 'pending'),
            ('cycle_datetime', '<', fields.Datetime.now() - timedelta(hours=1))
        ])
        
        if old_pending:
            alerts.append({
                'type': 'info',
                'title': _('Pending Cycles'),
                'message': _('%d cycles have been pending for more than 1 hour') % len(old_pending),
                'cycle_ids': old_pending.ids
            })
        
        # Check for high NOK rate (more than 10% in last 24 hours)
        recent_cycles = self.env['plc.cycle'].search([
            ('cycle_datetime', '>=', fields.Datetime.now() - timedelta(hours=24))
        ])
        
        if len(recent_cycles) >= 10:  # Only check if we have enough data
            nok_rate = len(recent_cycles.filtered(lambda c: c.result == 'nok')) / len(recent_cycles) * 100
            if nok_rate > 10:
                alerts.append({
                    'type': 'danger',
                    'title': _('High NOK Rate'),
                    'message': _('NOK rate is %.1f%% in the last 24 hours') % nok_rate,
                })
        
        return alerts
    
    @api.model
    def get_plc_online_status(self):
        """Get PLC online status for all workstations"""
        workstations = self.env['plc.workstation'].search([
            ('is_active', '=', True)
        ])
        
        status_data = []
        for workstation in workstations:
            status_data.append({
                'id': workstation.id,
                'name': workstation.name,
                'code': workstation.code,
                'plc_ip': workstation.plc_ip,
                'connection_status': workstation.connection_status,
                'last_connection': self._format_datetime(workstation.last_connection, fmt='iso'),
                'monitoring_active': workstation.monitoring_active,
                'cycle_count': workstation.cycle_count,
            })
        
        return status_data
    
    @api.model
    def get_qr_match_statistics(self, date_from=None, date_to=None):
        """Get QR match statistics"""
        if not date_from:
            date_from = fields.Datetime.now() - timedelta(days=30)
        if not date_to:
            date_to = fields.Datetime.now()
        
        # Get cycles with QR codes
        cycles = self.env['plc.cycle'].search([
            ('cycle_datetime', '>=', date_from),
            ('cycle_datetime', '<=', date_to),
            ('qr_code_data', '!=', False)
        ])
        
        # Get scan logs
        scans = self.env['qr.code.log'].search([
            ('scan_datetime', '>=', date_from),
            ('scan_datetime', '<=', date_to)
        ])
        
        total_cycles_with_qr = len(cycles)
        qr_printed = len(cycles.filtered(lambda c: c.qr_code_printed))
        qr_scanned = len(cycles.filtered(lambda c: c.qr_code_scanned))
        qr_matched = len(cycles.filtered(lambda c: c.qr_match_status == 'matched'))
        qr_not_matched = len(cycles.filtered(lambda c: c.qr_match_status == 'not_matched'))
        
        total_scans = len(scans)
        matched_scans = len(scans.filtered(lambda s: s.match_status == 'matched'))
        
        return {
            'total_cycles_with_qr': total_cycles_with_qr,
            'qr_printed': qr_printed,
            'qr_scanned': qr_scanned,
            'qr_matched': qr_matched,
            'qr_not_matched': qr_not_matched,
            'total_scans': total_scans,
            'matched_scans': matched_scans,
            'match_rate': round((matched_scans / total_scans * 100) if total_scans > 0 else 0, 2),
            'print_rate': round((qr_printed / total_cycles_with_qr * 100) if total_cycles_with_qr > 0 else 0, 2),
            'scan_rate': round((qr_scanned / total_cycles_with_qr * 100) if total_cycles_with_qr > 0 else 0, 2),
        }