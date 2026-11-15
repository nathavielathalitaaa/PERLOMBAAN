# Laporan Audit Inventarisasi & Persiapan Klasifikasi Kompetisi (Tahap 2 — V0.1)

Dokumen ini mendokumentasikan hasil audit mendalam terhadap inventarisasi tahap pertama (`data/processed/document_inventory.csv` dan `data/processed/document_inventory.json`) dibandingkan secara langsung dengan isi teks asli pada 80 dokumen di `data/raw/txt/`.

Seluruh file inventarisasi tahap pertama (`document_inventory.csv` dan `document_inventory.json`) dipertahankan utuh tanpa ditimpa, dan seluruh kolom klasifikasi asli disimpan berdampingan dengan kolom hasil validasi pada:
- `data/processed/document_inventory_validated.csv`
- `data/processed/document_inventory_validated.json`
- `data/processed/inventory_audit_report.json`
- `knowledge_base/competition_requirements/competition_taxonomy.json`
- `data/processed/competition_taxonomy.json`

---

## 1. Ringkasan Eksekutif Hasil Audit

| Metrik Audit | Jumlah | Keterangan |
| :--- | :---: | :--- |
| **Total Dokumen Diaudit** | **80** | Seluruh file TXT di `data/raw/txt/` |
| **Dokumen dengan Perubahan/Penyempurnaan Klasifikasi** | **26** | 21 perubahan `document_type`, 6 perubahan/penajaman `competition_branch` (`DOC-027` mengalami perubahan keduanya) |
| **Dokumen Kompetisi Multi-Cabang / Komposit (`is_multi_branch = True`)** | **22** | 17 dokumen event multi-cabang (`multi_branch_event`) + 5 dokumen kompetisi luaran komposit (`composite_branch_competition`) |
| **Dokumen Kompetisi Cabang Tunggal (`is_multi_branch = False`)** | **54** | Termasuk 4 dokumen yang memiliki pengantar multi-cabang namun isi teknis khusus 1 cabang (`DOC-033`, `DOC-054`, `DOC-070`, `DOC-073`) |
| **Dokumen Non-Kompetisi / Kosong** | **4** | `DOC-005` (Rekrutmen Duta), `DOC-014` (Bootcamp), `DOC-060` (Modul Belajar), `DOC-034` (Kosong / 0 kata) |
| **Dokumen Perlu Perbaikan / Konversi Ulang** | **16** | 1 kosong, 2 nama file tertukar, 4 kerusakan encoding font/ligatur, 9 derau OCR/template |

---

## 2. Pemisahan 6 Kategori Makro Dokumen

Berdasarkan audit struktur bab dan isi teks seluruh korpus, 80 dokumen dikelompokkan ke dalam 6 kategori makro (+ 1 `unknown` karena kosong):

| Kategori Makro (`macro_document_category`) | Sub-Tipe (`validated_document_type`) | Jumlah Dokumen | Deskripsi & Karakteristik Isi |
| :--- | :--- | :---: | :--- |
| **1. Dokumen Panduan Kompetisi** (`dokumen_panduan_kompetisi`) | `guidebook` (49), `panduan` (4), `panduan_pelaksanaan` (4), `pedoman` (3), `booklet` (2), `handbook` (1) | **63** | Memuat panduan penyelenggaraan komprehensif: Latar Belakang, Tema/Subtema, Timeline, Ketentuan Peserta, Mekanisme Tahapan Seleksi, Kriteria Penilaian, dan Hadiah. |
| **2. Dokumen Ketentuan dan Petunjuk Teknis** (`dokumen_ketentuan_dan_petunjuk_teknis`) | `ketentuan_lomba` (4), `guidebook_petunjuk_teknis` (2), `rulebook` (2), `petunjuk_teknis` (1), `panduan_teknis` (1), `syarat_ketentuan` (1) | **11** | Berfokus langsung pada aturan teknis pengerjaan/pengumpulan karya, spesifikasi format, dan syarat peserta (`DOC-046`, `DOC-053`, `DOC-058`, `DOC-059`, `DOC-063`, `DOC-065`, `DOC-076`, `DOC-077`, `DOC-078`, `DOC-079`, `DOC-080`). |
| **3. Modul Pembelajaran** (`modul_pembelajaran`) | `modul_pembelajaran` (1) | **1** | `DOC-060` (`Modul BST Advance 2025.txt`): Buku materi pembelajaran teknis Backend Development dengan Golang (25.690 kata), bukan aturan lomba. |
| **4. Katalog Karya atau Finalis** (`katalog_karya_atau_finalis`) | `booklet_profil_finalis` (1) | **1** | `DOC-007` (`Booklet Hackathon 2025.txt`): Katalog pasca-seleksi berisi statistik pendaftar dan profil karya Top 10 Finalis BI-OJK Hackathon 2025, bukan buku panduan pendaftaran. |
| **5. Dokumen Sosialisasi** (`dokumen_sosialisasi`) | `paparan_sosialisasi` (1) | **1** | `DOC-075` (`Sosialisasi LKS Dikmen 2025.txt`): Materi paparan slide sosialisasi kebijakan dan daftar 37 cabang LKS Dikmen 2025. |
| **6. Dokumen Lainnya** (`dokumen_lainnya`) | `booklet_rekrutmen` (1), `guidebook_bootcamp` (1) | **2** | `DOC-005` (Booklet Open Recruitment Duta Muda Bineka 2025) dan `DOC-014` (Guidebook kurikulum pelatihan 4 hari Schematics BST 2025). |
| **Tidak Diketahui (`unknown`)** | `unknown` (1) | **1** | `DOC-034` (`Guidebook BPC TSF 2026.txt`): File kosong (3 byte UTF-8 BOM, 0 kata). |

