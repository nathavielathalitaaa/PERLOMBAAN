# Laporan Penyempurnaan Ekstraksi Persyaratan (Stage 4.2: Requirement Extraction Refinement)

**Proyek:** AI Competition Mentor  
**Tahap:** Stage 4.2 — Requirement Extraction Refinement  
**Dasar Audit:** `docs/research_notes/requirement_extraction_audit.md` & `data/processed/requirement_extraction_audit.json`  
**Ruang Lingkup Uji:** 3 Dokumen Representatif (`DOC-001`, `DOC-024`, `DOC-009` — 8 `CompetitionBranchUnit`)  
**Status Rekomendasi Ekspansi Korpus:** `NEEDS_MORE_REFINEMENT`

---

## 1. Masalah pada Stage 4.0 (Ringkasan Temuan Audit Stage 4.1)

Berdasarkan audit komprehensif Stage 4.1 terhadap 98 record awal pada `data/processed/competition_requirements_stage4_0_baseline.json`, ditemukan **59 record bermasalah (`ISSUE_FOUND` / `NEEDS_REVISION`, 60,20%)** dan hanya **39 record bersih (`VERIFIED_CLEAN`, 39,80%)**, ditambah **7 kelompok False Negative**. Akar masalah utama pada Stage 4.0 meliputi:

1. **Bukti Kutipan Terpotong & Klaim Deskripsi Tidak Terdukung (`incomplete_evidence_span`: 42 kasus, `unsupported_claim_in_description`: 26 kasus, `header_only_evidence`: 4 kasus):**
   - Fungsi `_find_span` pada Stage 4.0 hanya mengambil 1 kalimat atau judul sub-bab pendek sebagai anchor, sementara `requirement_description` merangkum seluruh blok aturan (misalnya `REQ-DOC024-BU02-007` mengklaim 9 elemen BMC tetapi `evidence_text` hanya memuat 1 elemen; `REQ-DOC024-BU01-011` mengklaim 4 bobot rubrik 15%/40%/35%/10% tetapi `evidence_text` hanya memuat kalimat pengantar tanpa tabel).
2. **Pencampuran Informasi Tidak Tercantum (`NOT_STATED`) ke dalam Daftar Persyaratan Aktif (`not_stated_stored_as_requirement_record`: 11 kasus, `not_stated_status_conflation`: 4 kasus):**
   - Sebanyak 11 record yang tidak dinyatakan di dokumen (seperti `age_limit` pada seluruh 8 unit cabang) disimpan langsung di dalam array `requirements` dengan `evidence_text` yang mengutip kalimat syarat pendidikan/KTM yang sebenarnya tidak membahas usia. Selain itu, 4 record kriteria penilaian `DOC-009` yang nyata diberi status `validation_status="NOT_STATED"` hanya karena tabelnya tidak mencantumkan kolom bobot `%`.
3. **Penggabungan Berlebih (`compound_requirement_merging`: 19 kasus) & Granularitas Tidak Konsisten:**
   - Pada `DOC-001`, kriteria penilaian dipecah per aspek (4 record), namun pada `DOC-024` dan `DOC-009` seluruh tabel kriteria penilaian penyisihan dan final digabung ke dalam 1 record per unit. Pendaftaran 2 tahap pada `DOC-001` serta paket berkas pengumpulan pada `DOC-024` dan `DOC-009` juga digabung berlebihan.
4. **False Positive Narasi Latar Belakang sebagai Persyaratan (`false_positive_non_requirement`: 1 kasus):**
   - `REQ-DOC009-BU01-013` memasukkan narasi sejarah program tahunan Pharmacopeia dan statistik kematian PTM WHO 74% ke dalam kategori `competition_structure`.
5. **Kesalahan Klasifikasi Kategori (`category_misclassification`: 2 kasus) & Catatan Audit sebagai Aturan Resmi (`audit_note_stored_as_official_rule`: 1 kasus):**
   - `REQ-DOC024-BU03-008` menempatkan spesifikasi teknis resolusi dan format file poster (`JPG/PNG, 300 ppi, A4, RGB`) ke dalam `deliverables` alih-alih `technical_and_general_rules`.
   - `REQ-DOC009-BU01-006` menyimpan temuan audit pemotongan segmen Stage 3 sebagai persyaratan `competition_structure`.
