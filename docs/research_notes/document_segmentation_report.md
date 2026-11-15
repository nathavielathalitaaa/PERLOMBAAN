# Laporan Segmentasi Dokumen ke Unit Cabang Perlombaan (Tahap 3 — V0.1)

Dokumen ini mendokumentasikan hasil implementasi **Tahap 3: Document Segmentation** pada proyek **AI Competition Mentor**. Tujuan tahap ini adalah memecah dokumen kompetisi menjadi unit cabang perlombaan (`CompetitionBranchUnit`) yang terpisah dan memiliki batas struktural (`start_char..end_char` dan `start_page..end_page` bila tersedia) agar informasi persyaratan, tahapan seleksi, dan indikator penilaian dari satu cabang tidak tercampur dengan cabang lainnya pada tahap ekstraksi berikutnya.

Seluruh dokumen asli di `data/raw/txt/` serta hasil inventarisasi dan validasi sebelumnya (`document_inventory.csv`, `document_inventory.json`, `document_inventory_validated.csv`, `document_inventory_validated.json`, `competition_taxonomy.json`) dipertahankan **utuh tanpa perubahan**.

Output segmentasi disimpan di:
- `data/processed/competition_branch_units.json`
- `data/processed/competition_branch_units.csv`

---

## 1. Ringkasan Statistik Hasil Segmentasi

| Metrik Segmentasi | Jumlah | Keterangan |
| :--- | :---: | :--- |
| **Total Dokumen Induk Diperiksa** | **80** | `DOC-001` s.d. `DOC-080` |
| **Dokumen Kompetisi yang Disegmentasi** | **76** | Menghasilkan unit cabang perlombaan (`CompetitionBranchUnit`) |
| **Dokumen Kosong / Non-Kompetisi Dikecualikan** | **4** | `DOC-005`, `DOC-014`, `DOC-034` (kosong), `DOC-060` (0 unit cabang dibuat) |
| **Total Unit Cabang (`CompetitionBranchUnit`) Dibuat** | **114** | Terhubung ke dokumen induk melalui `document_id` |
| **Unit dari Dokumen `single_branch`** | **50** | 50 dokumen × 1 unit cabang (`DOC-xxx-BU-01`) |
| **Unit dari Dokumen `multi_branch_event`** | **55** | Berasal dari 17 dokumen multi-cabang (masing-masing dipecah menjadi 2 s.d. 8 unit) |
| **Unit dari Dokumen `composite_branch_competition`** | **5** | 5 dokumen kompetisi luaran komposit dengan `required_component_branches` lengkap |
| **Unit dari Dokumen `primary_branch_with_multi_event_intro`** | **4** | 4 dokumen dengan isolasi bagian pengantar event umum (`DOC-033`, `DOC-054`, `DOC-070`, `DOC-073`) |
| **Unit dengan Rentang Halaman Eksplisit (`start_page..end_page`)** | **47** | Hanya diisi bila nomor halaman tertulis eksplisit di Daftar Isi/dokumen (tanpa mengarang) |
| **Unit Ditandai `needs_review = True`** | **12** | Berasal dari 8 dokumen yang memerlukan pemeriksaan manual saat ekstraksi |

---

## 2. Perlakuan Berdasarkan Tipe Struktur Dokumen (`multi_branch_type`)

### 2.1 `single_branch` (50 Dokumen -> 50 Unit)
- Setiap dokumen menghasilkan tepat 1 unit (`DOC-xxx-BU-01`) dengan `start_char = 0` dan `end_char = len(text)`.
- Khusus **`DOC-007` (`Booklet Hackathon 2025.txt`)**, unit `DOC-007-BU-01` ditandai `needs_review = True` (`needs_review_non_rulebook_catalog`) karena dokumen ini merupakan katalog profil Top 10 Tim Finalis BI-OJK Hackathon 2025, bukan buku panduan persyaratan pendaftaran.

### 2.2 `multi_branch_event` (17 Dokumen -> 55 Unit Terpisah)
Pemisahan dilakukan berdasarkan Daftar Isi, tajuk bab/subbab eksplisit, dan pergantian struktur komponen lomba (bukan sekadar kemunculan kata kunci):

