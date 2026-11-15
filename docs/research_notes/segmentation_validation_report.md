# Laporan Audit Validasi Semantik dan Metodologi Stage 3: Document Segmentation

**Proyek:** AI Competition Mentor (V0.1 Foundation)  
**Tahap Audit:** Audit Validasi Stage 3 (`Document Segmentation`)  
**Sumber Data yang Diaudit (Read-Only):**
- `data/processed/competition_branch_units.json` & `data/processed/competition_branch_units.csv` (114 unit cabang dari 76 dokumen kompetisi + 4 dokumen dieksklusi)
- `data/processed/document_inventory_validated.json` (80 dokumen tervalidasi Stage 2)
- `knowledge_base/competition_requirements/competition_taxonomy.json` (Taksonomi 28 cabang dalam 9 domain)
- `data/raw/txt/*.txt` (80 dokumen teks mentah hasil konversi PDF/OCR)
- `docs/research_notes/document_segmentation_report.md`

**Artefak Hasil Audit:**
- `data/processed/segmentation_validation.json`
- `data/processed/segmentation_validation.csv`
- `src/document_processing/segmentation_validator.py`

---

## 1. Ringkasan Eksekutif

Audit ini mengevaluasi validitas **semantik** dan **metodologi pemotongan struktural** pada 114 unit cabang perlombaan (`CompetitionBranchUnit`) yang dihasilkan pada Stage 3, tanpa mengubah file TXT asli maupun hasil Stage 1, Stage 2, dan Stage 3.

### Statistik Hasil Validasi Unit (Total: 114 Unit)

| Status Validasi | Jumlah Unit | Persentase | Deskripsi Makna Metodologis |
| :--- | :---: | :---: | :--- |
| **`VALIDATED`** | **63** | 55,26% | Identitas cabang akurat, cakupan persyaratan utuh (`0..len` atau bagian cabang mandiri penuh), bebas kontaminasi cabang lain, dan batas struktural dapat dijelaskan. |
| **`VALIDATED_WITH_LIMITATION`** | **40** | 35,09% | Batas bagian khusus cabang sudah tepat atau memiliki alasan struktural yang jelas, namun memiliki keterbatasan semantik yang wajib ditangani pada Stage 4 (mis. membutuhkan penautan ke rentang `event_level_general_information` / `shared_registration_or_payment_rules` yang terpisah, merupakan brosur ringkasan sub-event `DOC-015`, aturan kalimat tercampur `DOC-008`, atau unit kerangka umum FIKSI/LKS). |
| **`NEEDS_REVISION`** | **11** | 9,65% | Memerlukan perbaikan batas karakter atau dekomposisi ulang sebelum ekstraksi persyaratan (meliputi `DOC-009-BU-01`, `DOC-047-BU-04`, `DOC-061-BU-01..04`, `DOC-062-BU-02`, `DOC-069-BU-02`, `DOC-071-BU-02..03`, dan `DOC-067-BU-02`). |
| **`UNRESOLVED`** | **0 unit** *(+ 1 dokumen kosong `DOC-034`)* | 0,00% | Seluruh 114 unit yang terbentuk memiliki teks yang cukup untuk diaudit; sedangkan pada level dokumen, `DOC-034` (`Guidebook BPC TSF 2026.txt`, hanya 3 byte BOM `\ufeff`) berstatus **`UNRESOLVED`** karena tidak memiliki isi teks untuk menentukan cabang maupun batas segmentasi tanpa menebak dari nama file. |

### Ringkasan Pemeriksaan Otomatis (Automated Structural Checks — Terpisah dari Validasi Semantik)

| Pemeriksaan Otomatis Struktural | Hasil | Keterangan |
| :--- | :---: | :--- |
| Seluruh 80 dokumen korpus terdata (76 tersegmentasi + 4 dieksklusi) | **LULUS (`80/80`)** | Tidak ada dokumen yang terlewat. |
| Keunikan ID unit (`branch_unit_id`) | **LULUS (`114/114`)** | Tidak ada duplikasi ID unit. |
| Batas karakter di dalam ukuran dokumen (`0 <= start_char < end_char <= doc_len`) | **LULUS (`114/114`)** | Seluruh rentang karakter valid secara indeks string. |
| Kode cabang terdaftar di `competition_taxonomy.json` | **LULUS (`114/114`)** | Seluruh `branch_code` sesuai taksonomi 28 cabang. |
| Pasangan unit yang tumpang tindih (`overlapping_unit_pairs`) | **1 pasangan** | `DOC-008-BU-01` & `DOC-008-BU-02` (`3228..9518`, disengaja karena aturan Puisi & Cerpen tercampur di tingkat kalimat). |

### Distribusi Tipe Entitas Semantik Aktual dari 114 Unit