---

## 3. Audit Dokumen Berstatus `needs_review`, `unclassified`, `empty`, dan `readable_with_ocr_noise`

### 3.1 Dokumen `empty` & `unclassified` (1 Dokumen)
- **`DOC-034` (`Guidebook BPC TSF 2026.txt`)**:
  - **Kondisi Fisik**: Hanya berisi 3 byte UTF-8 BOM (`\ufeff`), 0 karakter, 0 kata.
  - **Keputusan Audit**: Tetap dipertahankan sebagai `unknown` / `unclassified_empty`. Sesuai aturan integritas penelitian, cabang lomba tidak boleh ditetapkan sebagai *Business Plan Competition* hanya dari singkatan `BPC` pada nama file tanpa bukti isi teks.

### 3.2 Dokumen `needs_review` (6 Dokumen pada Tahap 1)
1. **`DOC-005` (`Booklet Duta Muda Bineka 2025 - Berbineka Indonesia.txt`)**:
   - **Temuan Audit**: Teks membuktikan dokumen ini adalah panduan seleksi peran duta komunitas (*"BOOKLET REKRUTMEN TERBUKA DUTA MUDA BINEKA Berbineka Indonesia 2025"*). Ditetapkan sebagai `validated_non_competition` pada kategori makro `dokumen_lainnya`.
2. **`DOC-007` (`Booklet Hackathon 2025.txt`)**:
   - **Temuan Audit**: Merupakan katalog profil Top 10 tim finalis BI-OJK Hackathon 2025 (*"10 Finalis Terpilih ... Profil 10 Tim Finalis Hackathon 2025"*). Ditetapkan pada kategori makro `katalog_karya_atau_finalis` (`needs_review_non_rulebook_catalog`).
3. **`DOC-014` (`FIX Guidebook Advanced 2025.txt`)**:
   - **Temuan Audit**: Merupakan panduan peserta program pelatihan/bootcamp 4 hari (*"Schematics Bootstrapping ... program pelatihan yang dirancang untuk generasi muda"*). Ditetapkan sebagai `validated_non_competition` pada kategori makro `dokumen_lainnya`.
4. **`DOC-054` (`HACKATHON GUIDEBOOK.txt`)**:
   - **Temuan Audit Kritis (Tertukarnya Nama File vs Isi)**: Nama file adalah `HACKATHON GUIDEBOOK.txt`, tetapi halaman 15–27 merupakan buku panduan spesifik untuk **PE STEM Competition Techtonic UI 3.0** (*"Welcome to the PE STEM Competition of Techtonic UI 3.0! ... Connecting Lives through IoT"*). Dipetakan ke kode cabang `["BR_STEM_PROJECT", "BR_IOT_ROBOTICS"]` dengan status `needs_review_filename_mismatch`.
