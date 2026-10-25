
"""Membuat file Excel output pada tahap Load ETL."""

from io import BytesIO

import pandas as pd


# 1. FORMAT WORKSHEET
def format_worksheet(worksheet):
    """Mengatur tampilan worksheet Excel."""
    # Membekukan baris header.
    worksheet.freeze_panes = "A2"

    # Mengaktifkan filter pada seluruh area data.
    worksheet.auto_filter.ref = worksheet.dimensions

    # Menyesuaikan lebar kolom berdasarkan isi.
    for column_cells in worksheet.columns:
        max_length = max(
            (
                len(str(cell.value))
                if cell.value is not None
                else 0
            )
            for cell in column_cells
        )

        column_letter = column_cells[0].column_letter

        worksheet.column_dimensions[column_letter].width = min(
            max_length + 2,
            32,
        )


# 2. CREATE EXCEL REPORT
def create_excel_report(report, summary):
    """Membuat file Excel dengan sheet Sheet1 dan SUMMARY."""
    buffer = BytesIO()

    with pd.ExcelWriter(
        buffer,
        engine="openpyxl",
    ) as writer:
        # Export laporan utama.
        report.to_excel(
            writer,
            sheet_name="Sheet1",
            index=False,
        )

        # Export ringkasan laporan.
        summary.to_excel(
            writer,
            sheet_name="SUMMARY",
            index=False,
        )

        # Format seluruh worksheet.
        for worksheet in writer.book.worksheets:
            format_worksheet(worksheet)

    # Kembalikan file Excel sebagai bytes.
    buffer.seek(0)

    return buffer.getvalue()
