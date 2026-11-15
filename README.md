# PERLOMBAAN — AI Competition Mentor

PERLOMBAAN adalah proyek riset dan pengembangan **AI Competition Mentor** untuk membantu memahami kebutuhan kompetisi, memetakan persyaratan ke indikator dan kompetensi, serta menjadi fondasi evaluasi dan pengembangan individu maupun tim.

Proyek ini tidak berfokus hanya pada prediksi kemenangan. Tujuan utamanya adalah membantu peserta memahami tuntutan kompetisi, mengenali kekuatan dan kesenjangan, meningkatkan kualitas gagasan/proposal, serta mengembangkan komposisi dan proses kerja tim.

---

## Tujuan

1. Mengumpulkan dan mengorganisasi dokumen kompetisi.
2. Mengekstraksi persyaratan dengan bukti yang dapat ditelusuri ke sumber.
3. Membedakan informasi eksplisit, inferensi, informasi yang tidak dinyatakan, dan hal yang perlu ditinjau.
4. Memetakan persyaratan ke indikator dan kompetensi.
5. Menjadi fondasi analisis kesiapan individu dan kesesuaian tim.
6. Memberikan arahan pengembangan yang transparan dan berbasis bukti.

---

## Dua Matriks Utama

### Matrix Perlombaan
Memetakan kelayakan peserta, registrasi, struktur kompetisi, *deliverables*, kriteria penilaian, aturan teknis, serta kompetensi yang dibutuhkan. Setiap informasi perlu memiliki sumber, lokasi bukti, cakupan cabang, dan status validasi. Bobot tidak boleh dibuat jika dokumen tidak menyatakannya.

### Matrix Personalisasi Tim
Direncanakan untuk memetakan kompetensi, pengetahuan, pengalaman, preferensi, dan kebutuhan pengembangan individu. Analisis tim juga mempertimbangkan komunikasi, koordinasi, komitmen, pembagian tanggung jawab, dan kolaborasi—bukan sekadar penjumlahan kemampuan anggota.

---

## Alur Konseptual

```text
Dokumen Kompetisi
      |
      v
Ekstraksi dan Pemrosesan Dokumen
      |
      v
Segmentasi Unit/Cabang Kompetisi
      |
      v
Ekstraksi Persyaratan
      |
      v
Pemetaan Indikator dan Kompetensi
      |
      v
Knowledge Base dengan Bukti Sumber
      |
      v
Analisis dan Evaluasi
      |
      v
AI Competition Mentor
```

---

## Progres Pengembangan

| Tahap | Hasil |
| --- | --- |
| Fondasi teknis | Python modular, SQLite/SQLAlchemy, Pydantic, PyMuPDF, Pandas, Pytest |
| Inventaris korpus | 80 dokumen TXT; 66 terbaca, 13 mengandung noise OCR, 1 kosong |
| Taksonomi | 6 kelompok makro, 31 kode cabang, 6 domain |
| Segmentasi | 76 dokumen kompetisi menghasilkan 114 unit |
| Stage 4 baseline | 145 rekaman persyaratan pada 8 unit dari 3 dokumen |
| Stage 4.4 ground truth | 73 anotasi dari 5 dokumen held-out, dibekukan sebagai v1.0 |
| Stage 4.4 evaluasi | Blind held-out pilot selesai; F1 strict `0,1714` |

---

## Hasil Evaluasi Stage 4.4

Lima dokumen *held-out*: `DOC-011` (ENERGY4ME/SPARK UP), `DOC-017` (Next Gen BMC), `DOC-051` (Hackathon Web Innovation), `DOC-070` (EIC/PGTC), dan `DOC-053` (WRECK-IT 7.0).

Dari 73 anotasi *ground truth*, 9 dikecualikan dari metrik utama tanpa penghitungan ganda: 7 anotasi ambigu dan 4 anotasi Hackathon pada `DOC-053`, dengan irisan 2 anotasi. *Primary ground truth* berjumlah **64**.

| Metrik | Hasil |
| --- | ---: |
| TP | 27 |
| FP | 224 |
| FN | 37 |
| Precision | 0,1076 |
| Recall | 0,4219 |
| F1 strict | 0,1714 |

TP terdiri dari **6 *exact match*** dan **21 *semantic match***. Sepuluh *partial match* dilaporkan terpisah. Temuan utama adalah *over-splitting*, ekstraksi bagian non-persyaratan, *fallback* kategori `technical_and_general_rules` yang berlebihan, serta performa rendah pada kategori `deliverables`.

> Hasil ini adalah pilot lima dokumen, bukan bukti generalisasi ke seluruh korpus. Parser belum layak diperluas ke seluruh dokumen.

---

## Prinsip Data

- Setiap persyaratan harus dapat ditelusuri ke bukti sumber.
- Bedakan fakta eksplisit dan inferensi.
- `NOT_STATED` adalah celah informasi, bukan persyaratan.
- Jangan mengarang bobot atau kriteria.
- Catat konflik sumber, *noise* OCR, dan ketidakpastian.
- Jangan mengubah *ground truth* beku untuk memperbaiki skor.
- Pisahkan data *development*, *validation*, dan pengujian.

---

## Rencana Berikutnya — Stage 4.5

1. Mengurangi *over-splitting* dan duplikasi fragmen.
2. Menyaring bagian non-persyaratan seperti rundown dan lampiran administratif.
3. Memperbaiki klasifikasi kategori dan mengurangi *fallback*.
4. Memperbaiki ekstraksi *deliverables*.
5. Memperjelas evaluasi *exact*, *semantic*, dan *partial match*.
6. Menyiapkan dokumen uji baru untuk evaluasi independen berikutnya.

> Lima dokumen Stage 4.4 tidak boleh lagi disebut *blind test* untuk iterasi parser berikutnya karena hasil dan pola kesalahannya telah diketahui.

---

## Teknologi & Dependensi Aktual

Berdasarkan [pyproject.toml](pyproject.toml) dan [requirements.txt](requirements.txt):
- **Python**: `>=3.10`
- **Dependensi utama**: `sqlalchemy>=2.0.30`, `pymupdf>=1.24.0`, `pydantic>=2.7.0`, `pandas>=2.2.0`
- **Pengujian**: `pytest>=8.0.0`

---

## Struktur Repositori Aktual

```text
.
├── config/                 # Konfigurasi aplikasi & path
├── data/
│   ├── raw/txt/            # Korpus dokumen TXT kompetisi
│   └── processed/          # Output terproses (diabaikan git; lokal)
├── docs/research_notes/    # Laporan riset, audit, dan evaluasi per tahap
├── knowledge_base/         # Taksonomi kompetensi & kompetisi
├── scripts/                # Skrip pipeline, audit, ground truth, dan evaluasi
├── src/
│   ├── analysis/
│   ├── competency_mapping/
│   ├── data_collection/
│   ├── database/
│   ├── document_processing/
│   ├── evaluation/
│   ├── indicator_mapping/
│   └── requirement_extraction/
└── tests/                  # Suite unit & integrasi Pytest
```

---

## Instalasi & Perintah Eksekusi

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Menjalankan seluruh *test suite*:
```bash
pytest
```

Contoh menjalankan skrip Stage 4.4 (setelah data terproses tersedia di `data/processed/`):
```bash
python scripts/build_stage_4_4_blind_gt.py
python scripts/run_stage_4_4_blind_eval.py
```

---

## Status

Proyek masih dalam tahap riset dan pengembangan. Parser ekstraksi persyaratan belum mencapai kualitas yang memadai untuk penggunaan luas. Struktur dan perintah eksekusi perlu disesuaikan dengan kondisi aktual repositori.