5. **`DOC-060` (`Modul BST Advance 2025.txt`)**:
   - **Temuan Audit**: Merupakan modul ajar pemrograman Golang (*"DISCLAIMER Modul ini dibuat untuk tujuan pendidikan dan pengembangan keterampilan pemrograman saja"*). Ditetapkan sebagai `validated_non_competition` pada kategori makro `modul_pembelajaran`.
6. **`DOC-073` (`STEM GUIDEBOOK.txt`)**:
   - **Temuan Audit Kritis (Tertukarnya Nama File vs Isi)**: Nama file adalah `STEM GUIDEBOOK.txt`, tetapi halaman 28–38 merupakan buku panduan spesifik untuk **Hackathon Competition Techtonic UI 3.0** (*"Welcome to Hackathon Competition of Techtonic UI 3.0! ... STASH (Smart Technology and Security Hackathon)"*). Dipetakan ke kode cabang `["BR_HACKATHON", "BR_CYBERSECURITY_CTF"]` dengan status `needs_review_filename_mismatch`.

### 3.3 Dokumen `readable_with_ocr_noise` (13 Dokumen)
Seluruh 13 dokumen dengan derau OCR/encoding (`DOC-007`, `DOC-008`, `DOC-009`, `DOC-015`, `DOC-033`, `DOC-055`, `DOC-058`, `DOC-059`, `DOC-066`, `DOC-071`, `DOC-072`, `DOC-076`, `DOC-077`) telah diperiksa terhadap isi teks aslinya:
- Seluruh 13 dokumen masih memiliki bagian isi utama (ketentuan peserta, mekanisme, dan kriteria penilaian) yang **dapat dibaca dan diverifikasi**.
- Namun, pada **`DOC-058` (`Juknis EPIC.txt`)** dan **`DOC-059` (`Juknis KOSA KATA Cerpen.txt`)**, kalimat **Tema Utama** berubah menjadi karakter kontrol ASCII (`\x02`–`\x1f`) akibat kegagalan *ToUnicode CMap* pada font judul PDF, sehingga bagian tema tersebut wajib diekstraksi ulang dengan OCR sebelum Tahap 3.

---

## 4. Daftar Seluruh Perubahan Klasifikasi Beserta Alasan dan Bukti Teks

Audit menemukan **26 dokumen** yang memerlukan perbaikan/penajaman pada `document_type` (21 dokumen) dan/atau `competition_branch` (6 dokumen):

### 4.1 Koreksi Klasifikasi Cabang Perlombaan (`competition_branch`) — 6 Dokumen

| ID | Nama File | Cabang Tahap 1 | Cabang Tervalidasi (Tahap 2) & Kode Taksonomi | Alasan Audit & Bukti Kutipan Teks |
| :--- | :--- | :--- | :--- | :--- |
| **`DOC-027`** | `GUIDEBOOK IT FEST 2026.txt` | `Software Development` (`identified`) | **Multi-Cabang: Software Development, IT Network System Administration (ITNSA), Capture The Flag (CTF), Short Movie** (`BR_SOFTWARE_DEV`, `BR_NETWORK_ADMIN`, `BR_CYBERSECURITY_CTF`, `BR_VIDEO_FILM_PHOTO`) | **Koreksi Kritis**: Tahap 1 hanya menangkap cabang pertama di Daftar Isi. Audit teks membuktikan dokumen ini memuat 4 cabang lengkap: *"DAFTAR ISI ... SOFTWARE DEVELOPMENT (hlm. 1) ... IT NETWORK SYSTEM ADMINISTRATION (ITNSA) (hlm. 7) ... CAPTURE THE FLAG (hlm. 19) ... SHORT MOVIE (hlm. 27)"*. |
| **`DOC-054`** | `HACKATHON GUIDEBOOK.txt` | `STEM Innovation / Project Exhibition (needs_review: filename mismatch)` | **STEM Innovation & IoT Project Exhibition (PE STEM Techtonic UI 3.0 — Filename Mismatch)** (`BR_STEM_PROJECT`, `BR_IOT_ROBOTICS`) | Penajaman cabang spesifik ke STEM & IoT berdasarkan isi hlm. 15–27: *"Welcome to the PE STEM Competition of Techtonic UI 3.0! ... Connecting Lives through IoT"*. |
| **`DOC-073`** | `STEM GUIDEBOOK.txt` | `Hackathon (needs_review: filename mismatch)` | **Hackathon — Smart Technology and Security Hackathon / STASH (Techtonic UI 3.0 — Filename Mismatch)** (`BR_HACKATHON`, `BR_CYBERSECURITY_CTF`) | Penajaman cabang spesifik ke Hackathon & Keamanan Siber berdasarkan isi hlm. 28–38: *"Welcome to Hackathon Competition of Techtonic UI 3.0! ... STASH (Smart Technology and Security Hackathon)"*. |
| **`DOC-005`** | `Booklet Duta Muda Bineka 2025 - Berbineka Indonesia.txt` | `needs_review` | **non_competition (Seleksi Duta Muda Bineka)** (`[]`) | Dikonfirmasi bukan cabang lomba, melainkan seleksi duta: *"BOOKLET REKRUTMEN TERBUKA DUTA MUDA BINEKA Berbineka Indonesia 2025"*. |
| **`DOC-014`** | `FIX Guidebook Advanced 2025.txt` | `needs_review` | **non_competition (Bootcamp Pelatihan Schematics BST Advanced)** (`[]`) | Dikonfirmasi bukan lomba, melainkan panduan pelatihan: *"Schematics Bootstrapping ... program pelatihan yang dirancang untuk generasi muda"*. |
| **`DOC-060`** | `Modul BST Advance 2025.txt` | `needs_review` | **non_competition (Modul Pembelajaran Backend Golang Schematics BST)** (`[]`) | Dikonfirmasi bukan lomba, melainkan modul belajar: *"DISCLAIMER Modul ini dibuat untuk tujuan pendidikan dan pengembangan keterampilan pemrograman saja"*. |

