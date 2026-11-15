# Stage 4.4 — Blind Held-Out Evaluation Report

**Status Akhir**: `BLIND_EVALUATION_COMPLETED_WITH_LIMITATIONS`  
**Waktu Evaluasi (UTC)**: Lihat `evaluated_at_utc` pada [stage_4_4_blind_evaluation.json](file:///home/lalita/Projects/perlombaan/data/processed/stage_4_4_blind_evaluation.json)  
**Target Evaluasi**: `generic_parser` ([generic_parser.py](file:///home/lalita/Projects/perlombaan/src/requirement_extraction/generic_parser.py)) pada 5 dokumen *blind held-out* (`DOC-011`, `DOC-017`, `DOC-051`, `DOC-070`, `DOC-053`) terhadap Ground Truth `v1.0` beku.

---

## 1. Verifikasi Pra-Evaluasi & Bukti Integritas Pembekuan

Seluruh kode parser/rules/evaluator, konfigurasi, data Stage 3, 5 dokumen TXT input, dan Ground Truth `v1.0` diverifikasi SHA-256 **sebelum dan sesudah** evaluasi pada [stage_4_4_parser_freeze_manifest.json](file:///home/lalita/Projects/perlombaan/data/processed/stage_4_4_parser_freeze_manifest.json):
- **Git Commit**: Repositori belum memiliki commit (`HEAD` *unborn*); seluruh status working tree & SHA-256 file dicatat lengkap di manifest.
- **Integritas File Beku (`all_frozen_files_unchanged: true`)**:
  - `generic_parser.py`: `pre == post` (tidak diubah).
  - `extractor.py`, `rules.py`, `evaluator.py`: `pre == post` (tidak diubah).
  - [stage_4_4_blind_held_out_ground_truth.json](file:///home/lalita/Projects/perlombaan/data/processed/stage_4_4_blind_held_out_ground_truth.json): SHA-256 `3688bf13191deae10776ab0c15105b359386f1f6441cfdb18048e6024f9448cd` (**cocok** dengan [stage_4_4_ground_truth_freeze.json](file:///home/lalita/Projects/perlombaan/data/processed/stage_4_4_ground_truth_freeze.json)).
  - Canonical `annotations` SHA-256: `200eb6e962e15310ea90d1bcd4895594bd5a30722aa2b9db7adbb97911b37cad` (**cocok**).

---

## 2. Kebijakan Partisi Ground Truth & Prediksi

Mengikuti kebijakan hasil audit kualitas Ground Truth `v1.0` (tanpa mengubah atau menghapus record dari file beku):
- **Total Ground Truth `v1.0`**: **73** record.
- **Kelompok 1 — `ambiguous_needs_review`**: **7** record (`GT-DOC-011-008`, `GT-DOC-011-009`, `GT-DOC-017-004`, `GT-DOC-070-007`, `GT-DOC-053-004`, `GT-DOC-053-007`, `GT-DOC-053-009`).
- **Kelompok 2 — `DOC-053` Hackathon `scope_mismatch`**: **4** record (`GT-DOC-053-004`, `GT-DOC-053-009`, `GT-DOC-053-011`, `GT-DOC-053-013`).
- **Irisan Kedua Kelompok**: **2** record (`GT-DOC-053-004`, `GT-DOC-053-009`) — ditangani sebagai union (`7 + 4 - 2 = 9`) agar **tidak ada penghitungan ganda**.
- **Primary Evaluation Ground Truth**: **`73 - 9 = 64`** record terverifikasi dan *in-scope*.
- **Partisi Prediksi `generic_parser`**:
  - Total prediksi mentah: **266** prediksi (`provenance_valid = 266/266`, `unsupported_by_evidence = 0`).
  - Prediksi pada wilayah yang dikecualikan (*ambiguous GT* atau bagian Hackathon `DOC-053`): **15** prediksi (`DOC-053`: 10, `DOC-011`: 3, `DOC-017`: 1, `DOC-070`: 1), dilaporkan terpisah.
  - **In-scope predictions** untuk metrik utama: **251** prediksi.

---

## 3. Aturan Matching & Normalisasi

Evaluasi dijalankan oleh [run_stage_4_4_blind_eval.py](file:///home/lalita/Projects/perlombaan/scripts/run_stage_4_4_blind_eval.py) dengan aturan deterministik **one-to-one greedy best-score matching**:
1. **Normalisasi teks**: *lowercase*, hapus karakter zero-width (`\u200b`), hapus tanda baca non-alfanumerik, dan rapikan spasi.
2. **Pass 1 (Kategori Sama — Urutan Prioritas)**:
   - **`exact_match`**: kategori sama DAN (`char_iou >= 0.85` ATAU teks ternormalisasi identik).
   - **`semantic_match`**: kategori sama DAN (`char_iou >= 0.40` ATAU `gt_token_coverage >= 0.60` ATAU (`overlap_chars > 0` dan `pred_token_coverage >= 0.70` dan `token_jaccard >= 0.35`)).
   - **`partial_match`**: kategori sama DAN (`overlap_chars > 0` ATAU `token_jaccard >= 0.25`), namun di bawah ambang `semantic_match`.
3. **Pass 2 (Lintas Kategori — `category_error`)**: untuk sisa prediksi & GT yang belum berpasangan jika `overlap_chars > 0` atau `token_jaccard >= 0.25`.
4. **Definisi TP Metrik Utama**: Hanya **`exact_match` + `semantic_match`** yang dihitung sebagai **TP** pada metrik utama. **`partial_match` tidak disamakan dengan TP** dan dilaporkan terpisah.

---

## 4. Hasil Kuantitatif Evaluasi

### 4.1 Metrik Keseluruhan (Strict Primary: `TP = exact + semantic`)

| Mode Evaluasi | GT | Pred (In-Scope) | TP | FP | FN | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Strict Primary (`exact + semantic`)** | **64** | **251** | **27** (6 exact + 21 semantic) | **224** | **37** | **0.1076** | **0.4219** | **0.1714** |
| *Sensitivitas (jika `partial_match` = TP)* | 64 | 251 | 37 (+10 partial) | 214 | 27 | 0.1474 | 0.5781 | 0.2349 |

- **`category_errors` (pada sisa belum berpasangan)**: **17** pasangan.
- **`scope_errors` (di antara pasangan cocok)**: **5** kasus (seluruhnya GT `event_shared` yang diprediksi `branch_specific`).
- **`unsupported_by_evidence`**: **0** (266/266 prediksi memiliki `raw_text[start:end] == evidence_text`).

### 4.2 Metrik per Kategori (`Strict Primary`)

| Kategori | GT | Pred | TP | FP | FN | Partial | CatErr (dari GT) | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `assessment_criteria` | 8 | 7 | 3 | 4 | 5 | 1 | 3 | 0.4286 | 0.3750 | **0.4000** |
| `eligibility_requirements` | 11 | 20 | 6 | 14 | 5 | 0 | 2 | 0.3000 | 0.5455 | **0.3871** |
| `registration_requirements` | 10 | 7 | 2 | 5 | 8 | 3 | 3 | 0.2857 | 0.2000 | **0.2353** |
| `technical_and_general_rules` | 13 | 137 | 11 | 126 | 2 | 1 | 1 | 0.0803 | **0.8462** | 0.1467 |
| `competition_structure` | 11 | 30 | 3 | 27 | 8 | 1 | 5 | 0.1000 | 0.2727 | 0.1463 |
| `deliverables` | 11 | 50 | 2 | 48 | 9 | 4 | 3 | **0.0400** | **0.1818** | **0.0656** |

### 4.3 Metrik per Dokumen (`Strict Primary`)

| Dokumen | GT Primary | Raw Pred | Excl. Pred | In-Scope Pred | TP | FP | FN | Partial | CatErr | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `DOC-011` | 16 | 17 | 3 | 14 | 5 | 9 | 11 | 0 | 5 | 0.3571 | 0.3125 | **0.3333** |
| `DOC-053` | 10 | 39 | 10 | 29 | 6 | 23 | 4 | 0 | 2 | 0.2069 | **0.6000** | 0.3077 |
| `DOC-017` | 7 | 26 | 1 | 25 | 3 | 22 | 4 | 2 | 2 | 0.1200 | 0.4286 | 0.1875 |
| `DOC-051` | 14 | 75 | 0 | 75 | 8 | 67 | 6 | 3 | 3 | 0.1067 | 0.5714 | 0.1798 |
| `DOC-070` | 17 | 109 | 1 | 108 | 5 | 103 | 12 | 5 | 5 | **0.0463** | **0.2941** | **0.0800** |

Data lengkap tersedia pada [stage_4_4_blind_evaluation.json](file:///home/lalita/Projects/perlombaan/data/processed/stage_4_4_blind_evaluation.json) dan [stage_4_4_blind_evaluation.csv](file:///home/lalita/Projects/perlombaan/data/processed/stage_4_4_blind_evaluation.csv).

---

## 5. Analisis Kesalahan & Akar Masalah

1. **Kategori Paling Lemah — `deliverables` (`F1 = 0.0656`) dan `technical_and_general_rules` (`P = 0.0803`)**:
   - **`technical_and_general_rules`** menyerap **54,6%** (137/251) dari seluruh prediksi *in-scope* karena berperan sebagai kategori *fallback* ketika pola kategori lain tidak terpenuhi (menyumbang **10 dari 17** `category_errors` dari `competition_structure`, `registration_requirements`, `deliverables`, `assessment_criteria`, dan `eligibility_requirements`).
   - **`deliverables`** (50 prediksi, hanya 2 TP) hancur presisinya karena daftar isi/struktur dokumen deliverable (seperti *Lampiran 1 Template Tulisan* pada `DOC-070` dan daftar isi proposal/pitch deck pada `DOC-051`) dipecah menjadi puluhan klausa kecil.
2. **Pola False Positive (`224` FP)**:
   - **`duplicate_or_fragment_of_gt` (106 FP)**: Parser memecah daftar bernomor/bullet menjadi klausa-klausa atomik sehingga satu persyaratan GT menghasilkan 5–30 fragmen FP (terutama pada `DOC-070`: 55 fragmen FP, `DOC-051`: 35 fragmen FP).
   - **`over_extracted_or_non_requirement` (91 FP)**: Parser mengekstrak bagian yang bukan persyaratan peserta, seperti:
     - `DOC-053` tabel rundown `WAKTU KEGIATAN` (10 FP per slot waktu Zoom/istirahat).
     - `DOC-070` Lampiran 2/3/4/5 (deklarasi `I affirm that` 3 FP, deskripsi rubrik detail per rentang skor 4 FP, dan perjanjian kerahasiaan juri).
     - Catatan: Sebagian FP di `DOC-051` (*Ketentuan Pitching & Demo*: 4 FP) merupakan persyaratan asli yang tidak memiliki span terpisah di GT `v1.0` (keterbatasan kelengkapan GT, bukan semata kesalahan parser).
3. **Pola False Negative (`37` FN = `10` benar-benar terlewat + `17` salah kategori + `10` *partial match*)**:
   - Pada `DOC-011`, **6 persyaratan benar-benar terlewat** karena header teks polos/OCR (`JUDGING CRITERIA`, `1.Prelimnary Round`, `TOURNAMENT OFFICIALS`, `4.Submission Guidelines`) tidak cocok dengan pola header atau kalimatnya tidak memicu kata kunci keharusan.
4. **Kesalahan Scope (`5` kasus `event_shared` → `branch_specific`)**:
   - `generic_parser` melabeli **266/266 (100%)** prediksi sebagai `branch_specific` karena `resolve_unit_windows()` bergantung penuh pada keberadaan span `event_level_general_info` dari Stage 3, yang tidak tersedia pada 5 unit *held-out* ini (keterbatasan desain *pipeline* Stage 3 + parser).
5. **Sumber Kesalahan & Batasan Generalisasi**:
   - *Provenance* bukan masalah (`0` *unsupported prediction*). Masalah utama berasal dari **granularitas segmentasi klausa (over-splitting)**, **penyaringan bagian non-persyaratan (Lampiran/rundown)**, dan **klasifikasi kategori (`fallback` ke `technical_and_general_rules`)**.
   - **Larangan Generalisasi**: Hasil pada 5 dokumen *blind held-out* ini **tidak boleh digeneralisasikan sebagai performa seluruh korpus**, karena ukuran sampel kecil (5 dokumen, 64 GT utama) dan mencakup variasi dokumen khusus (seperti pedoman 46 halaman berlampiran `DOC-070` dan dokumen multi-cabang tak terpecah `DOC-053`).

---

## 6. Backlog Perbaikan Stage 4.5 (Tanpa Mengubah Parser Saat Ini)

1. **Konsolidasi Granularitas Klausa (Mengurangi 106 `duplicate_or_fragment_of_gt` FP)**: Gabungkan butir daftar bernomor/bullet di bawah satu sub-judul persyaratan yang koheren sebelum klasifikasi.
2. **Perluasan `_IGNORED_SECTION_PATTERNS` & Filter Lampiran/Rundown**: Saring tabel rundown jam-per-jam (`WAKTU KEGIATAN`), formulir deklarasi kosong (`I affirm that`, `Perjanjian Kerahasiaan Juri`), dan rubrik deskriptif per rentang skor.
3. **Perbaikan Klasifikasi & Pengurangan Fallback `technical_and_general_rules`**: Tingkatkan sinyal kontekstual berbasis judul bagian untuk `deliverables`, `registration_requirements`, dan `competition_structure` agar tidak jatuh ke `technical_and_general_rules`.
4. **Dukungan Klasifikasi `event_shared` Berbasis Teks**: Tambahkan deteksi heuristik ketentuan tingkat event (mis. hak cipta penyelenggara utama, media sosial induk event) saat Stage 3 tidak memisahkan jendela `event_shared`.
5. **Resegmentasi Stage 3 `DOC-053` & GT `v1.1`**: Pisahkan cabang CTF dan Hackathon pada `DOC-053` serta selaraskan 5 span GT `v1.1` sebelum putaran evaluasi berikutnya.

---

## 7. Status Akhir

**`BLIND_EVALUATION_COMPLETED_WITH_LIMITATIONS`** — Evaluasi *blind held-out* telah dijalankan secara ketat, dapat diaudit, dan tanpa modifikasi terhadap parser, evaluator, maupun dataset GT `v1.0` beku.