| ID Dokumen | Nama File | Jumlah Unit | Rincian Unit Cabang (`branch_unit_id`, `branch_code`, Halaman, Rentang Karakter, & Judul Bagian) |
| :--- | :--- | :---: | :--- |
| **`DOC-006`** | `Booklet Firma Ceria 2025.txt` | **2** | • `DOC-006-BU-01` (`BR_RELIGIOUS_ARTS`, char `5499..7430`): *Lomba Tilawah Al-Qur'an*<br>• `DOC-006-BU-02` (`BR_LITERARY_WRITING`, char `7430..9869`): *Lomba Puisi Islami* |
| **`DOC-008`** | `Booklet Literat Fest 2024.txt` | **2** | • `DOC-008-BU-01` (`BR_LITERARY_WRITING`, hlm. `6..11`, char `3228..9518`, **`needs_review`**): *Sayembara Cipta Puisi (Syarat & Ketentuan Terpadu)*<br>• `DOC-008-BU-02` (`BR_LITERARY_WRITING`, hlm. `6..11`, char `3228..9518`, **`needs_review`**): *Sayembara Cipta Cerpen (Syarat & Ketentuan Terpadu)* |
| **`DOC-009`** | `Booklet SMA_K Sederajat_Pharmacopeia 2026.txt` | **4** | • `DOC-009-BU-01` (`BR_ESSAY`, char `3135..15328`): *Essay Competition Pharmacopeia 2026*<br>• `DOC-009-BU-02` (`BR_SCIENCE_OLYMPIAD`, char `15403..24614`): *Science Olympiad Pharmacopeia 2026*<br>• `DOC-009-BU-03` (`BR_POSTER_DESIGN`, char `24640..37583`): *Digital Poster Competition Pharmacopeia 2026*<br>• `DOC-009-BU-04` (`BR_VIDEO_FILM_PHOTO`, char `37584..46547`): *Video Campaign Competition Pharmacopeia 2026* |
| **`DOC-015`** | `FMIPA STEM Challenge.txt` | **8** | • `DOC-015-BU-01` (`BR_SCIENTIFIC_PAPER`, char `1005..1739`): *SCIENTA UGM 2026*<br>• `DOC-015-BU-02` (`BR_SCIENCE_OLYMPIAD`, char `1739..2589`): *LMNas 37 UGM 2026*<br>• `DOC-015-BU-03` (`BR_IOT_ROBOTICS`, char `2589..3247`): *INSPIRE 2026*<br>• `DOC-015-BU-04` (`BR_DATA_SCIENCE`, char `3247..4028`): *JOINTS 2026*<br>• `DOC-015-BU-05` (`BR_SCIENCE_OLYMPIAD`, char `4028..4847`): *TOP Challenge of Physics UGM 2026*<br>• `DOC-015-BU-06` (`BR_SCIENCE_OLYMPIAD`, char `4847..5851`): *Olimpiade Kimia Nasional (OKN) 2026*<br>• `DOC-015-BU-07` (`BR_ESSAY`, char `5851..7023`): *Lomba Esai Nasional Kimia (LENK) 2026*<br>• `DOC-015-BU-08` (`BR_ACTUARIAL_CASE`, char `7023..7903`): *ASiQ (Actuarial Science Quest) 2026* |
| **`DOC-024`** | `GUIDEBOOK IMPACTEERS UNIVERSITAS NEGERI SURABAYA.txt` | **3** | • `DOC-024-BU-01` (`BR_ESSAY`, hlm. `2..10`, char `4122..10785`): *Cabang Lomba Esai*<br>• `DOC-024-BU-02` (`BR_BMC`, hlm. `11..18`, char `10785..17612`): *Cabang Lomba BMC*<br>• `DOC-024-BU-03` (`BR_POSTER_DESIGN`, hlm. `19..25`, char `17612..24733`): *Cabang Lomba Poster* |
| **`DOC-027`** | `GUIDEBOOK IT FEST 2026.txt` | **4** | • `DOC-027-BU-01` (`BR_SOFTWARE_DEV`, hlm. `1..6`, char `6868..15487`): *Software Development Competition*<br>• `DOC-027-BU-02` (`BR_NETWORK_ADMIN`, hlm. `7..18`, char `15487..29905`): *IT Network System Administration (ITNSA)*<br>• `DOC-027-BU-03` (`BR_CYBERSECURITY_CTF`, hlm. `19..26`, char `29905..43550`): *Capture The Flag (CTF)*<br>• `DOC-027-BU-04` (`BR_VIDEO_FILM_PHOTO`, hlm. `27..31`, char `43550..49430`): *Short Movie Competition* |
| **`DOC-046`** | `Guidebook PJJ CHALLENGE Chapter II.txt` | **4** | • `DOC-046-BU-01` (`BR_SMART_QUIZ`, hlm. `3..3`, char `2776..3767`): *Brain Challenge Week*<br>• `DOC-046-BU-02` (`BR_SCIENTIFIC_PAPER`, hlm. `4..5`, char `3767..6029`): *Short Paper*<br>• `DOC-046-BU-03` (`BR_ESSAY`, hlm. `6..7`, char `6029..7881`): *Essay*<br>• `DOC-046-BU-04` (`BR_VIDEO_FILM_PHOTO`, hlm. `8..9`, char `7881..9460`): *Catch the Moment* |
| **`DOC-047`** | `Guidebook Tahap Terpusat Pre-Event OGG FITB ITB 2026.txt` | **4** | • `DOC-047-BU-01` (`BR_SMART_QUIZ`, hlm. `10..20`, char `12046..22487`): *Smart Competition*<br>• `DOC-047-BU-02` (`BR_STEM_PROJECT`, hlm. `21..25`, char `22487..27475`): *Science Project Competition*<br>• `DOC-047-BU-03` (`BR_DEBATE_SPEECH`, hlm. `26..32`, char `27475..34477`): *Geo Debate Competition*<br>• `DOC-047-BU-04` (`BR_POSTER_DESIGN`, hlm. `5..9`, char `4709..12037`, **`needs_review`**): *Subtema Pre-Event (Poster, Geo Video, Essay, English Speech — Tanpa Bab Tahap Terpusat)* |
| **`DOC-061`** | `NEW_GUIDEBOOK ENFORNATION 2026.txt` | **4** | • `DOC-061-BU-01` (`BR_SCIENTIFIC_PAPER`, char `11322..16582`): *Tahap Penyisihan 2: LKTI*<br>• `DOC-061-BU-02` (`BR_VIDEO_FILM_PHOTO`, char `16582..21090`): *Tahap Penyisihan 3: Videografi*<br>• `DOC-061-BU-03` (`BR_SMART_QUIZ`, char `21634..23489`): *Tahap Final 2: CBT*<br>• `DOC-061-BU-04` (`BR_ENG_CASE`, char `23489..26091`): *Tahap Final 3: Studi Kasus Lapangan & Infografis* |
| **`DOC-062`** | `Panduan FIKSI 2026.txt` | **2** | • `DOC-062-BU-01` (`BR_ENTREPRENEURSHIP_INNOVATION`, hlm. `7..35`, char `13873..70881`): *Ketentuan Umum, Mekanisme & Penilaian FIKSI 2026 (Bab I–VII)*<br>• `DOC-062-BU-02` (`BR_ENTREPRENEURSHIP_INNOVATION`, hlm. `37..63`, char `74271..124027`): *Lampiran Deskripsi 11 Cabang Lomba FIKSI 2026* |
| **`DOC-066`** | `Panduan_Ajang_Talenta_Lomba_Kompetensi_Siswa_Tahun_2024.txt` | **2** | • `DOC-066-BU-01` (`BR_VOCATIONAL_LKS`, hlm. `11..12`, char `20619..23060`, **`needs_review`**): *Bab II.C Daftar 6 Kelompok Bidang (37 Cabang LKS SMK 2024)*<br>• `DOC-066-BU-02` (`BR_VOCATIONAL_LKS`, hlm. `12..45`, char `23060..91264`, **`needs_review`**): *Mekanisme & Norma Penyelenggaraan Umum LKS 2024* |
| **`DOC-067`** | `Panduan_Ajang_Talenta_Lomba_Kompetensi_Siswa_Tahun_2025 .txt` | **2** | • `DOC-067-BU-01` (`BR_VOCATIONAL_LKS`, hlm. `5..52`, char `5825..90751`): *Panduan Penyelenggaraan Umum LKS Nasional 2025 (Bab I–IV)*<br>• `DOC-067-BU-02` (`BR_VOCATIONAL_LKS`, hlm. `53..179`, char `90751..302962`): *Lampiran Ruang Lingkup Keahlian 37 Bidang Lomba LKS Nasional 2025* |
| **`DOC-068`** | `Panduan_Ajang_Talenta_Lomba_Kompetensi_Siswa_Tahun_2026.txt` | **2** | • `DOC-068-BU-01` (`BR_VOCATIONAL_LKS`, hlm. `10..12`, char `19244..22150`, **`needs_review`**): *Bab II.C Daftar 37+1 Cabang Lomba LKS Dikmen 2026*<br>• `DOC-068-BU-02` (`BR_VOCATIONAL_LKS`, hlm. `12..37`, char `22150..83224`, **`needs_review`**): *Mekanisme, Skema Penilaian & Norma Penyelenggaraan LKS 2026* |
| **`DOC-069`** | `Panduan_FIKSI_SMA_MA_SMK 2025_.txt` | **2** | • `DOC-069-BU-01` (`BR_ENTREPRENEURSHIP_INNOVATION`, hlm. `6..29`, char `7763..53156`): *Ketentuan Umum, Mekanisme & Penilaian FIKSI 2025 (Bab I–VI)*<br>• `DOC-069-BU-02` (`BR_ENTREPRENEURSHIP_INNOVATION`, hlm. `31..51`, char `56532..91800`): *Lampiran Deskripsi 11 Cabang Lomba FIKSI 2025* |
| **`DOC-071`** | `Pedoman FIKSI SMA SMK 2024.txt` | **3** | • `DOC-071-BU-01` (`BR_ENTREPRENEURSHIP_INNOVATION`, hlm. `6..23`, char `7288..42332`): *Pedoman Umum & Ketentuan Khusus FIKSI 2024 (Bab I–V)*<br>• `DOC-071-BU-02` (`BR_ENTREPRENEURSHIP_INNOVATION`, hlm. `24..61`, char `42924..105896`): *Lampiran 1) Bidang Lomba Jenjang SMA/MA (11 Bidang)*<br>• `DOC-071-BU-03` (`BR_ENTREPRENEURSHIP_INNOVATION`, hlm. `61..72`, char `105896..124929`): *Lampiran 2) Bidang Lomba Jenjang SMK* |
| **`DOC-075`** | `Sosialisasi LKS Dikmen 2025.txt` | **2** | • `DOC-075-BU-01` (`BR_VOCATIONAL_LKS`, char `4838..7290`, **`needs_review`**): *Daftar Bidang dan 37+1 Cabang Lomba LKS Dikmen 2025*<br>• `DOC-075-BU-02` (`BR_VOCATIONAL_LKS`, char `7290..32521`, **`needs_review`**): *Komposisi Proyek Uji, Ketentuan Umum & Linimasa LKS 2025* |
| **`DOC-076`** | `Syarat & Ketentuan PIMA 2026.txt` | **5** | • `DOC-076-BU-01` (`BR_JOURNALISM`, hlm. `3..3`, char `3444..4714`): *Kategori Teks — Hard News*<br>• `DOC-076-BU-02` (`BR_JOURNALISM`, hlm. `4..4`, char `4714..6026`): *Kategori Teks — Feature*<br>• `DOC-076-BU-03` (`BR_JOURNALISM`, hlm. `5..5`, char `6026..7699`): *Kategori Foto Cerita*<br>• `DOC-076-BU-04` (`BR_JOURNALISM`, hlm. `6..6`, char `7699..9145`): *Kategori Jurnalistik Radio*<br>• `DOC-076-BU-05` (`BR_JOURNALISM`, hlm. `7..7`, char `9145..10625`): *Kategori Jurnalistik Televisi* |