### 4.2 Koreksi Klasifikasi Jenis Dokumen (`document_type`) — 21 Dokumen

| ID | Nama File | `document_type` Tahap 1 | `validated_document_type` (Tahap 2) | Kategori Makro | Alasan & Bukti Teks |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`DOC-008`** | `Booklet Literat Fest 2024.txt` | `ketentuan_lomba` | `booklet` | `dokumen_panduan_kompetisi` | Sampul rusak akibat OCR, namun memiliki Daftar Isi & struktur Booklet panduan lengkap (*"SAYEMBARA CIPTA PUISI DAN CERPEN TINGKAT NASIONAL ... Daftar Isi Latar Belakang"*). |
| **`DOC-012`** | `ESAI GAGASAN KREATIF UI SCIENCE OLYMPIAD 2026.txt` | `ketentuan_lomba` | `panduan_pelaksanaan` | `dokumen_panduan_kompetisi` | Teks eksplisit menyatakan: *"Demikian panduan pelaksanaan Lomba Esai Gagasan Kreatif UI Science Olympiad 2026 ini dirancang agar dapat menjadi pedoman jalannya acara"*. |
| **`DOC-013`** | `ESAI GAGASAN KRITIS UI SCIENCE OLYMPIAD 2026.txt` | `ketentuan_lomba` | `panduan_pelaksanaan` | `dokumen_panduan_kompetisi` | Teks eksplisit menyatakan: *"Demikian panduan pelaksanaan Lomba Esai Gagasan Kritis UI Science Olympiad 2026"*. |
| **`DOC-018`** | `GUIDEBOOK ALGOQUEST 2026.txt` | `ketentuan_lomba` | `guidebook` | `dokumen_panduan_kompetisi` | Memiliki Daftar Isi & bab Guidebook lengkap (Pendahuluan, Latar Belakang, Tujuan, Tema, Ketentuan, Mekanisme, Silabus, Hadiah). |
| **`DOC-025`** | `GUIDEBOOK INFOGRAFIS COMPETITION.txt` | `ketentuan_lomba` | `guidebook` | `dokumen_panduan_kompetisi` | Memiliki struktur Guidebook lengkap Fasilkom Fest 2026 (Daftar Isi, Latar Belakang, Tema, Timeline, Kriteria Penilaian). |
| **`DOC-027`** | `GUIDEBOOK IT FEST 2026.txt` | `petunjuk_teknis` | `guidebook` | `dokumen_panduan_kompetisi` | Pada Tahap 1 terpicu kata *"G. Petunjuk Teknis Pengumpulan"* di Daftar Isi, padahal merupakan Master Guidebook 4 cabang lomba (31 halaman). |
| **`DOC-039`** | `Guidebook EMIC 2026 [SMA].txt` | `panduan` | `guidebook` | `dokumen_panduan_kompetisi` | Teks tajuk utama tertulis eksplisit: *"EMIC SMA/MA GUIDEBOOK"*. |
| **`DOC-041`** | `Guidebook Essay EUREKA! ITB 2026.txt` | `ketentuan_lomba` | `guidebook` | `dokumen_panduan_kompetisi` | Memiliki struktur Guidebook multi-bab lengkap (*"COMP 01 ESSAY DAFTAR ISI ... BAB 1 PENDAHULUAN ... BAB 2 ISI ... BAB 3 PENUTUP"*). |
| **`DOC-043`** | `Guidebook Immersive Fiesta 2025.txt` | `panduan` | `guidebook` | `dokumen_panduan_kompetisi` | Teks Kata Pengantar menyatakan eksplisit: *"Guidebook ini disusun untuk menjadi panduan resmi bagi para peserta dalam mengikuti rangkaian kompetisi Immersive Fiesta 2025"*. |
| **`DOC-044`** | `Guidebook Logicodix 2024.txt` | `panduan` | `guidebook` | `dokumen_panduan_kompetisi` | Teks sampul menyatakan eksplisit: *"LOGICODIX 2024 ... GUIDEBOOK LOGICODIX 2024"*. |
| **`DOC-045`** | `Guidebook National BMC Competition 2026.txt` | `ketentuan_lomba` | `guidebook` | `dokumen_panduan_kompetisi` | Memiliki Daftar Isi dan struktur Guidebook lengkap (*"DAFTAR ISI ... PENDAHULUAN ... TEMA & SUB-TEMA ... KETENTUAN PESERTA"*). |
| **`DOC-047`** | `Guidebook Tahap Terpusat Pre-Event OGG FITB ITB 2026.txt` | `ketentuan_lomba` | `guidebook` | `dokumen_panduan_kompetisi` | Merupakan Guidebook komprehensif (10.752 kata) untuk 7 cabang Pre-Event OGG FITB ITB 2026. |
| **`DOC-050`** | `Guidebook_CleanCode_Updated.txt` | `ketentuan_lomba` | `guidebook` | `dokumen_panduan_kompetisi` | Memiliki Daftar Isi & bab Guidebook lengkap (*"DAFTAR ISI LOMBA CLEAN CODE ... TEMA KEGIATAN ... DESKRIPSI LOMBA"*). |
| **`DOC-052`** | `Guidebook_UIUX_Design.txt` | `ketentuan_lomba` | `guidebook` | `dokumen_panduan_kompetisi` | Memiliki Daftar Isi & bab Guidebook lengkap Milad IT Fest 19 (*"DAFTAR ISI Milad IT Fest 19 ... A. Tentang Milad IT Fest 19"*). |
| **`DOC-056`** | `INFOGRAFIS UI SCIENCE OLYMPIAD 2026.txt` | `ketentuan_lomba` | `panduan_pelaksanaan` | `dokumen_panduan_kompetisi` | Teks eksplisit menyatakan: *"Demikian panduan pelaksanaan Lomba Infografis UI Science Olympiad 2026"*. |
| **`DOC-061`** | `NEW_GUIDEBOOK ENFORNATION 2026.txt` | `ketentuan_lomba` | `guidebook` | `dokumen_panduan_kompetisi` | Memiliki Daftar Isi & struktur Guidebook lengkap ENFORNATION 2026 (4.353 kata). |
| **`DOC-063`** | `Panduan Lomba Esai untuk Pelajar SMP SMA.txt` | `panduan` | `ketentuan_lomba` | `dokumen_ketentuan_dan_petunjuk_teknis` | Judul baris pertama adalah *"Ketentuan Umum Lomba Esai Pelajar SMP dan SMA Sederajat"* yang langsung berisi poin ketentuan teknis tanpa bab latar belakang. |
| **`DOC-068`** | `Panduan_Ajang_Talenta_Lomba_Kompetensi_Siswa_Tahun_2026.txt` | `pedoman` | `panduan` | `dokumen_panduan_kompetisi` | Judul resmi halaman sampul dalam adalah *"PANDUAN AJANG LOMBA KOMPETENSI SISWA (LKS) TINGKAT NASIONAL TAHUN 2026"*. |
| **`DOC-074`** | `STUDY CASE COMPETITION UI SCIENCE OLYMPIAD 2026.txt` | `ketentuan_lomba` | `panduan_pelaksanaan` | `dokumen_panduan_kompetisi` | Teks eksplisit menyatakan: *"Demikian panduan pelaksanaan Lomba Study Case Competition UI Science Olympiad 2026"*. |
| **`DOC-076`** | `Syarat & Ketentuan PIMA 2026.txt` | `ketentuan_lomba` | `syarat_ketentuan` | `dokumen_ketentuan_dan_petunjuk_teknis` | Penajaman sub-tipe menjadi `syarat_ketentuan` untuk dokumen ketentuan 5 kategori jurnalistik PIMA 2026. |
| **`DOC-079`** | `essay.txt` | `pedoman` | `ketentuan_lomba` | `dokumen_ketentuan_dan_petunjuk_teknis` | Pada Tahap 1 terpicu kalimat *"Format penulisan mengikuti pedoman yang ditentukan"*, padahal judul utama dokumen adalah *"Ketentuan / IT - Competition AMIKOM Surakarta (IT-CAS) 2026 / ESSAY (Pelajar)"* (606 kata). |