| Semantic Entity Type | Jumlah Unit | Penjelasan |
| :--- | :---: | :--- |
| `single_branch_competition_guide` | 49 | Buku panduan/juknis utuh untuk 1 cabang perlombaan tunggal (`0..len`). |
| `branch_specific_technical_guide` | 26 | Bagian petunjuk teknis khusus 1 cabang di dalam dokumen multi-cabang. |
| `event_level_general_information` | 10 | Bagian kerangka penyelenggaraan umum lintas cabang (pada dokumen FIKSI & LKS) yang saat ini terekstrak sebagai unit `BU-01`/`BU-02`. |
| `sub_event_brochure_entry` | 8 | Halaman ringkasan sub-event dalam brosur payung `DOC-015` (bukan juknis lengkap). |
| `competition_category_guide` | 7 | Bagian khusus kategori/jenjang di dalam cabang yang sama (`DOC-076-BU-01..05` PIMA Jurnalistik & `DOC-071-BU-02..03` FIKSI SMA/SMK). |
| `composite_competition_guide` | 5 | Panduan utuh kompetisi komposit multi-tahap (`DOC-016`, `DOC-037`, `DOC-038`, `DOC-051`, `DOC-064`). |
| `competition_stage_guide` | 4 | Tahapan berurutan dari satu kompetisi komposit (`DOC-061-BU-01..04`) yang keliru dipecah menjadi 4 cabang terpisah. |
| `bundled_multi_branch_appendix` | 3 | Lampiran yang masih menggabungkan 11 bidang FIKSI (`DOC-062-BU-02`, `DOC-069-BU-02`) atau 37 bidang LKS (`DOC-067-BU-02`). |
| `non_rulebook_finalist_catalog` | 1 | Booklet profil finalis & problem statement (`DOC-007-BU-01`), bukan buku peraturan peserta. |
| `mixed_subtheme_overview` | 1 | Bagian daftar subtema 7 cabang Pre-Event (`DOC-047-BU-04`) yang keliru dilabeli sebagai unit teknis 4 cabang. |

---

## 2. Validasi Perbedaan 6 Entitas Semantik

Audit menemukan bahwa ketidaktepatan pada sebagian unit multi-cabang berakar pada kaburnya batas antara **6 entitas semantik** berikut:

| Entitas Semantik | Definisi Metodologis | Tingkat Cakupan | Contoh Konkret pada Korpus |
| :--- | :--- | :--- | :--- |
| **1. `competition_event`** | Penyelenggaraan/wadah acara kompetisi secara keseluruhan oleh suatu institusi yang memiliki tema induk, lini masa umum, dan dapat menaungi satu atau banyak mata lomba. | Makro (Acara Induk) | **Pharmacopeia 2026** (`DOC-009`), **OGG FITB ITB 2026** (`DOC-040`, `DOC-047`), **FMIPA STEM Challenge** (`DOC-015`), **Techtonic UI 3.0** (`DOC-054`, `DOC-073`), **FIKSI** (`DOC-062`, `DOC-069`, `DOC-071`), **LKS Dikmen** (`DOC-066`–`DOC-068`, `DOC-075`). |
| **2. `competition_branch`** | Cabang perlombaan / mata lomba spesifik di dalam suatu event yang menguji kompetensi berbeda, menghasilkan deliverable spesifik, dan memiliki rubrik penilaian tersendiri. | Cabang / Mata Lomba | *Essay Competition*, *Science Olympiad*, *Digital Poster*, dan *Video Campaign* pada `DOC-009`; 11 Bidang Lomba FIKSI pada `DOC-062`; 37 Bidang Lomba LKS pada `DOC-067`. |
| **3. `competition_category`** | Sub-kelompok kepesertaan atau jalur karya di dalam suatu cabang/event yang sama, dibedakan menurut jenjang pendidikan, kematangan usaha, atau medium publikasi. | Intra-Cabang / Kategori | Kategori *Rencana Usaha* vs *Pengembangan Usaha* dan kelompok jenjang *SMA* vs *SMK* pada FIKSI 2024 (`DOC-071`); 5 kategori medium jurnalistik (*Cetak*, *Online*, *Foto*, *Audio Visual*, *Radio*) di bawah `BR_JOURNALISM` pada PIMA 2026 (`DOC-076`). |
| **4. `competition_unit`** | Unit analisis hasil ekstraksi rentang karakter (`CompetitionBranchUnit`) pada Stage 3. Idealnya 1 `competition_unit` = 1 `competition_branch` (atau 1 `composite_branch_competition`) beserta tautan ke konteks umum event induknya. | Artefak Operasional Segmentasi | `DOC-027-BU-01..04` (ideal: 1 unit = 1 cabang mandiri); penyimpangan terjadi bila 1 unit berisi 11 cabang (`DOC-062-BU-02`), 37 cabang (`DOC-067-BU-02`), atau 1 tahap dari kompetisi komposit (`DOC-061-BU-01..04`). |
| **5. `event_level_general_information`** | Informasi dan ketentuan umum lintas cabang pada tingkat event induk: latar belakang, tema umum, syarat kelayakan umum peserta, alur pendaftaran & pembayaran terpadu, jadwal umum, akomodasi, template lampiran umum, dan narahubung utama. | Konteks Bersama Lintas Cabang | `DOC-009` char `0..3050` (pengantar) & `46547..48658` (alur pendaftaran & biaya 4 cabang); `DOC-054`/`DOC-073` char `2550..5101` (*General Terms & Conditions* hlm. 4–5); `DOC-062-BU-01` (`13873..70881`, ketentuan umum FIKSI) + `70881..74271` (*Lampiran A*). |
| **6. `branch_specific_technical_guide`** | Bagian dokumen yang secara spesifik memuat mekanisme babak, format karya, aturan teknis perlombaan, dan indikator/bobot penilaian khusus untuk satu cabang tertentu. | Aturan Teknis Khusus Cabang | `DOC-047-BU-01..03` (Rincian Perlombaan Tahap Terpusat hlm. 10–32); `DOC-009-BU-02..04`; `DOC-054-BU-01` (hlm. 15–27); `DOC-073-BU-01` (hlm. 28–38). |

