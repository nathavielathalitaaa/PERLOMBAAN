# Laporan Evaluasi Baseline & Kesiapan Ekspansi Korpus (Stage 4.3: Baseline Evaluation & Corpus Expansion Readiness)

**Proyek:** AI Competition Mentor  
**Tahap:** Stage 4.3 — Baseline Evaluation & Corpus Expansion Readiness  
**Artefak Dasar:**  
- [competition_requirements.json](file:///home/lalita/Projects/perlombaan/data/processed/competition_requirements.json)  
- [requirement_extraction_evaluation.json](file:///home/lalita/Projects/perlombaan/data/processed/requirement_extraction_evaluation.json)  
- [requirement_extraction_refinement_report.md](file:///home/lalita/Projects/perlombaan/docs/research_notes/requirement_extraction_refinement_report.md)  
- [segmentation_validation.json](file:///home/lalita/Projects/perlombaan/data/processed/segmentation_validation.json)  
- [document_inventory_validated.json](file:///home/lalita/Projects/perlombaan/data/processed/document_inventory_validated.json)  

**Keputusan Kesiapan Ekspansi:** **`NEEDS_MORE_REFINEMENT`** *(dengan jalur transisi ke `READY_WITH_RESTRICTIONS` untuk Wave 1 setelah implementasi parser klausa generik dan uji independen held-out)*

---

## Ringkasan Pemisahan Pengujian Otomatis vs. Validasi Semantik

Sesuai prinsip rekayasa riset, audit Stage 4.3 memisahkan secara tegas antara **Pengujian Integritas Otomatis (`automated_integrity_checks`)** dan **Validasi Semantik & Metodologis (`semantic_and_methodological_validation`)**:

| Dimensi Pemeriksaan | Jenis | Status | Bukti & Temuan Utama |
| :--- | :--- | :---: | :--- |
| Ketertelusuran ID dokumen & unit cabang (`145/145` record) | Otomatis | **PASS** | Seluruh `document_id` dan `branch_unit_id` valid pada Stage 2 & Stage 3. |
| Kecocokan kutipan *verbatim* `raw_text[start:end] == evidence_text` | Otomatis | **PASS** | `145/145` `requirements`, `3/3` `information_items`, dan `11/11` `review_items` cocok 100% *verbatim*. |
| Dukungan bukti terhadap klaim angka/persen/Rp/URL di deskripsi | Otomatis | **PASS** | `145/145` record lulus `verify_description_grounded_in_evidence()`. |
| Pemisahan `NOT_STATED` ke `extraction_gaps` (0 di `requirements`) | Otomatis | **PASS** | `0` record `NOT_STATED` di `requirements`; `14` celah tercatat di `extraction_gaps`. |
| Akuntabilitas 80 dokumen & 114 unit pada rencana ekspansi | Otomatis | **PASS** | Seluruh 118 baris (`114` unit + `4` dokumen non-segmen) terpetakan di `corpus_expansion_plan.csv`. |
| **Independensi Dataset Evaluasi (*Held-Out Test Set*)** | **Semantik & Metodologis** | **FAIL (`False`)** | Evaluasi Stage 4.2 dilakukan pada 3 dokumen yang sama yang dipakai untuk menyempurnakan aturan & membangun *ground truth* (*in-sample calibration*). |
| **Ketersediaan Parser Klausa Generik untuk Dokumen Baru** | **Semantik & Metodologis** | **FAIL (`False`)** | `extractor.py` saat ini baru memuat fungsi anchor terkurasi (`_extract_doc001_bu01`, `_extract_doc024_units`, `_extract_doc009_units`), belum memiliki parser generik untuk 73 dokumen lainnya. |
| **Keterwakilan Variasi Struktur & Jenis Dokumen Korpus** | **Semantik & Metodologis** | **FAIL (`False`)** | `0%` keterwakilan pada `composite_branch_competition` (5 unit), `primary_branch_with_multi_event_intro` (4 unit), `dokumen_ketentuan_dan_petunjuk_teknis` (18 unit), dan 8 dari 10 `semantic_entity_type`. |
| **Kesetaraan Jumlah Record dengan Kelengkapan Persyaratan** | **Semantik & Metodologis** | **FAIL (`False`)** | `145` record dari 8 unit tidak berarti lengkap 100%; seluruh 8 unit (`100%`) masih memiliki `extraction_gaps` dan 7 dari 8 unit (`87,5%`) memiliki `review_items` aktif. |

---

## 1. Evaluasi Baseline (Baseline Evaluation)

### 1.1 Metrik Precision, Recall, dan F1-Score Per Kategori dan Total
Pada 3 dokumen uji (`DOC-001`, `DOC-024`, `DOC-009` — total 8 unit cabang dan 147 persyaratan *ground truth*), perbandingan performa **Stage 4.0 Baseline** terhadap **Stage 4.2 Refined** adalah sebagai berikut:

| Kategori Persyaratan | Ground Truth | Stage 4.0 Strict P / R / F1 | Stage 4.0 Relaxed P / R / F1 | Stage 4.2 TP / FP / FN | Stage 4.2 Precision | Stage 4.2 Recall | Stage 4.2 F1-Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `eligibility_requirements` | 25 | 0.2857 / 0.2400 / 0.2609 | 0.7353 / 1.0000 / 0.8475 | 25 / 0 / 0 | **1.0000** | **1.0000** | **1.0000** |
| `registration_requirements` | 20 | 0.4286 / 0.3000 / 0.3529 | 1.0000 / 0.9500 / 0.9744 | 20 / 0 / 0 | **1.0000** | **1.0000** | **1.0000** |
| `competition_structure` | 28 | 0.0909 / 0.0357 / 0.0513 | 0.9500 / 0.6786 / 0.7917 | 28 / 0 / 0 | **1.0000** | **1.0000** | **1.0000** |
| `deliverables` | 14 | 0.3571 / 0.3571 / 0.3571 | 0.8667 / 0.9286 / 0.8966 | 14 / 0 / 0 | **1.0000** | **1.0000** | **1.0000** |
| `assessment_criteria` | 40 | 0.7200 / 0.4500 / 0.5538 | 1.0000 / 0.9500 / 0.9744 | 40 / 0 / 0 | **1.0000** | **1.0000** | **1.0000** |
| `technical_and_general_rules` | 20 | 0.1538 / 0.1000 / 0.1212 | 0.8889 / 0.8000 / 0.8421 | 18 / 0 / 2 | **1.0000** | **0.9000** | **0.9474** |
| **Total Keseluruhan (Micro)** | **147** | **0.3878 / 0.2585 / 0.3102** | **0.9028 / 0.8844 / 0.8935** | **145 / 0 / 2** | **1.0000** | **0.9864** | **0.9932** |
| **Rata-rata Kategori (Macro)** | **147** | — | — | — | **1.0000** | **0.9833** | **0.9912** |

### 1.2 Analisis False Positive (FP) dan False Negative (FN)
- **False Positive (`FP = 0` pada Stage 4.2, turun dari `60` *strict FP* / `14` *relaxed FP* pada Stage 4.0):**
  - Seluruh *false positive* pada Stage 4.0 telah dieliminasi dengan memindahkan narasi latar belakang acara & statistik WHO 74% kematian PTM (`REQ-DOC009-BU01-013`) ke `information_items` (`INFO-DOC009-BU01-001`), memindahkan 11 record `NOT_STATED` ke `extraction_gaps`, memperbaiki salah klasifikasi spesifikasi format poster `DOC-024-BU-03` dari `deliverables` ke `technical_and_general_rules`, serta memperluas rentang kutipan `evidence_text`.
- **False Negative (`FN = 2` pada Stage 4.2, turun dari `109` *strict FN* / `17` *relaxed FN* pada Stage 4.0):**
  - Seluruh 7 kelompok *False Negative* yang terbaca pada teks sumber telah diekstrak pada Stage 4.2.
  - Dua *False Negative* yang tersisa berada pada kategori `technical_and_general_rules` di `DOC-009`:
    1. `GT-DOC009BU01-021` (`DOC-009-BU-01`, halaman 14 bawah, karakter `12983..13328`): aturan jenis huruf, ukuran font, spasi, dan margin esai yang rusak berat akibat OCR (`'Pick Aha Mh Sh tt hAT teP... font€:'`) dan dialihkan ke `review_items` (`REV-DOC009-BU01-003`).
    2. `GT-DOC009BU03-018` (`DOC-009-BU-03`, halaman 39 bawah, karakter `35122..35486`): blok ketentuan tambahan pasca-butir 7 publikasi Instagram yang terdistorsi oleh OCR (`'TOPE T HOO TET ET ET TESST...'`) dan dialihkan ke `review_items` (`REV-DOC009-BU03-001`).

### 1.3 Audit Konsistensi Anotasi Manual & Independensi Evaluasi (*Data Leakage Check*)
1. **Konsistensi Internal Anotasi Manual:** Seluruh 147 item `ground_truth_annotations` pada `requirement_extraction_evaluation.json` memiliki ID unik, rentang karakter valid (`0 <= start < end`), kategori dan subkategori yang konsisten, serta granularitas rubrik atomik yang seragam (1 aspek penilaian = 1 item *ground truth*).
2. **Temuan Kritis Metodologi (Ketidakindependenan Evaluasi):**
   - Ketiga dokumen evaluasi (`DOC-001`, `DOC-024`, `DOC-009`) adalah dokumen yang sama yang digunakan untuk mengaudit Stage 4.1 dan menyempurnakan aturan pada Stage 4.2.
   - Di dalam [evaluator.py](file:///home/lalita/Projects/perlombaan/src/requirement_extraction/evaluator.py#L66-L101), fungsi `build_ground_truth_dataset()` membangun 145 item *ground truth* yang dapat diekstrak secara langsung dari daftar record `stage42_payload["requirements"]` (ditambah 2 item OCR rusak).
   - Di dalam [extractor.py](file:///home/lalita/Projects/perlombaan/src/requirement_extraction/extractor.py#L2498-L2502), fungsi `extract_representative_requirements()` memanggil tiga fungsi spesifik-dokumen (`_extract_doc001_bu01`, `_extract_doc024_units`, `_extract_doc009_units`) yang menggunakan anchor terkurasi untuk ketiga dokumen tersebut.
   - **Kesimpulan Audit Baseline:** Nilai F1-score `0.9932` adalah **skor kalibrasi *in-sample* dan verifikasi regresi** atas ketepatan kurasi bukti pada 3 dokumen uji, **bukan** hasil pengujian independen (*blind held-out evaluation*) atas kemampuan generalisasi ekstraktor pada dokumen baru.

---

## 2. Evaluasi Variasi Dokumen (Document Variation & Representation Evaluation)

Saat ini baru **3 dari 80 dokumen (`3,75%`)** dan **8 dari 114 unit cabang (`7,02%`)** yang dievaluasi. Pengelompokan seluruh korpus menunjukkan celah keterwakilan berikut:

### 2.1 Berdasarkan Struktur Cabang (`multi_branch_type`)

| Kelompok `multi_branch_type` | Total Dokumen | Dokumen Dievaluasi | Total Unit | Unit Dievaluasi | % Unit Dievaluasi | Status Keterwakilan |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `single_branch` | 50 | 1 (`DOC-001`) | 50 | 1 | 2,00% | Terwakili minimal (1 dokumen) |
| `multi_branch_event` | 17 | 2 (`DOC-024`, `DOC-009`) | 55 | 7 | 12,73% | Terwakili sebagian (2 dokumen) |
| `composite_branch_competition` | 5 | **0** | 5 | **0** | **0,00%** | **BELUM TERWAKILI (`0%`)** |
| `primary_branch_with_multi_event_intro` | 4 | **0** | 4 | **0** | **0,00%** | **BELUM TERWAKILI (`0%`)** |
| `non_competition_or_unclassified` | 4 | **0** | 0 | **0** | 0,00% | Dieksklusi (bukan lomba / kosong) |
| **Total Korpus** | **80** | **3 (3,75%)** | **114** | **8 (7,02%)** | **7,02%** | — |

### 2.2 Berdasarkan Kualitas Teks (`readability_status`)

| Kualitas Teks (`readability_status`) | Total Dokumen | Dokumen Dievaluasi | Total Unit | Unit Dievaluasi | % Unit Dievaluasi | Status Keterwakilan |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `readable` | 66 | 2 (`DOC-001`, `DOC-024`) | 87 | 4 | 4,60% | Terwakili sebagian |
| `readable_with_ocr_noise` | 13 | 1 (`DOC-009`) | 27 | 4 | 14,81% | Terwakili sebagian (1 dokumen) |
| `empty` | 1 (`DOC-034`) | 0 | 0 | 0 | 0,00% | Terblokir (wajib konversi ulang PDF) |

### 2.3 Berdasarkan Kategori Makro & Jenis Dokumen (`macro_document_category` & `validated_document_type`)

| Kategori Makro (`macro_document_category`) | Sub-Tipe (`validated_document_type`) | Total Dokumen | Total Unit | Dievaluasi (Dokumen / Unit) | Status Keterwakilan |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `dokumen_panduan_kompetisi` | `guidebook` (48), `panduan` (5), `pedoman` (3), `booklet` (2), `panduan_pelaksanaan` (2), `rulebook` (1), `handbook` (1), `ketentuan_lomba` (1) | 63 | 93 | 3 / 8 *(hanya subtipe `guidebook`)* | Subtipe non-`guidebook` **0% terwakili** |
| `dokumen_ketentuan_dan_petunjuk_teknis` | `ketentuan_lomba` (3), `panduan_pelaksanaan` (2), `guidebook_petunjuk_teknis` (2), `rulebook` (1), `panduan_teknis` (1), `syarat_ketentuan` (1), `petunjuk_teknis` (1) | 11 | 18 | **0 / 0 (0,00%)** | **BELUM TERWAKILI (`0%`)** |
| `katalog_karya_atau_finalis` | `booklet_profil_finalis` (`DOC-007`) | 1 | 1 | 0 / 0 | Non-rulebook (dieksklusi dari ekstraksi syarat) |
| `dokumen_sosialisasi` | `paparan_sosialisasi` (`DOC-075`) | 1 | 2 | 0 / 0 | Slide sosialisasi (dieksklusi dari ekstraksi syarat) |
| `dokumen_lainnya` / `modul_pembelajaran` / `unknown` | `booklet_rekrutmen` (`DOC-005`), `guidebook_bootcamp` (`DOC-014`), `modul_pembelajaran` (`DOC-060`), `unknown` (`DOC-034`) | 4 | 0 | 0 / 0 | Dieksklusi pada Stage 3 |

### 2.4 Berdasarkan Entitas Semantik Unit (`semantic_entity_type` dari Stage 3.1)
Dari 10 jenis entitas semantik pada `segmentation_validation.json`, **8 jenis entitas (`39 unit`) belum pernah diuji sama sekali (`0%`)**:
- **Sudah terwakili (2 jenis):** `single_branch_competition_guide` (`1/49` unit = `2,04%`) dan `branch_specific_technical_guide` (`7/26` unit = `26,92%`).
- **Belum terwakili (`0%`, 8 jenis):** `event_level_general_information` (`0/10` unit), `sub_event_brochure_entry` (`0/8` unit pada `DOC-015`), `competition_category_guide` (`0/7` unit pada `DOC-071` & `DOC-076`), `composite_competition_guide` (`0/5` unit), `competition_stage_guide` (`0/4` unit pada `DOC-061`), `bundled_multi_branch_appendix` (`0/3` unit pada `DOC-062-BU-02`, `DOC-067-BU-02`, `DOC-069-BU-02`), `mixed_subtheme_overview` (`0/1` unit pada `DOC-047-BU-04`), dan `non_rulebook_finalist_catalog` (`0/1` unit pada `DOC-007-BU-01`).

---

## 3. Evaluasi Provenance (Provenance & Semantic Integrity Evaluation)

Hasil pemeriksaan otomatis dan semantik terhadap seluruh record di `competition_requirements.json`:
1. **Ketertelusuran Sumber & Rentang Karakter:** `145/145` (`100%`) record di `requirements`, `3/3` di `information_items`, dan `11/11` di `review_items` memiliki `document_id`, `branch_unit_id`, `source_page`, `source_section`, serta rentang karakter `0 <= source_char_start < source_char_end <= len(raw_text)` yang 100% cocok *verbatim* dengan `raw_text[start:end]`.
2. **Dukungan Bukti terhadap Deskripsi (*Claim Grounding*):** `145/145` (`100%`) record di `requirements` lulus verifikasi `verify_description_grounded_in_evidence()` tanpa ada angka, persentase, nominal Rupiah, atau tautan yang dikarang.
3. **Integritas Halaman & Bagian:** Seluruh nomor halaman dihitung secara deterministik dari pemisah halaman `\n\n\n` dan judul bagian sesuai dengan teks sumber.
4. **Isolasi Lintas Cabang:**
   - `137/145` record (`94,48%`) berada di dalam batas ketat karakter unit cabang (`within_strict_unit_bounds = True`).
   - `8/145` record (`5,52%`, seluruhnya pada `DOC-009`) mengambil informasi pendaftaran/biaya bersama (`46547..48658`) serta baris Gelombang 1 Esai (`3157..3765`) yang berada di luar batas segmen Stage 3 secara terkontrol dan ditandai `within_strict_unit_bounds = False` dengan status `VALIDATED_WITH_SEGMENTATION_LIMITATION` atau `NEEDS_REVIEW`.
   - Kontaminasi salin-tempel yang berasal dari penulis buku panduan `DOC-024` (halaman 15 pada BMC dan halaman 23 pada Poster) berhasil diisolasi dan ditandai sebagai `NEEDS_REVIEW` (`REV-DOC024-BU02-001` dan `REV-DOC024-BU03-001`).
5. **Pemisahan Aturan Eksplisit vs. Inferensi:**
   - Skema dan kode mendukung pemisahan `explicit` vs `inferred` serta memisahkan konteks non-syarat ke `information_items` dan atribut kosong ke `extraction_gaps`. Namun karena seluruh `145` record aktif pada 3 dokumen uji saat ini bertipe `explicit` (`0` record `inferred`), logika ekstraksi untuk aturan implisit/inferensi belum teruji pada kasus nyata di korpus.

---

## 4. Evaluasi Extraction Coverage (Cakupan Ekstraksi vs. Kelengkapan Persyaratan)

### 4.1 Cakupan Unit dan Kategori
- **Unit yang sudah dievaluasi:** `8` dari `114` unit cabang (`7,02%` dari seluruh unit; `3` dari `76` dokumen kompetisi bersegmen = `3,95%`).
- **Unit yang belum dievaluasi:** `106` dari `114` unit cabang (`92,98%`; `73` dokumen kompetisi bersegmen + `4` dokumen dieksklusi).
- **Cakupan Kategori & Subkategori pada 8 Unit Uji:** Seluruh **6 kategori utama (`100%`)** dan **24 dari 32 subkategori (`75,00%`)** berhasil diekstraksi pada 8 unit uji.

### 4.2 Mengapa Jumlah Record Tidak Sama dengan Kelengkapan Persyaratan
Keberhasilan mengekstrak **145 record** (rata-rata `18,12` record/unit) **tidak berarti** persyaratan pada ke-8 unit tersebut telah lengkap 100%:

| ID Unit Cabang | Jumlah Record `requirements` | Kategori Terisi | Jumlah `extraction_gaps` (`NOT_STATED`) | Jumlah `review_items` (`NEEDS_REVIEW`) | Butuh Pemeriksaan Manusia? | Lengkap 100% Tanpa Celah/Anomali? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `DOC-001-BU-01` | 20 | 6 / 6 | **4** (`age_limit`, aturan lintas kampus, repo source code, format halaman proposal) | **3** (2 placeholder `[TBC]`, 1 kontradiksi jadwal Nov–Des 2026 vs Jan–Feb 2027) | **Ya** | **Tidak** |
| `DOC-024-BU-01` | 18 | 6 / 6 | **1** (`age_limit`) | **1** (kontradiksi tim 2 orang vs naskah ditulis individu) | **Ya** | **Tidak** |
| `DOC-024-BU-02` | 20 | 6 / 6 | **1** (`age_limit`) | **1** (salah ketik salin-tempel `'Dokumen esai'` pada BMC) | **Ya** | **Tidak** |
| `DOC-024-BU-03` | 18 | 6 / 6 | **1** (`age_limit`) | **1** (salah ketik salin-tempel syarat KTM, plagiasi, & esai PDF pada Poster) | **Ya** | **Tidak** |
| `DOC-009-BU-01` | 20 | 6 / 6 | **2** (`age_limit`, bobot `%` rubrik esai) | **3** (batas awal segmen terpotong, OCR `Ro70.001,-`, & **blok tipografi/margin hal. 14 rusak berat akibat OCR**) | **Ya** | **Tidak** |
| `DOC-009-BU-02` | 17 | 6 / 6 | **1** (`age_limit`) | **1** (URL ujian & token kuota rusak OCR + *shared registration span*) | **Ya** | **Tidak** |
| `DOC-009-BU-03` | 17 | 6 / 6 | **2** (`age_limit`, bobot `%` rubrik poster) | **1** (**blok hal. 39 bawah rusak berat akibat OCR** + *shared registration span*) | **Ya** | **Tidak** |
| `DOC-009-BU-04` | 15 | 6 / 6 | **2** (`age_limit`, bobot `%` rubrik video) | **0** *(namun 2 record memakai shared registration span di luar batas unit)* | **Ya** *(verifikasi batas segmen)* | **Tidak** |

- **Beban Pemeriksaan Manusia di Seluruh Korpus (114 Unit):** Berdasarkan `segmentation_validation.json`, sebanyak **51 dari 114 unit (`44,74%`)** di korpus berstatus `VALIDATED_WITH_LIMITATION` (40 unit) atau `NEEDS_REVISION` (11 unit) sehingga membutuhkan intervensi perbaikan segmen, *shared-span resolver*, atau verifikasi manual OCR.

---

## 5. Keputusan Ekspansi Korpus (Expansion Decision)

- **Status Keputusan Utama:** **`NEEDS_MORE_REFINEMENT`**
- **Status Transisi Bersyarat (Setelah Parser Generik & Pilot Held-Out):** **`READY_WITH_RESTRICTIONS`**

### Alasan dan Bukti Keputusan
1. **`DEC-REASON-01` — Ketiadaan Parser Klausa Generik pada `extractor.py`:** Saat ini `src/requirement_extraction/extractor.py` hanya mengimplementasikan fungsi ekstraksi berbasis anchor terkurasi untuk `DOC-001`, `DOC-024`, dan `DOC-009`. Belum ada fungsi pemisah bagian/klausa otomatis yang dapat memproses `DOC-002` s.d. `DOC-080`.
2. **`DEC-REASON-02` — Evaluasi Masih Bersifat *In-Sample Calibration*:** Skor F1 `0.9932` dihitung pada 3 dokumen yang sama yang dipakai untuk merancang aturan dan *ground truth*, sehingga belum ada bukti kuantitatif performa ekstraktor pada dokumen *held-out* yang belum pernah dilihat.
3. **`DEC-REASON-03` — Keterwakilan Nol (`0%`) pada Kelompok Struktur dan Tipe Dokumen Penting:** Kelompok `composite_branch_competition` (5 unit), `primary_branch_with_multi_event_intro` (4 unit), `dokumen_ketentuan_dan_petunjuk_teknis` (18 unit), serta 8 dari 10 `semantic_entity_type` belum diuji sama sekali.
4. **`DEC-REASON-04` — Ketergantungan pada Perbaikan Segmentasi Stage 3:** Sebanyak 11 unit berstatus `NEEDS_REVISION` (termasuk lampiran gabungan 11 bidang lomba FIKSI dan 37 bidang lomba LKS) serta 10 unit `event_level_general_information` tidak boleh diekstrak sebelum batas segmentasinya diperbaiki.

### Aturan Pembatasan Kelompok Dokumen (Jika/Saat Beralih ke `READY_WITH_RESTRICTIONS`)
- **Kelompok yang Boleh Diproses Terlebih Dahulu (Wave 1 — 36 Unit / 33 Dokumen):**
  - Unit `single_branch` (29 unit) dan `multi_branch_event` (7 unit pada `DOC-003`, `DOC-040`, `DOC-049`) yang berstatus kualitas teks `readable`, validasi segmen `VALIDATED`, dan bertipe `guidebook` standar — segera setelah parser klausa generik selesai dibuat dan diuji pada sampel *held-out* 3–5 dokumen.
- **Kelompok yang Harus Menunggu Perbaikan / Pilot Khusus (Wave 2 s.d. Wave 5 & Excluded — 74 Unit + 4 Dokumen Non-Segmen):**
  - **Wave 2 (17 unit / 17 dokumen):** Menunggu uji pilot representasi tipe dokumen non-`guidebook` (`ketentuan_lomba`, `petunjuk_teknis`, `rulebook`, `panduan`, `pedoman`) dan struktur `composite_branch_competition` / `primary_branch_with_multi_event_intro`.
  - **Wave 3 (11 unit / 5 dokumen):** Menunggu implementasi *automated shared-span inheritance resolver* untuk menggabungkan `uncovered_char_spans` (pendaftaran/ketentuan umum bersama pada `DOC-006`, `DOC-046`, `DOC-047-BU-01..03`, `DOC-054`, `DOC-073`).
  - **Wave 4 (21 unit / 9 dokumen):** Menunggu alur deteksi blok OCR rusak & antrean pemeriksaan manusia wajib (`readable_with_ocr_noise` pada `DOC-008`, `DOC-015`, `DOC-030`, `DOC-033`, `DOC-044`, `DOC-058`, `DOC-059`, `DOC-076`, `DOC-077`).
  - **Wave 5 / Terblokir (18 unit / 8 dokumen):** **Dilarang diproses** sebelum Stage 3.2 memperbaiki segmentasi (`DOC-047-BU-04`, `DOC-061-BU-01..04`, `DOC-062-BU-01..02`, `DOC-066-BU-01..02`, `DOC-067-BU-01..02`, `DOC-068-BU-01..02`, `DOC-069-BU-01..02`, `DOC-071-BU-01..03`).
  - **Excluded (7 baris / 6 dokumen):** **Tidak diekstrak** sebagai matriks persyaratan cabang (`DOC-005` rekrutmen, `DOC-014` bootcamp, `DOC-060` modul pembelajaran, `DOC-007-BU-01` katalog finalis, `DOC-075-BU-01..02` slide sosialisasi LKS, serta `DOC-034` file TXT kosong yang harus dikonversi ulang dari PDF).

---

## 6. Strategi Ekspansi Bertahap (Staged Expansion Strategy)

Rencana urutan pemrosesan untuk seluruh **80 dokumen (118 baris rencana: 114 unit cabang + 4 dokumen non-segmen)** disimpan secara lengkap di [corpus_expansion_plan.csv](file:///home/lalita/Projects/perlombaan/data/processed/corpus_expansion_plan.csv) dan dirangkum dalam tabel berikut:

| Urutan Gelombang (`expansion_wave`) | Prioritas | Jumlah Baris Rencana (Unit / Dokumen) | Dokumen Unik | Kualitas Teks & Status Segmen | Kompleksitas Struktur | Tingkat Validasi Manual | Prasyarat Sebelum Eksekusi |
| :--- | :---: | :---: | :---: | :--- | :---: | :---: | :--- |
| **`WAVE_0_COMPLETED_BASELINE`** | 0 | 8 unit | 3 (`DOC-001`, `DOC-024`, `DOC-009`) | Campuran (`VALIDATED`, `VALIDATED_WITH_LIMITATION`, `NEEDS_REVISION`) | Low – High | Medium – High | Sudah selesai pada Stage 4.2; tindak lanjuti 11 `review_items`. |
| **`WAVE_1_CLEAN_SINGLE_AND_VALIDATED_BRANCH`** | 1 | 36 unit | 33 dokumen | `readable` + `VALIDATED` (`guidebook`) | Low – Medium | `low_spot_check` | Implementasikan parser bagian/klausa generik di `extractor.py` & lulus evaluasi independen *held-out* pada 3–5 dokumen sampel. |
| **`WAVE_2_UNREPRESENTED_DOC_TYPES_AND_COMPOSITE_PILOT`** | 2 | 17 unit | 17 dokumen | `readable` + `VALIDATED` (`composite`, `multi_event_intro`, `ketentuan_lomba`, `petunjuk_teknis`, `rulebook`, `panduan`, `pedoman`) | Medium | `medium_targeted_review` | Kalibrasi parser generik pada sampel pilot untuk struktur komposit (`DOC-016`, `DOC-037`, `DOC-038`, `DOC-051`, `DOC-064`) dan format pasal/juknis (`DOC-053`, `DOC-063`, `DOC-065`, `DOC-078..080`). |
| **`WAVE_3_SHARED_CONTEXT_MULTI_BRANCH`** | 3 | 11 unit | 5 dokumen (`DOC-006`, `DOC-046`, `DOC-047`, `DOC-054`, `DOC-073`) | `readable` + `VALIDATED_WITH_LIMITATION` | High | `medium_targeted_review` | Bangun *automated shared-span inheritance resolver* yang menautkan `uncovered_char_spans` (syarat umum & registrasi bersama) ke tiap unit cabang. |
| **`WAVE_4_OCR_NOISE_HIGH_SUPERVISION`** | 4 | 21 unit | 9 dokumen (`DOC-008`, `DOC-015`, `DOC-030`, `DOC-033`, `DOC-044`, `DOC-058`, `DOC-059`, `DOC-076`, `DOC-077`) | `readable_with_ocr_noise` + (`VALIDATED` / `VALIDATED_WITH_LIMITATION`) | High | `high_mandatory_human_review` | Aktifkan detektor blok OCR korup (otomatis mengarahkan ke `review_items`), pisahkan aturan puisi vs cerpen pada `DOC-008`, dan wajibkan verifikasi manual terhadap PDF. |
| **`WAVE_5_BLOCKED_ON_STAGE3_RESEGMENTATION`** | 5 | 18 unit | 8 dokumen (`DOC-047`, `DOC-061`, `DOC-062`, `DOC-066`, `DOC-067`, `DOC-068`, `DOC-069`, `DOC-071`) | `NEEDS_REVISION` atau `event_level_general_information` | Very High | `full_manual_re_segmentation_first` | **Terblokir:** Jalankan perbaikan segmentasi Stage 3.2 terlebih dahulu (pecah lampiran 11 cabang FIKSI & 37 cabang LKS, satukan 4 tahap komposit `DOC-061`, pecah 4 cabang Pre-Event `DOC-047-BU-04`). |
| **`EXCLUDED_OR_NON_RULEBOOK`** | 6 | 7 baris (3 unit + 4 non-unit) | 6 dokumen (`DOC-005`, `DOC-007`, `DOC-014`, `DOC-034`, `DOC-060`, `DOC-075`) | Non-kompetisi, katalog finalis, sosialisasi, atau `empty` (`DOC-034`) | N/A | N/A | Jangan diekstrak sebagai persyaratan lomba; khusus `DOC-034` lakukan konversi ulang / OCR dari PDF asli. |

---

## 7. Rekomendasi Tahap Berikutnya

Berdasarkan audit kesiapan ekspansi korpus di atas, langkah pengembangan berikutnya yang direkomendasikan secara berurutan adalah:

1. **Stage 4.4 — Implementasi *Generic Section-and-Clause Requirement Parser* & Evaluasi *Held-Out Pilot* Independen:**
   - Bangun parser klausa generik di `src/requirement_extraction/extractor.py` yang secara otomatis memecah teks `CompetitionBranchUnit` menjadi blok sub-bab dan butir aturan, lalu mengklasifikasikan dan memverifikasinya menggunakan `src/requirement_extraction/rules.py` tanpa bergantung pada daftar anchor spesifik-dokumen.
   - Ambil sampel *held-out* independen sebanyak **5 dokumen yang belum pernah dilihat ekstraktor** (misalnya 2 dokumen dari **Wave 1** seperti `DOC-002` & `DOC-003`, serta 3 dokumen dari **Wave 2** yang mewakili `composite_branch_competition` `DOC-016`, `primary_branch_with_multi_event_intro` `DOC-070`, dan `dokumen_ketentuan_dan_petunjuk_teknis` `DOC-053`).
   - Buat anotasi *ground truth* manual terlebih dahulu **sebelum** menjalankan ekstraktor pada ke-5 dokumen *held-out* tersebut agar menghasilkan metrik Precision, Recall, dan F1-score yang benar-benar independen.
2. **Stage 3.2 — Perbaikan Segmentasi Terarah (*Targeted Segmentation Refinement*) untuk Wave 3 & Wave 5:**
   - Perbaiki ke-11 unit berstatus `NEEDS_REVISION` (terutama pemisahan lampiran cabang FIKSI `DOC-062`/`DOC-069`, LKS `DOC-067`, penggabungan unit tahapan `DOC-061`, dan pemisahan `DOC-047-BU-04`) serta integrasikan mekanisme pewarisan `uncovered_char_spans` (`shared_registration_or_payment_rules` dan `event_level_general_information`) ke unit cabang terkait.
3. **Stage 4.5 — Eksekusi Ekspansi Korpus Bertahap (*Wave-by-Wave Rollout*):**
   - Setelah *held-out pilot* pada Stage 4.4 mencapai ambang kualitas yang ditetapkan (misalnya Strict Grounded F1 $\ge 0.85$ dengan `0` klaim yang dikarang), ubah status menjadi `READY_WITH_RESTRICTIONS` dan jalankan ekstraksi bertahap mulai dari **Wave 1 (36 unit)** $\rightarrow$ **Wave 2 (17 unit)** $\rightarrow$ **Wave 3 (11 unit)** $\rightarrow$ **Wave 4 (21 unit dengan supervisi manusia)** $\rightarrow$ **Wave 5 (setelah Stage 3.2 rampung)**.
