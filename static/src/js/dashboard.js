/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class PlcDashboard extends Component {
    static template = "autoliv_plc.dashboard_template";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        
        this.state = useState({
            dashboard_data: {},
            workstations: [],
            recent_cycles: [],
            loading: true,
        });
        
        this.chart = null;
        this.refresh_interval = null;

        onMounted(async () => {
            try {
                await this._loadDashboardData();
                await this._renderCharts();
                await this._renderWorkstations();
                await this._renderRecentCycles();
                this.state.loading = false;
            } catch (error) {
                console.error('Error in dashboard initialization:', error);
                this.state.loading = false;
            }
            
            // Auto refresh every 30 seconds
            this.refresh_interval = setInterval(() => {
                this._loadDashboardData();
                this._renderWorkstations();
                this._renderRecentCycles();
            }, 30000);
        });

        onWillUnmount(() => {
            if (this.refresh_interval) {
                clearInterval(this.refresh_interval);
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
            this.state.workstations = workstations;
        } catch (error) {
            console.error('Error loading workstation data:', error);
        }
    }

    async _renderRecentCycles() {
        try {
            const cycles = await this.orm.call(
                'dashboard.data',
                'get_recent_cycles',
                [10]
            );
            this.state.recent_cycles = cycles;
        } catch (error) {
            console.error('Error loading recent cycles:', error);
        }
    }

    onRefresh() {
        this._loadDashboardData();
        this._renderWorkstations();
        this._renderRecentCycles();
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
}

registry.category("actions").add("autoliv_plc.dashboard", PlcDashboard);
