# Cycle Creation Debugging Guide

## Issue: M221 is visible but cycle record is not created

## Changes Made

1. **Improved Monitoring Service Logging**
   - Added detailed logging when M221 turns ON
   - Added logging every 10 seconds to show current state
   - Added initialization check to prevent false triggers

2. **Fixed Last State Initialization**
   - Changed from `False` to `None` on startup
   - Prevents creating cycle if M221 is already ON when monitoring starts
   - Waits for M221 to go OFF first, then detects next ON

3. **Enhanced Error Logging**
   - All cycle creation errors are now logged with full stack traces
   - Shows cycle number, ID, and QR code when created successfully

## How to Debug

### Step 1: Check if Monitoring is Active

1. Go to **PLC Workstation** form
2. Check **"Monitoring Active"** field - should be **✅ Yes**
3. If not, click **"Start Continuous Monitoring"** button

### Step 2: Check Odoo Logs

Look for these log messages:

#### When Monitoring Starts:
```
[MONITOR] Initializing monitoring for workstation X: M221=False/True
```

#### Every 10 seconds (shows current state):
```
[MONITOR] Workstation X: M221=True, Last M221=False
```

#### When M221 Turns ON:
```
[BIT CHANGE] ⬆️ Workstation X: Cycle OK (M221) changed: OFF -> ON
[CYCLE EVENT] ⚡ M221 (Cycle OK) RISING EDGE detected for workstation X
[CYCLE EVENT] Reading D registers and creating cycle...
```

#### If Cycle Created Successfully:
```
[CYCLE EVENT] ✅ Cycle record created successfully!
[CYCLE EVENT] Cycle Number: XXX
[CYCLE EVENT] Cycle ID: XXX
[CYCLE EVENT] QR Code: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

#### If Error Occurs:
```
[CYCLE EVENT] ❌ Error creating cycle record: [error message]
```

### Step 3: Manual Test

1. **Force M221 ON** in PLC program
2. Click **"Read PLC Data"** button in workstation form
3. This should create a cycle immediately (if M221 is ON)
4. Check if cycle is created in **PLC Cycles** menu

### Step 4: Check Common Issues

#### Issue 1: Monitoring Not Running
**Symptoms:** No log messages about monitoring
**Solution:** 
- Click "Start Continuous Monitoring" button
- Check "Monitoring Active" field is True
- Restart Odoo if needed

#### Issue 2: M221 Already ON When Monitoring Starts
**Symptoms:** M221 is ON but no cycle created
**Solution:**
- This is expected behavior - system waits for M221 to go OFF first
- Turn M221 OFF in PLC, then turn it ON again
- Or restart monitoring when M221 is OFF

#### Issue 3: Cycle Creation Error
**Symptoms:** Log shows "Error creating cycle record"
**Solution:**
- Check full error message in logs
- Verify D register addresses (D2704, D2706, D2708) are correct
- Test connection with "Test Connection" button

#### Issue 4: No Rising Edge Detected
**Symptoms:** M221 is ON but no "[CYCLE EVENT]" log
**Solution:**
- Check if M221 was already ON when monitoring started
- Turn M221 OFF, wait 2 seconds, then turn it ON again
- Check logs for "[BIT CHANGE]" messages

## Testing Procedure

1. **Start Monitoring:**
   - Open workstation form
   - Click "Start Continuous Monitoring"
   - Verify "Monitoring Active" = Yes

2. **Test Cycle Detection:**
   - Ensure M221 is OFF in PLC
   - Turn M221 ON in PLC
   - Watch Odoo logs for "[CYCLE EVENT]" message
   - Check PLC Cycles menu for new record

3. **Verify Cycle Data:**
   - Open created cycle record
   - Check S1_FOR, S2_FOR, final_position values
   - Verify QR code is generated

## Expected Log Flow

```
[MONITOR] Initializing monitoring for workstation 1: M221=False
[MONITOR] Workstation 1: M221=False, Last M221=False
[MONITOR] Workstation 1: M221=False, Last M221=False
[BIT CHANGE] ⬆️ Workstation 1: Cycle OK (M221) changed: OFF -> ON
[CYCLE EVENT] ⚡ M221 (Cycle OK) RISING EDGE detected for workstation 1
[CYCLE EVENT] Reading D registers and creating cycle...
[CYCLE EVENT] ✅ Cycle record created successfully!
[CYCLE EVENT] Cycle Number: CYCLE-001
[CYCLE EVENT] Cycle ID: 123
[CYCLE EVENT] QR Code: ABC123DEF456GHI789JKL012MNO345PQ
[CYCLE EVENT] ✅ QR code auto-printed for cycle CYCLE-001
```

## Next Steps

1. **Check Odoo logs** for the messages above
2. **Share log output** if cycle is not created
3. **Test manually** using "Read PLC Data" button
4. **Verify monitoring is active** before testing


