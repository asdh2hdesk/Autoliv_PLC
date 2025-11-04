# AutoLiv PLC Module Installation Guide

## Prerequisites

Before installing the module, ensure you have the following Python packages installed:

```bash
pip install pymodbus qrcode Pillow requests
```

## Installation Steps

### 1. Module Installation

1. **Restart Odoo Server**: Stop your Odoo server if it's running
2. **Update Apps List**: 
   - Go to Apps menu in Odoo
   - Click "Update Apps List"
   - Search for "AutoLiv PLC Integration"
3. **Install Module**: Click "Install" on the AutoLiv PLC Integration module

### 2. Initial Configuration

After installation, configure the module:

#### A. Create PLC Workstation
1. Go to **PLC Integration > Configuration > Workstations**
2. Click "Create" to add a new workstation
3. Fill in the details:
   - **Name**: Your workstation name (e.g., "Station 1")
   - **Code**: Unique code (e.g., "ST001")
   - **PLC IP**: IP address of your Mitsubishi PLC
   - **PLC Port**: 502 (default ModbusTCP port)
   - **Unit ID**: 1 (default)
   - **Timeout**: 5 seconds

#### B. Configure Modbus Registers
In the workstation form, set up the register mappings:

**Basic Registers:**
- **Cycle Complete Register**: Register that indicates cycle completion (e.g., 1000)
- **Torque Register**: Register containing torque value (e.g., 1001)
- **Initial Position Register**: Register for initial position (e.g., 1002)
- **Forward Load Register**: Register for forward load (e.g., 1003)
- **Final Position Register**: Register for final position (e.g., 1004)
- **Cycle Time Register**: Register for cycle time (e.g., 1005)
- **Result Register**: Register for OK/NOK result (e.g., 1006)

**Barcode Registers:**
- **Barcode Start Register**: Starting register for barcode data (e.g., 2000)
- **Barcode Length**: Number of characters (e.g., 20)

#### C. Test Connection
1. Click "Test Connection" button
2. Verify the connection status shows "Connected"
3. If connection fails, check:
   - PLC IP address is correct
   - Network connectivity
   - ModbusTCP is enabled on PLC

### 3. Zebra Printer Setup

#### A. Network Configuration
1. Connect your Zebra ZD421 printer to the network
2. Note the printer's IP address
3. Ensure port 9100 is open for communication

#### B. Test Printing
1. Go to **PLC Integration > Cycles**
2. Create a test cycle or use existing data
3. Click "Print QR Code" on any cycle
4. Configure printer settings:
   - **Printer IP**: Your printer's IP address
   - **Printer Port**: 9100
   - **Label Size**: Choose appropriate size
5. Click "Test Connection" to verify printer communication
6. Click "Print" to generate QR code label

### 4. QR Code Scanning

#### A. Scan Process
1. Go to **PLC Integration > QR Code > Scan Logs**
2. Click "Create" to start a new scan
3. Paste scanned QR code data in the "Scanned Data" field
4. Click "Process Scan" to match with database
5. Verify the match status and cycle information

#### B. Integration with Hand Scanner
- Configure your hand scanner to output the scanned data
- Use the API endpoint `/api/plc/scan` for automated scanning
- The system will automatically match scanned data with logged cycles

### 5. Dashboard Access

#### A. Main Dashboard
1. Go to **PLC Integration > Dashboard**
2. View real-time production metrics
3. Monitor workstation status
4. Review quality rates and trends

#### B. Real-time Monitor
1. Go to **PLC Integration > Real-time Monitor**
2. View live workstation connections
3. Monitor recent cycle data
4. Test PLC connections manually

## Troubleshooting

### Common Issues

#### 1. Module Installation Fails
- **Error**: "Module not found"
- **Solution**: Ensure the module is in the correct addons path and restart Odoo

#### 2. PLC Connection Failed
- **Error**: "Unable to connect to PLC"
- **Solutions**:
  - Verify PLC IP address and port
  - Check network connectivity (ping the PLC)
  - Ensure ModbusTCP is enabled on the PLC
  - Check firewall settings

#### 3. QR Code Not Printing
- **Error**: "Failed to send print job"
- **Solutions**:
  - Verify printer IP address and port
  - Check printer network connectivity
  - Ensure printer is online and ready
  - Test with a simple print job first

#### 4. Scan Not Matching
- **Error**: "No matching cycle found"
- **Solutions**:
  - Verify QR code data format (should be JSON)
  - Check if cycle exists in database
  - Ensure barcode is unique
  - Check scan log for detailed error messages

### Debug Mode

Enable debug logging for troubleshooting:

1. **Odoo Log Level**: Set to DEBUG in Odoo configuration
2. **Python Logging**: Add debug statements in model methods
3. **Browser Console**: Check JavaScript console for client-side errors

### Performance Optimization

1. **Database Indexing**: Ensure proper indexes on cycle tables
2. **Data Archiving**: Archive old cycle data periodically
3. **Memory Usage**: Monitor real-time features for memory leaks
4. **Network Latency**: Optimize PLC communication intervals

## Support

For technical support:
- **Email**: support@autoliv.com
- **Documentation**: Check the README.md file
- **Training**: Contact for on-site training sessions

## Next Steps

After successful installation:

1. **Train Users**: Provide training on the new system
2. **Create Workflows**: Establish standard operating procedures
3. **Monitor Performance**: Track system performance and optimize
4. **Expand Usage**: Add more workstations and features as needed

---

**Installation Complete!** Your AutoLiv PLC Integration module is now ready for use.
