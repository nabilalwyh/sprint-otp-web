
"""Normalisasi primary key dan pencocokan indikator pada tahap Transform ETL."""

import re
from calendar import month_name

import pandas as pd


# 1. CONSTANTS
SPRINT_COLUMNS = [
    "recipient",
    "provider",
    "divisi",
    "client_name",
    "name-u",
    "masking",
    "content",
    "send_status",
    "delivery_status",
    "messagecount",
    "service",
    "country",
    "ref_id",
    "time_dbrecv",
    "time_send",
    "time_sent",
    "time_delivery",
]

INDICATORS = [
    "MDINSUCCESS",
    "MDINREG",
    "MDINREGNOPAN",
    "COB",
    "COB_MITRA",
    "HAJJ",
    "IB",
    "MQRIS",
]


# 2. PHONE NUMBER NORMALIZATION
def normalize_phone(value):
    """
    Menormalisasi nomor HP ke format tanpa awalan 0 atau 62.

    Contoh:
    - 628123456789  -> 8123456789
    - 08123456789   -> 8123456789
    - 8123456789    -> 8123456789
    """
    if pd.isna(value):
        return ""

    text = str(value).strip()

    if not text:
        return ""

    # Mengatasi angka yang terbaca sebagai float oleh pandas.
    if text.endswith(".0"):
        text = text[:-2]

    # Mengatasi angka dalam format scientific notation.
    if "e" in text.lower():
        try:
            text = str(int(float(text)))
        except (ValueError, OverflowError):
            pass

    # Hanya mempertahankan karakter angka.
    digits = re.sub(r"\D", "", text)

    # Menghapus awalan nomor Indonesia.
    if digits.startswith("62"):
        digits = digits[2:]
    elif digits.startswith("0"):
        digits = digits[1:]

    return digits


# 3. PRIMARY KEY VALIDATION
def get_pk_column(df, expected, label):
    """Mencari kolom primary key tanpa membedakan huruf besar/kecil."""
    column_lookup = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    expected_column = expected.strip().lower()

    if expected_column not in column_lookup:
        available_columns = ", ".join(
            map(str, df.columns)
        )

        raise ValueError(
            f"PK '{expected}' tidak ditemukan pada {label}. "
            f"Kolom tersedia: {available_columns}"
        )

    return column_lookup[expected_column]


# 4. NORMALIZE SOURCE PHONE NUMBERS
def normalized_phone_set(df, pk, label):
    """
    Mengambil nomor HP dari kolom PK dan mengubahnya menjadi set unik.
    Nomor kosong diabaikan dan duplikat tidak dihitung berulang.
    """
    pk_column = get_pk_column(
        df=df,
        expected=pk,
        label=label,
    )

    normalized_values = df[pk_column].map(
        normalize_phone
    )

    return {
        phone
        for phone in normalized_values
        if phone
    }


# 5. BUILD SOURCE LOOKUPS
def build_source_lookups(
    user_sheets,
    mdinreg_df,
    mdinregnopan_df,
    cob_df,
    cobmitra_df,
    hajj_df,
):
    """Membuat lookup nomor HP unik untuk setiap kategori."""
    sources = {
        "MDINSUCCESS": normalized_phone_set(
            user_sheets["MDIN"],
            "PHONE",
            "sheet MDIN",
        ),
        "MDINREG": normalized_phone_set(
            mdinreg_df,
            "phone",
            "MDINREG",
        ),
        "MDINREGNOPAN": normalized_phone_set(
            mdinregnopan_df,
            "phone",
            "MDINREGNOPAN",
        ),
        "COB": normalized_phone_set(
            cob_df,
            "MOBILE_NUMBER",
            "COB",
        ),
        "COB_MITRA": normalized_phone_set(
            cobmitra_df,
            "phone",
            "COBMITRA",
        ),
        "HAJJ": normalized_phone_set(
            hajj_df,
            "phone",
            "HAJJ",
        ),
        "IB": normalized_phone_set(
            user_sheets["IB"],
            "NO_HP",
            "sheet IB",
        ),
        "MQRIS": normalized_phone_set(
            user_sheets["MQRIS"],
            "PHONE",
            "sheet MQRIS",
        ),
    }

    return sources


