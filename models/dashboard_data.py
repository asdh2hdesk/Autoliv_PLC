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

    @api.model
    def get_dashboard_metrics(self, date_from=None, date_to=None):
        """Get comprehensive dashboard metrics"""
        if not date_from:
            date_from = fields.Datetime.now() - timedelta(days=30)
        if not date_to:
            date_to = fields.Datetime.now()
        
        # Get cycle data
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
            hour_key = cycle.cycle_datetime.strftime('%Y-%m-%d %H:00')
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
                'cycle_number': cycle.cycle_number,
                'part_name': cycle.part_name,
                'barcode': cycle.barcode,
                'cycle_datetime': cycle.cycle_datetime,
                'result': cycle.result,
                'torque_nm': cycle.torque_nm,
                'cycle_time': cycle.cycle_time,
                'qr_printed': cycle.qr_code_printed,
                'qr_scanned': cycle.qr_code_scanned,
                'operator': cycle.operator_id.name,
                'workstation': cycle.workstation_id.name,
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