6. **Anomali Sumber & Kerusakan OCR yang Tidak Ditandai (`missed_source_contradiction`, `unflagged_source_typo`, `unflagged_ocr_noise_in_evidence`):**
   - Kontradiksi jadwal internal `DOC-001` (Nov–Des 2026 vs Jan–Feb 2027), salah ketik salin-tempel `DOC-024` halaman 23 (Mekanisme Pendaftaran Poster yang menyalin syarat KTM, cek plagiasi, dan file esai PDF), distorsi OCR nominal biaya `DOC-009` (`Ro70.001,-`, `Rop85.001,-`), serta blok ketentuan teknis halaman 14 bawah `DOC-009` yang rusak berat akibat OCR belum dipisahkan ke entitas review.
7. **Tujuh Kelompok False Negative (`FN-001` s.d. `FN-007`):**
   - `DOC-001`: Program Coaching Terstruktur (Bagian 7) dan syarat *Verified Participant* (Bagian 10).
   - `DOC-024`: Aturan pengiriman >1 karya & biaya *non-refundable*, daftar subtema spesifik per cabang (Esai 7 subtema, BMC 6 subtema, Poster 6 subtema), serta hak cipta & wewenang publikasi karya poster.
   - `DOC-009`: Kuota delegasi sekolah & larangan lintas cabang (kecuali *Video Campaign*), serta aturan Babak Final Luring (karantina wajib, *dress code* kemeja/celana panjang, larangan atribut/logo sekolah, kewajiban menghadiri Seminar Nasional, dan ketiadaan akomodasi).

---

## 2. Perbaikan yang Dilakukan pada Stage 4.2

Arsitektur paket `src/requirement_extraction/` telah direfaktor menjadi tiga modul terpisah dengan tanggung jawab yang tegas:

1. **`src/requirement_extraction/rules.py` (Aturan Klasifikasi, Filter, Normalisasi, dan Verifikasi Grounding):**
   - **Detektor False Positive Latar Belakang (`is_non_requirement_background`):** Memblokir narasi latar belakang acara dan statistik epidemiologi (seperti statistik WHO 74% kematian PTM pada `DOC-009`) apabila teks tidak memuat penanda kewajiban/aturan peserta.
   - **Klasifikator Klausul Deterministik (`classify_requirement_clause`):** Memetakan setiap klausul ke pasangan `(requirement_category, requirement_subcategory, statement_nature)` dengan *negative guard* yang mencegah spesifikasi teknis format/resolusi berkas (`JPG/PNG, 300 ppi, A4, RGB`) salah masuk ke `deliverables`.
   - **Ekstraktor Pengecualian & Kondisi (`extract_exception_or_condition`):** Mengekstrak klausa pengecualian dan syarat tambahan secara otomatis (`kecuali...`, `tidak termasuk...`, `meskipun tidak dihadiri...`, `without a working demo...`, `individual entries are not accepted`).
   - **Normalisasi Istilah Aktif (`apply_term_normalization`):** Mengaktifkan kamus `TERM_NORMALIZATION_RULES` pada setiap record sehingga menghasilkan daftar istilah ternormalisasi (`normalized_terms`).
   - **Verifikator Grounding Otomatis (`verify_description_grounded_in_evidence`):** Memeriksa secara programatik bahwa setiap angka, persentase (`%`), nominal mata uang (`Rp`), dan URL di dalam `requirement_description` benar-benar muncul di dalam `evidence_text`. Ekstraktor akan menolak (*raise `ValueError`*) setiap record yang deskripsinya melebihi bukti kutipan.

2. **`src/requirement_extraction/extractor.py` (Mesin Ekstraksi dengan Pemisahan 4 Entitas & Granularitas Atomik):**
   - Menindaklanjuti seluruh **59 record bermasalah** dan menambahkan seluruh **7 kelompok False Negative**.
   - Memperluas rentang `evidence_text` agar mencakup seluruh kalimat/butir persyaratan utuh (termasuk persyaratan multi-kalimat dan tabel penuh).
   - Menyeragamkan granularitas `assessment_criteria` menjadi **1 record per aspek penilaian / babak** di seluruh dokumen (`DOC-001`: 4 record; `DOC-024`: 4 + 6 + 6 = 16 record; `DOC-009`: 6 + 4 + 5 + 5 = 20 record; total **40 record kriteria penilaian**).

