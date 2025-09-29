odoo.define('plc_integration.monitoring', function (require) {
    'use strict';

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var framework = require('web.framework');

    var _t = core._t;

    var PlcMonitoringDashboard = AbstractAction.extend({
        template: 'plc_integration.monitoring_dashboard',

        events: {
            'click .start-monitoring': '_onStartMonitoring',
            'click .stop-monitoring': '_onStopMonitoring',
            'click .refresh-data': '_onRefreshData',
        },

        init: function(parent, context) {
            this._super(parent, context);
            this.monitoring_status = false;
            this.recent_records = [];
        },

        willStart: function() {
            var self = this;
            return this._super().then(function() {
                return self._loadData();
            });
        },

        start: function() {
            var self = this;
            return this._super().then(function() {
                self._startPeriodicRefresh();
            });
        },

        _loadData: function() {
            var self = this;
            return rpc.query({
                model: 'plc.data',
                method: 'search_read',
                args: [[], ['part_number', 'barcode', 'state', 'create_date', 'verification_result']],
                kwargs: {
                    limit: 10,
                    order: 'create_date desc'
                }
            }).then(function(records) {
                self.recent_records = records;
                self._updateDashboard();
            });
        },

        _updateDashboard: function() {
            var $dashboard = this.$('.monitoring-dashboard');
            if ($dashboard.length) {
                $dashboard.html(core.qweb.render('plc_integration.dashboard_content', {
                    records: this.recent_records,
                    monitoring_status: this.monitoring_status
                }));
            }
        },

        _onStartMonitoring: function(ev) {
            var self = this;
            ev.preventDefault();

            framework.blockUI();
            rpc.query({
                route: '/plc/start_monitoring',
                params: {}
            }).then(function(result) {
                framework.unblockUI();
                if (result.success) {
                    self.monitoring_status = true;
                    self._updateDashboard();
                    self.displayNotification({
                        type: 'success',
                        title: _t('PLC Monitoring Started'),
                        message: result.message
                    });
                } else {
                    self.displayNotification({
                        type: 'danger',
                        title: _t('Error'),
                        message: result.message
                    });
                }
            }).catch(function(error) {
                framework.unblockUI();
                console.error('Error starting monitoring:', error);
            });
        },

        _onStopMonitoring: function(ev) {
            ev.preventDefault();
            this.monitoring_status = false;
            this._updateDashboard();
        },

        _onRefreshData: function(ev) {
            ev.preventDefault();
            this._loadData();
        },

        _startPeriodicRefresh: function() {
            var self = this;
            setInterval(function() {
                if (self.monitoring_status) {
                    self._loadData();
                }
            }, 5000); // Refresh every 5 seconds
        },
    });

    core.action_registry.add('plc_monitoring_dashboard', PlcMonitoringDashboard);

    return PlcMonitoringDashboard;
});