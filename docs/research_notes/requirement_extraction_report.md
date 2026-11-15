# Laporan Penelitian Stage 4 (Tahap Awal): Rule-Based Requirement Extraction Baseline

**Proyek:** AI Competition Mentor (V0.1 Foundation)  
**Tahap:** Stage 4 Initial Baseline — Ekstraksi Persyaratan pada 3 Dokumen Representatif  
**Sumber Data (Read-Only):**
- `data/processed/segmentation_validation.json` (Audit Semantik Stage 3)
- `data/processed/competition_branch_units.json` (114 Unit Cabang Stage 3)
- `data/processed/document_inventory_validated.json` (Inventarisasi Tervalidasi Stage 2)
- `data/raw/txt/` (`DOC-001`, `DOC-024`, `DOC-009`)

**Artefak Output Stage 4:**
- `src/requirement_extraction/extractor.py`
- `scripts/run_requirement_extraction.py`
- `data/processed/competition_requirements.json`
- `data/processed/competition_requirements.csv`
- `tests/test_requirement_extraction.py`

---

## 1. Ringkasan Eksekutif

Tahap awal Stage 4 ini membangun **baseline ekstraksi persyaratan berbasis aturan (rule-based, deterministik, tanpa ML/LLM)** pada **3 dokumen representatif (8 `CompetitionBranchUnit`)** yang dipilih berdasarkan status validasi pada `data/processed/segmentation_validation.json`. Seluruh hasil ekstraksi tertaut langsung ke rentang karakter (`source_char_start..source_char_end`), nomor halaman (`source_page`), dan kutipan bukti tekstual verbatim (`evidence_text`).

### Statistik Hasil Ekstraksi Baseline (Total: 98 Record Persyaratan)

| Dimensi Statistik | Rincian Jumlah |
| :--- | :--- |
| **Dokumen Representatif Diproses** | **3 Dokumen** (`DOC-001`, `DOC-024`, `DOC-009`) |
| **Unit Cabang (`CompetitionBranchUnit`)** | **8 Unit** (`DOC-001-BU-01`, `DOC-024-BU-01..03`, `DOC-009-BU-01..04`) |
| **Total Record Persyaratan** | **98 Record** |
| **Distribusi per Kategori (`requirement_category`)** | `assessment_criteria`: **25** \| `eligibility_requirements`: **21** \| `registration_requirements`: **14** \| `deliverables`: **14** \| `technical_and_general_rules`: **13** \| `competition_structure`: **11** |
| **Distribusi per Status Validasi (`validation_status`)** | `VALIDATED`: **72** \| `NOT_STATED`: **15** \| `NEEDS_REVIEW`: **6** \| `VALIDATED_WITH_SEGMENTATION_LIMITATION`: **5** |
| **Distribusi Tipe Bukti (`evidence_type`)** | `explicit`: **97** \| `inferred`: **1** (deteksi inkonsistensi jadwal lintas bab pada `DOC-001`) |
| **Distribusi Sifat Pernyataan (`statement_nature`)** | `official_rule`: **94** \| `template`: **1** \| `example`: **1** \| `recommendation`: **1** \| `historical_or_background_info`: **1** |
| **Cakupan terhadap Batas Unit Stage 3** | **92 record** berada di dalam rentang ketat `unit.start_char..unit.end_char`; **6 record** dipulihkan secara terkontrol dari rentang tidak tercakup `DOC-009` (`0..3050`, `3050..3135`, dan `46547..48658`) yang telah teridentifikasi pada `segmentation_validation.json`. |

---

## 2. Pemilihan 3 Dokumen Representatif Berdasarkan `segmentation_validation.json`

Sesuai prinsip metodologis untuk tidak menganggap seluruh unit telah tervalidasi sempurna, pemilihan 3 dokumen didasarkan langsung pada hasil audit `segmentation_validation.json`:

