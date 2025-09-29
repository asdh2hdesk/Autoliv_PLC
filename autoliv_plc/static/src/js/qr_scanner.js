odoo.define('plc_integration.qr_scanner', function (require) {
    'use strict';

    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var viewRegistry = require('web.view_registry');
    var rpc = require('web.rpc');
    var core = require('web.core');
    var Dialog = require('web.Dialog');

    var _t = core._t;
    var QWeb = core.qweb;

    var PlcDataFormController = FormController.extend({
        events: _.extend({}, FormController.prototype.events, {
            'click #start_qr_scanner': '_onStartQRScanner',
        }),

        _onStartQRScanner: function(ev) {
            ev.preventDefault();
            this._startQRScanner();
        },

        _startQRScanner: function() {
            var self = this;

            // Check if camera is available
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                this.displayNotification({
                    type: 'warning',
                    title: _t('Camera Not Available'),
                    message: _t('Camera access is required for QR code scanning.')
                });
                return;
            }

            var $scannerDialog = $(QWeb.render('plc_integration.qr_scanner_dialog'));

            var dialog = new Dialog(this, {
                title: _t('QR Code Scanner'),
                $content: $scannerDialog,
                size: 'large',
                buttons: [{
                    text: _t('Close'),
                    classes: 'btn-secondary',
                    close: true,
                }],
            });

            dialog.opened().then(function() {
                self._initializeScanner(dialog.$el.find('#qr_video')[0], dialog);
            });

            dialog.open();
        },

        _initializeScanner: function(videoElement, dialog) {
            var self = this;
            var canvas = document.createElement('canvas');
            var context = canvas.getContext('2d');
            var scanning = true;

            // Get camera stream
            navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'environment', // Use back camera if available
                    width: { ideal: 640 },
                    height: { ideal: 480 }
                }
            }).then(function(stream) {
                videoElement.srcObject = stream;
                videoElement.play();

                // Start scanning loop
                function scanQR() {
                    if (!scanning) return;

                    if (videoElement.readyState === videoElement.HAVE_ENOUGH_DATA) {
                        canvas.height = videoElement.videoHeight;
                        canvas.width = videoElement.videoWidth;

                        context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);

                        var imageData = context.getImageData(0, 0, canvas.width, canvas.height);

                        // Use jsQR library to decode QR code
                        if (window.jsQR) {
                            var code = jsQR(imageData.data, imageData.width, imageData.height);

                            if (code) {
                                scanning = false;
                                stream.getTracks().forEach(track => track.stop());
                                self._processScannedCode(code.data);
                                dialog.close();
                                return;
                            }
                        }
                    }
                    requestAnimationFrame(scanQR);
                }
                scanQR();

            }).catch(function(err) {
                console.error('Error accessing camera:', err);
                self.displayNotification({
                    type: 'danger',
                    title: _t('Camera Error'),
                    message: _t('Could not access camera: ') + err.message
                });
            });

            // Handle dialog close
            dialog.on('closed', function() {
                scanning = false;
                if (videoElement.srcObject) {
                    videoElement.srcObject.getTracks().forEach(track => track.stop());
                }
            });
        },

        _processScannedCode: function(scannedData) {
            var self = this;
            var recordId = this.model.get(this.handle).res_id;

            rpc.query({
                route: '/plc/scan_qr',
                params: {
                    scanned_data: scannedData,
                    record_id: recordId
                }
            }).then(function(result) {
                if (result.success) {
                    self.displayNotification({
                        type: 'success',
                        title: _t('QR Code Verified'),
                        message: result.message
                    });
                    // Reload the form to update the state
                    self.reload();
                } else {
                    self.displayNotification({
                        type: 'danger',
                        title: _t('Verification Failed'),
                        message: result.message
                    });
                }
            }).catch(function(error) {
                console.error('Error processing scanned code:', error);
                self.displayNotification({
                    type: 'danger',
                    title: _t('Error'),
                    message: _t('An error occurred while processing the scanned code.')
                });
            });
        },

        // Add method to handle scan QR button in header
        _onButtonClicked: function(ev) {
            if (ev.data.modifiers.name === 'action_scan_qr') {
                ev.preventDefault();
                ev.stopPropagation();
                this._startQRScanner();
                return;
            }
            return this._super.apply(this, arguments);
        },
    });

    var PlcDataFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: PlcDataFormController,
        }),
    });

    viewRegistry.add('plc_data_form', PlcDataFormView);

    // QR Scanner Dialog Template
    core.qweb.add_template(
        '<div>' +
        '<t t-name="plc_integration.qr_scanner_dialog">' +
            '<div class="qr-scanner-container">' +
                '<div class="text-center mb-3">' +
                    '<p>Position the QR code within the camera view</p>' +
                '</div>' +
                '<div class="video-container text-center">' +
                    '<video id="qr_video" width="640" height="480" autoplay muted playsinline></video>' +
                '</div>' +
                '<div class="scanner-overlay">' +
                    '<div class="scanner-frame"></div>' +
                '</div>' +
            '</div>' +
        '</t>' +
        '</div>'
    );

    return {
        PlcDataFormController: PlcDataFormController,
        PlcDataFormView: PlcDataFormView,
    };
});