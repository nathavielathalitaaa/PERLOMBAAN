# Stage 4.4 — Ground Truth Quality Audit Report

**Keputusan Akhir**: `GROUND_TRUTH_READY_WITH_LIMITATIONS`  
**Tanggal Audit**: `2026-11-15T21:05:00+07:00`  
**Objek Audit**:
- [stage_4_4_blind_held_out_ground_truth.json](file:///home/lalita/Projects/perlombaan/data/processed/stage_4_4_blind_held_out_ground_truth.json) (73 record, 5 dokumen)
- [stage_4_4_ground_truth_freeze.json](file:///home/lalita/Projects/perlombaan/data/processed/stage_4_4_ground_truth_freeze.json)
- [stage_4_4_ground_truth_annotation_report.md](file:///home/lalita/Projects/perlombaan/docs/research_notes/stage_4_4_ground_truth_annotation_report.md)
- [build_stage_4_4_blind_gt.py](file:///home/lalita/Projects/perlombaan/scripts/build_stage_4_4_blind_gt.py)

---

## A. Audit Independensi Anotasi (`VERIFIED_INDEPENDENT`)

Pemeriksaan langsung terhadap [build_stage_4_4_blind_gt.py](file:///home/lalita/Projects/perlombaan/scripts/build_stage_4_4_blind_gt.py) membuktikan:
1. Seluruh 73 anotasi berasal dari kurasi manual berdasarkan pembacaan langsung 5 file TXT asli di `data/raw/txt/` (`ENERGY4ME GUIDEBOOK.txt`, `GUIDE BOOK NEXTGEN BMC.txt`, `Guidebook_Hackathon.txt`, `Pedoman EIC - PGTC 2026.txt`, `Guidebook_Wreck_IT_7.0.txt`).
2. Tidak ada impor `src.*` (`extractor.py`, `rules.py`, `evaluator.py`, maupun `generic_parser`) dan tidak ada pembacaan `data/processed/competition_requirements.json`. Kemunculan kata `generic_parser` di skrip hanya berupa key metadata boolean `"used_old_extractor_or_generic_parser": False`.
3. Skrip hanya memetakan *anchor* teks kurasi manual ke indeks karakter persis pada file TXT asli, memverifikasi invarian span, lalu menghasilkan JSON dan *hash freeze*.

---

## B. Audit Kelengkapan Persyaratan & E. Audit Kualitas Evidence

### 1. Validasi Teknis Span
- `raw_text[source_char_start:source_char_end] == evidence_text`: **73/73 cocok persis**.
- Seluruh span berada dalam rentang `branch_unit_id` Stage 3 dan memiliki **0 overlap** serta **0 duplikasi**.

### 2. Temuan Substantif Kualitas Evidence vs Deskripsi (5 Record)
Akibat pemangkasan span saat menghindari overlap pada tahap build, terdapat 5 record yang *scope* `requirement_description`-nya sedikit lebih luas daripada `evidence_text`-nya:
- **`GT-DOC-011-011`**: `evidence_text` (`6057..6690`) berhenti di `File format: PDF`, sedangkan `requirement_description` masih mencantumkan aturan penamaan file (`SPARKUP2026_ENERGY4ME_Preliminary_TeamName.pdf`) yang berada di `6786..6843` (`4.Submission Guidelines`).
- **`GT-DOC-017-004`**: `evidence_text` (`6704..6787`) hanya mencakup `Alur Lomba:...`, sedangkan modalitas `online` (`2863..2938`, `4088..4118`) dan tema `"Business Innovation for the Future"` (`1612..1660`) yang dirangkum di `requirement_description` berada di luar span.
- **`GT-DOC-070-012`**: `evidence_text` (`39631..40470`) berhenti sebelum sub-butir `c) Booth pameran` (`41289..41598`) karena menghindari overlap dengan `GT-DOC-070-017`.
- **`GT-DOC-053-007`**: `evidence_text` (`467..1204`) berasal dari *Pendahuluan CTF*, sedangkan `requirement_description` turut merangkum detail durasi/tanggal dari bagian `G`, `H`, dan `J`.
- **`GT-DOC-053-010`**: `evidence_text` (`6340..6691`) hanya mencakup `G.6` (`WriteupwreckitGeneral`), sedangkan `requirement_description` juga menyebut tautan `WriteupwreckitJunior` (`J.6.c`) dan batas jam `14.30 WIB` dari rundown.

### 3. Persyaratan Minor yang Belum Memiliki Span Tersendiri
- `DOC-017`: *Ketentuan dan Peraturan* butir 1–4 (modalitas online, pendaftaran & pengumpulan via Google Form) serta *Penutup*.
- `DOC-051`: Bagian `B. Ketentuan Pitching & Demo` (baris 767–800) belum memiliki record terpisah (hanya terwakili sebagian lewat `GT-DOC-051-009` *Deliverables*).
- `DOC-070`: `Bab II.D.1.c` (kewajiban mencantumkan 1 subtema) dan rincian batas persentase struktur naskah (`Bab II.D.2`) baru dicatat pada `annotator_notes` pada `GT-DOC-070-010`.
- `DOC-053`: `H. BABAK FINAL GENERAL CTF` (baris 243–267) dan tabel rundown rinci (baris 551–720) belum memiliki span terpisah.

---

## C. Audit Konflik Sumber (`ambiguous_needs_review` — 7 Record)

| Document ID | Annotation ID | Evidence Pertama | Evidence Kedua | Jenis Konflik | Dampak Interpretasi |
| --- | --- | --- | --- | --- | --- |
| `DOC-011` | `GT-DOC-011-008` | Tabel Timeline: `October 15 – November 8, 2026` (`4967..5035`, l.174) | Preliminary 4. Submission Guidelines: `November 15 2026 at 23.59 WIB` (`6718..6785`, l.247) | Kontradiksi tanggal internal | Tenggat pengumpulan abstrak ambigu antara 8 Nov atau 15 Nov 2026. |
| `DOC-011` | `GT-DOC-011-009` | `November 15 2026 at 23.59 WIB` (`6718..6785`, l.247) | `October 15 – November 8, 2026` (`4967..5035`, l.174) | Kontradiksi tanggal internal | Pasangan konflik dengan `GT-DOC-011-008`. |
| `DOC-017` | `GT-DOC-017-004` | `Alur Lomba: Registrasi → Pengumpulan BMC → Join Grup WhatsApp → Pengumuman Pemenang` (`6704..6787`, l.292) | Hadiah & Benefit: `Top 10 Finalis` & `Top 25 Semifinalis` (`3160..3281`, l.131) | Inkonsistensi tahapan seleksi | Tidak jelas apakah ada babak semifinal/final atau hanya seleksi satu tahap. |
| `DOC-070` | `GT-DOC-070-007` | Bab II.B.2.b.a: `tanya-jawab selama 15 menit` (`14684..14781`, l.364) | Bab II.G.2.b.b: `sesi tanya jawab ... selama 30 menit` (`38595..38667`, l.1022) | Kontradiksi durasi internal | Durasi tanya-jawab Babak Final ambigu antara 15 menit atau 30 menit. |
| `DOC-053` | `GT-DOC-053-004` | Pendahuluan Hackathon: `Peserta, baik individu maupun tim` (`11682..11715`, l.372) | F.3 Hackathon: `minimal tiga orang dan paling banyak lima orang` (`15908..15967`, l.502) | Kontradiksi syarat tim + *scope mismatch* | Ambigu apakah individu boleh ikut Hackathon; sekaligus berada di unit CTF. |
| `DOC-053` | `GT-DOC-053-007` | Pendahuluan CTF: `total 7 tim yang masuk ke babak final` (`1037..1074`, l.28) | G.9 (`7337..7378`, l.231) & J.9 (`10799..10841`, l.346): `sepuluh tim` | Kontradiksi kuota finalis | Ambigu apakah 7 tim total atau 10 tim per kategori CTF yang lolos ke final. |
| `DOC-053` | `GT-DOC-053-009` | Timeline Hackathon: `1 Juli 2-26` (`13076..13131`, l.415) | Rundown TM Final Hackathon: `1 Juli 2026` (l.677) | Salah ketik tahun + *scope mismatch* | Tahun `2-26` seharusnya `2026`; sekaligus milik cabang Hackathon. |

### Kebijakan Evaluasi Konflik
1. **Verified annotations (66 record)**: digunakan pada perhitungan metrik utama (dengan pengecualian perlakuan *scope mismatch* `DOC-053` di bawah).
2. **Ambiguous annotations (7 record)**: dikecualikan sementara dari metrik utama (*Precision/Recall/F1*) dan dilaporkan terpisah.
3. **Prediksi parser yang bertentangan dengan sumber**: dicatat sebagai kasus *manual review*, tidak otomatis dianggap benar ataupun salah.

---

## D. Audit Khusus `DOC-053` (`Guidebook_Wreck_IT_7.0.txt`)

Struktur aktual [Guidebook_Wreck_IT_7.0.txt](file:///home/lalita/Projects/perlombaan/data/raw/txt/Guidebook_Wreck_IT_7.0.txt) terbagi atas 3 scope cabang berbeda:
- **CTF Umum (Shared A–E)**: char `15..5139` (baris 6–157)
- **CTF General (F–H + rundown)**: char `5140..8546` (baris 158–270) & baris 551–623
- **CTF Junior (I–J + rundown)**: char `8547..11138` (baris 271–358) & baris 624–674
- **Hackathon (A–H + rundown)**: char `11139..17234` (baris 359–550) & baris 675–720

Ketiganya memiliki *scope* persyaratan yang berbeda (CTF General terbuka umum 1–3 orang Jeopardy/Attack-Defense; CTF Junior khusus siswa SMA/SMK 1–3 orang; Hackathon tim 3–5 orang dengan proposal, video, dan GitHub repo). Karena Stage 3 menyatukan seluruh dokumen ke `DOC-053-BU-01` (`BR_CYBERSECURITY_CTF`), audit menemukan:
- **4 record `event_shared` valid**: `GT-DOC-053-001`, `GT-DOC-053-005`, `GT-DOC-053-006`, `GT-DOC-053-015`.
- **7 record CTF (`BR_CYBERSECURITY_CTF`) valid**: `GT-DOC-053-002`, `GT-DOC-053-003`, `GT-DOC-053-007`, `GT-DOC-053-008`, `GT-DOC-053-010`, `GT-DOC-053-012`, `GT-DOC-053-014`.
- **4 record `scope_mismatch` (milik Hackathon di bawah unit CTF)**: `GT-DOC-053-004`, `GT-DOC-053-009`, `GT-DOC-053-011`, `GT-DOC-053-013`.

> [!IMPORTANT]
> Saat mengevaluasi parser yang berjalan pada unit `DOC-053-BU-01` (`BR_CYBERSECURITY_CTF`), 4 record Hackathon tidak boleh dijadikan penalti *false negative* bagi ekstraktor CTF, melainkan harus dilaporkan terpisah sebagai efek keterbatasan segmentasi Stage 3.

---

## F. Audit Hash dan Pembekuan

Verifikasi ulang pada `2026-11-15T21:03+07:00` memastikan dataset beku **tidak berubah**:
- **File Ground Truth SHA-256**: `3688bf13191deae10776ab0c15105b359386f1f6441cfdb18048e6024f9448cd` (**COCOK**)
- **Canonical `annotations` SHA-256**: `200eb6e962e15310ea90d1bcd4895594bd5a30722aa2b9db7adbb97911b37cad` (**COCOK**)

---

## G. Rekomendasi Perbaikan (Untuk Versi `v1.1` tanpa Menimpa Dataset Beku)

1. Pertahankan file `v1.0` beku apa adanya; jika dilakukan pembaruan, terbitkan sebagai versi baru (`stage_4_4_blind_held_out_ground_truth_v1_1.json`).
2. Selaraskan cakupan `evidence_text` vs `requirement_description` pada 5 record (`GT-DOC-011-011`, `GT-DOC-017-004`, `GT-DOC-070-012`, `GT-DOC-053-007`, `GT-DOC-053-010`).
3. Tambahkan span eksplisit untuk `DOC-051` *Pitching & Demo*, `DOC-070` *Bab II.D.1.c & II.D.2*, dan `DOC-053` *Section H (Final General CTF)*.
4. Pisahkan pelaporan 4 record Hackathon pada `DOC-053` saat evaluasi Stage 4.4 berlangsung, dan jadwalkan pemecahan unit `DOC-053` (CTF vs Hackathon) pada revisi Stage 3 mendatang.

---

## H. Keputusan Akhir

**`GROUND_TRUTH_READY_WITH_LIMITATIONS`**  
Independensi anotasi, integritas hash pembekuan, dan ketepatan karakter 73/73 record terverifikasi penuh. Evaluasi *blind held-out* dapat dilanjutkan dengan syarat menerapkan kebijakan pengecualian sementara 7 record `ambiguous_needs_review` dari metrik utama serta memisahkan pelaporan 4 record `scope_mismatch` Hackathon pada `DOC-053`.
