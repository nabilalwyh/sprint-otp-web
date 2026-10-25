# Generate Sprint OTP Report

## Aturan bisnis
- Sprint hanya membaca kolom A-Q.
- PK Sprint: `recipient`.
- User MB: MDIN=`PHONE`, IB=`NO_HP`, MQRIS=`PHONE`.
- File lain: MDINREG=`phone`, MDINREGNOPAN=`phone`, COB=`MOBILE_NUMBER`, COBMITRA=`phone`, HAJJ=`phone`.
- Nomor HP dinormalisasi tanpa awalan `0` atau `62`.
- Indikator = 1 jika nomor ditemukan; 0 jika tidak.
- TOTAL = MDINSUCCESS + MDINREG + MDINREGNOPAN + COB + COB_MITRA + HAJJ + IB + MQRIS.

## Menjalankan di Windows dengan venv bmi2
```powershell
py -m venv test
.\test\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m streamlit run app.py
```

Upload file Sprint, workbook User MB, MDINREG, MDINREGNOPAN, COB, COBMITRA, dan HAJJ. Nama file boleh berbeda; nama kolom PK harus sesuai.