---

## 3. Audit Mendalam Kasus Khusus (Mandat Tugas 2)

### 3.1. `DOC-047` (`Guidebook Tahap Terpusat Pre-Event OGG FITB ITB 2026.txt`)
- **Temuan Semantik & Struktural:**
  1. Dokumen ini berjudul **`TAHAP FINAL / Guidebook Tahap Terpusat Pre-Event OGG FITB ITB 2026`**. Dari 7 cabang Pre-Event OGG, hanya **3 cabang** yang memiliki babak Tahap Terpusat (final luring di ITB), yaitu `Smart Competition` (`DOC-047-BU-01`, char `12046..22487`), `Science Project` (`DOC-047-BU-02`, char `22487..27475`), dan `Geo Debate` (`DOC-047-BU-03`, char `27475..34477`).
  2. Unit **`DOC-047-BU-04` (`4709..12037`, hlm. 5–9)** dilabeli `BR_POSTER_DESIGN` dengan judul *"Pre-Event Competition Overview (Poster, Geo Video, Essay, English Speech)"*. Pemeriksaan teks asli membuktikan bahwa halaman 5–9 adalah bab **`SUBTEMA PRE EVENT OGG FITB ITB 2026`** yang mencantumkan subtema untuk **ketujuh cabang Pre-Event sekaligus**:
     - `1. Essay`, `2. Geo Debate`, `3. Smart Competition`, `4. Poster`, `5. Geo Video`, `6. Science Project`, dan `7. English Speech`.
  3. Akibat pemotongan `4709..12037` ke dalam `DOC-047-BU-04`, ketiga unit Tahap Terpusat (`BU-01..03`) justru kehilangan informasi subtema cabangnya masing-masing, sementara `BU-04` mencampurkan 7 cabang tanpa memuat aturan teknis perlombaan sama sekali (aturan lengkap cabang non-terpusat berada di guidebook terpisah per cabang, misalnya `DOC-040` untuk *Essay Competition*).
  4. Selain itu, rentang tidak tercakup `0..4709` memuat **Timeline Pre-Event** dan rentang `34477..36745` memuat **Benefit Tahap Terpusat (Konsumsi, Akomodasi, Transportasi finalis)** serta **Kontak Narahubung**.
- **Status Validasi:**
  - `DOC-047-BU-04`: **`NEEDS_REVISION`**
  - `DOC-047-BU-01`, `DOC-047-BU-02`, `DOC-047-BU-03`: **`VALIDATED_WITH_LIMITATION`**
- **Rekomendasi Perbaikan:**
  - Hapus `DOC-047-BU-04` sebagai unit cabang mandiri.
  - Reklasifikasikan `0..12046` (Pengantar, Timeline, dan Subtema 7 Cabang) serta `34477..36745` (Benefit & Narahubung) sebagai `event_level_general_information` yang ditautkan ke `DOC-047-BU-01..03`.

---

### 3.2. `DOC-015` (`FMIPA STEM Challenge.txt`)
- **Temuan Semantik & Struktural:**
  1. `DOC-015` (7.903 karakter, 9 halaman) secara semantik adalah **brosur katalog event induk (`sub_event_brochure_entry`)** dalam rangka Dies Natalis ke-71 FMIPA UGM, **bukan** buku petunjuk teknis perlombaan. Setiap unit (`DOC-015-BU-01` s.d. `DOC-015-BU-08`, panjang 658–1.172 karakter) hanya berisi ringkasan 1 slide (deskripsi umum, sasaran peserta, lini masa tanggal penting, dan tautan/QR menuju guidebook eksternal masing-masing sub-event).
  2. Empat dari delapan unit sebenarnya merupakan **sub-event multi-cabang (`competition_event` tingkat sub-acara)**:
     - `DOC-015-BU-01` (**SCIENTA**): menaungi *LKTI Mahasiswa*, *LKTI Siswa*, dan *Open Laboratory*.
     - `DOC-015-BU-03` (**INSPIRE**): menaungi *Line Follower*, *Transporter*, *Research Innovation Challenge (RIC)*, dan *Workshop*.
     - `DOC-015-BU-04` (**JOINTS**): menaungi *Capture The Flag (CTF)*, *Data Competition*, *UI/UX Design*, *Gamejam*, dan *Programming Competition*.
     - `DOC-015-BU-08` (**ASiQ**): menaungi *International Case Competition*, *Smart Challenge*, dan *Talkshow*.
  3. **Batas Karakter (Boundary Bleed):** Karena anchor pemotongan dipasang pada nama sub-event (mis. `3. INSPIRE`), baris kop institusi slide berikutnya (`UNIVERSITAS GADJAH MADA DIES NATALIS / FAKULTAS MATEMATIKA DAN ILMU PENGETAHUAN ALAM`, ~95 karakter) ikut tertinggal di bagian akhir `BU-02` (`2488..2589`), `BU-04` (`3920..4028`), `BU-05` (`4751..4847`), `BU-06` (`5731..5851`), dan `BU-07` (`6916..7023`).