3. **`src/requirement_extraction/evaluator.py` (Mesin Evaluasi Kualitas terhadap Ground Truth Manual):**
   - Membangun dataset anotasi manual (*ground truth*) untuk ketiga dokumen (`147` persyaratan *ground truth*) dan menghitung **Precision**, **Recall**, serta **F1-score** per kategori, per dokumen, dan secara keseluruhan (*micro* & *macro*) untuk membandingkan Stage 4.0 Baseline dan Stage 4.2 Refined.

---

## 3. Perubahan Struktur Data (Model 4 Entitas Terpisah)

Pada `data/processed/competition_requirements.json` (Schema Version `4.2`), informasi hasil ekstraksi dipisahkan secara eksplisit menjadi **4 entitas**:

| Entitas | Key JSON | Dataclass | Jumlah Record (Stage 4.2) | Definisi & Aturan Penyimpanan |
| :--- | :--- | :--- | :---: | :--- |
| **1. Requirement** | `requirements` | `ExtractedRequirementRecord` | **145** | Persyaratan dan ketentuan kompetisi yang benar-benar dinyatakan di dokumen sumber. Memiliki kutipan `evidence_text` utuh, rentang karakter presisi, `requirement_subcategory`, `exception_or_condition`, `related_requirement_ids`, dan `normalized_terms`. |
| **2. Information** | `information_items` | `SupportingInformationRecord` | **3** | Informasi pendukung/kontekstual kompetisi yang bukan syarat mengikat peserta (`INFO-DOC001-BU01-001` struktur prize pool berdasarkan kuota, `INFO-DOC024-BU01-001` info e-sertifikat & pengumuman IG, `INFO-DOC009-BU01-001` latar belakang Pharmacopeia & statistik WHO 74%). |
| **3. Extraction Gap** | `extraction_gaps` | `ExtractionGapRecord` | **14** | Kategori atau atribut persyaratan standar yang telah dicari pada bagian terkait namun **tidak tercantum** di dokumen (`NOT_STATED`), seperti `age_limit` pada 8 unit cabang dan `rubric_aspect_percentage_weights` pada 3 unit cabang `DOC-009`. Tidak pernah disimpan di dalam `requirements`. |
| **4. Review Item** | `review_items` | `ReviewItemRecord` | **11** | Anomali sumber yang wajib diperiksa manusia (`NEEDS_REVIEW`), meliputi placeholder `[TBC]`, kontradiksi jadwal/aturan internal, salah ketik salin-tempel lintas cabang pada `DOC-024`, pemotongan batas segmen `DOC-009`, serta 2 blok teks `DOC-009` yang rusak berat akibat OCR (`REV-DOC009-BU01-003` halaman 14 bawah dan `REV-DOC009-BU03-001` halaman 39 bawah). |

### Taksonomi `requirement_subcategory` (24 Subkategori di Bawah 6 Kategori Utama)
Seluruh 6 kategori utama dipertahankan dan diperkaya dengan `requirement_subcategory` berbasis temuan dokumen:
- **`eligibility_requirements` (25 record):** `education_level_and_student_status` (8), `participation_mode_and_team_size` (7), `single_team_or_cross_branch_restriction` (5), `team_composition_and_institution_rule` (3), `student_identity_document` (1), `school_delegation_quota` (1).
- **`registration_requirements` (20 record):** `registration_fee_and_payment` (10), `registration_mechanism_and_portal` (6), `administrative_and_twibbon_requirements` (3), `participant_verification_rule` (1).
- **`competition_structure` (28 record):** `competition_stages_and_selection` (9), `competition_timeline_and_deadlines` (8), `competition_tracks_and_themes` (7), `final_stage_offline_protocol` (3), `coaching_and_mentoring_program` (1).
- **`deliverables` (14 record):** `proposal_or_essay_deliverable` (3), `presentation_slide_deliverable` (3), `prototype_or_exam_deliverable` (2), `poster_deliverable` (2), `deliverable_template_or_example` (2), `bmc_deliverable` (1), `video_deliverable` (1).
- **`assessment_criteria` (40 record):** `judging_criterion_weighted` (20), `judging_criterion_unweighted` (16), `exam_point_scoring_formula` (4).
- **`technical_and_general_rules` (18 record):** `content_and_tool_prohibition` (5), `document_formatting_and_length` (4), `media_and_file_specification` (4), `exam_proctoring_and_device_rules` (2), `originality_and_plagiarism_threshold` (1), `copyright_and_publication_rights` (1), `disqualification_and_sanction_rules` (1).

