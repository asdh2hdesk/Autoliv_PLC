/* Autoline PLC Real-time Monitor JavaScript */

import { AbstractAction } from "@web/legacy/js/core/abstract_action";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

export class PlcMonitor extends AbstractAction {
        constructor() {
            super();
            this.template = 'autoline_clutch_1.monitor_template';
            this.events = {
                'click .btn-read-plc': '_onReadPlc',
                'click .btn-test-connection': '_onTestConnection',
                'click .workstation-item': '_onWorkstationClick',
            };
        }

        init() {
            super.init(...arguments);
            this.workstations = [];
            this.live_cycles = [];
            this.monitor_interval = null;
        }

        async willStart() {
            return super.willStart(...arguments);
        }

        async start() {
            await super.start(...arguments);
            this._loadWorkstations();
            this._startLiveMonitoring();
            return this._render();
        }

        async _render() {
            await super._render(...arguments);
            this._renderWorkstations();
            this._renderLiveCycles();
        }

        async _loadWorkstations() {
            try {
                const workstations = await rpc.query({
                    model: 'plc.workstation',
                    method: 'search_read',
                    args: [[], ['name', 'plc_ip', 'connection_status', 'last_connection', 'cycle_count']],
                });
                this.workstations = workstations;
                this._renderWorkstations();
            } catch (error) {
                console.error('Error loading workstations:', error);
            }
        }

        _renderWorkstations() {
            const container = this.el.querySelector('#workstation-monitor');
            container.innerHTML = '';
            
            this.workstations.forEach(workstation => {
                const statusClass = workstation.connection_status;
                const statusText = workstation.connection_status.charAt(0).toUpperCase() + 
                                workstation.connection_status.slice(1);
                const lastConnection = workstation.last_connection ? 
                    new Date(workstation.last_connection).toLocaleDateString() + ' ' + new Date(workstation.last_connection).toLocaleTimeString() : 'Never';
                
                const html = `
                    <div class="workstation-item" data-workstation-id="${workstation.id}">
                        <div class="workstation-card">
                            <div class="workstation-header">
                                <h5>${workstation.name}</h5>
                                <span class="status-badge ${statusClass}">${statusText}</span>
                            </div>
                            <div class="workstation-details">
                                <p><strong>IP:</strong> ${workstation.plc_ip}</p>
                                <p><strong>Last Connection:</strong> ${lastConnection}</p>
                                <p><strong>Total Cycles:</strong> ${workstation.cycle_count}</p>
                            </div>
                            <div class="workstation-actions">
                                <button class="btn btn-sm btn-primary btn-read-plc" data-workstation-id="${workstation.id}">
                                    Read PLC Data
                                </button>
                                <button class="btn btn-sm btn-info btn-test-connection" data-workstation-id="${workstation.id}">
                                    Test Connection
                                </button>
                            </div>
                        </div>
                    </div>
                `;
                container.insertAdjacentHTML('beforeend', html);
            });
        }