- **Status Validasi:** **`VALIDATED_WITH_LIMITATION`** untuk seluruh 8 unit (`DOC-015-BU-01..08`).
- **Rekomendasi Perbaikan:**
  - Beri atribut `semantic_entity_type = "sub_event_brochure_entry"` agar pada Stage 4 tidak diekstrak seolah-olah memiliki rubrik penilaian penuh.
  - Pangkas ~95 karakter kop institusi slide berikutnya pada akhir `BU-02`, `BU-04`, `BU-05`, `BU-06`, dan `BU-07`, serta tautkan halaman sampul `0..1005` sebagai `event_level_general_information`.

---

### 3.3. `DOC-009` (`Booklet SMA_K Sederajat_Pharmacopeia 2026.txt`)
- **Audit 5 Celah Rentang Karakter (`uncovered_char_spans`) pada `DOC-009`:**

| Rentang Celah | Panjang | Klasifikasi | Temuan Bukti Isi Teks Asli | Dampak Metodologis |
| :---: | :---: | :--- | :--- | :--- |
| `0..3050` | 3.050 | `event_level_general_information` | Sampul, Kata Pengantar, Latar Belakang Pharmacopeia 2026, & pengenalan 4 cabang lomba. | Konteks umum event induk. |
| **`3050..3135`** | **85** | **`truncated_branch_content`** | Teks asli: `LOMDaCork Es \n\n Pendaftaran 01-07 September | Google Forms | Gelombang 1 2026`. Judul `"LOMBA ESSAY"` rusak akibat OCR menjadi `"LOMDaCork Es"`, sehingga `DOC-009-BU-01` baru dimulai di char `3135` (`Pendaftaran 08 — 14 September 2026 Gelombang 2`). | **Persyaratan hilang:** `DOC-009-BU-01` kehilangan judul cabang dan jadwal **Pendaftaran Gelombang 1 (`01-07 September 2026`)**! |
| `15328..15403` | 75 | `separator_or_ocr_artifact` | Teks asli: `\n\na .\n‘ ~ ee\n. -\n" % ~~ ™. 4 *\n\n` (noise OCR dari banner visual pemisah sebelum *Science Olympiad*). | Murni artefak OCR pemisah; tidak ada informasi yang hilang. |
| `24614..24640` | 26 | `separator_or_ocr_artifact` | Teks asli: `\n\n< FE J\n: = x\n‘ rh\n\n` (noise OCR dari banner visual pemisah sebelum *Digital Poster*). | Murni artefak OCR pemisah; tidak ada informasi yang hilang. |
| `37583..37584` | 1 | `separator_or_ocr_artifact` | Karakter newline tunggal `\n` sebelum *Video Campaign*. | Pemisah baris murni. |
| **`46547..48658`** | **2.111** | **`shared_registration_or_payment_rules`** | Memuat **Alur Pendaftaran** (tautan `https://linktr.ee/pharmacopeia2026`, format konfirmasi `Cabang Lomba_Nama Lengkap_Asal Institusi`, kewajiban unggah Twibbon & share poster ke 3 grup) serta **Biaya Pendaftaran Gelombang 1, 2, dan 3** untuk keempat cabang lomba dan Narahubung Utama. | **Persyaratan krusial lintas cabang:** jika tidak ditautkan, keempat unit kehilangan syarat administrasi pendaftaran dan rincian biaya pendaftaran! |

- **Status Validasi:**
  - `DOC-009-BU-01`: **`NEEDS_REVISION`** (karena jadwal Gelombang 1 pada `3050..3135` terpotong).
  - `DOC-009-BU-02`, `DOC-009-BU-03`, `DOC-009-BU-04`: **`VALIDATED_WITH_LIMITATION`** (batas bagian teknis cabang sangat tepat dan celah antar-unit murni noise OCR, tetapi wajib ditautkan ke `46547..48658` dan `0..3050`).

---

