# Stage 4.4 — Pre-Implementation Readiness Audit

**Proyek:** AI Competition Mentor  
**Tahap:** Stage 4.4 Pre-Implementation Readiness Audit  
**Keputusan Akhir:** **`READY_WITH_LIMITATIONS`**

---

## 1. Ringkasan Kondisi Proyek

Audit ini memeriksa kesiapan proyek sebelum mengimplementasikan (atau merevisi secara terkendali) **Stage 4.4: Generic Requirement Parser & Blind Held-Out Evaluation** tanpa mengubah kode sumber, dokumen TXT asli, maupun output Stage 1–4.3.

**Kondisi Aktual Workspace yang Diamati:**
- Artefak Stage 1–4.3 lengkap dan konsisten sebagai baseline terkurasi pada 3 dokumen (`DOC-001`, `DOC-009`, `DOC-024`; 8 unit; 145 record `requirements` di [competition_requirements.json](file:///home/lalita/Projects/perlombaan/data/processed/competition_requirements.json)).
- Di workspace juga sudah terdapat artefak eksplorasi awal Stage 4.4 (`src/requirement_extraction/generic_parser.py`, `data/processed/held_out_ground_truth.json` pada `DOC-002`, `DOC-003`, `DOC-016`, `DOC-054`, `DOC-063`, dan `data/processed/generic_parser_evaluation.json` yang mencatat Blind Held-Out Precision `0.2794`, Recall `0.7170`, F1 `0.4021`). Karena 5 dokumen tersebut serta `DOC-004`, `DOC-037`, `DOC-079` sudah terekspos pada eksplorasi awal, **audit ini mengeluarkan seluruhnya dari himpunan blind held-out baru** dan memilih 5 kandidat lain yang 100% belum pernah disentuh.

---

## 2. Hasil Audit Artefak Stage 4.3 (Bagian A)

Pemeriksaan silang terhadap [corpus_expansion_readiness.json](file:///home/lalita/Projects/perlombaan/data/processed/corpus_expansion_readiness.json), [corpus_expansion_plan.csv](file:///home/lalita/Projects/perlombaan/data/processed/corpus_expansion_plan.csv), dan [corpus_expansion_readiness_report.md](file:///home/lalita/Projects/perlombaan/docs/research_notes/corpus_expansion_readiness_report.md) menunjukkan:

### 2.1 Jumlah Dokumen dan Branch Unit Per Wave
| Wave (`expansion_wave`) | Baris Rencana (CSV) | Unit Cabang | Dokumen Unik | Status Gate |
|---|---:|---:|---:|---|
| `WAVE_0_COMPLETED_BASELINE` | 8 | 8 | 3 | `ALREADY_EXTRACTED_IN_STAGE_4_2` |
| `WAVE_1_CLEAN_SINGLE_AND_VALIDATED_BRANCH` | 36 | 36 | 33 | `FIRST_COHORT_TO_PROCESS_AFTER_GENERIC_PARSER` |
| `WAVE_2_UNREPRESENTED_DOC_TYPES_AND_COMPOSITE_PILOT` | 17 | 17 | 17 | `WAIT_FOR_REPRESENTATION_PILOT` |
| `WAVE_3_SHARED_CONTEXT_MULTI_BRANCH` | 11 | 11 | 5 | `WAIT_FOR_SHARED_SPAN_INHERITANCE_RESOLVER` |
| `WAVE_4_OCR_NOISE_HIGH_SUPERVISION` | 21 | 21 | 9 | `WAIT_FOR_OCR_REVIEW_WORKFLOW` |
| `WAVE_5_BLOCKED_ON_STAGE3_RESEGMENTATION` | 18 | 18 | 8 | `BLOCKED_UNTIL_STAGE3_REFINEMENT` |
| `EXCLUDED_OR_NON_RULEBOOK` | 7 | 3 | 6 | `EXCLUDED` (`DOC-005`, `DOC-014`, `DOC-034`, `DOC-060` non-unit; `DOC-007-BU-01`, `DOC-075-BU-01..02`) |
| **Total Akuntabel** | **118** | **114** | **80 unik** | *Catatan: `DOC-047` muncul di Wave 3 & Wave 5* |

### 2.2 Ketidaksesuaian yang Ditemukan Antara Laporan dan CSV/JSON
1. **Wave 1 `multi_branch_event` pada laporan baris 162:** Laporan menyebut *"Unit `single_branch` (29 unit) dan `multi_branch_event` (7 unit pada `DOC-003`, `DOC-040`, `DOC-049`)"*. Faktanya di `corpus_expansion_plan.csv`, Wave 1 berisi **32 unit `single_branch`** (termasuk `DOC-003`, `DOC-040`, `DOC-049`) dan **4 unit `multi_branch_event`** (`DOC-027-BU-01..04`).
2. **Penjumlahan dokumen unik antar-wave:** Penjumlahan `unique_documents_count` per wave berjumlah `81` (`3+33+17+5+9+8+6`), sedangkan total korpus `80` dokumen, karena `DOC-047` terbagi ke `WAVE_3` (`DOC-047-BU-01..03`) dan `WAVE_5` (`DOC-047-BU-04`).
3. **Ringkasan baris non-Wave 1 pada laporan baris 163:** Laporan menulis *"74 Unit + 4 Dokumen Non-Segmen"*, padahal `74` adalah total baris rencana Wave 2–5 + Excluded (`70` unit cabang + `4` dokumen non-unit).

---

## 3. Hasil Audit Kode Ekstraktor (Bagian B)

Audit terhadap modul di `src/requirement_extraction/` dan `tests/`:

### 3.1 Pemisahan Logika
| Kelompok Logika | File & Fungsi | Karakteristik |
|---|---|---|
| **Document-Specific Extraction Logic** | [extractor.py](file:///home/lalita/Projects/perlombaan/src/requirement_extraction/extractor.py): `_extract_doc001_bu01` (L279–655), `_extract_doc024_units` (L658–1389), `_extract_doc009_units` (L1392–2412), `extract_representative_requirements` (L2415–2608) | Bergantung langsung pada `document_id` (`DOC-001`, `DOC-024`, `DOC-009`), `branch_unit_id`, dan string anchor spesifik dokumen. Menangani *shared span* `DOC-009` (`46547..48658`) secara hardcoded. |
| **Generic Extraction & Rule Logic** | [rules.py](file:///home/lalita/Projects/perlombaan/src/requirement_extraction/rules.py): `is_non_requirement_background`, `classify_requirement_clause`, `extract_exception_or_condition`, `apply_term_normalization`, `verify_description_grounded_in_evidence`; [extractor.py](file:///home/lalita/Projects/perlombaan/src/requirement_extraction/extractor.py): `_build_page_spans`, `_locate_page_for_char`, `_find_exact_span`, `_make_record`; [generic_parser.py](file:///home/lalita/Projects/perlombaan/src/requirement_extraction/generic_parser.py) (26 fungsi, 0 referensi `DOC-`) | Sudah mendukung klasifikasi 6 kategori, *negative guard* format vs deliverable, ekstraksi pengecualian (`kecuali`, `tidak termasuk`), dan verifikasi *verbatim provenance* `raw_text[s:e] == evidence_text`. Catatan: `rules.py` memiliki catatan komentar/normalisasi yang menyebut `DOC-009`/`DOC-024`, tetapi logikanya dapat digeneralisasi. |
| **Evaluation Logic** | [evaluator.py](file:///home/lalita/Projects/perlombaan/src/requirement_extraction/evaluator.py): `build_ground_truth_dataset` (L82–167), `_evaluate_stage42_against_gt` (L170–298), `_evaluate_stage40_baseline_against_gt` (L301–430), `evaluate_requirement_extraction` (L433–588) | Menghitung TP/FP/FN dan P/R/F1, tetapi `build_ground_truth_dataset()` mengambil GT langsung dari output `stage42_payload["requirements"]` (*in-sample*). |

### 3.2 Keterbatasan Kode yang Memengaruhi Generic Parser
1. `extractor.py` lama tidak memiliki segmenter bagian/klausa generik; seluruh logika ekstraksinya adalah *hardcoded dispatch* untuk 3 dokumen.
2. `generic_parser.py` yang sudah ada di workspace masih menghasilkan Precision rendah (`0.2794`) pada uji eksplorasi karena terlalu permisif pada header berakhiran `:`, deduplikasi belum tahan *OCR noise* tingkat karakter, serta *over-splitting* di `technical_and_general_rules`.
3. `rules.py` (`classify_requirement_clause`) berorientasi keyword dan perlu didukung konteks seksi agar tidak salah mengklasifikasikan klausa multi-kalimat.

---

## 4. Audit Kandidat Held-Out & Risiko Data Leakage (Bagian C)

Untuk menjaga independensi penuh, **5 kandidat baru yang benar-benar belum pernah disentuh** dipilih dari [stage_4_4_candidate_documents.json](file:///home/lalita/Projects/perlombaan/data/processed/stage_4_4_candidate_documents.json):

| Document ID | Nama Dokumen | Jenis | Branch Unit | Validasi Segmen | Kualitas Teks | Riwayat Pakai (Aturan / Eval) | Potensi Masalah |
|---|---|---|---|---|---|---|---|
| `DOC-011` | Guidebook ENERGY4ME Competition - SPARK UP 2026 | `guidebook` (`single_branch`, Wave 1) | `DOC-011-BU-01` (`BR_STEM_PROJECT`) | `VALIDATED` | `readable` | `False` / `False` | Belum diinspeksi penuh (blind); potensi header/tabel standar |
| `DOC-017` | Guidebook Next Gen BMC 2.0 | `guidebook` (`single_branch`, Wave 1) | `DOC-017-BU-01` (`BR_BMC`) | `VALIDATED` | `readable` | `False` / `False` | Dokumen ringkas (970 kata), potensi blok BMC/jadwal rapat |
| `DOC-051` | Guidebook Hackathon Web Innovation - Milad IT Fest 19 | `guidebook` (`composite_branch_competition`, Wave 2) | `DOC-051-BU-01` (`BR_HACKATHON`) | `VALIDATED` | `readable` | `False` / `False` | Unit panjang (3.355 kata), risiko *over-splitting* |
| `DOC-070` | Pedoman EIC - PGTC 2026 | `pedoman` (`primary_branch_with_multi_event_intro`, Wave 2) | `DOC-070-BU-01` (`BR_SCIENTIFIC_PAPER`, `3103..66490`) | `VALIDATED` | `readable` | `False` / `False` | Sangat panjang (8.194 kata); rentang `0..3103` adalah sampul/kata pengantar |
| `DOC-053` | Guidebook Petunjuk Teknis Perlombaan CTF - WRECK-IT 7.0 | `guidebook_petunjuk_teknis` (`dokumen_ketentuan_dan_petunjuk_teknis`, Wave 2) | `DOC-053-BU-01` (`BR_CYBERSECURITY_CTF`) | `VALIDATED` | `readable` | `False` / `False` | Format juknis CTF dengan aturan infrastruktur & *flag submission* |

---

## 5. Rancangan Ground Truth (Bagian D)

Setiap record ground truth wajib memuat 11 field: `document_id`, `branch_unit_id`, `requirement_category`, `requirement_name`, `requirement_description`, `evidence_text`, `source_char_start`, `source_char_end`, `source_page`, `statement_nature`, `evidence_type`.

**Aturan Anotasi Baku:**
- **Multi-kalimat:** Disatukan dalam 1 record selama masih satu kesatuan aturan/daftar persyaratan utuh.
- **Pengecualian & Multi-kondisi:** Wajib tetap menempel pada aturan induknya dan diberi `statement_nature = "mandatory_with_exception"` atau `"conditional_requirement"`.
- **Event-level vs Branch-specific:** Aturan bersama event (mis. alur registrasi di pengantar) diberi atribut `scope_level = "event_shared"`, sedangkan aturan cabang diberi `scope_level = "branch_specific"`.
- **Tersebar di beberapa bagian:** Jika dua bagian menyatakan aspek berbeda dari satu topik, dianotasi masing-masing sesuai `source_char_start..end`; jika identik/pengulangan persis (mis. `Ketentuan` & `Syarat` yang sama), cukup dianotasi satu kali sebagai persyaratan kanonis.
- **Bukan persyaratan & `NOT_STATED`:** Latar belakang, sambutan, daftar hadiah, kontak panitia, contoh teks, dan formulir kosong **tidak** dimasukkan ke ground truth persyaratan; kategori yang tidak dinyatakan dalam dokumen dicatat terpisah pada `expected_not_stated_categories`, bukan sebagai record persyaratan.

---

## 6. Rancangan Evaluasi (Bagian E)

Evaluator Stage 4.2 (`evaluator.py`) saat ini **belum memadai** untuk uji parser generik karena memakai `stage42_payload["requirements"]` sebagai ground truth dan hanya mencocokkan nama/overlap span secara sederhana.

**Metode Matching 5-Tingkat yang Diusulkan:**
1. **Exact Match:** `branch_unit_id` dan `requirement_category` sama, *span IoU* $\ge 0.70$ dan *token Jaccard* $\ge 0.70$ (TP = 1).
2. **Semantic-Equivalent Match:** Kategori sama, makna semantik/topik kanonis sama (*topic recall* $\ge 0.60$ & *evidence token recall* $\ge 0.45$), meskipun mengutip salinan halaman duplikat (TP = 1).
3. **Partial Match:** Kategori sama tetapi hanya menangkap sebagian kondisi/butir (*span overlap* $\ge 0.15$ atau *token recall* $\ge 0.25$) — dicatat terpisah untuk analisis *under/over-splitting*; untuk metrik ketat tidak dihitung sebagai Exact TP penuh kecuali memenuhi ambang minimal.
4. **Incorrect Extraction (FP):** Salah kategori, mengutip narasi non-persyaratan (latar belakang/hadiah/kontak), duplikasi berulang, atau deskripsi tidak didukung bukti.
5. **Missed Requirement (FN):** Persyaratan ground truth tidak tercakup oleh prediksi yang valid.

*Peninjauan Kasus Ambigu:* Setiap pasangan *Partial Match* atau *boundary mismatch* ditinjau manual terhadap teks sumber TXT asli untuk membedakan kesalahan parser vs perbedaan granularitas anotasi.

---

## 7. Desain Pemisahan Data (Bagian F)

Rencana lengkap tersimpan pada [stage_4_4_data_split_plan.json](file:///home/lalita/Projects/perlombaan/data/processed/stage_4_4_data_split_plan.json):
1. **Development Dataset** (`DOC-001`, `DOC-009`, `DOC-024` — 8 unit): Referensi baseline terkurasi Stage 4.2.
2. **Validation Dataset** (`DOC-004`, `DOC-037`, `DOC-079`, `DOC-002`, `DOC-003`, `DOC-016`, `DOC-054`, `DOC-063` — 8 unit): Untuk menyempurnakan dan mengkalibrasi parser generik secara iteratif sebelum uji buta.
3. **Blind Held-Out Test Dataset** (`DOC-011`, `DOC-017`, `DOC-051`, `DOC-070`, `DOC-053` — 5 unit): Pengujian buta satu kali (*single-shot*), ground truth dibekukan dengan SHA-256 sebelum parser dijalankan, dan hasilnya tidak boleh dipakai untuk menala ulang aturan pada set dokumen yang sama. **Catatan metodologis:** Lima dokumen ini hanyalah pilot representatif lintas kelompok dan **tidak cukup** untuk membuktikan generalisasi penuh ke seluruh 80 dokumen korpus (terutama Wave 4 OCR noise dan Wave 5 yang terblokir segmentasi).

---

## 8. Keputusan Akhir & Daftar Masalah Sebelum Eksekusi

- **Keputusan Akhir:** **`READY_WITH_LIMITATIONS`**
- **Alasan:** Proyek memiliki 5 kandidat held-out yang benar-benar independen (`DOC-011`, `DOC-017`, `DOC-051`, `DOC-070`, `DOC-053`), pemisahan dataset 3-arah yang bersih dari kebocoran data, serta rancangan ground truth dan evaluasi semantik yang valid.
- **Batasan & Masalah yang Harus Diterima/Diselesaikan:**
  1. Lima dokumen held-out hanya menguji kelayakan awal (*pilot*), bukan pembuktian generalisasi korpus 80 dokumen.
  2. Sebelum menjalankan uji buta pada 5 kandidat baru, parser generik (`generic_parser.py`) perlu disempurnakan terlebih dahulu menggunakan **Validation Dataset** (terutama menekan FP dari header `:`, *OCR-noise duplicates*, dan *over-splitting* `technical_and_general_rules`).
  3. Wave 3 (`VALIDATED_WITH_LIMITATION` dengan *shared registration spans*) dan Wave 5 (`NEEDS_REVISION`) tetap terblokir hingga *shared-span resolver* dan perbaikan segmentasi Stage 3.2 selesai.