        _renderLiveCycles() {
            const container = this.el.querySelector('#live-cycles');
            container.innerHTML = '';
            
            if (this.live_cycles.length === 0) {
                container.innerHTML = '<p class="text-muted text-center">No live cycle data available</p>';
                return;
            }
            
            let table = `
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Workstation</th>
                            <th>Part</th>
                            <th>Barcode</th>
                            <th>Torque</th>
                            <th>Result</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            this.live_cycles.forEach(cycle => {
                const resultClass = cycle.result === 'ok' ? 'badge-ok' : 
                                 cycle.result === 'nok' ? 'badge-nok' : 'badge-pending';
                
                let qrStatus = '';
                if (cycle.qr_printed && cycle.qr_scanned) {
                    qrStatus = '<span class="qr-status printed">✓ Printed</span> <span class="qr-status scanned">✓ Scanned</span>';
                } else if (cycle.qr_printed) {
                    qrStatus = '<span class="qr-status printed">✓ Printed</span>';
                } else {
                    qrStatus = '<span class="text-muted">Not printed</span>';
                }
                
                table += `
                    <tr class="fade-in">
                        <td>${new Date(cycle.cycle_datetime).toLocaleTimeString()}</td>
                        <td>${cycle.workstation || 'Unknown'}</td>
                        <td>${cycle.part_name}</td>
                        <td>${cycle.barcode}</td>
                        <td>${cycle.torque_nm} Nm</td>
                        <td><span class="badge-custom ${resultClass}">${cycle.result.toUpperCase()}</span></td>
                        <td>${qrStatus}</td>
                    </tr>
                `;
            });
            
            table += '</tbody></table>';
            container.innerHTML = table;
        }

        _startLiveMonitoring() {
            this.monitor_interval = setInterval(() => {
                this._loadWorkstations();
                this._loadRecentCycles();
            }, 5000); // Update every 5 seconds
        }

        async _loadRecentCycles() {
            try {
                const cycles = await rpc.query({
                    model: 'plc.cycle',
                    method: 'search_read',
                    args: [[], ['cycle_number', 'part_name', 'barcode', 'cycle_datetime', 'torque_nm', 'result', 'qr_code_printed', 'qr_code_scanned', 'workstation_id'], 0, 20],
                    kwargs: {
                        order: 'cycle_datetime desc'
                    }
                });
                
                // Add workstation names to cycles
                cycles.forEach(cycle => {
                    const workstation = this.workstations.find(w => w.id === cycle.workstation_id[0]);
                    cycle.workstation = workstation ? workstation.name : 'Unknown';
                });
                
                this.live_cycles = cycles;
                this._renderLiveCycles();
            } catch (error) {
                console.error('Error loading recent cycles:', error);
            }
        }

        async _onReadPlc(event) {
            event.preventDefault();
            const workstationId = event.currentTarget.dataset.workstationId;
            
            // Show loading state
            event.currentTarget.disabled = true;
            event.currentTarget.innerHTML = '<span class="loading-spinner"></span> Reading...';
            
            try {
                const result = await rpc.query({
                    model: 'plc.workstation',
                    method: 'action_read_plc_data',
                    args: [workstationId],
                });
                
                if (result.success) {
                    this._showNotification('Success', 'PLC data read successfully!', 'success');
                    this._loadRecentCycles();
                } else {
                    this._showNotification('Error', result.message || 'Failed to read PLC data', 'danger');
                }
            } catch (error) {
                console.error('Error reading PLC data:', error);
                this._showNotification('Error', 'Failed to read PLC data: ' + error.message, 'danger');
            } finally {
                event.currentTarget.disabled = false;
                event.currentTarget.innerHTML = 'Read PLC Data';
            }
        }

        async _onTestConnection(event) {
            event.preventDefault();
            const workstationId = event.currentTarget.dataset.workstationId;
            
            // Show loading state
            event.currentTarget.disabled = true;
            event.currentTarget.innerHTML = '<span class="loading-spinner"></span> Testing...';
            
            try {
                const result = await rpc.query({
                    model: 'plc.workstation',
                    method: 'test_connection',
                    args: [workstationId],
                });
                
                if (result.success) {
                    this._showNotification('Success', 'Connection test successful!', 'success');
                } else {
                    this._showNotification('Error', result.message || 'Connection test failed', 'danger');
                }
            } catch (error) {
                console.error('Error testing connection:', error);
                this._showNotification('Error', 'Connection test failed: ' + error.message, 'danger');
            } finally {
                event.currentTarget.disabled = false;
                event.currentTarget.innerHTML = 'Test Connection';
            }
        }

        _onWorkstationClick(event) {
            event.preventDefault();
            const workstationId = event.currentTarget.dataset.workstationId;
            // Navigate to workstation details
            this.do_action({
                type: 'ir.actions.act_window',
                name: 'Workstation Details',
                res_model: 'plc.workstation',
                res_id: workstationId,
                view_mode: 'form',
                target: 'current',
            });
        }

        _showNotification(title, message, type) {
            this.do_notify(title, message, type);
        }

        destroy() {
            if (this.monitor_interval) {
                clearInterval(this.monitor_interval);
            }
            super.destroy(...arguments);
        }
    }

    registry.category("actions").add("autoline_clutch_1.monitor", PlcMonitor);

    export default PlcMonitor;