### 2.3 `composite_branch_competition` (5 Dokumen -> 5 Unit Komposit)
Seluruh komponen cabang yang diwajibkan dalam satu mata lomba dicatat pada atribut `required_component_branches`:
1. **`DOC-016-BU-01`** (`GUIDE BOOK HIMTEC-1.txt`): `required_component_branches = ["BR_HACKATHON", "BR_APP_DEV", "BR_AI"]` (*Build App With AI*).
2. **`DOC-037-BU-01`** (`Guidebook EIC College.txt`): `required_component_branches = ["BR_ESSAY", "BR_INFOGRAPHIC"]` (*Essay & Infographic Competition MetalFest ITB 2027 — Mahasiswa*).
3. **`DOC-038-BU-01`** (`Guidebook EIC High School.txt`): `required_component_branches = ["BR_ESSAY", "BR_INFOGRAPHIC"]` (*Essay & Infographic Competition MetalFest ITB 2027 — SMA/Sederajat*).
4. **`DOC-051-BU-01`** (`Guidebook_Hackathon.txt`): `required_component_branches = ["BR_HACKATHON", "BR_WEB_DEV"]` (*Hackathon Web Innovation*).
5. **`DOC-064-BU-01`** (`Panduan SOBAT Competition 2026.txt`): `required_component_branches = ["BR_STEM_PROJECT", "BR_SCIENTIFIC_PAPER"]` (*SOBAT Competition — Output: Prototype & Makalah*).

