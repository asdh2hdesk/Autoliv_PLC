# -*- coding: utf-8 -*-

import threading
import time
import logging
from datetime import datetime as dt, timedelta
from odoo import api, registry, SUPERUSER_ID, fields

_logger = logging.getLogger(__name__)


class PLCMonitorService:
    """
    Continuous PLC Monitoring Service with Threading
    Monitors Mitsubishi PLC continuously for cycle detection and data logging
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(PLCMonitorService, cls).__new__(cls)
                    cls._instance.monitors = {}  # Dictionary of workstation_id -> monitor thread
                    cls._instance.stop_events = {}  # Dictionary of workstation_id -> stop event
                    cls._instance.monitor_locks = {}  # Dictionary of workstation_id -> lock
                    cls._instance.last_states = {}  # Dictionary of workstation_id -> last PLC state
        return cls._instance
    
    def start_monitoring(self, db_name, workstation_id):
        """
        Start continuous monitoring for a workstation
        
        Args:
            db_name: Database name
            workstation_id: ID of the workstation to monitor
        """
        with self._lock:
            # Stop existing monitor if any
            if workstation_id in self.monitors:
                self.stop_monitoring(workstation_id)
            
            # Create stop event
            stop_event = threading.Event()
            self.stop_events[workstation_id] = stop_event
            
            # Create monitor lock
            monitor_lock = threading.Lock()
            self.monitor_locks[workstation_id] = monitor_lock
            
            # Initialize last state (simplified - only track cycle_ok)
            # Start with None to force first read to establish baseline
            self.last_states[workstation_id] = {
                'cycle_ok': None,  # None means not initialized yet
            }
            
            # Create and start monitor thread
            monitor_thread = threading.Thread(
                target=self._monitor_loop,
                args=(db_name, workstation_id, stop_event),
                daemon=True,
                name=f"PLCMonitor-{workstation_id}"
            )
            
            self.monitors[workstation_id] = monitor_thread
            monitor_thread.start()
            
            _logger.info(f"Started PLC monitoring for workstation {workstation_id} in database {db_name}")
            return True
    
    def stop_monitoring(self, workstation_id):
        """Stop monitoring for a workstation"""
        with self._lock:
            if workstation_id in self.stop_events:
                self.stop_events[workstation_id].set()
                
            if workstation_id in self.monitors:
                thread = self.monitors[workstation_id]
                if thread.is_alive():
                    thread.join(timeout=5.0)
                del self.monitors[workstation_id]
            
            if workstation_id in self.stop_events:
                del self.stop_events[workstation_id]
            
            if workstation_id in self.monitor_locks:
                del self.monitor_locks[workstation_id]
            
            if workstation_id in self.last_states:
                del self.last_states[workstation_id]
            
            _logger.info(f"Stopped PLC monitoring for workstation {workstation_id}")
            return True
    
    def stop_all_monitoring(self):
        """Stop all monitoring threads"""
        with self._lock:
            workstation_ids = list(self.monitors.keys())
            for workstation_id in workstation_ids:
                self.stop_monitoring(workstation_id)
    
    def _monitor_loop(self, db_name, workstation_id, stop_event):
        """
        Main monitoring loop for a workstation
        
        Args:
            db_name: Database name
            workstation_id: ID of the workstation
            stop_event: Threading event to signal stop
        """
        _logger.info(f"PLC Monitor loop started for workstation {workstation_id}")
        
        scan_interval = 1.0  # Scan every 1 second (reduced frequency to avoid overwhelming PLC)
        retry_delay = 5.0  # Retry after 5 seconds on error
        consecutive_errors = 0
        max_consecutive_errors = 10
        loop_count = 0
        
        _logger.info(f"[MONITOR LOOP] Starting monitoring loop for workstation {workstation_id}, scan interval: {scan_interval}s")
        
        while not stop_event.is_set():
            loop_count += 1
            # Log every 60 loops (approximately every minute) to confirm loop is running
            if loop_count % 60 == 0:
                _logger.info(f"[MONITOR LOOP] Workstation {workstation_id}: Loop iteration #{loop_count}, still running...")
            try:
                # Get database registry
                registry_instance = registry(db_name)
                if not registry_instance:
                    _logger.error(f"Registry not found for database {db_name}")
                    time.sleep(retry_delay)
                    continue
                
                with registry_instance.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    workstation = env['plc.workstation'].browse(workstation_id)
                    
                    if not workstation.exists():
                        _logger.error(f"[MONITOR LOOP] Workstation {workstation_id} does not exist, stopping monitor")
                        break
                    
                    if not workstation.is_active:
                        _logger.info(f"[MONITOR LOOP] Workstation {workstation_id} is not active, stopping monitor")
                        break
                    
                    # Log workstation status every 30 loops (approximately every 30 seconds)
                    if loop_count % 30 == 0:
                        _logger.info(f"[MONITOR LOOP] Workstation {workstation_id}: is_active={workstation.is_active}, monitoring_active={workstation.monitoring_active}, connection_status={workstation.connection_status}")
                    
                    # Update connection status
                    try:
                        # Test connection
                        _logger.debug(f"[MONITOR LOOP] Testing PLC connection for workstation {workstation_id}...")
                        client = workstation._get_plc_client()
                        if client and client.connect():
                            workstation.connection_status = 'connected'
                            workstation.last_connection = fields.Datetime.now()
                            consecutive_errors = 0
                            client.close()
                            _logger.debug(f"[MONITOR LOOP] Workstation {workstation_id}: Connection successful")
                        else:
                            workstation.connection_status = 'disconnected'
                            consecutive_errors += 1
                            _logger.warning(f"[MONITOR LOOP] Workstation {workstation_id}: Connection failed, status set to 'disconnected'")
                    except Exception as e:
                        _logger.error(f"[MONITOR LOOP] Connection test failed for workstation {workstation_id}: {e}", exc_info=True)
                        workstation.connection_status = 'error'
                        consecutive_errors += 1
                    
                    # If too many errors, wait longer before retry
                    if consecutive_errors >= max_consecutive_errors:
                        _logger.warning(f"Too many consecutive errors for workstation {workstation_id}, waiting {retry_delay * 2}s")
                        time.sleep(retry_delay * 2)
                        consecutive_errors = 0
                        continue
                    
                    # Only monitor if connected
                    if workstation.connection_status == 'connected':
                        _logger.debug(f"[MONITOR] Workstation {workstation_id} is connected, reading cycle status...")
                        # Read cycle status bits
                        cycle_state = workstation._read_cycle_status()
                        _logger.debug(f"[MONITOR] Cycle state read: {cycle_state}")
                        
                        # Log current state periodically (every 30 seconds) to show monitoring is active
                        current_time = int(time.time())
                        if current_time % 30 == 0:
                            bit_summary = []
                            if workstation.part_presence_bit:
                                bit_summary.append(f"M{workstation.part_presence_bit}={cycle_state.get('part_presence', False)}")
                            bit_summary.append(f"M{workstation.cycle_start_bit}={cycle_state.get('cycle_start', False)}")
                            bit_summary.append(f"M{workstation.cycle_complete_bit}={cycle_state.get('cycle_complete', False)}")
                            bit_summary.append(f"M{workstation.cycle_ok_bit}={cycle_state.get('cycle_ok', False)}")
                            bit_summary.append(f"M{workstation.cycle_nok_bit}={cycle_state.get('cycle_nok', False)}")
                            _logger.info(f"[MONITORING ACTIVE] Workstation {workstation_id}: {', '.join(bit_summary)}")
                        
                        # Also log every 5 seconds to show monitoring is working
                        if current_time % 5 == 0:
                            cycle_ok_bit_num = workstation.cycle_ok_bit or 221
                            _logger.info(f"[MONITOR] Workstation {workstation_id}: Monitoring active, M{cycle_ok_bit_num}={cycle_state.get('cycle_ok', False)}")
                        
                        if cycle_state:
                            # Get last state for comparison
                            last_state = self.last_states.get(workstation_id, {})
                            
                            # Monitor cycle_ok_bit (M221 or M2000 - configured in workstation)
                            # When cycle_ok_bit turns ON, read D registers and create cycle
                            current_cycle_ok = cycle_state.get('cycle_ok', False)
                            last_cycle_ok = last_state.get('cycle_ok')
                            
                            # Log cycle_ok status (every read for cycle_ok_bit to catch it quickly)
                            if current_cycle_ok:
                                _logger.info(f"[MONITOR] ⚠️ Workstation {workstation_id}: cycle_ok_bit (M{workstation.cycle_ok_bit}) is ON!")
                            
                            # Log full cycle_state for debugging (less frequently)
                            if int(time.time()) % 30 == 0:
                                _logger.debug(f"[MONITOR] Workstation {workstation_id} - Full cycle_state: {cycle_state}")
                                _logger.debug(f"[MONITOR] Workstation {workstation_id} - cycle_ok from state: {current_cycle_ok}, type: {type(current_cycle_ok)}")
                            
                            # If last_state is None (first read), initialize it and skip cycle creation
                            # This prevents creating a cycle if cycle_ok_bit is already ON when monitoring starts
                            if last_cycle_ok is None:
                                cycle_ok_bit_num = workstation.cycle_ok_bit or 221
                                _logger.info(f"[MONITOR] Initializing monitoring for workstation {workstation_id}: M{cycle_ok_bit_num}={current_cycle_ok}")
                                self.last_states[workstation_id] = {'cycle_ok': current_cycle_ok}
                                # Skip cycle creation on first read
                                cr.commit()
                                time.sleep(scan_interval)
                                continue
                            
                            # Log current state for debugging (every 10 seconds)
                            if int(time.time()) % 10 == 0:
                                cycle_ok_bit_num = workstation.cycle_ok_bit or 221
                                _logger.info(f"[MONITOR] Workstation {workstation_id}: M{cycle_ok_bit_num}={current_cycle_ok}, Last M{cycle_ok_bit_num}={last_cycle_ok}, Type check: current={type(current_cycle_ok)}, last={type(last_cycle_ok)}")
                            
                            # Detect rising edge on cycle_ok_bit (M221 or M2000 - configured in workstation)
                            # M2000 is a 5-second hold bit, so it stays ON longer for reliable detection
                            # Trigger if cycle_ok_bit is ON and was OFF (rising edge)
                            # Use truthy check to handle both True and truthy values
                            rising_edge_detected = False
                            if current_cycle_ok and not last_cycle_ok:
                                rising_edge_detected = True
                                cycle_ok_bit_num = workstation.cycle_ok_bit or 221
                                _logger.info(f"[MONITOR] Rising edge detected: current_cycle_ok={current_cycle_ok} (type: {type(current_cycle_ok)}), last_cycle_ok={last_cycle_ok} (type: {type(last_cycle_ok)})")
                            
                            if rising_edge_detected:
                                cycle_ok_bit_num = workstation.cycle_ok_bit or 221
                                _logger.info(f"[CYCLE EVENT] ⚡ M{cycle_ok_bit_num} (Cycle OK) RISING EDGE detected for workstation {workstation_id}")
                                if cycle_ok_bit_num == 2000:
                                    _logger.info(f"[CYCLE EVENT] M2000 (5-second hold bit) detected - creating cycle record...")
                                _logger.info(f"[CYCLE EVENT] Last state: cycle_ok={last_cycle_ok} (type: {type(last_cycle_ok)}), Current state: cycle_ok={current_cycle_ok} (type: {type(current_cycle_ok)})")
                                _logger.info(f"[CYCLE EVENT] Reading D registers and creating cycle...")
                                
                                # Read all measurement data and create cycle record
                                try:
                                    _logger.info(f"[CYCLE EVENT] Calling _create_cycle_from_plc_data() for workstation {workstation_id}...")
                                    cycle = workstation._create_cycle_from_plc_data()
                                    _logger.info(f"[CYCLE EVENT] _create_cycle_from_plc_data() returned: {cycle}, type: {type(cycle)}")
                                    
                                    if cycle:
                                        _logger.info(f"[CYCLE EVENT] ✅ Cycle record created successfully!")
                                        _logger.info(f"[CYCLE EVENT] Cycle Number: {cycle.cycle_number}")
                                        _logger.info(f"[CYCLE EVENT] Cycle ID: {cycle.id}")
                                        _logger.info(f"[CYCLE EVENT] QR Code: {cycle.qr_code_data[:32] if cycle.qr_code_data else 'None'}")
                                        
                                        # Commit the cycle creation
                                        cr.commit()
                                        _logger.info(f"[CYCLE EVENT] ✅ Cycle record committed to database")
                                        
                                        # Auto-print QR code immediately after cycle creation
                                        try:
                                            _logger.info(f"[CYCLE EVENT] 🖨️ Attempting to auto-print QR code for cycle {cycle.cycle_number}...")
                                            _logger.info(f"[CYCLE EVENT] QR Code Data: {cycle.qr_code_data}")
                                            
                                            # Ensure QR code is generated before printing
                                            if not cycle.qr_code_data:
                                                _logger.warning(f"[CYCLE EVENT] QR code data is empty, generating...")
                                                cycle.generate_qr_code_data()
                                            
                                            # Print QR code
                                            print_result = cycle._auto_print_qr_code()
                                            if print_result:
                                                _logger.info(f"[CYCLE EVENT] ✅ QR code auto-printed successfully for cycle {cycle.cycle_number}")
                                                if workstation.printer_type == 'usb':
                                                    _logger.info(f"[CYCLE EVENT] Printer: USB - {workstation.printer_usb_name or 'Auto-detected'}")
                                                else:
                                                    _logger.info(f"[CYCLE EVENT] Printer: Network - {workstation.printer_ip}:{workstation.printer_port}")
                                            else:
                                                _logger.warning(f"[CYCLE EVENT] ⚠️ QR code auto-print returned False (may have failed silently)")
                                        except Exception as e:
                                            _logger.error(f"[CYCLE EVENT] ❌ Error auto-printing QR code: {e}", exc_info=True)
                                            _logger.error(f"[CYCLE EVENT] Cycle {cycle.cycle_number} was created but QR code printing failed. You can print manually from the cycle record.")
                                    else:
                                        _logger.error(f"[CYCLE EVENT] ❌ Cycle creation returned None (no record created)")
                                        _logger.error(f"[CYCLE EVENT] Check _create_cycle_from_plc_data() method for errors")
                                except Exception as e:
                                    _logger.error(f"[CYCLE EVENT] ❌ Error creating cycle record: {e}", exc_info=True)
                                    _logger.error(f"[CYCLE EVENT] Exception type: {type(e).__name__}, Exception details:", exc_info=True)
                            # Log cycle_ok_bit state change for debugging (before updating state)
                            if current_cycle_ok != last_cycle_ok:
                                cycle_ok_bit_num = workstation.cycle_ok_bit or 221
                                if current_cycle_ok:
                                    _logger.info(f"[BIT CHANGE] ⬆️ Workstation {workstation_id}: Cycle OK (M{cycle_ok_bit_num}) changed: OFF -> ON")
                                    if cycle_ok_bit_num == 2000:
                                        _logger.info(f"[BIT CHANGE] M2000 (5-second hold bit) is now ON - cycle should be detected within 5 seconds")
                                else:
                                    _logger.info(f"[BIT CHANGE] ⬇️ Workstation {workstation_id}: Cycle OK (M{cycle_ok_bit_num}) changed: ON -> OFF")
                            
                            # Update last state AFTER processing (only store cycle_ok for simplicity)
                            # This ensures we capture the state change correctly
                            self.last_states[workstation_id] = {'cycle_ok': bool(current_cycle_ok)}  # Ensure it's a boolean
                            
                            # If cycle_ok_bit is ON but was already ON, log occasionally
                            if current_cycle_ok and last_cycle_ok:
                                if int(time.time()) % 30 == 0:
                                    cycle_ok_bit_num = workstation.cycle_ok_bit or 221
                                    _logger.debug(f"[MONITOR] Workstation {workstation_id}: M{cycle_ok_bit_num} is ON (was already ON)")
                        else:
                            _logger.debug(f"Could not read cycle status for workstation {workstation_id}")
                    else:
                        # Log connection status more frequently so we know monitoring is running
                        if int(time.time()) % 10 == 0:
                            _logger.info(f"[MONITOR] Workstation {workstation_id} connection status: {workstation.connection_status}, skipping cycle check")
                    
                    cr.commit()
                
                # Sleep before next scan
                time.sleep(scan_interval)
                
            except Exception as e:
                _logger.error(f"[MONITOR LOOP] Error in PLC monitor loop for workstation {workstation_id} (loop #{loop_count}): {e}", exc_info=True)
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    _logger.error(f"[MONITOR LOOP] Too many consecutive errors ({consecutive_errors}) for workstation {workstation_id}, waiting {retry_delay * 2}s before retry")
                time.sleep(retry_delay)
        
        _logger.info(f"PLC Monitor loop stopped for workstation {workstation_id}")


# Global function to get the service instance
def get_plc_monitor_service():
    """Get the global PLC monitor service instance"""
    return PLCMonitorService()