---

## 5. Rancangan Taksonomi Cabang Perlombaan & Klasifikasi Multi-Branch

Taksonomi kompetisi disimpan dalam `knowledge_base/competition_requirements/competition_taxonomy.json` (dan disinkronkan ke `data/processed/competition_taxonomy.json`). Taksonomi ini terdiri atas **6 Domain Utama** dan **31 Kode Cabang (`branch_codes`)**:

1. **`DOM_IT_DIGITAL` (Teknologi Informasi, Komputasi & Digital — 24 dokumen)**:
   - `BR_AI` (5 dok), `BR_ML` (1 dok), `BR_DATA_SCIENCE` (3 dok), `BR_DATA_ANALYTICS` (1 dok), `BR_CYBERSECURITY_CTF` (5 dok), `BR_NETWORK_ADMIN` (1 dok), `BR_SOFTWARE_DEV` (1 dok), `BR_APP_DEV` (2 dok), `BR_WEB_DEV` (5 dok), `BR_HACKATHON` (4 dok), `BR_UIUX_DESIGN` (1 dok), `BR_IOT_ROBOTICS` (3 dok), `BR_COMP_PROGRAMMING_LOGIC` (2 dok), `BR_3D_ANIMATION` (1 dok).
2. **`DOM_BUSINESS_ECON` (Bisnis, Kewirausahaan, Manajemen & Kebijakan — 18 dokumen)**:
   - `BR_BUSINESS_PLAN` (9 dok), `BR_BUSINESS_CASE` (5 dok), `BR_BMC` (3 dok), `BR_ENTREPRENEURSHIP_INNOVATION` (3 dok), `BR_POLICY_CASE` (1 dok), `BR_ACTUARIAL_CASE` (1 dok).