### 3.4. Dokumen FIKSI (`DOC-062`, `DOC-069`, `DOC-071`) dan LKS (`DOC-066`, `DOC-067`, `DOC-068`, `DOC-075`)
- **Temuan Semantik & Struktural:**
  1. **Pencampuran Entitas `event_level_general_information` sebagai Unit Cabang:**
     - Pada `DOC-062-BU-01` (`13873..70881`), `DOC-069-BU-01` (`7763..53156`), `DOC-071-BU-01` (`7288..42332`), `DOC-067-BU-01` (`5825..90751`), serta `BU-02` pada `DOC-066`, `DOC-068`, dan `DOC-075`, kontennya adalah **Kerangka Penyelenggaraan Umum, Persyaratan Umum Peserta, Mekanisme Seleksi, dan Ketentuan Penilaian Umum lintas bidang (`event_level_general_information`)**, bukan panduan satu cabang lomba tunggal.
  2. **Penggabungan Banyak Cabang Lomba dalam Satu Unit Lampiran (`bundled_multi_branch_appendix`):**
     - `DOC-062-BU-02` (`74271..124027`) dan `DOC-069-BU-02` (`56532..91800`) menggabungkan deskripsi teknis dari **11 Bidang Lomba FIKSI yang berbeda** (*1. Agribisnis, Agroteknologi, dan Kemaritiman* s.d. *11. Seni Rupa dan Desain*) ke dalam satu unit tunggal.
     - `DOC-067-BU-02` (`90751..302962`, 212.211 karakter) menggabungkan ruang lingkup uji kompetensi dari **37 Bidang Lomba LKS Dikmen 2025** ke dalam satu unit raksasa.
     - `DOC-071-BU-02` (`42924..105896`, *Bidang Lomba SMA*) dan `DOC-071-BU-03` (`105896..124929`, *Bidang Lomba SMK*) membagi berdasarkan **kategori jenjang pendidikan (`competition_category`)**, tetapi masing-masing masih menggabungkan 6 bidang lomba SMA dan 8 bidang lomba SMK.
  3. **Rentang Penting yang Terlewat di Antara Unit:**
     - Pada `DOC-062` (celah `70881..74271`, 3.390 karakter) dan `DOC-069` (celah `53156..56532`, 3.376 karakter), bagian yang tidak tercakup adalah **`Lampiran A: Format Artikel Karya Ilmiah`** (`shared_templates_or_appendices`), yang merupakan spesifikasi wajib penulisan naskah peserta.
     - Pada `DOC-071` (celah `42332..42924`, 592 karakter), bagian yang terlewat memuat definisi **2 Kategori Kompetisi FIKSI 2024** (*1. Kompetisi Rencana Usaha* untuk pemula vs *2. Kompetisi Pengembangan Usaha* untuk usaha berjalan).
- **Status Validasi & Rekomendasi:**
  - `DOC-062-BU-02`, `DOC-069-BU-02`, `DOC-071-BU-02`, `DOC-071-BU-03`, `DOC-067-BU-02`: **`NEEDS_REVISION`** — pecah menjadi unit per bidang lomba (11 unit pada `DOC-062` & `DOC-069`; 14 unit pada `DOC-071`; 37 unit pada `DOC-067`).
  - `DOC-062-BU-01`, `DOC-069-BU-01`, `DOC-071-BU-01`, `DOC-067-BU-01`, `DOC-066-BU-01..02`, `DOC-068-BU-01..02`, `DOC-075-BU-01..02`: **`VALIDATED_WITH_LIMITATION`** — tetapkan sebagai konteks induk `event_level_general_information` (dan sertakan `Lampiran A` pada `DOC-062`/`DOC-069` serta definisi kategori `42332..42924` pada `DOC-071`).

---

### 3.5. `DOC-008` (`Booklet Literat Fest 2024.txt`)
- **Temuan Semantik & Struktural:**
  - `DOC-008-BU-01` (*Lomba Cipta Puisi*) dan `DOC-008-BU-02` (*Lomba Cipta Cerpen*) memiliki rentang karakter identik `3228..9518` (hlm. 6–11).
  - Pemeriksaan teks asli menunjukkan bahwa panitia menyatukan aturan kedua cabang di dalam bab, paragraf, bahkan **kalimat yang sama**:
    > *"3. Panjang karya puisi maksimal 16 baris dan cerpen maksimal 1200 kata."*  
    > *"Aspek Penilaian Lomba Cipta Puisi dan Cerpen: 1. Kesesuaian isi dengan tema (25%)..."*
  - Karena pencampuran terjadi pada tingkat klausa kalimat dan tabel rubrik bersama, pemisahan berbasis rentang karakter non-overlapping tidak mungkin dilakukan tanpa memotong kalimat di tengah jalan.
- **Status Validasi:** **`VALIDATED_WITH_LIMITATION`** untuk `DOC-008-BU-01` dan `DOC-008-BU-02`.
- **Rekomendasi Perbaikan:**
  - Pertahankan rentang bersama `3228..9518`, tautkan pengantar `0..3228` (`event_level_general_information`), dan lakukan ekstraksi persyaratan berbasis filter subjek klausa (*puisi* vs *cerpen*) pada Stage 4.

---