| Slot Representatif | `document_id` & Nama File | Unit Cabang (`branch_unit_id`) | Status di `segmentation_validation.json` | Kondisi Teks & Alasan Pemilihan |
| :--- | :--- | :--- | :---: | :--- |
| **1. `single_branch`** | **`DOC-001`**<br>`AI Builder Challenge 2026 – Participant Guidebook.txt` | `DOC-001-BU-01` (`BR_AI`, `0..11367`) | `VALIDATED` | Teks `readable` berbahasa Inggris yang sangat terstruktur; mencakup 6 kategori persyaratan secara eksplisit (termasuk bobot penilaian `25% x 4`), namun memiliki placeholder `[TBC]` dan perbedaan jadwal antara Bagian 5 (Jan–Feb 2027) dan Bagian 6 (Nov–Des 2026) yang menguji deteksi `NEEDS_REVIEW`. |
| **2. `multi_branch_event`** | **`DOC-024`**<br>`GUIDEBOOK IMPACTEERS UNIVERSITAS NEGERI SURABAYA.txt` | `DOC-024-BU-01` (`BR_ESSAY`, `4122..10785`)<br>`DOC-024-BU-02` (`BR_BMC`, `10785..17612`)<br>`DOC-024-BU-03` (`BR_POSTER_DESIGN`, `17612..24733`) | `VALIDATED` (ketiga unit) | Dokumen `multi_branch_event` dengan 3 unit cabang mandiri. Menguji isolasi lintas cabang: Esai & BMC diperuntukkan bagi Mahasiswa (individu/tim 2 orang) dengan struktur babak dan bobot rubrik berbeda, sedangkan Poster diperuntukkan bagi Individu (kategori Mahasiswa & Siswa SMA/Sederajat). |
| **3. Keterbatasan Teks / Segmentasi** | **`DOC-009`**<br>`Booklet SMA_K Sederajat_Pharmacopeia 2026.txt` | `DOC-009-BU-01` (`BR_ESSAY`, `3135..15328`)<br>`DOC-009-BU-02` (`BR_SCIENCE_OLYMPIAD`, `15403..24614`)<br>`DOC-009-BU-03` (`BR_POSTER_DESIGN`, `24640..37583`)<br>`DOC-009-BU-04` (`BR_VIDEO_FILM_PHOTO`, `37584..46547`) | `BU-01`: `NEEDS_REVISION`<br>`BU-02..04`: `VALIDATED_WITH_LIMITATION` | Memiliki keterbatasan ganda: (1) Kualitas teks `readable_with_ocr_noise` (judul `"LOMDaCork Es"`, blok tipografi halaman 14 rusak parah `"Pick Aha Mh Sh..."`, distorsi angka biaya `"Ro70.001,-"`); (2) Keterbatasan segmentasi di mana Pendaftaran Gelombang 1 Esai terpotong di `3050..3135` dan Alur/Biaya Pendaftaran 4 cabang berada di ekor dokumen `46547..48658`; serta (3) Tabel kriteria penilaian Esai, Poster, dan Video tidak mencantumkan bobot (`indicator_weight = NOT_STATED`). |

---

## 3. Prinsip Integritas Data dan Aturan Normalisasi Istilah

1. **Verifikasi Bukti Teks (`evidence_text`) & Indeks Karakter Presisi:**
   - Setiap record memenuhi `raw_text[source_char_start:source_char_end] == evidence_text`.
2. **Penanganan Informasi Tidak Tercantum (`NOT_STATED`) Tanpa Asumsi:**
   - Apabila suatu atribut standar tidak disebutkan di dokumen (misalnya `age_limit` pada `DOC-001`, `DOC-024`, dan `DOC-009`; atau `proposal_page_limit_and_file_format` dan `standalone_source_code_repository_submission` pada `DOC-001`), field `requirement_description` dan `validation_status` diisi **`NOT_STATED`** dengan mengutip bagian teks tempat ketiadaan informasi tersebut diverifikasi.
   - Pada `DOC-009-BU-01` (Esai), `DOC-009-BU-03` (Poster), dan `DOC-009-BU-04` (Video Campaign), dokumen mencantumkan aspek dan uraian penilaian tetapi **tidak mencantumkan bobot persentase**. Sesuai prinsip ke-3 (*"Jangan mengisi bobot penilaian jika dokumen tidak menyebutkannya"*), `indicator_weight` diisi **`NOT_STATED`**.
3. **Pembedaan Sifat Pernyataan (`statement_nature`):**
   - `official_rule` (94 record): Aturan resmi yang mengikat peserta.
   - `recommendation` (1 record): Anjuran non-mutlak, contoh pada `DOC-009-BU-02`: *"Dimana 1 device (diusahakan laptop/komputer) digunakan untuk mengerjakan soal"*.
   - `example` (1 record): Contoh desain tidak mengikat, contoh pada `DOC-024-BU-02`: *"Template dibawah hanya dipergunakan sebagai contoh sehingga peserta bebas mengkreasikan"*.
   - `template` (1 record): Ketentuan format template dokumen, contoh pada `DOC-024-BU-01`: *"Format cover dan lembar orisinalitas peserta dapat diakses melalui link linktr.ee/impacteers2025"*.
   - `historical_or_background_info` (1 record): Informasi historis/epidemiologis di latar belakang (`DOC-009`: *"Pharmacopeia merupakan program tahunan... data WHO menunjukkan pola hidup tidak sehat berkontribusi pada 74% kematian"*).