3. **`DOM_SCIENCE_ENG_STEM` (Sains, Rekayasa, Energi, Lingkungan & STEM — 14 dokumen)**:
   - `BR_SCIENCE_OLYMPIAD` (3 dok), `BR_STEM_PROJECT` (6 dok), `BR_ENG_CASE` (3 dok), `BR_ENG_MANAGEMENT_INNOVATION` (1 dok), `BR_ENV_ECO_PROJECT` (1 dok), `BR_SMART_QUIZ` (4 dok).
4. **`DOM_WRITING_RESEARCH` (Karya Tulis Ilmiah, Esai & Literasi Sastra — 26 dokumen)**:
   - `BR_SCIENTIFIC_PAPER` (6 dok), `BR_ESSAY` (16 dok), `BR_LITERARY_WRITING` (3 dok), `BR_JOURNALISM` (1 dok).
5. **`DOM_CREATIVE_MEDIA_COMMUNICATION` (Desain Visual, Media Kreatif & Komunikasi — 14 dokumen)**:
   - `BR_INFOGRAPHIC` (5 dok), `BR_POSTER_DESIGN` (4 dok), `BR_VIDEO_FILM_PHOTO` (5 dok), `BR_DEBATE_SPEECH` (1 dok), `BR_RELIGIOUS_ARTS` (1 dok).
6. **`DOM_VOCATIONAL_NATIONAL` (Kompetensi Keahlian Vokasi Multi-Bidang — 4 dokumen)**:
   - `BR_VOCATIONAL_LKS` (4 dok).

