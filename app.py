
"""Membaca file upload pada tahap Extract ETL."""

from io import BytesIO
import zipfile

import pandas as pd


# =========================================================
# 1. GET FILE CONTENT
# =========================================================
def get_file_bytes(file):
    """Mengambil isi file upload dalam bentuk bytes."""
    file.seek(0)
    file_bytes = file.getvalue()

    if not file_bytes:
        raise ValueError(
            f"File '{file.name}' kosong."
        )

    return file_bytes


# =========================================================
# 2. DETECT EXCEL FILE FORMAT
# =========================================================
def detect_excel_engine(file):
    """
    Mendeteksi format Excel berdasarkan struktur file.

    XLSX menggunakan struktur ZIP.
    XLS menggunakan OLE Compound Document.
    """
    file_bytes = get_file_bytes(file)

    # Check XLSX format.
    try:
        with BytesIO(file_bytes) as buffer:
            if zipfile.is_zipfile(buffer):
                return "openpyxl", "XLSX"
    except Exception:
        pass

    # Check XLS format.
    signature = file_bytes[:8]

    if signature.startswith(b"\xD0\xCF\x11\xE0"):
        return "xlrd", "XLS"

    raise ValueError(
        f"Format internal file '{file.name}' tidak dikenali.\n"
        f"Ukuran file: {len(file_bytes):,} bytes.\n"
        f"Signature: {signature.hex(' ')}.\n"
        "Pastikan file merupakan workbook Excel yang valid "
        "dan tidak rusak."
    )


# =========================================================
# 3. READ GENERAL FILE
# =========================================================
def read_table(file):
    """Membaca file CSV atau Excel menjadi DataFrame."""

    file_name = file.name.lower()
    file_bytes = get_file_bytes(file)

    try:
        # -------------------------------------------------
        # Read CSV
        # -------------------------------------------------
        if file_name.endswith(".csv"):
            try:
                df = pd.read_csv(
                    BytesIO(file_bytes),
                    dtype=object,
                    sep=None,
                    engine="python",
                )

            except Exception:
                # Fallback menggunakan delimiter default.
                df = pd.read_csv(
                    BytesIO(file_bytes),
                    dtype=object,
                )

            return df

        # -------------------------------------------------
        # Read Excel
        # -------------------------------------------------
        if file_name.endswith((".xlsx", ".xls")):
            engine, detected_format = detect_excel_engine(file)

            df = pd.read_excel(
                BytesIO(file_bytes),
                dtype=object,
                engine=engine,
            )

            return df

        raise ValueError(
            f"Format file tidak didukung: {file.name}"
        )

    except Exception as error:
        raise ValueError(
            f"Gagal membaca file '{file.name}'.\n"
            f"Detail error: {error}"
        ) from error


# =========================================================
# 4. CLEAN COLUMN NAMES
# =========================================================
def clean_column_names(df):
    """Membersihkan spasi pada nama kolom DataFrame."""
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    return df


# =========================================================
# 5. READ SPRINT REPORT
# =========================================================
def read_sprint_file(file):
    """Membaca laporan Sprint hanya dari kolom A sampai Q."""

    file_name = file.name.lower()
    file_bytes = get_file_bytes(file)

    try:
        # -------------------------------------------------
        # Read CSV: first 17 columns
        # -------------------------------------------------
        if file_name.endswith(".csv"):
            df = read_table(file)

            df = df.iloc[:, :17]

        # -------------------------------------------------
        # Read Excel: columns A-Q
        # -------------------------------------------------
        elif file_name.endswith((".xlsx", ".xls")):
            engine, detected_format = detect_excel_engine(file)

            df = pd.read_excel(
                BytesIO(file_bytes),
                usecols="A:Q",
                dtype=object,
                engine=engine,
            )

        else:
            raise ValueError(
                f"Format file tidak didukung: {file.name}"
            )

        return clean_column_names(df)

    except Exception as error:
        raise ValueError(
            f"Gagal membaca Laporan Sprint '{file.name}'.\n"
            f"Detail error: {error}"
        ) from error


# =========================================================
# 6. READ USER MB WORKBOOK
# =========================================================
def read_user_workbook(file):
    """
    Membaca sheet MDIN, IB, dan MQRIS dari workbook User MB.

    Primary key:
    - MDIN  : PHONE
    - IB    : NO_HP
    - MQRIS : PHONE
    """

    file_bytes = get_file_bytes(file)

    # -----------------------------------------------------
    # Detect workbook format
    # -----------------------------------------------------
    try:
        engine, detected_format = detect_excel_engine(file)

    except Exception as error:
        raise ValueError(
            f"Gagal mendeteksi format workbook User MB "
            f"'{file.name}'.\n"
            f"Detail: {error}"
        ) from error

    # -----------------------------------------------------
    # Open workbook
    # -----------------------------------------------------
    try:
        excel_file = pd.ExcelFile(
            BytesIO(file_bytes),
            engine=engine,
        )

    except Exception as error:
        raise ValueError(
            f"Gagal membuka workbook User MB '{file.name}'.\n"
            f"Format terdeteksi: {detected_format}.\n"
            f"Ukuran file: {len(file_bytes):,} bytes.\n"
            f"Detail error: {error}\n\n"
            "Kemungkinan penyebab:\n"
            "- File Excel rusak atau tidak lengkap.\n"
            "- File dilindungi password/enkripsi.\n"
            "- Format internal file tidak sesuai."
        ) from error

    # -----------------------------------------------------
    # Normalize sheet names
    # -----------------------------------------------------
    sheet_names = {
        sheet.strip().upper(): sheet
        for sheet in excel_file.sheet_names
    }

    required_sheets = [
        "MDIN",
        "IB",
        "MQRIS",
    ]

    result = {}

    # -----------------------------------------------------
    # Read required sheets
    # -----------------------------------------------------
    for sheet_name in required_sheets:

        if sheet_name not in sheet_names:
            raise ValueError(
                f"Sheet '{sheet_name}' tidak ditemukan "
                f"di workbook '{file.name}'.\n"
                f"Sheet tersedia: "
                f"{', '.join(excel_file.sheet_names)}"
            )

        original_sheet_name = sheet_names[sheet_name]

        try:
            df = pd.read_excel(
                BytesIO(file_bytes),
                sheet_name=original_sheet_name,
                dtype=object,
                engine=engine,
            )

            result[sheet_name] = clean_column_names(df)

        except Exception as error:
            raise ValueError(
                f"Gagal membaca sheet '{sheet_name}' "
                f"pada workbook '{file.name}'.\n"
                f"Detail error: {error}"
            ) from error

    return result


# =========================================================
# 7. READ SUPPORTING DATA
# =========================================================
def read_source_file(file):
    """Membaca file data pendukung dan merapikan nama kolom."""

    try:
        df = read_table(file)

        return clean_column_names(df)

    except Exception as error:
        raise ValueError(
            f"Gagal membaca file data pendukung "
            f"'{file.name}'.\n"
            f"Detail error: {error}"
        ) from error