---

## 4. Perbandingan Hasil Sebelum dan Sesudah Perbaikan (Stage 4.0 vs Stage 4.2)

File keluaran Stage 4.0 disimpan utuh pada `data/processed/competition_requirements_stage4_0_baseline.json` dan `data/processed/competition_requirements_stage4_0_baseline.csv` untuk perbandingan langsung:

| Indikator Kualitas & Struktur | Stage 4.0 Baseline | Stage 4.2 Refined | Perubahan / Dampak |
| :--- | :---: | :---: | :--- |
| Total Record di `requirements` | 98 | **145** | +47 record atomik (pemecahan rubrik & penambahan 7 kelompok FN) |
| Record `NOT_STATED` Tercampur di `requirements` | 11 | **0** | Dipindahkan seluruhnya ke `extraction_gaps` (14 gap) |
| False Positive Latar Belakang di `requirements` | 1 | **0** | Dipindahkan ke `information_items` (`INFO-DOC009-BU01-001`) |
| Kesalahan Klasifikasi Kategori (`WRONG_CATEGORY`) | 2 | **0** | Diperbaiki dengan *negative guard* pada `classify_requirement_clause` |
| Record dengan Klaim Deskripsi Tidak Terdukung Bukti | 38 | **0** | 100% lulus verifikasi `verify_description_grounded_in_evidence` |
| Record dengan Pengecualian/Kondisi Eksplisit | 0 (tidak diekstrak) | **17** | Diekstrak di field `exception_or_condition` |
| Record dengan Relasi Antar-Persyaratan | 0 (tidak ditautkan) | **42** | Ditautkan melalui `related_requirement_ids` |
| Record dengan Istilah Ternormalisasi | 0 (aturan pasif) | **28** | Diaktifkan melalui `apply_term_normalization` |
| Entitas `information_items` | 0 | **3** | Konteks hadiah, e-sertifikat, dan latar belakang acara |
| Entitas `extraction_gaps` | 0 | **14** | 8 gap `age_limit`, 3 gap bobot rubrik, 3 gap teknis/institusi |
| Entitas `review_items` | 0 | **11** | Kontradiksi jadwal/aturan, salah ketik salin-tempel, & blok OCR rusak |

---

## 5. Hasil Evaluasi Kualitas Ekstraksi (Precision, Recall, dan F1-Score)

> **Catatan Ruang Lingkup (Disclaimer):** Seluruh metrik evaluasi di bawah ini dihitung secara ketat terhadap dataset *ground truth* manual untuk **3 dokumen representatif (`DOC-001`, `DOC-024`, `DOC-009` — 8 unit cabang, 147 persyaratan *ground truth*)** yang disimpan pada `data/processed/requirement_extraction_evaluation.json`. **Metrik ini TIDAK mewakili performa pada seluruh korpus 76 dokumen.**

Evaluasi dilakukan dengan dua skema pencocokan terhadap 147 persyaratan *ground truth*:
1. **Strict Grounded Atomic Evaluation (Utama):** Mengharuskan kesesuaian unit cabang, kesesuaian kategori, granularitas atomik (1 aspek rubrik = 1 record), serta 100% dukungan `evidence_text` terhadap klaim di `requirement_description` (record Stage 4.0 yang berstatus `ISSUE_FOUND` karena bukti terpotong, penggabungan rubrik, `NOT_STATED`, atau salah kategori dihitung sebagai *False Positive*).
2. **Relaxed Span/Topic Overlap Evaluation (Diagnostik Sekunder):** Memberikan kredit kecocokan topik/rentang meskipun pada Stage 4.0 bukti kutipannya terpotong atau tabel rubriknya digabung, dan hanya menghukum record `NOT_STATED`, *false positive* latar belakang, serta kesalahan kategori sebagai *False Positive*.

