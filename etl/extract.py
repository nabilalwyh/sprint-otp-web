"""Membaca file upload pada tahap Extract ETL."""

import io
import zipfile

import pandas as pd


ZIP_MAGIC = b"PK\x03\x04"            # .xlsx
OLE_MAGIC = b"\xd0\xcf\x11\xe0"      # .xls lama


# 1. HELPER: BACA ISI FILE
def _read_bytes(file):
    """Mengambil seluruh isi file upload sebagai bytes."""
    if hasattr(file, "getvalue"):
        return file.getvalue()

    file.seek(0)
    return file.read()


def _file_name(file):
    return getattr(file, "name", "file")


def _detect_format(data):
    """
    Mendeteksi format dari ISI file, bukan dari ekstensi.
    File berekstensi .xlsx tetapi isinya CSV/HTML tetap terbaca benar.
    """
    if data.startswith(ZIP_MAGIC):
        return "xlsx"

    if data.startswith(OLE_MAGIC):
        return "xls"

    return "text"


def _open_excel(data, file_name):
    """Membuka workbook Excel dari bytes dengan pesan error yang jelas."""
    file_format = _detect_format(data)

    if file_format == "xlsx":
        if not zipfile.is_zipfile(io.BytesIO(data)):
            raise ValueError(
                f"File '{file_name}' rusak atau terpotong saat upload "
                f"(ukuran terbaca {len(data):,} bytes). "
                "Bandingkan ukurannya dengan file asli, lalu buka di Excel "
                "dan Save As .xlsx baru, kemudian upload ulang."
            )

        return pd.ExcelFile(io.BytesIO(data), engine="openpyxl")

    if file_format == "xls":
        return pd.ExcelFile(io.BytesIO(data), engine="xlrd")

    raise ValueError(
        f"File '{file_name}' bukan file Excel (isinya teks/CSV/HTML). "
        "Buka di Excel lalu Save As .xlsx."
    )


# 2. HELPER: BACA CSV
def _detect_delimiter(data):
    """Memilih delimiter dari baris header (default koma, aman untuk 1 kolom)."""
    first_line = data.split(b"\n", 1)[0].decode("utf-8", errors="ignore")

    counts = {
        delimiter: first_line.count(delimiter)
        for delimiter in (",", ";", "\t", "|")
    }

    best = max(counts, key=counts.get)

    return best if counts[best] > 0 else ","


def _read_csv(data, file_name):
    delimiter = _detect_delimiter(data)

    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(
                io.BytesIO(data),
                dtype=object,
                sep=delimiter,
                encoding=encoding,
            )
        except UnicodeDecodeError:
            continue

    raise ValueError(f"Encoding file '{file_name}' tidak dikenali.")


# 3. READ GENERAL FILE
def read_table(file, usecols=None):
    """Membaca file CSV atau Excel (sheet pertama) menjadi DataFrame."""
    data = _read_bytes(file)
    name = _file_name(file)

    if not data:
        raise ValueError(f"File '{name}' kosong (0 bytes).")

    if _detect_format(data) == "text":
        return _read_csv(data, name)

    excel_file = _open_excel(data, name)

    return excel_file.parse(
        0,
        dtype=object,
        usecols=usecols,
    )


def _tidy_columns(df):
    df.columns = [str(column).strip() for column in df.columns]
    return df


# 4. READ SPRINT REPORT
def read_sprint_file(file):
    """Membaca laporan Sprint hanya dari kolom A sampai Q."""
    df = read_table(file, usecols="A:Q")

    return _tidy_columns(df.iloc[:, :17])


# 5. READ USER MB WORKBOOK
def read_user_workbook(file):
    """
    Membaca sheet MDIN, IB, dan MQRIS dari workbook User MB.

    Primary key:
    - MDIN  : PHONE
    - IB    : NO_HP
    - MQRIS : PHONE
    """
    data = _read_bytes(file)
    name = _file_name(file)

    if not data:
        raise ValueError(f"File '{name}' kosong (0 bytes).")

    # Workbook dibuka SEKALI, lalu tiga sheet dibaca dari objek yang sama.
    excel_file = _open_excel(data, name)

    sheet_names = {
        sheet.strip().upper(): sheet
        for sheet in excel_file.sheet_names
    }

    result = {}

    for sheet_name in ["MDIN", "IB", "MQRIS"]:
        if sheet_name not in sheet_names:
            raise ValueError(
                f"Sheet {sheet_name} tidak ditemukan di workbook User MB. "
                f"Sheet yang ada: {excel_file.sheet_names}"
            )

        df = excel_file.parse(
            sheet_names[sheet_name],
            dtype=object,
        )

        result[sheet_name] = _tidy_columns(df)

    return result


# 6. READ SUPPORTING DATA
def read_source_file(file):
    """Membaca file data pendukung dan merapikan nama kolom."""
    return _tidy_columns(read_table(file))