### Dukungan Multi-Branch (`multi_branch_type`)
Sistem membedakan 5 pola pemetaan cabang:
- `single_branch` (50 dokumen): Mengatur 1 cabang spesifik.
- `multi_branch_event` (17 dokumen): Satu buku panduan mengatur beberapa cabang lomba terpisah dalam satu event (contoh: `DOC-009` Pharmacopeia, `DOC-015` FMIPA STEM Challenge, `DOC-024` Impacteers, `DOC-027` IT Fest 2026, `DOC-046` PJJ Challenge, `DOC-047` OGG FITB ITB, `DOC-061` ENFORNATION).
- `composite_branch_competition` (5 dokumen): Satu mata lomba mewajibkan kombinasi dua luaran lintas cabang (contoh: `DOC-037` & `DOC-038` *Essay & Infographic Competition*, `DOC-016` *Build App With AI*, `DOC-051` *Hackathon Web Dev*, `DOC-064` *SOBAT Prototype & Makalah*).
- `primary_branch_with_multi_event_intro` (4 dokumen): Bagian pengantar menyebutkan beberapa cabang event induk (disimpan di `secondary_event_branch_codes`), namun isi teknis dokumen khusus untuk 1 cabang utama (`DOC-033`, `DOC-054`, `DOC-070`, `DOC-073`).
- `non_competition_or_unclassified` (4 dokumen): Dokumen non-kompetisi (`DOC-005`, `DOC-014`, `DOC-060`) dan dokumen kosong (`DOC-034`).

---

## 6. Daftar 16 Dokumen yang Perlu Diperbaiki atau Dikonversi Ulang

| Prioritas | ID | Nama File | Status Perbaikan (`reconversion_status`) | Masalah Spesifik & Rekomendasi Teknis |
| :---: | :--- | :--- | :--- | :--- |
| **P1 (Kritis)** | `DOC-034` | `Guidebook BPC TSF 2026.txt` | `needs_reextraction_empty` | File kosong (0 kata, 3 byte BOM). Ekstraksi ulang PDF asli menggunakan OCR (Tesseract/PaddleOCR). |
| **P1 (Kritis)** | `DOC-054` | `HACKATHON GUIDEBOOK.txt` | `needs_filename_swap_fix` | Nama file tertukar: isi hlm. 15–27 adalah **PE STEM Competition** Techtonic UI 3.0. |
| **P1 (Kritis)** | `DOC-073` | `STEM GUIDEBOOK.txt` | `needs_filename_swap_fix` | Nama file tertukar: isi hlm. 28–38 adalah **Hackathon Competition (STASH)** Techtonic UI 3.0. |
| **P2 (Tinggi)** | `DOC-058` | `Juknis EPIC.txt` | `needs_font_encoding_fix` | 69 karakter kontrol ASCII (`\x02`–`\x1f`) pada bagian `TEMA` akibat kegagalan *ToUnicode font map*. Perlu OCR ulang halaman 1. |
| **P2 (Tinggi)** | `DOC-059` | `Juknis KOSA KATA Cerpen.txt` | `needs_font_encoding_fix` | 71 karakter kontrol ASCII (`\x02`–`\x1f`) pada bagian `TEMA`. Perlu OCR ulang halaman 1. |
| **P2 (Sedang)** | `DOC-007` | `Booklet Hackathon 2025.txt` | `needs_font_encoding_fix` | 58 karakter kontrol (`\x1e`/`\x1f`) menggantikan ligatur `fi`/`fl` (`e\x1fsiensi`, `signi\x1fkan`). |
| **P2 (Sedang)** | `DOC-071` | `Pedoman FIKSI SMA SMK 2024.txt` | `needs_font_encoding_fix` | 13 karakter null byte (`\x00`) dari simbol bullet kustom PDF. |
| **P3 (Rendah)** | `DOC-008` | `Booklet Literat Fest 2024.txt` | `needs_ocr_cleanup` | Teks sampul terpecah per karakter (`Explore the Powe / L r of Words`). |
| **P3 (Rendah)** | `DOC-009` | `Booklet SMA_K Sederajat_Pharmacopeia 2026.txt` | `needs_ocr_cleanup` | Typo OCR pada sampul dan isi (`we ompetition Buideline a)`, `SMAIK Sederajat`, `terobuka`). |
| **P3 (Rendah)** | `DOC-015` | `FMIPA STEM Challenge.txt` | `needs_ocr_cleanup` | Derau OCR pada sampul (`f= mn ©)`) dan `IoT` terbaca `lol`. |
| **P3 (Rendah)** | `DOC-033` | `Guidebook BCC MANIFEST 2026 (fixx).txt` | `needs_ocr_cleanup` | Derau OCR pada header/paragraf awal (`NSINCSwS)i CaUiS C,`, `Manaj emen Bisnii s`). |
| **P3 (Rendah)** | `DOC-055` | `HSC BRAND UI 2026 HANDBOOK.txt` | `needs_ocr_cleanup` | Derau OCR pada sampul (`Powere d by // GC. -@-O¢`). |
| **P3 (Rendah)** | `DOC-066` | `Panduan_Ajang_Talenta_Lomba_Kompetensi_Siswa_Tahun_2024.txt` | `needs_ocr_cleanup` | Halaman i mengandung placeholder template MS Word (`[DOCUMENT TITLE]`, `[COMPANY NAME]`). |
| **P3 (Rendah)** | `DOC-072` | `Preliminary Guidebook ECC.txt` | `needs_ocr_cleanup` | Kata tergabung underscore & multi-kolom (`metalurgi_memiliki`, `Inteenegrgi rte`, `em_b_aplei`). |
| **P3 (Rendah)** | `DOC-076` | `Syarat & Ketentuan PIMA 2026.txt` | `needs_ocr_cleanup` | Derau OCR pada banner (`31 Besember 2026`, `mt: ee oe F`, `tesien«`). |
| **P3 (Rendah)** | `DOC-077` | `[AIC] AI Innovation Challenge.txt` | `needs_ocr_cleanup` | Derau OCR pada banner (`Tam@e)it-lelelae-harelam`, `Al` untuk `AI`). |