### 5.1 Tabel Perbandingan Per Kategori (Stage 4.0 vs Stage 4.2)

| Kategori Persyaratan | GT | Stage 4.0 Strict P / R / F1 | Stage 4.0 Relaxed P / R / F1 | Stage 4.2 Refined TP / FP / FN | Stage 4.2 Precision | Stage 4.2 Recall | Stage 4.2 F1-Score | $\Delta$ F1 (Strict) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `eligibility_requirements` | 25 | 0.2857 / 0.2400 / **0.2609** | 0.7353 / 1.0000 / **0.8475** | 25 / 0 / 0 | **1.0000** | **1.0000** | **1.0000** | +0.7391 |
| `registration_requirements` | 20 | 0.4286 / 0.3000 / **0.3529** | 1.0000 / 0.9500 / **0.9744** | 20 / 0 / 0 | **1.0000** | **1.0000** | **1.0000** | +0.6471 |
| `competition_structure` | 28 | 0.0909 / 0.0357 / **0.0513** | 0.9500 / 0.6786 / **0.7917** | 28 / 0 / 0 | **1.0000** | **1.0000** | **1.0000** | +0.9487 |
| `deliverables` | 14 | 0.3571 / 0.3571 / **0.3571** | 0.8667 / 0.9286 / **0.8966** | 14 / 0 / 0 | **1.0000** | **1.0000** | **1.0000** | +0.6429 |
| `assessment_criteria` | 40 | 0.7200 / 0.4500 / **0.5538** | 1.0000 / 0.9500 / **0.9744** | 40 / 0 / 0 | **1.0000** | **1.0000** | **1.0000** | +0.4462 |
| `technical_and_general_rules` | 20 | 0.1538 / 0.1000 / **0.1212** | 0.8889 / 0.8000 / **0.8421** | 18 / 0 / 2 | **1.0000** | **0.9000** | **0.9474** | +0.8262 |
| **Total Keseluruhan (Micro)** | **147** | 0.3878 / 0.2585 / **0.3102** | 0.9028 / 0.8844 / **0.8935** | **145 / 0 / 2** | **1.0000** | **0.9864** | **0.9932** | **+0.6830** |
| **Rata-rata Kategori (Macro)** | **147** | — | — | — | **1.0000** | **0.9833** | **0.9912** | — |

### 5.2 Ringkasan Evaluasi Per Dokumen (Stage 4.2 Refined)

| ID Dokumen | Nama Kompetisi | Jumlah Unit | Ground Truth | TP | FP | FN | Precision | Recall | F1-Score |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `DOC-001` | AI Builder Challenge 2026 | 1 | 20 | 20 | 0 | 0 | **1.0000** | **1.0000** | **1.0000** |
| `DOC-024` | Impacteers UNESA 2025 (Esai, BMC, Poster) | 3 | 56 | 56 | 0 | 0 | **1.0000** | **1.0000** | **1.0000** |
| `DOC-009` | Pharmacopeia 2026 (Essay, Olympiad, Poster, Video) | 4 | 71 | 69 | 0 | 2 | **1.0000** | **0.9718** | **0.9857** |
| **Total 3 Dokumen** | **8 Cabang Perlombaan** | **8** | **147** | **145** | **0** | **2** | **1.0000** | **0.9864** | **0.9932** |