# 6. BUILD SPRINT REPORT
def build_report(
    sprint_df,
    user_sheets,
    mdinreg_df,
    mdinregnopan_df,
    cob_df,
    cobmitra_df,
    hajj_df,
):
    """
    Mencocokkan recipient Sprint dengan seluruh sumber pendukung.

    Indikator:
    - 1 jika nomor HP ditemukan pada sumber terkait.
    - 0 jika nomor HP tidak ditemukan atau kosong.
    - TOTAL merupakan jumlah delapan indikator.
    """
    sprint = sprint_df.copy()

    # 6.1 Validate and arrange Sprint columns
    column_lookup = {
        str(column).strip().lower(): column
        for column in sprint.columns
    }

    missing_columns = [
        column
        for column in SPRINT_COLUMNS
        if column.lower() not in column_lookup
    ]

    if missing_columns:
        raise ValueError(
            "Kolom Sprint tidak ditemukan: "
            + ", ".join(missing_columns)
        )

    # Mempertahankan urutan kolom A-Q yang ditentukan.
    original_columns = [
        column_lookup[column.lower()]
        for column in SPRINT_COLUMNS
    ]

    sprint = sprint[original_columns].copy()
    sprint.columns = SPRINT_COLUMNS

    # 6.2 Build supporting data lookups
    sources = build_source_lookups(
        user_sheets=user_sheets,
        mdinreg_df=mdinreg_df,
        mdinregnopan_df=mdinregnopan_df,
        cob_df=cob_df,
        cobmitra_df=cobmitra_df,
        hajj_df=hajj_df,
    )

    # 6.3 Normalize Sprint recipient
    sprint["HP_CUT"] = sprint["recipient"].map(
        normalize_phone
    )

    # 6.4 Match phone numbers against each source
    for indicator, source_phones in sources.items():
        sprint[indicator] = sprint["HP_CUT"].map(
            lambda phone: int(
                bool(phone) and phone in source_phones
            )
        ).astype("int64")

    # 6.5 Calculate total matches per Sprint row
    sprint["TOTAL"] = sprint[INDICATORS].sum(axis=1)

    # 6.6 Prepare diagnostic information
    diagnostics = {
        "source_unique_phones": {
            name: len(phones)
            for name, phones in sources.items()
        }
    }

    return sprint, diagnostics


# 7. BUILD SUMMARY
def summarize_report(
    report,
    diagnostics,
    month,
    year,
):
    """Membuat ringkasan jumlah match per kategori."""
    period = f"{month_name[month]} {year}"

    rows = [
        {
            "Kategori": indicator,
            "Jumlah match": int(report[indicator].sum()),
            "Nomor unik pada sumber": (
                diagnostics["source_unique_phones"][indicator]
            ),
        }
        for indicator in INDICATORS
    ]

    # Total seluruh match dari delapan indikator.
    rows.append(
        {
            "Kategori": "TOTAL",
            "Jumlah match": int(report["TOTAL"].sum()),
            "Nomor unik pada sumber": "",
        }
    )

    summary = pd.DataFrame(rows)

    summary.insert(
        0,
        "Periode",
        period,
    )

    return summary


# 8. BUILD OPERATOR SUMMARY
def summarize_operator(report):
    """
    Menyiapkan struktur summary traffic berdasarkan operator
    dan negara.

    Catatan:
    Klasifikasi Premium/Reguler dan tarif perlu mengikuti
    mapping bisnis yang telah ditentukan.
    """
    operator_columns = [
        "Operator",
        "Traffic Premium",
        "Traffic Reguler",
        "Price Premium",
        "Price Reguler",
        "Grand Total",
    ]

    # Daftar operator dan negara sesuai format laporan.
    operators = [
        "Email",
        "Excelcom",
        "Hutchinson",
        "Indosat",
        "Smartfren",
        "Telkomsel",
        "Azerbaijan",
        "Hong Kong",
        "Japan",
        "Laos",
        "Macao",
        "Malaysia",
        "Saudi Arabia",
        "Singapore",
        "South Korea",
        "Sri Lanka",
        "Taiwan",
        "Thailand",
        "Turkey",
        "United States",
        "Wallis and Futuna",
    ]

    rows = []

    for operator in operators:
        rows.append(
            {
                "Operator": operator,
                "Traffic Premium": 0,
                "Traffic Reguler": 0,
                "Price Premium": 0,
                "Price Reguler": 0,
                "Grand Total": 0,
            }
        )

    rows.append(
        {
            "Operator": "GRAND TOTAL",
            "Traffic Premium": 0,
            "Traffic Reguler": 0,
            "Price Premium": None,
            "Price Reguler": None,
            "Grand Total": 0,
        }
    )

    summary_operator = pd.DataFrame(
        rows,
        columns=operator_columns,
    )

    # Catatan harga.
    summary_operator.loc[
        len(summary_operator)
    ] = {
        "Operator": "^harga belum termasuk pajak",
        "Traffic Premium": None,
        "Traffic Reguler": None,
        "Price Premium": None,
        "Price Reguler": None,
        "Grand Total": None,
    }

    return summary_operator
