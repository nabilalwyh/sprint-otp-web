"""Membuat file Excel output pada tahap Load ETL."""

from io import BytesIO

import pandas as pd


EXCEL_MAX_DATA_ROWS = 1_048_575   # batas baris Excel dikurangi header
WIDTH_SAMPLE_ROWS = 200           # lebar kolom dihitung dari sampel saja


# 1. FORMAT WORKSHEET
def format_worksheet(worksheet):
    """Mengatur tampilan worksheet Excel."""
    # Membekukan baris header.
    worksheet.freeze_panes = "A2"

    # Mengaktifkan filter pada seluruh area data.
    worksheet.auto_filter.ref = worksheet.dimensions

    # Lebar kolom dihitung dari header + sampel baris awal saja,
    # agar tetap cepat untuk file ratusan ribu baris.
    widths = {}

    for row in worksheet.iter_rows(
        min_row=1,
        max_row=WIDTH_SAMPLE_ROWS,
    ):
        for cell in row:
            length = (
                len(str(cell.value))
                if cell.value is not None
                else 0
            )

            widths[cell.column_letter] = max(
                widths.get(cell.column_letter, 0),
                length,
            )

    for column_letter, max_length in widths.items():
        worksheet.column_dimensions[column_letter].width = min(
            max_length + 2,
            32,
        )


# 2. CREATE EXCEL REPORT
def create_excel_report(report, summary):
    """Membuat file Excel dengan sheet Sheet1 dan SUMMARY."""
    if len(report) > EXCEL_MAX_DATA_ROWS:
        raise ValueError(
            f"Jumlah baris report ({len(report):,}) melebihi batas Excel "
            f"({EXCEL_MAX_DATA_ROWS:,}). Pecah file Sprint menjadi "
            "beberapa bagian."
        )

    buffer = BytesIO()

    with pd.ExcelWriter(
        buffer,
        engine="openpyxl",
    ) as writer:
        report.to_excel(
            writer,
            sheet_name="Sheet1",
            index=False,
        )

        summary.to_excel(
            writer,
            sheet_name="SUMMARY",
            index=False,
        )

        for worksheet in writer.book.worksheets:
            format_worksheet(worksheet)

    return buffer.getvalue()