### 5.3 Penjelasan atas 2 False Negative pada `DOC-009` (`technical_and_general_rules`)
Kedua *False Negative* pada Stage 4.2 berasal dari blok teks persyaratan buku panduan asli `DOC-009` yang **rusak berat akibat OCR** di dalam file `data/raw/txt/DOC-009_Guideline Pharmacopeia 2026.txt`:
1. **`GT-DOC009BU01-021` (`DOC-009-BU-01`, halaman 14 bawah, karakter `12983..13328`):** Memuat ketentuan teknis tipografi/margin naskah esai yang terdistorsi menjadi `'Pick Aha Mh Sh tt hAT teP... font€:, > See s eae Po eta rae. vg. 7 wt ii /herer'`. Agar tidak mengarang spesifikasi ukuran font atau margin di dalam `requirements`, Stage 4.2 mengalihkan blok ini ke `review_items` (`REV-DOC009-BU01-003`).
2. **`GT-DOC009BU03-018` (`DOC-009-BU-03`, halaman 39 bawah, karakter `35122..35486`):** Memuat ketentuan tambahan pasca-butir 7 publikasi Instagram yang terdistorsi menjadi `'TOPE T HOO TET ET ET TESST...'`. Dialihkan secara jujur ke `review_items` (`REV-DOC009-BU03-001`).

---

## 6. Hasil Pengujian Otomatis (`pytest`)

Rangkaian pengujian pada `tests/test_requirement_extraction.py` telah diperluas untuk menguji integritas struktural sekaligus **9 skenario semantik dan regresi** menggunakan contoh nyata dari `DOC-001`, `DOC-024`, dan `DOC-009`:
1. `test_1_false_positive_filtering_with_real_doc009_example`: Memastikan narasi latar belakang Pharmacopeia & statistik WHO 74% terdeteksi oleh `is_non_requirement_background` dan disimpan di `information_items` (`INFO-DOC009-BU01-001`), bukan di `requirements`.
2. `test_2_known_false_negatives_resolved_across_doc001_doc024_doc009`: Memverifikasi keberadaan seluruh 7 kelompok False Negative hasil audit Stage 4.1.
3. `test_3_category_classification_accuracy_with_real_doc024_poster_specs`: Memastikan spesifikasi format/resolusi poster (`JPG/PNG, 300 ppi, A4, RGB`) diklasifikasikan ke `technical_and_general_rules` (`media_and_file_specification`), bukan `deliverables`.
4. `test_4_multi_sentence_requirements_preserved_intact`: Memastikan persyaratan multi-kalimat (seperti *Live demo requirement* 3 kalimat pada `DOC-001`, 6 bagian struktur esai pada `DOC-024`, dan 3 berkas pengumpulan pada `DOC-009`) utuh tanpa pemotongan kalimat.
5. `test_5_requirements_with_exceptions_and_conditions`: Memastikan klausa pengecualian (seperti `kecuali Video Campaign Competition...`, `Without a working demo...`, dan `tidak termasuk cover...`) terekstrak pada field `exception_or_condition`.
6. `test_6_interrelated_requirements_and_review_linkage`: Memastikan seluruh `related_requirement_ids` merujuk ke ID yang valid di `requirements` atau `review_items`.
7. `test_7_description_to_evidence_grounding_verification`: Memastikan 100% dari 145 record di `requirements` lulus verifikasi `verify_description_grounded_in_evidence` serta menguji penolakan atas klaim angka/persentase/nominal/URL yang tidak ada di `evidence_text`.
8. `test_8_missing_information_handled_in_extraction_gaps_only`: Memastikan `requirements` bebas dari record `NOT_STATED` dan seluruh 14 atribut yang tidak tercantum disimpan di `extraction_gaps`.
9. `test_9_idempotent_rerun_and_quality_evaluation_metrics`: Memastikan eksekusi ulang menghasilkan output yang 100% identik (*idempotent*) dan memvalidasi hasil evaluasi pada `requirement_extraction_evaluation.json`.

Seluruh suite pengujian proyek (**51 test** di seluruh `tests/`, termasuk 13 test pada `test_requirement_extraction.py`) lulus 100% (`51 passed`).

---

## 7. Keterbatasan yang Masih Tersisa & Rekomendasi Status