### 3.6. `DOC-054` (`HACKATHON GUIDEBOOK.txt`) dan `DOC-073` (`STEM GUIDEBOOK.txt`)
- **Temuan Semantik & Struktural:**
  1. Kedua dokumen berasal dari event induk **Techtonic UI 3.0** dan mengalami ketidaksesuaian nama file dari sumber aslinya:
     - `DOC-054` (`HACKATHON GUIDEBOOK.txt`) berisi pengantar Techtonic UI 3.0 (hlm. 1–5) diikuti panduan **PE STEM Competition** (hlm. 15–27, char `5101..15413`).
     - `DOC-073` (`STEM GUIDEBOOK.txt`) berisi pengantar Techtonic UI 3.0 (hlm. 1–5) diikuti panduan **Hackathon Competition (STASH)** (hlm. 28–38, char `5113..13768`).
  2. Stage 3 telah dengan benar menetapkan kode cabang berdasarkan bukti isi (`DOC-054-BU-01` = `BR_STEM_PROJECT`, `DOC-073-BU-01` = `BR_HACKATHON`) dan memulai rentang teknis pada char `5101` / `5113` sehingga ringkasan cabang lain di halaman 1–3 (`0..2550`) tidak mengontaminasi unit.
  3. **Temuan Penting pada Bagian yang Terpotong (`2550..5101` / `2550..5113`):** Halaman 4–5 buku panduan memuat **`GENERAL TERMS & CONDITIONS`** Techtonic UI 3.0 yang berisi persyaratan umum wajib bagi seluruh peserta:
     - Mahasiswa aktif S1/D3/D4 berusia maksimal 24 tahun;
     - Tim terdiri atas 3–4 mahasiswa dari universitas yang sama (diperbolehkan lintas jurusan/angkatan);
     - Prosedur registrasi akun di situs resmi dan ketentuan pembayaran.
- **Status Validasi:** **`VALIDATED_WITH_LIMITATION`** untuk `DOC-054-BU-01` dan `DOC-073-BU-01`.
- **Rekomendasi Perbaikan:**
  - Pertahankan batas bagian teknis `5101..15413` dan `5113..13768` (agar halaman 1–3 tidak mengontaminasi), tetapi **wajib tautkan rentang `2550..5101` (`DOC-054`) dan `2550..5113` (`DOC-073`)** sebagai `shared_registration_or_payment_rules`.

---

### 3.7. Temuan Penting Tambahan pada Dokumen Multi-Unit Lainnya (`DOC-061` & `DOC-076`)
1. **`DOC-061` (`NEW_GUIDEBOOK ENFORNATION 2026.txt` — 4 Unit: **`NEEDS_REVISION`**):**
   - Stage 3 memecah `DOC-061` menjadi 4 unit (`BU-01` LKTI, `BU-02` Videografi, `BU-03` CBT, `BU-04` Studi Kasus) sebagai `multi_branch_event`.
   - Pemeriksaan teks asli (khususnya celah `21090..21634` tentang *Tahap Final*) membuktikan bahwa keempatnya **bukan cabang terpisah**, melainkan **rangkaian tahapan wajib dari satu kompetisi komposit (`composite_branch_competition`)**:
     > *"Tahap Penyisihan terdiri dari dua rangkaian perlombaan, yaitu Lomba Karya Tulis Ilmiah dan Videografi yang wajib untuk diikuti seluruh peserta ENFORNATION 2026 ... 10 tim terbaik yang diambil dari 70% nilai LKTI dan 30% nilai videografi ... berhak melaju ke babak final (CBT dan Studi Kasus)."*
   - Selain itu, pemotongan `0..11322` menyebabkan hilangnya Tema & Subtema, Timeline, Hadiah, Syarat Peserta, dan Alur Pendaftaran!
   - **Rekomendasi:** Gabungkan kembali `DOC-061` menjadi 1 unit `composite_branch_competition` (`0..26262`) dengan `required_component_branches = ["BR_SCIENTIFIC_PAPER", "BR_VIDEO_FILM_PHOTO", "BR_SMART_QUIZ", "BR_ENG_CASE"]`.
2. **`DOC-076` (`Syarat & Ketentuan PIMA 2026.txt` — 5 Unit: **`VALIDATED_WITH_LIMITATION`**):**
   - Kelima unit (`DOC-076-BU-01..05`) secara semantik adalah 5 `competition_category` di bawah cabang Jurnalistik (`BR_JOURNALISM`). Batas antar-kategori (`3444..10625`) sudah akurat, namun Slide 1–2 (`0..3444`) memuat **14 butir Syarat & Ketentuan Umum Jurnalis** (WNI jurnalis media massa, wajib ID Pers & NPWP, maksimal 5 karya, tenggat 31 Desember 2026 pukul 23.59 WIB) serta rincian hadiah. Rentang `0..3444` wajib ditautkan ke kelima unit.

---

## 4. Evaluasi 5 Kriteria Kualitas pada Seluruh 114 Unit (Mandat Tugas 3)