4. **Aturan Normalisasi Istilah Terdokumentasi (`TERM_NORMALIZATION_RULES`):**
   - `NORM-EDU-01`: Tidak menyamakan *Mahasiswa* dengan *Siswa/Pelajar SMA/K*.
   - `NORM-DOC-01`: Membedakan secara tegas antara *KTM* (Kartu Tanda Mahasiswa), *KTMS* (Kartu Tanda Mahasiswa Sementara), dan *KTP* pada `DOC-024-BU-03` yang di dalam teks tertulis eksplisit sebagai **Kartu Tanda Pelajar (KTP)** (bukan Kartu Tanda Penduduk).
   - `NORM-DELIV-01`: Tidak menyamakan jenis karya (*Written Proposal*, *Naskah Esai*, *BMC 9 Elemen*, *Poster Digital*, *Working AI Prototype*, *Video Campaign*) meskipun sebagian dikumpulkan dalam format berkas `.pdf` yang sama.

---

## 4. Ringkasan Temuan Ekstraksi per Dokumen dan Unit Cabang

### 4.1. `DOC-001` — `DOC-001-BU-01` (*AI Builder Challenge 2026*, 21 Record)
- **Eligibility:** Mahasiswa aktif perguruan tinggi di Indonesia (wajib KTM valid), wajib beregu 3–4 orang (individu ditolak, 1 orang maksimal 1 tim). Batas usia dan pembatasan lintas kampus berstatus `NOT_STATED`.
- **Registration:** Gratis (`no fee for any team`), dua langkah wajib: (1) Ketua tim mengisi Google Form (`[TBC: paste Google Form link]` -> ditandai `NEEDS_REVIEW` karena tautan masih placeholder), dan (2) Setiap anggota bergabung secara individu di laman event Xdemia.
- **Competition Structure & Anomaly (`inferred` / `NEEDS_REVIEW`):** Terdiri dari 2 track (*General Track* & *Industry Case Track ARSA*) dan 5 tahap. Ekstraktor mendeteksi inkonsistensi jadwal internal (`REQ-DOC001-BU01-011`): tabel Bagian 5 mencantumkan Proposal/Semifinal pada Januari 2027 & Grand Final Februari 2027, sedangkan kalimat pengantar Bagian 5 dan rincian Bagian 6 mencantumkan Proposal/Semifinal pada November 2026 & Grand Final Desember 2026.
- **Deliverables & Assessment Criteria:** Wajib mengumpulkan *Written Proposal* dan mendemonstrasikan *Working AI Prototype* secara langsung (*live demo*, 20 menit + Q&A; sekadar slide/mockup/video rekaman didiskualifikasi). Empat kriteria penilaian berbobot eksplisit masing-masing `25%` (*Innovation and Originality*, *Technical Feasibility*, *Impact and Operational Value*, *Presentation and Communication*).

### 4.2. `DOC-024` — `DOC-024-BU-01..03` (*Impacteers UNESA 2025*, 42 Record)
- **Isolasi Persyaratan Antar-Cabang (3 Unit Terpisah):**
  - **`DOC-024-BU-01` (Esai, 14 Record):** Mahasiswa aktif (KTM/KTMS), individu atau tim 2 orang satu universitas; seleksi 1 tahap langsung memilih 6 karya terbaik; panjang 7–10 halaman A4, batas plagiasi Turnitin maks. 30%; 4 kriteria penilaian (`Topik` 15%, `Mutu Gagasan` 40%, `Data & Informasi` 35%, `Format` 10%).
  - **`DOC-024-BU-02` (BMC, 15 Record):** Mahasiswa aktif (KTM/KTMS), individu atau tim 2 orang satu universitas; seleksi **2 tahap** (6 karya terbaik melaju ke Technical Meeting 1 Juni 2025 & Final Online 8 Juni 2025); wajib memuat 9 elemen BMC tanpa batas halaman deskripsi ide bisnis; 6 kriteria penilaian (`Topik` 20%, `Kelengkapan 9 Elemen` 20%, `Inovasi` 20%, `Relevan` 10%, `Kreativitas` 15%, `Potensi Realistis Bisnis` 15%).
  - **`DOC-024-BU-03` (Poster, 13 Record):** Bersifat **Individu** untuk **2 kategori peserta** (*Mahasiswa* dengan KTM & *Pelajar Sekolah/SMA* dengan Kartu Tanda Pelajar); format JPG/JPEG/PNG resolusi min. 300 ppi ukuran A4 portrait RGB; 6 kriteria penilaian (`Kreativitas` 10%, `Kejelasan` 25%, `Kualitas Visual` 30%, `Ketepatan` 20%, `Dampak` 10%, `Kepatuhan` 5%).
  - **Deteksi Anomali Salin-Tempel Dokumen Sumber (`REQ-DOC024-BU03-003` -> `NEEDS_REVIEW`):** Pada halaman 23 (*Mekanisme Pendaftaran Cabang Poster*), panitia menyalin teks dari cabang Esai/BMC (*"Dokumen esai yang diunggah berupa softcopy PDF... judul esai"* dan *"Karya BMC"*), yang bertentangan dengan spesifikasi JPG/JPEG/PNG di halaman 21.

