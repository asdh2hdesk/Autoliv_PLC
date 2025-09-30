from pymodbus.client import ModbusTcpClient

def main():
    # PLC IP and Port
    client = ModbusTcpClient("192.168.2.140", port=502)

    try:
        if client.connect():
            print("✅ Connected to Mitsubishi FX5U via Modbus/TCP")

            # --- Read Holding Registers (D0 → D9) ---
            rr = client.read_holding_registers(address=0, count=10)
            if not rr.isError():
                print("D0-D9 values:", rr.registers)
            else:
                print("❌ Read D registers failed:", rr)

            # # --- Write value 1234 into D0 ---
            # rq = client.write_register(address=0, value=1234)
            # if not rq.isError():
            #     print("✅ Wrote 1234 into D0")
            # else:
            #     print("❌ Write to D0 failed:", rq)

            # --- Read Coils (M0 → M9) ---
            coils = client.read_coils(address=0, count=10)
            if not coils.isError():
                print("M0-M9 values:", coils.bits)
            else:
                print("❌ Read M bits failed:", coils)

            # --- Read Discrete Inputs (X0 → X9) ---
            inputs = client.read_discrete_inputs(address=0, count=10)
            if not inputs.isError():
                print("X0-X9 values:", inputs.bits)
            else:
                print("❌ Read X inputs failed:", inputs)

        else:
            print("❌ Could not connect to PLC")

    finally:
        client.close()

if __name__ == "__main__":
    main()
