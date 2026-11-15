# Stage 4.4: Generic Requirement Parser & Blind Held-Out Evaluation Report

## 1. Ringkasan Eksekutif

Stage 4.4 mengembangkan parser persyaratan kompetisi generik ([generic_parser.py](file:///home/lalita/Projects/perlombaan/src/requirement_extraction/generic_parser.py)) yang **bebas dari aturan spesifik `document_id`** dan mengevaluasinya secara buta (*blind held-out evaluation*) terhadap **5 dokumen tak terlihat** dengan **53 anotasi ground truth beku** ([held_out_ground_truth.json](file:///home/lalita/Projects/perlombaan/data/processed/held_out_ground_truth.json)).

- **Hasil Blind Held-Out Overall (5 Dokumen, 53 GT)**:
  - **TP = 38**, **FP = 98**, **FN = 15**
  - **Precision = 0.2794 (27.94%)**
  - **Recall = 0.7170 (71.70%)**
  - **F1-Score (Micro) = 0.4021 (40.21%)**
  - **Macro F1-Score = 0.4483 (44.83%)**
- **Keputusan Status Akhir**: **`NEEDS_MORE_REFINEMENT`** — Arsitektur *section-and-clause* mampu menggeneralisasi dan menangkap **71.70%** persyaratan pada dokumen tak terlihat tanpa hardcoding `document_id`, tetapi presisi (**27.94%**) masih terlalu rendah untuk ekspansi langsung ke korpus Wave 1–3 akibat pemecahan fragmen pada baris berakhiran tanda titik dua (`:`), kebocoran halaman duplikat ber-noise OCR, dan *over-splitting* pada kategori `technical_and_general_rules`.

---

## 2. Pemisahan Dataset Evaluasi (Bagian A)

Untuk mencegah kebocoran data (*data leakage*), dataset dipisah secara eksplisit menjadi tiga kelompok sebelum parser generik dikembangkan:

| Split | Document IDs | Tujuan |
|---|---|---|
| **Development Dataset** | `DOC-001`, `DOC-024`, `DOC-009` (8 unit) | Digunakan pada Stage 4.0–4.3 untuk menyusun dan mengaudit baseline terkurasi (`extractor.py`) |
| **Validation Dataset** | `DOC-004`, `DOC-037`, `DOC-079` (3 unit) | Digunakan untuk merancang pola header/klausa generik tanpa menyentuh held-out set |
| **Blind Held-Out Test Dataset** | `DOC-002`, `DOC-003`, `DOC-016`, `DOC-054`, `DOC-063` (5 unit) | Evaluasi buta independen dengan ground truth dibekukan terlebih dahulu |

### Karakteristik 5 Dokumen Blind Held-Out
1. **`DOC-002` (`App Dev.txt`, Wave 1, `single_branch`, `guidebook`)** — 14 GT. Tantangan: hampir seluruh halaman terduplikasi dua kali secara berurutan akibat konversi PDF/OCR, disertai *OCR noise* pada salinan kedua.
2. **`DOC-003` (`BPC GUIDEBOOK.txt`, Wave 1, `single_branch`, `guidebook`)** — 8 GT. Tantangan: berbahasa Inggris dengan pengantar multi-event Techtonic UI 3.0, biaya bersyarat (*pay only upon qualifying for Semifinal Round*), header timeline ber-OCR (`TITMIMELEILNINEE`), dan `assessment_criteria` tidak dicantumkan (`NOT_STATED`).
3. **`DOC-016` (`GUIDE BOOK HIMTEC-1.txt`, Wave 2, `composite_branch_competition`, `guidebook`)** — 11 GT. Tantangan: struktur hierarkis `A`–`N` dengan sub-poin bertingkat, sistem nilai 4 juri (10–100 poin, maks 400 poin) + *tie-breaker*, serta pengecualian boilerplate/AI.
4. **`DOC-054` (`HACKATHON GUIDEBOOK.txt`, Wave 3, `primary_branch_with_multi_event_intro`, `guidebook`)** — 9 GT. Tantangan: rentang `0..5101` merupakan pengantar & registrasi bersama Techtonic UI 3.0 sedangkan `5101..15413` adalah panduan PE STEM Competition (ketidaksesuaian nama file vs isi), serta `assessment_criteria = NOT_STATED`.
5. **`DOC-063` (`Panduan Lomba Esai untuk Pelajar SMP SMA.txt`, Wave 2, `dokumen_ketentuan_dan_petunjuk_teknis`)** — 11 GT. Tantangan: penggabungan `Ketentuan Umum` + `PANDUAN LOMBA ESAI` dengan pengulangan `Syarat Esai`, contoh teks esai WHO, serta template kosong `LEMBAR PERNYATAAN ORISINALITAS KARYA`.

Ground truth dibekukan pada `data/processed/held_out_ground_truth.json` dengan digest SHA-256 `6c06b86b06019206d835ede6c80a904088dd4682013a11ee7a314a6a2396ef90` sebelum `generic_parser.py` dibuat dan tidak diubah setelah melihat hasil evaluasi.

---

## 3. Arsitektur Parser Generik (Bagian B)

Pipeline pada [generic_parser.py](file:///home/lalita/Projects/perlombaan/src/requirement_extraction/generic_parser.py) terdiri dari lima tahap tanpa cabang `document_id`:

1. **Unit & Shared-Event Span Resolver (`resolve_unit_windows`)**: Membaca batas karakter unit dari `competition_branch_units.json` serta memeriksa `uncovered_char_spans` pada `segmentation_validation.json` untuk kategori `shared_registration_or_payment_rules`.
2. **Page & Section Segmenter (`_segment_window_into_sections`)**: Mendeteksi header bernomor (`A. ...`), header huruf kapital, header multi-baris terpecah (`Alur\npendaftaran`, `ketentuan\numum`), dan menyaring seksi non-persyaratan (Cover, TOC, Latar Belakang, Hadiah, Kontak Panitia, Daftar Pustaka, Template Pernyataan Orisinalitas) serta baris *running header/footer* (`@techtonic.ui`, `#TechForTomorrow`, nomor halaman).
3. **Clause, List & Table Grouping + Deduplication**: Mengelompokkan seksi `timeline` dan `assessment` secara kohesif, menjaga sub-item (`a..f`, `•`) tetap terikat pada induknya, dan membuang blok duplikat menggunakan Jaccard token ($\ge 0.72$) atau *containment* ($\ge 0.85$).
4. **Contextual & Linguistic Classifier (`_classify_clause_text`)**: Mengklasifikasikan kandidat ke 6 kategori persyaratan dengan *negative guard* (mis. aturan format kertas/font/halaman/sitasi masuk ke `technical_and_general_rules`, bukan `deliverables`).
5. **Verbatim Provenance & Grounding**: Memverifikasi `raw_text[source_char_start:source_char_end] == evidence_text` untuk setiap rekaman (100% terverifikasi pada seluruh hasil ekstraksi).

---

## 4. Hasil Evaluasi Blind Held-Out (Bagian C)

### 4.1 Metrik Keseluruhan & Per Dokumen
| Document ID | Struktur / Kategori | TP | FP | FN | Precision | Recall | F1-Score |
|---|---|---:|---:|---:|---:|---:|---:|
| `DOC-002` | `single_branch` (Wave 1) | 11 | 25 | 3 | 0.3056 | 0.7857 | 0.4400 |
| `DOC-003` | `single_branch` (Wave 1) | 4 | 17 | 4 | 0.1905 | 0.5000 | 0.2759 |
| `DOC-016` | `composite_branch_competition` | 10 | 39 | 1 | 0.2041 | 0.9091 | 0.3333 |
| `DOC-054` | `primary_branch_with_multi_event_intro` | 4 | 6 | 5 | 0.4000 | 0.4444 | 0.4211 |
| `DOC-063` | `dokumen_ketentuan_dan_petunjuk_teknis` | 9 | 11 | 2 | 0.4500 | 0.8182 | 0.5806 |
| **ALL HELD-OUT** | **5 Dokumen (Micro)** | **38** | **98** | **15** | **0.2794** | **0.7170** | **0.4021** |

### 4.2 Metrik Per Kategori
| Kategori | TP | FP | FN | Precision | Recall | F1-Score |
|---|---:|---:|---:|---:|---:|---:|
| `eligibility_requirements` | 5 | 13 | 1 | 0.2778 | 0.8333 | 0.4167 |
| `registration_requirements` | 9 | 4 | 3 | 0.6923 | 0.7500 | **0.7200** |
| `competition_structure` | 6 | 12 | 4 | 0.3333 | 0.6000 | 0.4286 |
| `deliverables` | 9 | 20 | 1 | 0.3103 | **0.9000** | 0.4615 |
| `assessment_criteria` | 2 | 2 | 3 | 0.5000 | 0.4000 | 0.4444 |
| `technical_and_general_rules` | 7 | 47 | 3 | 0.1296 | 0.7000 | 0.2188 |

### 4.3 Contoh Nyata Kesalahan Ekstraksi (FP & FN)
1. **False Positive akibat header palsu berakhiran `:` / teks pengantar**:
   - `GEN-DOC-002-01-001` (`DOC-002`, `technical_and_general_rules`): Fragmen cover/deskripsi umum (`"GUIDEBOOK\nDevelopment\nCompetition..."`) lolos karena header halaman awal tidak terbuang sebelum seksi `deskripsi umum`.
   - `GEN-DOC-002-01-002` (`DOC-002`): Baris prosa `"Future”. yang membawa subtema:"` terdeteksi sebagai header karena diakhiri tanda `:`.
2. **False Positive akibat duplikasi halaman dengan *OCR noise***:
   - `GEN-DOC-002-01-007` (`DOC-002`, `registration_requirements`): Salinan kedua berisi korup OCR (`"Mengunggah KTAP/Kartlu Pelajar ... peMengunggah twibbon"`) sehingga kemiripan Jaccard turun di bawah ambang `0.72` dan lolos deduplikasi.
3. **False Positive akibat *over-splitting* (`technical_and_general_rules`: 47 FP)**:
   - Pada `DOC-016` (39 FP) dan `DOC-002` (25 FP), klausa-klausa bernomor di dalam satu ketentuan umum dipecah menjadi puluhan rekaman terpisah, padahal ground truth mengelompokkannya per topik aturan.
4. **False Negative akibat span event-bersama tidak terhubung & header OCR rusak**:
   - `GT-HO-DOC054-002` & `GT-HO-DOC054-003` (`DOC-054`, `0..5101`): Tidak tertangkap karena `segmentation_validation.json` tidak menandai rentang `0..5101` `DOC-054` sebagai `shared_registration_or_payment_rules`.
   - `GT-HO-DOC003-004` & `GT-HO-DOC003-005` (`DOC-003`): Header `TITMIMELEILNINEE` gagal dikenali sebagai seksi `TIMELINE` akibat distorsi OCR.
   - `GT-HO-DOC063-009` (`DOC-063`): `Penilaian Presentasi` tergabung dengan blok `Penilaian Naskah Esai` sehingga pencocokan 1-to-1 hanya menghitung 1 TP.

---

## 5. Perbandingan dengan Baseline Stage 4.2 pada Development Dataset (Bagian D)

| Sistem | Dataset | Jumlah Rekaman | TP | FP | FN | Precision | Recall | F1-Score |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **Stage 4.2 Curated Baseline** | Development (`DOC-001`, `DOC-024`, `DOC-009`) | 145 | — | — | — | (Referensi Terkurasi) | — | — |
| **Stage 4.4 Generic Parser** | Development (`DOC-001`, `DOC-024`, `DOC-009`) | 153 | 42 | 111 | 103 | 0.2745 | 0.2897 | 0.2819 |
| **Stage 4.4 Generic Parser** | **Blind Held-Out (5 Dokumen)** | **136** | **38** | **98** | **15** | **0.2794** | **0.7170** | **0.4021** |

*Catatan*: F1 pada Development Dataset (0.2819) tampak lebih rendah karena referensi Stage 4.2 memecah setiap atribut kecil (mis. batas usia, jenjang, kuota tim, tiap item berkas) menjadi 145 rekaman atomik terkurasi lintas 8 unit, sedangkan parser generik mengelompokkan klausa per blok seksi/paragraf. Evaluasi yang lebih adil terhadap kemampuan generalisasi adalah hasil **Blind Held-Out (Recall 71.70%, Precision 27.94%, F1 40.21%)**.

---

## 6. Keterbatasan Parser & Rekomendasi Status Akhir

### Keterbatasan yang Ditemukan
1. Deteksi header seksi terlalu permisif terhadap baris prosa yang diakhiri `:`.
2. Deduplikasi berbasis Jaccard token (`>= 0.72`) belum tahan terhadap korup OCR tingkat karakter (*character-level OCR noise*).
3. Resolusi span event-bersama pada `primary_branch_with_multi_event_intro` bergantung sepenuhnya pada label `shared_registration_or_payment_rules` di `segmentation_validation.json`, sehingga intro `0..start_char` belum otomatis dipindai untuk `FLOW REGISTRATION` / `MATERIALS REQUIREMENTS`.
4. Over-splitting pada klausa `technical_and_general_rules` menurunkan presisi secara drastis (12.96%).

### Keputusan Akhir
**`NEEDS_MORE_REFINEMENT`**

Parser generik **belum siap** diperluas ke seluruh korpus Wave 1–3 sebelum perbaikan berikut diterapkan:
1. Perketat deteksi header seksi (tolak kalimat panjang atau klausa yang diawali kata kerja/objek sebelum `:`).
2. Gunakan deduplikasi *character n-gram* (mis. 4-gram Jaccard) agar halaman duplikat ber-OCR noise tetap terdeteksi.
3. Tambahkan pemindaian otomatis rentang `0..unit.start_char` untuk seksi registrasi bersama pada tipe `primary_branch_with_multi_event_intro`.
4. Gabungkan sub-klausa bernomor dalam satu seksi aturan umum (`KETENTUAN UMUM`, `GENERAL RULES`) ke dalam klaster tematik untuk meningkatkan presisi di atas 0.70.
