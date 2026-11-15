# Stage 4.4 — Manual Ground Truth Annotation & Dataset Freeze Report

**Status Akhir**: `GROUND_TRUTH_FROZEN_WITH_LIMITATIONS`  
**Waktu Freeze (UTC)**: `2026-11-15T13:59:59.084770+00:00`  
**Total Dokumen Blind Held-Out**: 5 dokumen (`DOC-011`, `DOC-017`, `DOC-051`, `DOC-070`, `DOC-053`)  
**Total Record Anotasi Manual**: 73 record  

---

## 1. Prinsip Independensi & Kepatuhan Protokol

Seluruh anotasi pada tahap ini dibuat **secara manual murni berdasarkan pembacaan langsung** terhadap dokumen TXT asli di `data/raw/txt/`:
- Tidak membaca atau menggunakan `data/processed/competition_requirements.json` sebagai sumber anotasi.
- Tidak mengubah kode parser/rules dan tidak menjalankan `generic_parser` terhadap kelima dokumen held-out.
- Tidak mengubah dokumen TXT asli.
- Informasi yang tidak tercantum dalam dokumen (`NOT_STATED`) tidak diubah menjadi record persyaratan, melainkan dicatat pada `expected_not_stated_categories` per dokumen.
- Ketidakkonsistenan internal di dalam dokumen sumber tidak "diperhalus" secara asumtif, melainkan ditandai dengan `annotation_status = "ambiguous_needs_review"` beserta catatan eksplisit pada `annotator_notes`.

---

## 2. Ringkasan Kuantitatif Anotasi

### 2.1 Jumlah Anotasi per Dokumen

| Document ID | File TXT Asli | Branch Unit ID | Branch Code | Jumlah Anotasi | `expected_not_stated_categories` |
| --- | --- | --- | --- | ---: | --- |
| `DOC-011` | `ENERGY4ME GUIDEBOOK.txt` | `DOC-011-BU-01` | `BR_STEM_PROJECT` | 18 | `registration_fee`, `participant_age_limit` |
| `DOC-017` | `GUIDE BOOK NEXTGEN BMC.txt` | `DOC-017-BU-01` | `BR_BMC` | 8 | `education_level_restriction` (umum), `participant_age_limit` |
| `DOC-051` | `Guidebook_Hackathon.txt` | `DOC-051-BU-01` | `BR_HACKATHON` | 14 | `participant_age_limit`, `prize_or_awards` |
| `DOC-070` | `Pedoman EIC - PGTC 2026.txt` | `DOC-070-BU-01` | `BR_SCIENTIFIC_PAPER` | 18 | `registration_fee`, `participant_age_limit` |
| `DOC-053` | `Guidebook_Wreck_IT_7.0.txt` | `DOC-053-BU-01` | `BR_CYBERSECURITY_CTF` | 15 | `registration_fee`, `participant_age_limit`, `ctf_and_hackathon_scoring_weights` |
| **Total** | | | | **73** | |

### 2.2 Jumlah Anotasi per Kategori Persyaratan

| `requirement_category` | Jumlah |
| --- | ---: |
| `eligibility_requirements` | 12 |
| `registration_requirements` | 10 |
| `competition_structure` | 17 |
| `deliverables` | 12 |
| `assessment_criteria` | 9 |
| `technical_and_general_rules` | 13 |
| **Total** | **73** |

### 2.3 Distribusi `scope_level` dan `annotation_status`

- **`scope_level`**:
  - `branch_specific`: 67 record
  - `event_shared`: 6 record (ketentuan bersama tingkat event pada PGTC 2026 di `DOC-070` serta ketentuan registrasi/disiplin bersama WRECK-IT 7.0 di `DOC-053`)
- **`annotation_status`**:
  - `verified`: 66 record
  - `ambiguous_needs_review`: 7 record

---

## 3. Kasus Ambigu & Keterbatasan Anotasi (`ambiguous_needs_review` & Limitations)

1. **Keterbatasan Segmentasi Stage 3 pada `DOC-053` (`Guidebook_Wreck_IT_7.0.txt`)**:
   - Stage 3 mengelompokkan seluruh `DOC-053` ke dalam satu unit `DOC-053-BU-01` (`BR_CYBERSECURITY_CTF`, rentang `0..19471`), padahal isi dokumen memuat petunjuk teknis untuk **CTF (General CTF & Junior CTF)** sekaligus **Hackathon**.
   - Untuk menjaga konsistensi ID unit Stage 3 sambil tetap akurat terhadap teks sumber, seluruh 15 record `DOC-053` ditautkan ke `DOC-053-BU-01` dengan pemisahan jelas pada `requirement_name`, `scope_level` (`event_shared` vs `branch_specific`), dan `annotator_notes`.