### 4.3. `DOC-009` — `DOC-009-BU-01..04` (*Pharmacopeia 2026*, 35 Record)
- **Penanganan Keterbatasan Segmentasi Berbasis `segmentation_validation.json`:**
  - Pada `DOC-009-BU-01` (Esai), jadwal Pendaftaran Gelombang 1 (`01-07 September 2026`) yang terpotong di `3050..3135` akibat judul OCR `'LOMDaCork Es'` berhasil dipulihkan (`REQ-DOC009-BU01-005`, `within_strict_unit_bounds = False`, `validation_status = NEEDS_REVIEW`).
  - Pada keempat cabang (`BU-01..04`), ketentuan Alur Pendaftaran terpadu dan Biaya Pendaftaran Gelombang 1–3 (`Rp70.001..Rp95.001` untuk Esai, `Rp50.004..Rp70.004` untuk Olimpiade, `Rp75.003..Rp90.003` untuk Poster, `Rp70.002..Rp90.002` untuk Video) berhasil ditautkan dari rentang bersama `46547..48658` (`validation_status = VALIDATED_WITH_SEGMENTATION_LIMITATION` / `NEEDS_REVIEW`).
- **Penanganan Keterbatasan Kualitas Teks OCR (`NEEDS_REVIEW`):**
  - Pada halaman 14 bawah (`DOC-009-BU-01`, char `12625..12722`), aturan tipografi/margin berubah menjadi deretan karakter acak (`"Pick Aha Mh Sh tt hAT teP ia ipet..."`). Ekstraktor menolak mengarang ukuran margin/font dan menandainya sebagai `NEEDS_REVIEW` dengan `confidence_level = "low"`.
- **Perbedaan Karakteristik 4 Cabang Pharmacopeia:**
  - `BU-01` (*Essay*): Tim 3 orang, 5–10 halaman PDF + Turnitin maks. 25%, 5 finalis presentasi PPT luring di Unpad (bobot rubrik `NOT_STATED`).
  - `BU-02` (*Science Olympiad*): Individu, 2 perangkat (Zoom + e-ujian.com), 40 soal PG dalam 45 menit (skoring eksplisit `+4 / -1 / 0`), 5 finalis melaju ke 3 babak final luring.
  - `BU-03` (*Digital Poster*): Tim 3 orang, poster infografis A3 portrait `.pdf`, **dilarang menggunakan AI maupun template siap pakai**, 5 finalis presentasi luring tanpa wajib PPT (bobot rubrik `NOT_STATED`).
  - `BU-04` (*Video Campaign*): Tim 2–3 orang, 1 babak online (tanpa final luring, sehingga peserta boleh merangkap 1 cabang lain), video `.mp4` portrait 9:16 durasi 1–3 menit (boleh menggunakan Filmora/CapCut, bobot rubrik `NOT_STATED`).

---

## 5. Keterbatasan Hasil Ekstraksi Baseline dan Rekomendasi Tahap Selanjutnya

1. **Keterbatasan Cakupan Korpus Saat Ini:**
   - Sesuai desain bertahap Stage 4, ekstraksi baru mencakup 3 dokumen representatif (8 dari 114 unit cabang). Sebelum diperluas ke 73 dokumen kompetisi lainnya, 11 unit berstatus `NEEDS_REVISION` pada Stage 3 (terutama sub-segmentasi 11 bidang FIKSI, 37 bidang LKS, penggabungan tahapan komposit `DOC-061`, dan pergeseran `start_char` `DOC-009-BU-01`) perlu diterapkan terlebih dahulu.
2. **Keterbatasan Teks Akibat Kerusakan OCR Berat pada Bagian Tertentu:**
   - Pada dokumen dengan status `readable_with_ocr_noise` seperti `DOC-009` (halaman 14, 39, dan 49 bagian bawah), informasi spasi/margin/font yang tercetak di atas latar grafis berubah menjadi karakter noise. Ekstraktor berbasis aturan maupun AI tidak boleh menebak angka yang hilang; solusinya adalah OCR ulang terfokus pada halaman tersebut dari PDF asli.
3. **Keterbatasan Pemisahan Tabel Multi-Kolom Hasil Konversi TXT:**
   - Pada beberapa tabel penilaian (`DOC-024` dan `DOC-009`), urutan baris teks hasil ekstraksi PDF mengalami penyisipan kolom (interleaving) antara nomor urut, nama aspek, uraian indikator, dan angka persentase bobot. Baseline aturan saat ini menangani hal tersebut dengan pencocokan rentang blok tabel utuh dan validasi jumlah total bobot (`100%`).
