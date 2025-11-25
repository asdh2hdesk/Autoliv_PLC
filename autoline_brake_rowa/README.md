# Autoline PLC Integration Module

## Overview

This Odoo 18 module provides comprehensive integration between Odoo and Mitsubishi PLCs via ModbusTCP communication. It enables real-time data logging, QR code generation and printing, scanning functionality, and modern dashboard analytics for manufacturing operations.

## Features

### 🔌 PLC Communication
- **ModbusTCP Client**: Direct communication with Mitsubishi PLCs
- **Real-time Data Reading**: Automatic cycle data retrieval
- **Multiple Workstation Support**: Manage multiple PLC workstations
- **Connection Monitoring**: Real-time connection status tracking

### 📊 Data Management
- **Cycle Logging**: Complete cycle data recording (torque, position, timing, results)
- **Barcode Management**: Unique barcode generation and tracking
- **Quality Control**: OK/NOK result tracking with analytics
- **Operator Tracking**: User assignment and accountability

### 🏷️ QR Code System
- **QR Code Generation**: Automatic QR code creation with cycle data
- **Zebra Printer Integration**: Direct printing to Zebra ZD421 printers
- **Scanning & Matching**: QR code scanning with database matching
- **Print Tracking**: Monitor print and scan status

### 📈 Modern Dashboard
- **Real-time Metrics**: Live production statistics
- **Interactive Charts**: Production trends and analytics
- **Workstation Status**: Live connection and performance monitoring
- **Quality Analytics**: OK/NOK rates and trends
- **Recent Activity**: Live cycle feed

## Installation

### Prerequisites

Install required Python packages:
```bash
pip install pymodbus qrcode Pillow requests
```

### Module Installation

1. Copy the module to your Odoo addons directory
2. Update the addons list in Odoo
3. Install the "Autoline PLC Integration" module
4. Configure workstations and start using

## Configuration

### 1. PLC Workstation Setup

Navigate to **PLC Integration > Configuration > Workstations** and create workstation records:

- **Name**: Workstation identifier
- **Code**: Unique workstation code
- **PLC IP**: IP address of the Mitsubishi PLC
- **PLC Port**: ModbusTCP port (default: 502)
- **Unit ID**: Modbus unit identifier
- **Register Mappings**: Configure Modbus register addresses for:
  - Cycle start/complete triggers
  - Torque, position, and timing data
  - Result status
  - Barcode data

### 2. Zebra Printer Configuration

Configure your Zebra ZD421 printer:
- **IP Address**: Network IP of the printer
- **Port**: Communication port (default: 9100)
- **Label Size**: Configure appropriate label dimensions

### 3. User Permissions

Ensure users have appropriate access rights:
- **PLC Cycle User**: Can view and create cycles
- **PLC Workstation Manager**: Can configure workstations
- **QR Code Log User**: Can process scans

## Usage

### Dashboard

Access the main dashboard at **PLC Integration > Dashboard**:
- View real-time production metrics
- Monitor workstation status
- Track quality rates and trends
- Review recent cycle activity

### Cycle Management

1. **Automatic Data Reading**: PLC data is automatically read when cycles complete
2. **Manual Data Entry**: Create cycles manually if needed
3. **QR Code Generation**: QR codes are automatically generated for each cycle
4. **Printing**: Use the print wizard to print QR code labels

### QR Code Workflow

1. **Cycle Completion**: PLC completes cycle and triggers data read
2. **Data Logging**: Cycle data is stored in Odoo database
3. **QR Code Generation**: QR code is created with cycle information
4. **Label Printing**: Print QR code label using Zebra printer
5. **Scanning**: Scan printed QR code to verify and match data
6. **Verification**: System confirms QR code matches logged data

### Real-time Monitoring

Access **PLC Integration > Real-time Monitor** for:
- Live workstation status
- Real-time cycle data
- Connection testing
- Manual PLC data reading

## API Endpoints

### Cycle Management
- `POST /api/plc/cycle` - Create new cycle
- `GET /api/plc/status/<cycle_id>` - Get cycle status

### QR Code Operations
- `POST /api/plc/scan` - Process QR code scan
- `POST /api/plc/print` - Print QR code

### Dashboard Data
- `GET /api/plc/dashboard` - Get dashboard metrics
- `GET /api/plc/workstations` - Get workstation list

## Data Models

### PLC Cycle (`plc.cycle`)
- Cycle number, part name, barcode
- PLC measurements (torque, positions, timing)
- Quality results (OK/NOK)
- QR code data and status
- Operator and workstation assignment

### PLC Workstation (`plc.workstation`)
- Connection configuration
- Modbus register mappings
- Connection status and monitoring
- Cycle history

### QR Code Log (`qr.code.log`)
- Scan tracking and matching
- Parsed QR code data
- Match status and results
- Scanner and operator information

## Customization

### Adding Custom Fields

Extend the cycle model to include additional PLC data:

```python
class PlcCycle(models.Model):
    _inherit = 'plc.cycle'
    
    custom_field = fields.Float(string='Custom Measurement')
```

### Custom Dashboard Widgets

Create custom dashboard components:

```javascript
odoo.define('your_module.custom_widget', function (require) {
    // Custom widget implementation
});
```

### Printer Integration

Extend printer support for other label printers:

```python
def _send_to_custom_printer(self, zpl_command):
    # Custom printer implementation
    pass
```

## Troubleshooting

### Common Issues

1. **PLC Connection Failed**
   - Verify PLC IP address and port
   - Check network connectivity
   - Ensure ModbusTCP is enabled on PLC

2. **QR Code Not Printing**
   - Verify printer IP and port
   - Check printer network connectivity
   - Validate ZPL command format

3. **Scan Not Matching**
   - Verify QR code data format
   - Check cycle exists in database
   - Ensure barcode uniqueness

### Debug Mode

Enable debug logging:
```python
import logging
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)
```

## Security

### Access Control
- Role-based permissions for different user types
- Secure API endpoints with authentication
- Data encryption for sensitive information

### Network Security
- Secure PLC communication
- Printer network isolation
- API rate limiting

## Performance

### Optimization Tips
- Use database indexing for large datasets
- Implement data archiving for old cycles
- Monitor memory usage for real-time features
- Use connection pooling for PLC communication

### Monitoring
- Track cycle processing times
- Monitor database performance
- Alert on connection failures
- Dashboard performance metrics

## Support

For technical support and customization requests:
- **Email**: support@autoliv.com
- **Documentation**: Internal wiki
- **Training**: Available upon request

## Version History

- **v1.0.0**: Initial release with basic PLC integration
- **v1.1.0**: Added QR code scanning and matching
- **v1.2.0**: Enhanced dashboard with real-time monitoring
- **v1.3.0**: Zebra printer integration and label printing

## License

This module is proprietary software developed for Autoline. All rights reserved.

---

**Autoline PLC Integration Module** - Streamlining manufacturing operations with intelligent PLC integration and modern analytics.
