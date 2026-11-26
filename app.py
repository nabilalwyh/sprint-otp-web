
"""Membaca file upload pada tahap Extract ETL."""

from io import BytesIO

import pandas as pd


# =========================================================
# 1. DETECT EXCEL FILE FORMAT
# =========================================================
def detect_excel_engine(file):
    """
    Mendeteksi format Excel berdasarkan signature file.

    XLSX menggunakan format ZIP.
    XLS menggunakan format OLE Compound Document.
    """
    file_bytes = file.getvalue()

    if not file_bytes:
        raise ValueError(
            f"File '{file.name}' kosong."
        )

    signature = file_bytes[:8]

    # XLSX signature
    if signature.startswith(b"PK"):
        return "openpyxl", "XLSX"

    # XLS signature
    if signature.startswith(b"\xD0\xCF\x11\xE0"):
        return "xlrd", "XLS"

    raise ValueError(
        f"File '{file.name}' bukan workbook Excel yang valid "
        "atau formatnya tidak dikenali.\n"
        f"Ukuran file: {len(file_bytes):,} bytes.\n"
        f"Signature: {signature.hex(' ')}.\n"
        "Silakan buka file menggunakan Microsoft Excel "
        "dan simpan ulang sebagai Excel Workbook (*.xlsx)."
    )


# =========================================================
# 2. READ GENERAL FILE
# =========================================================
def read_table(file):
    """Membaca file CSV atau Excel menjadi DataFrame."""

    file_name = file.name.lower()
    file.seek(0)

    try:
        # Read CSV
        if file_name.endswith(".csv"):
            try:
                return pd.read_csv(
                    file,
                    dtype=object,
                    sep=None,
                    engine="python",
                )

            except Exception:
                file.seek(0)

                return pd.read_csv(
                    file,
                    dtype=object,
                )

        # Read Excel
        if file_name.endswith((".xlsx", ".xls")):
            engine, detected_format = detect_excel_engine(file)

            file_bytes = file.getvalue()

            return pd.read_excel(
                BytesIO(file_bytes),
                dtype=object,
                engine=engine,
            )

        raise ValueError(
            f"Format file tidak didukung: {file.name}"
        )

    except Exception as error:
        raise ValueError(
            f"Gagal membaca file '{file.name}'.\n"
            f"Detail error: {error}"
        ) from error


# =========================================================
# 3. READ SPRINT REPORT
# =========================================================
def read_sprint_file(file):
    """Membaca laporan Sprint hanya dari kolom A sampai Q."""

    file_name = file.name.lower()

    try:
        file.seek(0)

        # Read CSV: mengambil maksimal 17 kolom pertama.
        if file_name.endswith(".csv"):
            df = read_table(file).iloc[:, :17]

        # Read Excel: mengambil kolom A sampai Q.
        elif file_name.endswith((".xlsx", ".xls")):
            engine, detected_format = detect_excel_engine(file)

            file_bytes = file.getvalue()

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

        # Clean column names.
        df.columns = [
            str(column).strip()
            for column in df.columns
        ]

        return df

    except Exception as error:
        raise ValueError(
            f"Gagal membaca Laporan Sprint '{file.name}'.\n"
            f"Detail error: {error}"
        ) from error


# =========================================================
# 4. READ USER MB WORKBOOK
# =========================================================
def read_user_workbook(file):
    """
    Membaca sheet MDIN, IB, dan MQRIS dari workbook User MB.

    Primary key:
    - MDIN  : PHONE
    - IB    : NO_HP
    - MQRIS : PHONE
    """

    try:
        # Detect actual Excel format.
        engine, detected_format = detect_excel_engine(file)

        file_bytes = file.getvalue()

        # Read workbook sheet names.
        excel_file = pd.ExcelFile(
            BytesIO(file_bytes),
            engine=engine,
        )

    except Exception as error:
        raise ValueError(
            f"Gagal membuka workbook User MB '{file.name}'.\n"
            f"Format terdeteksi: {locals().get('detected_format', 'Tidak diketahui')}.\n"
            f"Ukuran file: {len(file.getvalue()):,} bytes.\n"
            f"Detail error: {error}\n\n"
            "Pastikan file tidak rusak, tidak terenkripsi password, "
            "dan sudah disimpan dalam format Excel yang valid."
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

            # Clean column names.
            df.columns = [
                str(column).strip()
                for column in df.columns
            ]

            result[sheet_name] = df

        except Exception as error:
            raise ValueError(
                f"Gagal membaca sheet '{sheet_name}' "
                f"pada workbook '{file.name}'.\n"
                f"Detail error: {error}"
            ) from error

    return result


# =========================================================
# 5. READ SUPPORTING DATA
# =========================================================
def read_source_file(file):
    """Membaca file data pendukung dan merapikan nama kolom."""

    try:
        df = read_table(file)

        # Clean column names.
        df.columns = [
            str(column).strip()
            for column in df.columns
        ]

        return df

    except Exception as error:
        raise ValueError(
            f"Gagal membaca file data pendukung '{file.name}'.\n"
            f"Detail error: {error}"
        ) from error
