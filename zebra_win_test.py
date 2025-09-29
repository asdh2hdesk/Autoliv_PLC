import win32print

def send_zpl_to_printer(printer_name: str, zpl: str):
    hPrinter = win32print.OpenPrinter(printer_name)
    hJob = win32print.StartDocPrinter(hPrinter, 1, ("Zebra Label", None, "RAW"))
    win32print.StartPagePrinter(hPrinter)

    # Send ZPL data
    win32print.WritePrinter(hPrinter, zpl.encode("utf-8"))

    win32print.EndPagePrinter(hPrinter)
    win32print.EndDocPrinter(hPrinter)
    win32print.ClosePrinter(hPrinter)
    print("✅ ZPL sent to", printer_name)


if __name__ == "__main__":
    # 👇 Make sure this matches exactly your installed printer name
    PRINTER_NAME = "ZDesigner ZD421-300dpi ZPL"

    # ZPL: QR code + label text
    zpl = """
        ^XA
        ^FO50,50
        ^BQN,2,6
        ^FDLA,00547629200112^FS

        ^FO200,50^A0N,30,30^FD00547629200112^FS
        ^FO200,90^A0N,30,30^FD0H^FS
        ^FO200,130^A0N,30,30^FDA68767^FS
        ^FO200,170^A0N,30,30^FD0725^FS
        ^FO200,210^A0N,30,30^FD000050^FS

        ^FO50,300^A0N,28,28^FDAUTOLINE INDUST LTD^FS
        ^FO50,340^A0N,28,28^FDBREAK PEDAL ASSY, COLLAPSIBLE MT^FS
        ^XZ
        """

    send_zpl_to_printer(PRINTER_NAME, zpl)
