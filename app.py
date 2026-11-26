
from datetime import date
import traceback

import streamlit as st

from etl.extract import (
    read_sprint_file,
    read_user_workbook,
    read_source_file,
)

from etl.transform import (
    build_report,
    summarize_report,
)

from etl.load import create_excel_report


# =========================================================
# 1. PAGE CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="Generate Sprint OTP Report",
    page_icon="📊",
    layout="wide",
)

st.title("Generate Sprint OTP Report")
st.caption("DIB - BMI")


# =========================================================
# 2. PROCESSING RULES
# =========================================================
with st.expander("Aturan proses", expanded=True):
    st.markdown(
        """
        - File Sprint dibaca hanya kolom **A–Q**.
        - PK Sprint: `recipient`.
        - PK User:
            - MDIN = `PHONE`
            - IB = `NO_HP`
            - MQRIS = `PHONE`
        - PK data pendukung lainnya:
            - MDINREG = `phone`
            - MDINREGNOPAN = `phone`
            - COB = `MOBILE_NUMBER`
            - COBMITRA = `phone`
            - HAJJ = `phone`
        - Nomor HP dinormalisasi tanpa awalan `0` atau `62`.
        - Setiap indikator bernilai **1 jika nomor ditemukan**,
          dan **0 jika nomor tidak ditemukan**.
        - `TOTAL` merupakan penjumlahan delapan indikator.
        """
    )


# =========================================================
# 3. REPORT PERIOD
# =========================================================
today = date.today()

col_month, col_year = st.columns(2)

with col_month:
    month = st.selectbox(
        "Bulan laporan",
        options=range(1, 13),
        index=today.month - 1,
        format_func=lambda value: date(
            2000,
            value,
            1,
        ).strftime("%B"),
    )

with col_year:
    year = st.number_input(
        "Tahun laporan",
        min_value=2000,
        max_value=2100,
        value=today.year,
        step=1,
    )


# =========================================================
# 4. FILE UPLOADS
# =========================================================
st.header("Upload file")

sprint_file = st.file_uploader(
    "Laporan Sprint OTP (.xlsx/.xls/.csv)",
    type=["xlsx", "xls", "csv"],
)

user_file = st.file_uploader(
    "User MB PER [tanggal] — sheet MDIN, IB, MQRIS (.xlsx)",
    type=["xlsx"],
)

col_left, col_right = st.columns(2)

with col_left:
    mdinreg_file = st.file_uploader(
        "MDINREG (.csv/.xlsx)",
        type=["csv", "xlsx"],
    )

    mdinregnopan_file = st.file_uploader(
        "MDINREGNOPAN (.csv/.xlsx)",
        type=["csv", "xlsx"],
    )

    cob_file = st.file_uploader(
        "COB (.csv/.xlsx)",
        type=["csv", "xlsx"],
    )

with col_right:
    cobmitra_file = st.file_uploader(
        "COBMITRA (.csv/.xlsx)",
        type=["csv", "xlsx"],
    )

    hajj_file = st.file_uploader(
        "HAJJ (.csv/.xlsx)",
        type=["csv", "xlsx"],
    )