| Kriteria Validasi Unit | Lulus (`True`) | Gagal (`False`) | Unit yang Gagal & Penyebab Utamanya |
| :--- | :---: | :---: | :--- |
| **1. `has_accurate_identity`** *(Memiliki identitas tepat)* | **104** | **10** | `DOC-047-BU-04` (diberi kode `BR_POSTER_DESIGN` padahal berisi subtema 7 cabang); `DOC-061-BU-01..04` (4 tahap kompetisi komposit dilabeli sebagai 4 cabang terpisah); `DOC-062-BU-02`, `DOC-069-BU-02`, `DOC-071-BU-02..03`, `DOC-067-BU-02` (lampiran puluhan bidang lomba dalam 1 unit). |
| **2. `has_relevant_content`** *(Memuat konten relevan)* | **113** | **1** | `DOC-047-BU-04` (hanya berisi daftar subtema 7 cabang Pre-Event, bukan petunjuk teknis perlombaan). |
| **3. `no_lost_requirements_from_truncation`** *(Tidak kehilangan syarat akibat pemotongan)* | **89** | **25** | `DOC-009-BU-01..04` (Gelombang 1 terpotong di `3050..3135` + pendaftaran/biaya di `46547..48658`); `DOC-006-BU-01..02` (`0..5499`); `DOC-046-BU-01..04` (`0..2776` & `9460..9943`); `DOC-047-BU-01..03` (`0..12046` & `34477..36745`); `DOC-054-BU-01` & `DOC-073-BU-01` (*General Terms* hlm. 4–5); `DOC-061-BU-01..04` (`0..11322`); `DOC-071-BU-01` (`42332..42924`); `DOC-076-BU-01..05` (`0..3444`). |
| **4. `no_cross_branch_contamination`** *(Tidak memasukkan informasi cabang lain)* | **102** | **12** | `DOC-008-BU-01..02` (aturan Puisi & Cerpen menyatu di kalimat yang sama); `DOC-015-BU-01, 03, 04, 08` (sub-event yang memuat 3–5 mata lomba internal); `DOC-047-BU-04` (memuat subtema 7 cabang); `DOC-062-BU-02`, `DOC-069-BU-02`, `DOC-071-BU-02..03`, `DOC-067-BU-02` (menggabungkan 6–37 bidang lomba). |
| **5. `has_explainable_structural_boundary`** *(Batas dapat dijelaskan secara struktural)* | **113** | **1** | `DOC-009-BU-01` (batas awal jatuh di char `3135` pada Gelombang 2 karena judul `'LOMDaCork Es'` pada char `3050` rusak akibat OCR). |

---

## 5. Analisis Seluruh Rentang Karakter yang Tidak Tercakup (`uncovered_char_spans` — Mandat Tugas 4)

Secara keseluruhan terdapat **40 rentang karakter yang tidak tercakup** di 19 dokumen multi-unit/intro (sedangkan 57 dokumen lainnya memiliki cakupan 100% dari karakter `0` hingga akhir dokumen). Dari 40 rentang tersebut, **25 rentang memuat informasi penting** yang tidak boleh dianggap sebagai teks tidak relevan:

| Klasifikasi Rentang Tidak Tercakup (`span_classification`) | Jumlah Rentang | Memuat Info Penting? | Dokumen Terkait & Penjelasan |
| :--- | :---: | :---: | :--- |
| **`truncated_branch_content`** | **1** | **Ya (1/1)** | `DOC-009` (`3050..3135`): Judul Lomba Esai (`LOMDaCork Es`) dan jadwal Pendaftaran Gelombang 1 (`01-07 September 2026`) yang terpotong karena OCR noise. |
| **`shared_registration_or_payment_rules`** | **7** | **Ya (7/7)** | `DOC-006` (`0..5499`), `DOC-009` (`46547..48658`), `DOC-046` (`9460..9943`), `DOC-054` (`2550..5101`), `DOC-061` (`0..11322`), `DOC-073` (`2550..5113`), `DOC-076` (`0..3444`). Memuat syarat kelayakan umum peserta, alur registrasi, biaya pendaftaran per gelombang, dan batas waktu pengiriman. |
| **`shared_templates_or_appendices`** | **4** | **Ya (4/4)** | `DOC-062` (`70881..74271` — *Lampiran A Format Artikel Ilmiah*), `DOC-069` (`53156..56532` — *Lampiran A Format Artikel Ilmiah*), `DOC-066` (`91264..96772`), `DOC-068` (`83224..84574`). |
| **`event_level_general_information`** | **16** | **Ya (13/16)** | Meliputi timeline umum, subtema, tabel hadiah, benefit akomodasi, narahubung, dan definisi kategori usaha (`DOC-008`, `DOC-009` `0..3050`, `DOC-015` `0..1005`, `DOC-046` `0..2776`, `DOC-047` `0..4709` & `34477..36745`, `DOC-061` `21090..21634` & `26091..26262`, `DOC-066`/`067`/`068`/`075` Bab I, `DOC-071` `42332..42924`). Tiga rentang lainnya (`DOC-024` `0..4122` serta Bab Penutup `DOC-062` & `DOC-069`) bersifat normatif/redundan. |
| **`table_of_contents_or_cover`** | **5** | Tidak (0/5) | Sampul dan Daftar Isi murni pada `DOC-027` (`0..6868`), `DOC-062` (`0..13873`), `DOC-069` (`0..7763`), `DOC-070` (`0..3103`), dan `DOC-071` (`0..7288`). |
| **`multi_event_intro_other_branches`** | **3** | Tidak (0/3) | Pengantar event induk yang merangkum cabang lain pada `DOC-033` (`0..4970`), `DOC-054` (`0..2550`), dan `DOC-073` (`0..2550`). Pemotongan bagian ini sudah tepat untuk mencegah kontaminasi lintas cabang. |
| **`separator_or_ocr_artifact`** | **4** | Tidak (0/4) | Noise OCR dari gambar pemisah halaman pada `DOC-009` (`15328..15403`, `24614..24640`, `37583..37584`) dan nomor halaman `'9'` pada `DOC-047` (`12037..12046`). |