2. **Konflik Internal Dokumen Sumber (7 record `ambiguous_needs_review`)**:
   - `DOC-011` (`GT-DOC-011-008`, `GT-DOC-011-009`): Tabel *Timeline* mencantumkan pengumpulan abstrak Preliminary Round `15 Oktober – 8 November 2026`, sedangkan bagian *Preliminary Round — 4. Submission Guidelines* mencantumkan tenggat `15 November 2026 pukul 23.59 WIB`.
   - `DOC-017` (`GT-DOC-017-004`): *Alur Lomba* menggambarkan alur satu tahap (`Registrasi → Pengumpulan BMC → Join Grup WhatsApp → Pengumuman Pemenang`), namun bagian *Hadiah dan Benefit* mencantumkan `Top 10 Finalis` dan `Top 25 Semifinalis` tanpa mekanisme seleksi semifinal/final.
   - `DOC-070` (`GT-DOC-070-007`): Bab II.B.2.b.a mencantumkan sesi tanya-jawab Babak Final selama `15 menit`, sedangkan Bab II.G.2.b.b mencantumkan `30 menit`.
   - `DOC-053` (`GT-DOC-053-004`, `GT-DOC-053-007`, `GT-DOC-053-009`): Bagian *Pendahuluan CTF* menyebut `7 tim` masuk babak final, sedangkan ketentuan G.9 & J.9 menyebut `10 tim`; *Pendahuluan Hackathon* menyebut `individu maupun tim`, sedangkan F.3 mewajibkan tim `3–5 orang`; tabel *Timeline Hackathon* memiliki salah ketik tahun `1 Juli 2-26`.
3. **Ketersediaan `source_page`**:
   - Hanya `DOC-070` yang memiliki footer nomor halaman tercetak dalam file TXT; untuk `DOC-011`, `DOC-017`, `DOC-051`, dan `DOC-053`, `source_page` bernilai `null`.

---

## 4. Hasil Validasi Integritas Evidence & Dataset Freeze

Validasi otomatis oleh [build_stage_4_4_blind_gt.py](file:///home/lalita/Projects/perlombaan/scripts/build_stage_4_4_blind_gt.py) setelah pembentukan file [stage_4_4_blind_held_out_ground_truth.json](file:///home/lalita/Projects/perlombaan/data/processed/stage_4_4_blind_held_out_ground_truth.json) menunjukkan:
- `raw_text[source_char_start:source_char_end] == evidence_text`: **73/73 cocok persis** (`exact_char_span_match_all_passed: true`).
- Seluruh span berada di dalam rentang karakter `branch_unit_id` pada Stage 3 (`branch_unit_bounds_all_passed: true`).
- Seluruh 15 field wajib hadir pada setiap record (`required_fields_all_present: true`).
- Nol duplikasi dan nol tumpang-tindih span antar-record dalam dokumen yang sama (`zero_overlapping_or_duplicate_spans: true`).

### Manifest Freeze (`stage_4_4_ground_truth_freeze.json`)
- **File Ground Truth**: [stage_4_4_blind_held_out_ground_truth.json](file:///home/lalita/Projects/perlombaan/data/processed/stage_4_4_blind_held_out_ground_truth.json)
- **File Manifest Freeze**: [stage_4_4_ground_truth_freeze.json](file:///home/lalita/Projects/perlombaan/data/processed/stage_4_4_ground_truth_freeze.json)
- **SHA-256 File Ground Truth**: `3688bf13191deae10776ab0c15105b359386f1f6441cfdb18048e6024f9448cd`
- **SHA-256 Kanonik Array `annotations`**: `200eb6e962e15310ea90d1bcd4895594bd5a30722aa2b9db7adbb97911b37cad`
- **Timestamp Freeze (UTC)**: `2026-11-15T13:59:59.084770+00:00`

> [!NOTE]
> Kelulusan pemeriksaan kecocokan karakter dan integritas skema tidak berarti dataset bebas dari ambiguitas sumber. Justru dengan mencatat 7 konflik internal dokumen dan keterbatasan segmentasi `DOC-053`, dataset ini siap dibekukan sebagai acuan evaluasi blind held-out secara jujur dan dapat diaudit.

---

## 5. Keputusan Status

**`GROUND_TRUTH_FROZEN_WITH_LIMITATIONS`** — Dataset ground truth blind held-out resmi dibekukan dan tidak boleh diubah setelah tahap ini, dengan catatan keterbatasan di atas dibawa secara eksplisit saat menginterpretasikan hasil evaluasi pada tahap berikutnya.