---

## 7. Rekomendasi Struktur Metadata untuk Tahap Ekstraksi Informasi Berikutnya (Tahap 3)

Agar proses ekstraksi persyaratan kompetisi, tahapan seleksi, dan indikator penilaian pada Tahap 3 berjalan akurat serta mampu menangani dokumen *multi-branch*, struktur metadata direkomendasikan dibagi menjadi **3 lapis entitas relasional**:

1. **Lapis 1 — `DocumentMetadata` (Level File Sumber)**:
   - Menyimpan identitas dokumen (`document_id`, `file_name`, `file_sha256`), `macro_document_category`, `validated_document_type`, `readability_status`, `reconversion_status`, dan flag `is_eligible_for_requirement_extraction` (`True` hanya untuk 73 dokumen bertipe `dokumen_panduan_kompetisi` dan `dokumen_ketentuan_dan_petunjuk_teknis` yang tidak kosong).
2. **Lapis 2 — `CompetitionEventMetadata` (Level Ajang/Event Induk)**:
   - Menyimpan identitas penyelenggaraan (`event_id`, `event_name`, `organizer_institution`, `organizer_unit`, `event_year`, `scale`, `general_theme`, `sub_themes`, `multi_branch_type`).
3. **Lapis 3 — `CompetitionBranchUnit` (Level Mata Lomba Spesifik — Relasi 1-ke-N dari Dokumen)**:
   - **Penting untuk Multi-Branch**: Satu dokumen `multi_branch_event` (seperti `DOC-027` *GUIDEBOOK IT FEST 2026*) harus dipecah menjadi 4 unit `CompetitionBranchUnit` terpisah berdasarkan `section_char_span` (rentang halaman/karakter masing-masing cabang di dalam dokumen), sehingga syarat peserta, format karya, dan bobot penilaian *Capture The Flag* tidak tercampur dengan *Short Movie* atau *Software Development*.
   - Setiap `CompetitionBranchUnit` memuat:
     - `taxonomy_domain_codes` & `taxonomy_branch_codes`
     - `participant_education_level` (`SMP`, `SMA_MA`, `SMK`, `Mahasiswa_D3_D4_S1`, `Umum`)
     - `team_composition_rule` (`participation_mode`, `min_members`, `max_members`, `cross_major_allowed`, `cross_institution_allowed`)
     - `stages_and_deliverables` (daftar tahapan seleksi, artefak yang dikumpulkan, dan tenggat waktu)
     - `evaluation_criteria` (nama kriteria, `weight_percentage`, sub-indikator, dan `source_status`)
     - `evidence_trace` (`source_status: explicit | inferred | unverified`, `verbatim_quote`, `line_or_page_reference`).
