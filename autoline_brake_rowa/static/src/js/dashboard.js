/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class PlcDashboard extends Component {
    static template = "autoline_brake_rowa.dashboard_template";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        
        this.state = useState({
            dashboard_data: {},
            workstations: [],
            recent_cycles: [],
            recent_scans: [],
            last_cycle: null,
            loading: true,
            scanner_ready: false,
            scan_result: null,
        });
        
        this.chart = null;
        this.refresh_interval = null;
        this.scan_buffer = '';
        this.scan_timeout = null;

        onMounted(async () => {
            try {
                await this._loadDashboardData();
                await this._renderCharts();
                await this._renderWorkstations();
                await this._renderRecentCycles();
                await this._loadRecentScans();
                await this._loadLastCycle();
                this.state.loading = false;
            } catch (error) {
                console.error('Error in dashboard initialization:', error);
                this.state.loading = false;
            }
            
            // Initialize scanner input
            this._initScanner();
            
            // Auto refresh every 5 seconds for real-time updates
            this.refresh_interval = setInterval(() => {
                this._loadDashboardData();
                this._renderWorkstations();
                this._renderRecentCycles();
                this._loadRecentScans();
                this._loadLastCycle();
            }, 5000);
        });

        onWillUnmount(() => {
            if (this.refresh_interval) {
                clearInterval(this.refresh_interval);
            }
            if (this.scan_timeout) {
                clearTimeout(this.scan_timeout);
            }
            if (this.chart) {
                this.chart.destroy();
            }
        });
    }

    async _loadDashboardData() {
        const now = new Date();
        const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        const date_from = yesterday.toISOString().slice(0, 19).replace('T', ' ');
        const date_to = now.toISOString().slice(0, 19).replace('T', ' ');
        
        try {
            const data = await this.orm.call(
                'dashboard.data',
                'get_dashboard_metrics',
                [date_from, date_to]
            );
            this.state.dashboard_data = data;
            this._updateMetrics();
        } catch (error) {
            console.error('Error loading dashboard data:', error);
        }
    }

    _updateMetrics() {
        // This will be handled by the template with t-esc
        // No need to manually update DOM in OWL
    }

    async _renderCharts() {
        await new Promise(resolve => {
            // Wait for template to render
            setTimeout(() => {
                const chartElement = document.querySelector('#production-chart');
                
                if (!chartElement) {
                    console.warn('Chart canvas not found');
                    resolve();
                    return;
                }
                
                const ctx = chartElement.getContext('2d');
                
                // Load hourly data for chart
                const now = new Date();
                const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
                const date_from = yesterday.toISOString().slice(0, 19).replace('T', ' ');
                const date_to = now.toISOString().slice(0, 19).replace('T', ' ');
                
                this.orm.call(
                    'dashboard.data',
                    'get_hourly_data',
                    [date_from, date_to]
                ).then((hourly_data) => {
                    this._createProductionChart(ctx, hourly_data);
                    resolve();
                }).catch((error) => {
                    console.error('Error loading chart data:', error);
                    resolve();
                });
            }, 100);
        });
    }

    _createProductionChart(ctx, data) {
        const labels = data.map((item) => {
            const date = new Date(item.hour);
            return date.getHours() + ':' + (date.getMinutes() < 10 ? '0' : '') + date.getMinutes();
        });
        const totalData = data.map((item) => item.total);
        const okData = data.map((item) => item.ok);
        const nokData = data.map((item) => item.nok);
        
        // Simple chart implementation without Chart.js dependency
        this._drawSimpleChart(ctx, labels, totalData, okData, nokData);
    }

    _drawSimpleChart(ctx, labels, totalData, okData, nokData) {
        if (!labels || labels.length === 0) {
            return;
        }
        
        const canvas = ctx.canvas;
        const container = canvas.parentElement;
        
        const width = container ? container.clientWidth - 32 : canvas.width || 800;
        const height = canvas.height || 300;
        
        canvas.width = width;
        canvas.height = height;
        
        const padding = 40;
        const chartWidth = width - 2 * padding;
        const chartHeight = height - 2 * padding;
        
        ctx.clearRect(0, 0, width, height);
        
        // Draw axes
        ctx.strokeStyle = '#ccc';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padding, padding);
        ctx.lineTo(padding, height - padding);
        ctx.lineTo(width - padding, height - padding);
        ctx.stroke();
        
        const maxValue = Math.max(
            Math.max.apply(Math, totalData.length > 0 ? totalData : [0]),
            Math.max.apply(Math, okData.length > 0 ? okData : [0]),
            Math.max.apply(Math, nokData.length > 0 ? nokData : [0]),
            1
        );
        const scaleY = chartHeight / maxValue;
        
        // Total line (blue)
        if (totalData.length > 0) {
            ctx.strokeStyle = '#667eea';
            ctx.lineWidth = 2;
            this._drawLine(ctx, labels, totalData, padding, chartHeight, scaleY);
        }
        
        // OK line (green)
        if (okData.length > 0) {
            ctx.strokeStyle = '#4facfe';
            ctx.lineWidth = 2;
            this._drawLine(ctx, labels, okData, padding, chartHeight, scaleY);
        }
        
        // NOK line (red)
        if (nokData.length > 0) {
            ctx.strokeStyle = '#fa709a';
            ctx.lineWidth = 2;
            this._drawLine(ctx, labels, nokData, padding, chartHeight, scaleY);
        }
    }

    _drawLine(ctx, labels, data, padding, chartHeight, scaleY) {
        if (!data || data.length === 0) {
            return;
        }
        
        ctx.beginPath();
        const chartWidth = ctx.canvas.width - 2 * padding;
        const step = data.length > 1 ? chartWidth / (data.length - 1) : 0;
        
        for (let i = 0; i < data.length; i++) {
            const x = padding + (i * step);
            const y = padding + chartHeight - (data[i] * scaleY);
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        }
        ctx.stroke();
    }

    async _renderWorkstations() {
        try {
            const workstations = await this.orm.searchRead(
                'plc.workstation',
                [],
                ['name', 'connection_status', 'last_connection', 'cycle_count']
            );
            // Ensure each workstation has an id for the template key
            this.state.workstations = (workstations || []).map((ws, index) => ({
                ...ws,
                id: ws.id || `ws_${index}`,
            }));
        } catch (error) {
            console.error('Error loading workstation data:', error);
            this.state.workstations = [];
        }
    }

    async _renderRecentCycles() {
        try {
            const cycles = await this.orm.call(
                'dashboard.data',
                'get_recent_cycles',
                [10]
            );
            // Ensure each cycle has an id for the template key
            this.state.recent_cycles = (cycles || []).map((cycle, index) => ({
                ...cycle,
                id: cycle.id || `cycle_${index}`,
            }));
        } catch (error) {
            console.error('Error loading recent cycles:', error);
            this.state.recent_cycles = [];
        }
    }

    async _loadRecentScans() {
        try {
            const result = await this.orm.call(
                'dashboard.data',
                'get_recent_scans',
                [10]
            );
            // Ensure each scan has an id for the template key
            const scans = result || [];
            this.state.recent_scans = scans.map((scan, index) => ({
                ...scan,
                id: scan.id || `scan_${index}`,
            }));
        } catch (error) {
            console.error('Error loading recent scans:', error);
            this.state.recent_scans = [];
        }
    }

    async _loadLastCycle() {
        try {
            const result = await this.orm.call(
                'dashboard.data',
                'get_last_cycle_info',
                []
            );
            this.state.last_cycle = result;
        } catch (error) {
            console.error('Error loading last cycle:', error);
        }
    }

    onRefresh() {
        this._loadDashboardData();
        this._renderWorkstations();
        this._renderRecentCycles();
        this._loadRecentScans();
        this._loadLastCycle();
    }

    onExport() {
        console.log('Export functionality to be implemented');
    }

    onWorkstationClick(workstationId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Workstation Details',
            res_model: 'plc.workstation',
            res_id: parseInt(workstationId),
            views: [[false, 'form']],
            target: 'current',
        });
    }

    _initScanner() {
        // Focus scanner input when dashboard is ready
        setTimeout(() => {
            const scannerInput = this.el?.querySelector('.o_scanner_input');
            if (scannerInput) {
                scannerInput.focus();
                this.state.scanner_ready = true;
            }
        }, 500);
        
        // Re-focus scanner input when clicking anywhere on dashboard
        if (this.el) {
            this.el.addEventListener('click', (e) => {
                // Don't refocus if clicking on buttons or inputs
                if (e.target.tagName === 'BUTTON' || e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                    return;
                }
                const scannerInput = this.el.querySelector('.o_scanner_input');
                if (scannerInput) {
                    scannerInput.focus();
                }
            });
        }
    }

    onScannerKeyDown(ev) {
        // Clear timeout
        if (this.scan_timeout) {
            clearTimeout(this.scan_timeout);
        }
        
        // If Enter key, process the scan
        if (ev.key === 'Enter') {
            ev.preventDefault();
            if (this.scan_buffer.trim()) {
                this._processScan(this.scan_buffer.trim());
                this.scan_buffer = '';
                const scannerInput = this.el?.querySelector('.o_scanner_input');
                if (scannerInput) {
                    scannerInput.value = '';
                }
            }
            return;
        }
        
        // Add character to buffer (only printable characters)
        if (ev.key.length === 1 && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
            this.scan_buffer += ev.key;
        }
        
        // Auto-process after 200ms of no input (scanner sends data quickly)
        this.scan_timeout = setTimeout(() => {
            if (this.scan_buffer.trim().length >= 10) { // Minimum QR code length
                this._processScan(this.scan_buffer.trim());
                this.scan_buffer = '';
                const scannerInput = this.el?.querySelector('.o_scanner_input');
                if (scannerInput) {
                    scannerInput.value = '';
                }
            }
        }, 200);
    }

    async _processScan(qrData) {
        if (!qrData || qrData.length < 10) {
            return;
        }
        
        console.log('[SCANNER] Processing scan:', qrData);
        
        try {
            const response = await fetch('/api/scanner/verify', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ qr_code: qrData })
            });
            
            const result = await response.json();
            
            // Show result
            this.state.scan_result = result;
            
            // Auto-hide result after 3 seconds
            setTimeout(() => {
                this.state.scan_result = null;
            }, 3000);
            
            // Refresh dashboard data to show updated scan status
            await this._loadRecentScans();
            await this._loadLastCycle();
            await this._loadDashboardData();
            
            // Re-focus scanner input
            setTimeout(() => {
                const scannerInput = this.el?.querySelector('.o_scanner_input');
                if (scannerInput) {
                    scannerInput.focus();
                }
            }, 100);
            
        } catch (error) {
            console.error('[SCANNER] Error processing scan:', error);
            this.state.scan_result = {
                success: false,
                match_found: false,
                message: 'Error processing scan: ' + error.message
            };
            setTimeout(() => {
                this.state.scan_result = null;
            }, 3000);
        }
    }
}

registry.category("actions").add("autoline_brake_rowa.dashboard", PlcDashboard);
