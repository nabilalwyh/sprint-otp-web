
"""Membaca file upload pada tahap Extract ETL."""

import pandas as pd


# 1. READ GENERAL FILE
def read_table(file):
    """Membaca file CSV atau Excel menjadi DataFrame."""
    file_name = file.name.lower()
    file.seek(0)

    if file_name.endswith(".csv"):
        try:
            return pd.read_csv(
                file,
                dtype=object,
                sep=None,
                engine="python",
            )
        except Exception:
            # Coba kembali menggunakan delimiter default CSV.
            file.seek(0)

            return pd.read_csv(
                file,
                dtype=object,
            )

    if file_name.endswith((".xlsx", ".xls")):
        return pd.read_excel(
            file,
            dtype=object,
        )

    raise ValueError(
        f"Format file tidak didukung: {file.name}"
    )


# 2. READ SPRINT REPORT
def read_sprint_file(file):
    """Membaca laporan Sprint hanya dari kolom A sampai Q."""
    file_name = file.name.lower()

    file.seek(0)

    if file_name.endswith(".csv"):
        df = read_table(file).iloc[:, :17]
    else:
        df = pd.read_excel(
            file,
            usecols="A:Q",
            dtype=object,
        )

    # Rapikan nama kolom.
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    return df


# 3. READ USER MB WORKBOOK
def read_user_workbook(file):
    """
    Membaca sheet MDIN, IB, dan MQRIS dari workbook User MB.

    Primary key:
    - MDIN  : PHONE
    - IB    : NO_HP
    - MQRIS : PHONE
    """
    file.seek(0)

    excel_file = pd.ExcelFile(file)

    # Normalisasi nama sheet untuk pencarian.
    sheet_names = {
        sheet.strip().upper(): sheet
        for sheet in excel_file.sheet_names
    }

    required_sheets = ["MDIN", "IB", "MQRIS"]
    result = {}

    for sheet_name in required_sheets:
        if sheet_name not in sheet_names:
            raise ValueError(
                f"Sheet {sheet_name} tidak ditemukan "
                "di workbook User MB."
            )

        original_sheet_name = sheet_names[sheet_name]

        file.seek(0)

        df = pd.read_excel(
            file,
            sheet_name=original_sheet_name,
            dtype=object,
        )

        # Rapikan nama kolom.
        df.columns = [
            str(column).strip()
            for column in df.columns
        ]

        result[sheet_name] = df

    return result


# 4. READ SUPPORTING DATA
def read_source_file(file):
    """Membaca file data pendukung dan merapikan nama kolom."""
    df = read_table(file)

    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    return df