### 2.4 `primary_branch_with_multi_event_intro` (4 Dokumen -> 4 Unit Terisolasi)
Bagian pengenalan event umum di awal dokumen (yang menyebutkan cabang lain dari event induk) dipotong (`start_char > 0`) agar tidak mencemari ekstraksi cabang utama:
1. **`DOC-033-BU-01`** (`Guidebook BCC MANIFEST 2026 (fixx).txt`): `BR_BUSINESS_CASE`, hlm. `5..18`, char `4970..22813` (mengisolasi pengantar umum MANIFEST pada char `0..4970` yang menyebutkan BPC & EBPC).
2. **`DOC-054-BU-01`** (`HACKATHON GUIDEBOOK.txt`): `BR_STEM_PROJECT`, hlm. `15..27`, char `5101..15413`, **`needs_review = True`** (mengisolasi pengantar umum Techtonic UI 3.0 pada char `0..5101`; ditandai `needs_review` karena nama file tertukar dengan isi PE STEM Competition).
3. **`DOC-070-BU-01`** (`Pedoman EIC - PGTC 2026.txt`): `BR_SCIENTIFIC_PAPER`, hlm. `2..46`, char `3103..66490` (mengisolasi Kata Pengantar PGTC 2026 pada hlm. 1 / char `0..3103` yang menyebutkan Debat & Kompetisi Bisnis).
4. **`DOC-073-BU-01`** (`STEM GUIDEBOOK.txt`): `BR_HACKATHON`, hlm. `28..38`, char `5113..13768`, **`needs_review = True`** (mengisolasi pengantar umum Techtonic UI 3.0 pada char `0..5113`; ditandai `needs_review` karena nama file tertukar dengan isi Hackathon STASH).

### 2.5 `non_competition_or_unclassified` (4 Dokumen -> Dikecualikan / 0 Unit)
Sesuai Ketentuan 13 (*"Dokumen kosong dan non-kompetisi tidak boleh dipaksakan menjadi unit cabang kompetisi"*), 4 dokumen berikut disimpan pada daftar `excluded_documents` dan tidak menghasilkan `CompetitionBranchUnit`:
- **`DOC-005`** (`Booklet Duta Muda Bineka 2025 - Berbineka Indonesia.txt`): Booklet seleksi duta pemuda.
- **`DOC-014`** (`FIX Guidebook Advanced 2025.txt`): Panduan kurikulum bootcamp pelatihan 4 hari.
- **`DOC-034`** (`Guidebook BPC TSF 2026.txt`): Dokumen kosong (0 kata, 3 byte UTF-8 BOM).
- **`DOC-060`** (`Modul BST Advance 2025.txt`): Modul pembelajaran teknis pemrograman Golang.