# =========================================================
# 5. GENERATE REPORT
# =========================================================
if st.button(
    "Generate Report",
    type="primary",
    width="stretch",
):

    # -----------------------------------------------------
    # 5.1 Validate uploaded files
    # -----------------------------------------------------
    uploads = [
        ("Laporan Sprint", sprint_file),
        ("Workbook User MB", user_file),
        ("MDINREG", mdinreg_file),
        ("MDINREGNOPAN", mdinregnopan_file),
        ("COB", cob_file),
        ("COBMITRA", cobmitra_file),
        ("HAJJ", hajj_file),
    ]

    missing_files = [
        name
        for name, uploaded_file in uploads
        if uploaded_file is None
    ]

    if missing_files:
        st.error(
            "Upload file berikut terlebih dahulu: "
            + ", ".join(missing_files)
        )
        st.stop()

    # -----------------------------------------------------
    # 5.2 Initialize process tracking
    # -----------------------------------------------------
    current_step = "Memulai proses ETL"

    try:
        with st.spinner(
            "Membaca dan mencocokkan nomor HP..."
        ):

            # -------------------------------------------------
            # EXTRACT: Sprint report
            # -------------------------------------------------
            current_step = "Membaca file Laporan Sprint"

            sprint = read_sprint_file(
                sprint_file
            )

            # -------------------------------------------------
            # EXTRACT: User MB workbook
            # -------------------------------------------------
            current_step = "Membaca workbook User MB"

            users = read_user_workbook(
                user_file
            )

            # -------------------------------------------------
            # EXTRACT: Supporting data
            # -------------------------------------------------
            current_step = "Membaca file MDINREG"

            mdinreg = read_source_file(
                mdinreg_file
            )

            current_step = "Membaca file MDINREGNOPAN"

            mdinregnopan = read_source_file(
                mdinregnopan_file
            )

            current_step = "Membaca file COB"

            cob = read_source_file(
                cob_file
            )

            current_step = "Membaca file COBMITRA"

            cobmitra = read_source_file(
                cobmitra_file
            )

            current_step = "Membaca file HAJJ"

            hajj = read_source_file(
                hajj_file
            )

            # -------------------------------------------------
            # TRANSFORM: Match phone numbers
            # -------------------------------------------------
            current_step = "Mencocokkan nomor HP"

            report, diagnostics = build_report(
                sprint,
                users,
                mdinreg,
                mdinregnopan,
                cob,
                cobmitra,
                hajj,
            )

            # -------------------------------------------------
            # TRANSFORM: Generate summary
            # -------------------------------------------------
            current_step = "Membuat SUMMARY"

            summary = summarize_report(
                report,
                diagnostics,
                int(month),
                int(year),
            )

            # -------------------------------------------------
            # LOAD: Export Excel report
            # -------------------------------------------------
            current_step = "Membuat file Excel"

            excel_file = create_excel_report(
                report,
                summary,
            )

        # =================================================
        # 5.3 DISPLAY SUCCESS MESSAGE
        # =================================================
        st.success(
            "Report berhasil dibuat!"
        )

        # -------------------------------------------------
        # Display metrics
        # -------------------------------------------------
        metric_1, metric_2, metric_3 = st.columns(3)

        with metric_1:
            st.metric(
                "Baris Sprint",
                f"{len(report):,}",
            )

        with metric_2:
            st.metric(
                "Jumlah match seluruh kategori",
                f"{int(report['TOTAL'].sum()):,}",
            )

        with metric_3:
            unique_phones = (
                report["HP_CUT"]
                .replace("", None)
                .nunique()
            )

            st.metric(
                "Nomor HP unik Sprint",
                f"{unique_phones:,}",
            )

        # =================================================
        # 5.4 PREVIEW REPORT
        # =================================================
        st.subheader("Preview Sheet1")

        st.dataframe(
            report.head(100),
            width="stretch",
            hide_index=True,
        )

        st.subheader("Preview SUMMARY")

        st.dataframe(
            summary,
            width="stretch",
            hide_index=True,
        )

        # =================================================
        # 5.5 DOWNLOAD EXCEL REPORT
        # =================================================
        file_name = (
            f"Sprint_OTP_Report_{int(year)}_"
            f"{int(month):02d}.xlsx"
        )

        st.download_button(
            label="Download Excel Report",
            data=excel_file,
            file_name=file_name,
            mime=(
                "application/vnd.openxmlformats-officedocument"
                ".spreadsheetml.sheet"
            ),
            width="stretch",
        )

    # =====================================================
    # 6. ERROR HANDLING AND LOGGING
    # =====================================================
    except Exception as error:

        # Capture complete Python traceback.
        error_details = traceback.format_exc()

        # Display error status.
        st.error(
            "Report gagal dibuat!"
        )

        # Display the process where the error occurred.
        st.warning(
            f"Proses gagal pada tahap: {current_step}"
        )

        # Display error message.
        st.markdown("### Pesan Error")

        st.code(
            str(error),
            language="text",
        )

        # Display complete traceback.
        with st.expander(
            "Lihat Detail Error (Traceback)",
            expanded=True,
        ):
            st.code(
                error_details,
                language="text",
            )

        # Create downloadable error log.
        error_log = (
            "SPRINT OTP REPORT - ERROR LOG\n"
            "====================================\n\n"
            f"Tahap Proses:\n{current_step}\n\n"
            f"Error Message:\n{str(error)}\n\n"
            f"Traceback:\n{error_details}"
        )

        st.download_button(
            label="Download Error Log",
            data=error_log,
            file_name="sprint_otp_error_log.txt",
            mime="text/plain",
            width="stretch",
        )

        st.info(
            "Periksa detail error di atas untuk mengetahui "
            "penyebab kegagalan proses. Pastikan format file, "
            "nama kolom PK, dan struktur data sudah sesuai."
        )