### 7.1 Keterbatasan Teknis Saat Ini
1. **Jenis Persyaratan yang Sulit Diekstrak Secara Otomatis:**
   - Tabel jadwal dan matriks rubrik multi-kolom yang kehilangan struktur kolom saat dikonversi dari PDF ke TXT (terutama ketika sel multi-baris terpecah oleh spasi/baris baru seperti pada tabel kriteria penilaian `DOC-009`).
   - Ketentuan yang tersebar lintas bagian dokumen (misalnya aturan umum di awal dokumen atau lampiran mekanisme pendaftaran bersama di akhir dokumen seperti rentang `46547..48658` pada `DOC-009`).
2. **Pola Bahasa dan Anomali Sumber yang Belum Tertangani Secara Generik Lintas-Korpus:**
   - Salah ketik salin-tempel antar-cabang oleh penulis buku panduan (seperti halaman 23 `DOC-024` Cabang Poster yang menyalin kata `'Dokumen esai'`, `'KTM'`, `'bukti cek plagiasi'`, dan `'Karya BMC'`). Saat ini anomali tersebut ditangani melalui pemeriksaan aturan dan pencatatan di `review_items`, namun untuk 73 dokumen lainnya diperlukan detektor ketidakcocokan kata kunci cabang secara otomatis.
3. **Ketergantungan terhadap Kualitas OCR:**
   - Apabila hasil konversi TXT mengalami kerusakan karakter parah (seperti bagian bawah halaman 14 dan halaman 39 pada `DOC-009`), ekstraktor berbasis TXT tidak dapat memulihkan nilai ukuran font, margin, atau aturan tambahan tanpa berisiko mengarang informasi.
4. **Kategori yang Paling Membutuhkan Validasi Manual:**
   - `competition_structure` (subkategori `competition_timeline_and_deadlines` ketika terdapat inkonsistensi tanggal antar-bab seperti pada `DOC-001` atau pemotongan header OCR seperti pada `DOC-009`).
   - `registration_requirements` (ketika nominal biaya mengalami distorsi OCR seperti `Ro70.001,-` atau tautan pendaftaran masih berupa placeholder `[TBC]`).
   - `technical_and_general_rules` (ketika terdapat kontradiksi aturan penulisan individu vs kelompok atau kerusakan OCR pada spesifikasi format).
5. **Risiko Kesalahan jika Diterapkan ke Seluruh 76 Dokumen Saat Ini:**
   - Ekstraktor Stage 4.2 memadukan aturan klasifikasi/verifikasi generik (`rules.py`) dengan pemetaan anchor terkurasi untuk ketiga dokumen representatif (`DOC-001`, `DOC-024`, `DOC-009`). Apabila langsung dijalankan pada 73 dokumen lainnya yang memiliki variasi format penomoran (seperti pedoman FIKSI, LKS, OSN, dan PKM) tanpa *section/clause parser* generik yang telah dikalibrasi, recall pada dokumen di luar 3 dokumen uji akan rendah.

### 7.2 Rekomendasi Status Akhir
- **Status Rekomendasi:** **`NEEDS_MORE_REFINEMENT`**
- **Alasan Ilmiah & Rekayasa:**
  Meskipun pada ketiga dokumen representatif (`DOC-001`, `DOC-024`, `DOC-009`) Stage 4.2 telah mencapai **Precision 1.0000, Recall 0.9864, dan F1-score 0.9932** serta menuntaskan 100% temuan audit Stage 4.1, fondasi ekstraksi belum boleh langsung diklaim siap untuk ekspansi buta ke seluruh 76 dokumen (`READY_FOR_CORPUS_EXPANSION`) sebelum dua langkah lanjutan diselesaikan pada iterasi berikutnya:
  1. Mengembangkan dan menguji **pemisah klausa/bagian generik (*generic section-and-clause segmenter*)** yang menerapkan fungsi-fungsi pada `src/requirement_extraction/rules.py` secara otomatis pada dokumen baru tanpa memerlukan daftar anchor per dokumen, lalu mengujinya pada sampel 5–10 dokumen tambahan (misalnya FIKSI, LKS, OSN).
  2. Menyelesaikan perbaikan batas segmen Stage 3 (`DOC-009`, `DOC-047`, `DOC-015`, `DOC-008`) agar ekstraktor tidak perlu melakukan *shared-span fallback* di luar rentang unit cabang.
