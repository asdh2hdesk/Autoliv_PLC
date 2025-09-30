# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api
import win32print

_logger = logging.getLogger(__name__)


class PartLabel(models.Model):
    _name = "autoline.part"
    _description = "Autoline Part Master"
    _rec_name = "part_no"

    part_no = fields.Char("Part No")
    revision = fields.Char("Revision Level")
    vendor_code = fields.Char("Vendor Code")
    mfg_date = fields.Char("Mfg Date")
    serial_no = fields.Char("Serial No")
    part_desc = fields.Char("Part Description")
    company_name = fields.Char("Company", default="AUTOLINE INDUST LTD")

    def _generate_qr_data(self):
        """ Merge fields into QR code string """
        return f"{self.part_no}{self.revision}{self.vendor_code}{self.mfg_date}{self.serial_no}"

    def send_zpl_to_printer(self, printer_name: str, zpl: str):
        hPrinter = win32print.OpenPrinter(printer_name)
        hJob = win32print.StartDocPrinter(hPrinter, 1, ("Zebra Label", None, "RAW"))
        win32print.StartPagePrinter(hPrinter)
        win32print.WritePrinter(hPrinter, zpl.encode("utf-8"))
        win32print.EndPagePrinter(hPrinter)
        win32print.EndDocPrinter(hPrinter)
        win32print.ClosePrinter(hPrinter)
        _logger.info("✅ ZPL sent to %s", printer_name)

    # @api.multi
    def action_print_labels(self):
        """Triggered from tree view header button"""
        printer_name = "ZDesigner ZD421-300dpi ZPL"  # 👈 adjust to your installed printer name

        for rec in self:
            qr_code = f"{rec.part_no}{rec.revision}{rec.vendor_code}{rec.mfg_date}{rec.serial_no}"

            # Build ZPL
            zpl = f"""
                ^XA
                ^PW591
                ^LL300     # increase LL to fit new positions
                ~SD15
                
                ^FO50,60
                ^BQN,2,5
                ^FDLA,{qr_code}^FS
                
                ^FO220,35^A0N,32,32^FD{rec.part_no}^FS
                ^FO220,68^A0N,32,32^FD{rec.revision}^FS
                ^FO220,101^A0N,32,32^FD{rec.vendor_code}^FS
                ^FO220,134^A0N,32,32^FD{rec.mfg_date}^FS
                ^FO220,167^A0N,32,32^FD{rec.serial_no}^FS
                
                ^FO0,210
                ^FB591,1,0,C,0
                ^A0N,32,32
                ^FD{rec.part_desc or ''}^FS
                
                ^FO0,250
                ^FB591,1,0,C,0
                ^A0N,32,32
                ^FD AUTOLINE INDUST LTD ^FS
                ^XZ

               """

            # Send to Zebra printer
            self.send_zpl_to_printer(printer_name, zpl)

        return True
