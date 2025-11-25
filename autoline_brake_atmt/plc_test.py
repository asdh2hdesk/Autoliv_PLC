from pymodbus.client import ModbusTcpClient

def main():
    # PLC IP and Port
    client = ModbusTcpClient("192.168.2.140", port=502)

    try:
        if client.connect():
            print("✅ Connected to Mitsubishi FX5U via Modbus/TCP")

            # --- Read Holding Registers (D0 → D9) ---
            rr = client.read_holding_registers(address=2700, count=10)
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
            coils = client.read_coils(address=8413, count=10)#M0=8192
            if not coils.isError():
                print("M0-M9 values:", coils.bits)
            else:
                print("❌ Read M bits failed:", coils)

            # --- Read Discrete Inputs (X0 → X9) ---
            inputs = client.read_discrete_inputs(address=220, count=10)
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
#
#
# from pymodbus.client import ModbusTcpClient
#
# def main():
#     client = ModbusTcpClient("192.168.2.140", port=502)
#
#     try:
#         if client.connect():
#             print("✅ Connected to Mitsubishi FX5U via Modbus/TCP\n")
#
#             # Test different address calculations for M221
#             test_addresses = [
#                 (221, "Direct (M0=0)"),
#                 (441, "Offset +220 (like your M0-M9 code)"),
#                 (2269, "Standard Mitsubishi (M0=2048)"),
#                 (8413, "Alternative mapping (M0=8192)"),
#                 (221 + 2048, "M0=2048 base"),
#                 (221 + 8192, "M0=8192 base"),
#             ]
#
#             print("Testing different address mappings for M221:\n")
#             for address, description in test_addresses:
#                 try:
#                     result = client.read_coils(address=address, count=1)
#                     if not result.isError():
#                         status = "🟢 ON" if result.bits[0] else "🔴 OFF"
#                         print(f"Address {address:5d} ({description:30s}): {status}")
#                     else:
#                         print(f"Address {address:5d} ({description:30s}): ❌ Error")
#                 except Exception as e:
#                     print(f"Address {address:5d} ({description:30s}): ❌ Exception: {e}")
#
#             # Also try reading a range that includes M221
#             print("\n--- Reading M200-M230 range ---")
#             try:
#                 # Assuming M0 starts at address 2048
#                 result = client.read_coils(address=2048 + 200, count=31)
#                 if not result.isError():
#                     print(f"M221 (index 21) = {result.bits[21]}")
#                     print(f"All bits M200-M230: {result.bits[:31]}")
#             except Exception as e:
#                 print(f"Range read error: {e}")
#
#         else:
#             print("❌ Could not connect to PLC")
#
#     finally:
#         client.close()
#
# if __name__ == "__main__":
#     main()