---

## 6. Rekomendasi Perbaikan Konkret Sebelum Stage 4 (Requirement Extraction)

Agar tahap ekstraksi persyaratan (Stage 4) memiliki ketepatan struktural dan semantik yang tinggi, berikut rekomendasi perbaikan terstruktur berdasarkan prioritas:

1. **Perbaikan Unit Berstatus `NEEDS_REVISION` (11 Unit pada 7 Dokumen):**
   - **`DOC-009-BU-01`:** Geser `start_char` dari `3135` ke `3050` untuk memulihkan judul cabang esai (`LOMDaCork Es`) dan jadwal **Pendaftaran Gelombang 1 (`01-07 September 2026`)**.
   - **`DOC-047-BU-04`:** Hapus sebagai unit cabang mandiri; ubah rentang `0..12046` (Pengantar, Timeline, & Subtema 7 Cabang) serta `34477..36745` (Benefit & Narahubung) menjadi `event_level_general_information` yang diwariskan ke `DOC-047-BU-01..03`.
   - **`DOC-061-BU-01..04`:** Gabungkan kembali keempat unit tahapan menjadi **1 unit `composite_branch_competition`** (`DOC-061-BU-01`, char `0..26262`) dengan `required_component_branches = ["BR_SCIENTIFIC_PAPER", "BR_VIDEO_FILM_PHOTO", "BR_SMART_QUIZ", "BR_ENG_CASE"]`.
   - **`DOC-062-BU-02` & `DOC-069-BU-02`:** Sub-segmentasikan masing-masing menjadi **11 unit cabang FIKSI** (*1. Agribisnis* s.d. *11. Seni Rupa dan Desain*).
   - **`DOC-071-BU-02` & `DOC-071-BU-03`:** Sub-segmentasikan menjadi **6 unit bidang lomba SMA** dan **8 unit bidang lomba SMK**.
   - **`DOC-067-BU-02`:** Sub-segmentasikan menjadi **37 unit bidang lomba LKS Dikmen 2025** berdasarkan struktur Lampiran 1.

2. **Penautan Konteks Induk (`shared_context_spans`) untuk Unit Berstatus `VALIDATED_WITH_LIMITATION` (40 Unit):**
   - Tambahkan field `inherited_event_spans` pada skema unit cabang sehingga setiap unit `branch_specific_technical_guide` atau `competition_category_guide` secara otomatis mewarisi:
     - `DOC-006`: `0..5499` (Tata Tertib & Teknis Pendaftaran);
     - `DOC-008`: `0..3228` (Latar Belakang & Tujuan);
     - `DOC-009`: `0..3050` (Pengantar) dan `46547..48658` (Alur Pendaftaran & Biaya Pendaftaran Gelombang 1–3);
     - `DOC-015`: `0..1005` (Sampul Induk FMIPA STEM Challenge);
     - `DOC-046`: `0..2776` (Timeline & Tabel Hadiah) dan `9460..9943` (Link Pendaftaran & Kontak);
     - `DOC-047`: `0..12046` (Timeline & Subtema) dan `34477..36745` (Benefit Tahap Terpusat & Narahubung);
     - `DOC-054` & `DOC-073`: `2550..5101` / `2550..5113` (*General Terms & Conditions* Techtonic UI 3.0 hlm. 4–5);
     - `DOC-062` & `DOC-069`: `BU-01` (Ketentuan Umum FIKSI) + `Lampiran A: Format Artikel Karya Ilmiah` (`70881..74271` / `53156..56532`);
     - `DOC-071`: `7288..42924` (Ketentuan Umum FIKSI 2024 + Definisi Kategori Rencana vs Pengembangan Usaha);
     - `DOC-066`, `DOC-067`, `DOC-068`, `DOC-075`: Bab I + Kerangka Umum Penyelenggaraan LKS + Lampiran Akhir;
     - `DOC-076`: `0..3444` (14 Syarat Umum Jurnalis PIMA 2026, Periode Lomba, dan Hadiah).
