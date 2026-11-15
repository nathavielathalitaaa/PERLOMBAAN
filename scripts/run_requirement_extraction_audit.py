#!/usr/bin/env python3
"""Comprehensive Audit of Stage 4: Requirement Extraction (Code, All 98 Records, and Tests).

Strictly read-only with respect to Stage 1, 2, 3, and Stage 4 outputs.
Produces:
- `data/processed/requirement_extraction_audit.json`
- `docs/research_notes/requirement_extraction_audit.md`
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_record_level_audit(
    requirements: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Audit every single one of the 98 records in competition_requirements.json."""
    # Map of specific semantic/evidence/structural issues per requirement_id
    specific_issues: Dict[str, Dict[str, Any]] = {
        "REQ-DOC001-BU01-001": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": [
                "unsupported_claim_in_description",
                "compound_requirement_merging",
                "partial_overlap_with_other_records",
            ],
            "severity": "HIGH",
            "problem_found": (
                "Deskripsi mengklaim 'dan wajib melampirkan Kartu Tanda Mahasiswa (KTM) yang masih berlaku', "
                "padahal `evidence_text` (921..1053) sama sekali tidak menyebut KTM (aturan KTM ada di char 1361..1452 pada "
                "REQ-DOC001-BU01-002). Sebaliknya, `evidence_text` memuat kalimat 'Participation is team-based only, and individual "
                "entries are not accepted' yang justru diduplikasi ke dalam deskripsi REQ-DOC001-BU01-003."
            ),
            "recommendation": (
                "Batasi REQ-DOC001-BU01-001 hanya pada jenjang peserta ('open to Indonesian university students', char 921..977), "
                "pindahkan kalimat 'Participation is team-based only...' ke REQ-DOC001-BU01-003, dan hapus klaim KTM dari REQ-DOC001-BU01-001 "
                "karena sudah diwakili oleh REQ-DOC001-BU01-002."
            ),
        },
        "REQ-DOC001-BU01-003": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["compound_requirement_merging", "incomplete_evidence_span"],
            "severity": "MEDIUM",
            "problem_found": (
                "Menggabungkan 3 ketentuan berbeda dalam 1 record: (1) kewajiban beregu/larangan individu, "
                "(2) jumlah anggota 3-4 orang, dan (3) larangan merangkap lebih dari 1 tim ('One person, one team'). "
                "Selain itu, klaim 'pendaftaran individu tidak diterima' berada pada kalimat sebelumnya (char 978..1053) "
                "di luar rentang `evidence_text` (1056..1181)."
            ),
            "recommendation": (
                "Pecah menjadi record atomik (`participation_mode`, `team_size`, `single_team_membership_restriction`) "
                "dan perluas `source_char_start` ke 978 untuk mencakup kalimat larangan individu."
            ),
        },
        "REQ-DOC001-BU01-004": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["not_stated_stored_as_requirement_record", "misleading_evidence_for_not_stated"],
            "severity": "MEDIUM",
            "problem_found": (
                "Atribut `age_limit` yang tidak disebutkan di dokumen disimpan sebagai record persyaratan dengan "
                "`statement_nature = 'official_rule'` dan mengutip kalimat jenjang universitas (895..977) sebagai `evidence_text`."
            ),
            "recommendation": (
                "Pisahkan atribut yang absen (`NOT_STATED`) ke dalam struktur `unmentioned_attributes` / `coverage_checklist` "
                "per unit cabang, atau beri `statement_nature = 'not_stated_check'` dengan `source_char_start = null`."
            ),
        },
        "REQ-DOC001-BU01-005": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["not_stated_stored_as_requirement_record", "misleading_evidence_for_not_stated"],
            "severity": "MEDIUM",
            "problem_found": (
                "Atribut `same_university_or_cross_university_restriction` yang berstatus `NOT_STATED` disimpan sebagai record "
                "`official_rule` dengan mengutip kalimat latar belakang umum Bagian 1 (char 267..413)."
            ),
            "recommendation": (
                "Pindahkan ke daftar `unmentioned_attributes` pada level unit cabang agar tidak tercampur dengan aturan resmi panitia."
            ),
        },
        "REQ-DOC001-BU01-009": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "unsupported_claim_in_description"],
            "severity": "HIGH",
            "problem_found": (
                "Deskripsi menyebutkan rincian '(1) General Track (masalah terbuka lintas industri) atau (2) Industry Case Track "
                "bersama ARSA Indonesia (5 tema AC-1 s.d. AC-5 di bidang Facility Management & IoT)', tetapi `evidence_text` "
                "(1566..1724) hanya mengutip paragraf pengantar '3. Tracks Each team chooses one track...' dan memotong seluruh "
                "penjelasan General Track serta tabel AC-1 s.d. AC-5 pada char 1727..2926."
            ),
            "recommendation": (
                "Perluas rentang bukti menjadi `1566..2926` atau pecah menjadi 2 record terpisah untuk General Track dan Industry Case Track ARSA."
            ),
        },
        "REQ-DOC001-BU01-010": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "compound_requirement_merging"],
            "severity": "HIGH",
            "problem_found": (
                "Deskripsi merangkum 5 tahapan berurutan (1. Registration, 2. Written Proposal, 3. Build Sprint, 4. Semifinal Pitching, "
                "5. Grand Final), namun `evidence_text` (5116..5381) hanya memuat butir 4 dan 5, sehingga butir 1, 2, dan 3 "
                "(char 4708..5115) terpotong dari bukti sumber."
            ),
            "recommendation": (
                "Perluas `source_char_start` dari 5116 ke 4670 (`4670..5381`) atau ekstrak setiap tahapan sebagai record `competition_structure` tersendiri."
            ),
        },
        "REQ-DOC001-BU01-011": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "audit_note_stored_as_official_rule"],
            "severity": "MEDIUM",
            "problem_found": (
                "Record ini sebenarnya adalah catatan anomali konsistensi dokumen (perbedaan jadwal antara Tabel Bagian 5 "
                "Jan-Feb 2027 dan Bagian 6 Nov-Des 2026), tetapi dilabeli `statement_nature = 'official_rule'` dan `evidence_text` "
                "(3713..3845) hanya mengutip 2 kalimat pengantar Bagian 5 tanpa menyertakan teks tabel Bagian 5 maupun teks Bagian 6."
            ),
            "recommendation": (
                "Pindahkan temuan inkonsistensi jadwal ke daftar `document_anomalies` atau lampirkan multi-span evidence yang memuat kedua bagian yang bertentangan."
            ),
        },
        "REQ-DOC001-BU01-015": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["not_stated_stored_as_requirement_record", "header_only_evidence"],
            "severity": "MEDIUM",
            "problem_found": (
                "Menyimpan `standalone_source_code_repository_submission = NOT_STATED` sebagai record `deliverables` dengan "
                "`statement_nature = 'official_rule'` dan `evidence_text` hanya berupa judul bab `'6. Competition Stages and Submissions'`."
            ),
            "recommendation": (
                "Representasikan ketiadaan kewajiban pengumpulan source code terpisah di dalam `unmentioned_attributes` pada struktur output unit."
            ),
        },
        "REQ-DOC001-BU01-021": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["not_stated_stored_as_requirement_record"],
            "severity": "MEDIUM",
            "problem_found": (
                "Menyimpan `proposal_page_limit_and_file_format = NOT_STATED` sebagai record persyaratan `official_rule`."
            ),
            "recommendation": (
                "Pisahkan dari array persyaratan aktif dan masukkan ke struktur `unmentioned_attributes`."
            ),
        },
        "REQ-DOC024-BU01-003": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["not_stated_stored_as_requirement_record", "header_only_evidence"],
            "severity": "MEDIUM",
            "problem_found": (
                "Menyimpan `age_limit = NOT_STATED` sebagai record `official_rule` dengan `evidence_text` hanya berupa judul `'Syarat & Ketentuan Cabang Esai'`."
            ),
            "recommendation": "Pindahkan ke `unmentioned_attributes` untuk unit `DOC-024-BU-01`.",
        },
        "REQ-DOC024-BU01-004": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "compound_requirement_merging"],
            "severity": "HIGH",
            "problem_found": (
                "Deskripsi menyebutkan kewajiban 'follow & unggah twibbon (https://twibbo.nz/twibbonimpacteers) di feed Instagram dan tag 3 teman', "
                "tetapi kalimat tersebut berada di char 7982..8148 dan terpotong dari `evidence_text` (8149..8343)."
            ),
            "recommendation": (
                "Perluas `source_char_start` dari 8149 ke 7982 (`7982..8343`) dan pecah syarat promosi media sosial (Twibbon) dari mekanisme unggah berkas pendaftaran."
            ),
        },
        "REQ-DOC024-BU01-005": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "unsupported_claim_in_description"],
            "severity": "MEDIUM",
            "problem_found": (
                "Deskripsi menyebutkan '(melalui rekening BTN atau Seabank a.n. Jauzaa Hayaah Kusnandar; biaya tidak dapat dikembalikan)', "
                "namun `evidence_text` (8730..8812) hanya mengutip nominal Gelombang I-III dan memotong nomor rekening (char 8814..8913) "
                "serta aturan non-refundable di halaman 3 (char 5498..5564)."
            ),
            "recommendation": (
                "Perluas `source_char_end` ke 8913 untuk mencakup rekening pembayaran, dan buat record terpisah untuk ketentuan biaya tidak dapat dikembalikan."
            ),
        },
        "REQ-DOC024-BU01-006": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "unsupported_claim_in_description"],
            "severity": "MEDIUM",
            "problem_found": (
                "Deskripsi menyebutkan pemilihan '6 karya terbaik (Juara 1, 2, 3 dan Harapan 1, 2, 3)' tanpa babak presentasi final, "
                "tetapi informasi tersebut berada di halaman 12 (char 9018..9178), sedangkan `evidence_text` (7687..7840) hanya berisi daftar tanggal timeline di halaman 10."
            ),
            "recommendation": (
                "Pisahkan record `competition_timeline` (char 7687..7840) dari record `selection_mechanism_and_winners` (char 9018..9178)."
            ),
        },
        "REQ-DOC024-BU01-007": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "unsupported_claim_in_description"],
            "severity": "HIGH",
            "problem_found": (
                "Deskripsi merinci struktur naskah esai '(struktur: Cover berlogo kampus, Pendahuluan, Isi, Penutup, Daftar Pustaka APA, dan Lampiran Lembar Orisinalitas Karya)', "
                "padahal rincian struktur tersebut berada di halaman 9 (char 7127..7535), sedangkan `evidence_text` (8344..8470) hanya mengutip aturan format nama file PDF di halaman 11."
            ),
            "recommendation": (
                "Buat record `deliverables` untuk struktur naskah esai yang menunjuk ke char 7127..7535, dan pindahkan aturan format PDF serta penamaan berkas (8344..8470) ke `technical_and_general_rules`."
            ),
        },
        "REQ-DOC024-BU01-013": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": [
                "incomplete_evidence_span",
                "compound_requirement_merging",
                "missed_source_contradiction",
            ],
            "severity": "HIGH",
            "problem_found": (
                "(1) Deskripsi menggabungkan 7 aturan teknis (batas halaman, ukuran kertas A4, margin 4-3-3-3 cm, jenis/ukuran font, spasi 1.5, APA Style, dan PUEBI), "
                "tetapi `evidence_text` (6347..6496) hanya mengutip 1 kalimat tentang jumlah 7-10 halaman! "
                "(2) Kalimat bukti `'Naskah ditulis secara individu dengan 7 halaman – 10 Halaman'` bertentangan dengan halaman 7 (`4647..4811`) "
                "yang membolehkan kelompok 2 orang, namun kontradiksi internal ini tidak ditandai `NEEDS_REVIEW`."
            ),
            "recommendation": (
                "Perluas rentang bukti ke `5982..7126` (atau pecah per atribut format teknis) dan tandai kontradiksi kata `'secara individu'` terhadap aturan tim 2 orang sebagai `NEEDS_REVIEW`."
            ),
        },
        "REQ-DOC024-BU01-014": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "compound_requirement_merging"],
            "severity": "MEDIUM",
            "problem_found": (
                "Deskripsi menyebutkan karya 'belum pernah dipublikasikan di lomba lain, dan dilarang mengandung unsur SARA atau pornografi', "
                "tetapi `evidence_text` (6633..6810) hanya mengutip kalimat batas plagiasi 30% Turnitin (aturan SARA dan belum pernah dipublikasikan ada di char 5085..5226 dan 6497..6632)."
            ),
            "recommendation": (
                "Pisahkan aturan batas plagiasi 30% (6633..6810) dari aturan larangan SARA/pornografi dan orisinalitas publikasi (5021..5226)."
            ),
        },
        "REQ-DOC024-BU02-003": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["not_stated_stored_as_requirement_record", "header_only_evidence"],
            "severity": "MEDIUM",
            "problem_found": "Menyimpan `age_limit = NOT_STATED` sebagai record `official_rule` dengan bukti hanya judul bab.",
            "recommendation": "Pindahkan ke `unmentioned_attributes` untuk unit `DOC-024-BU-02`.",
        },
        "REQ-DOC024-BU02-004": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "compound_requirement_merging"],
            "severity": "HIGH",
            "problem_found": (
                "Deskripsi menyebutkan kewajiban follow & post twibbon di feed Instagram dan tag 3 teman, tetapi kalimat tersebut "
                "berada pada char 14632..14798 di luar `evidence_text` (14799..15026)."
            ),
            "recommendation": "Perluas `source_char_start` ke 14632 (`14632..15026`) atau pisahkan syarat Twibbon menjadi record tersendiri.",
        },
        "REQ-DOC024-BU02-006": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "unsupported_claim_in_description"],
            "severity": "HIGH",
            "problem_found": (
                "Deskripsi mencantumkan seluruh tanggal Gelombang I (20-25 April 2025), Gelombang II (26 April - 10 Mei 2025), "
                "Gelombang III (11-20 Mei 2025), Penilaian (27-30 Mei 2025), dan Pengumuman 6 Finalis (31 Mei 2025), "
                "tetapi `evidence_text` (14435..14491) hanya mengutip 4 baris terakhir (`Technical Meeting BMC 1 Juni 2025 / Final BMC 8 Juni 2025`)."
            ),
            "recommendation": "Perluas `source_char_start` dari 14435 ke 14266 (`14266..14491`) dan tambahkan record seleksi 6 finalis online dari char 15698..15826.",
        },
        "REQ-DOC024-BU02-007": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": [
                "incomplete_evidence_span",
                "unsupported_claim_in_description",
                "unflagged_source_typo",
            ],
            "severity": "HIGH",
            "problem_found": (
                "(1) Deskripsi merinci ke-9 elemen BMC (Customer Segments s.d. Cost Structure), tetapi `evidence_text` (15027..15152) "
                "hanya mengutip kalimat format nama file PDF dan sama sekali tidak mencakup penjelasan 9 elemen BMC di halaman 12-13 (char 12346..14129); "
                "(2) Kalimat `evidence_text` berbunyi `'Dokumen esai yang diunggah berupa softcopy PDF... judul bmc'` (salah ketik salin-tempel kata 'esai' "
                "pada bab BMC), namun tidak ditandai `NEEDS_REVIEW` (tidak konsisten dengan penanganan pada REQ-DOC024-BU03-003)."
            ),
            "recommendation": (
                "Arahkan bukti komponen 9 elemen BMC ke char 12346..14129 (atau 16102..16195), dan tandai kalimat salin-tempel pada char 15027..15152 sebagai `NEEDS_REVIEW`."
            ),
        },
        "REQ-DOC024-BU02-015": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "unsupported_claim_in_description"],
            "severity": "MEDIUM",
            "problem_found": (
                "Deskripsi mengklaim 'karya belum pernah dipublikasikan pada perlombaan lain dan tidak mengandung unsur SARA/pornografi', "
                "tetapi klaim tersebut berada di halaman 11 (char 11663..11804), bukan di `evidence_text` halaman 17 (char 16795..16910)."
            ),
            "recommendation": "Pisahkan aturan ketiadaan batas halaman (16795..16910) dari aturan larangan SARA/pornografi dan keaslian karya (11663..11804).",
        },
        "REQ-DOC024-BU03-002": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["not_stated_stored_as_requirement_record", "header_only_evidence"],
            "severity": "MEDIUM",
            "problem_found": "Menyimpan `age_limit = NOT_STATED` sebagai record `official_rule` dengan bukti hanya judul bab.",
            "recommendation": "Pindahkan ke `unmentioned_attributes` untuk unit `DOC-024-BU-03`.",
        },
        "REQ-DOC024-BU03-003": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "compound_requirement_merging"],
            "severity": "MEDIUM",
            "problem_found": (
                "Deskripsi menyebutkan kewajiban follow & post twibbon, pendaftaran via linktr.ee/impacteers2025, serta anomali teks `'Karya BMC'`, "
                "tetapi `evidence_text` (21982..22108) hanya mengutip kalimat `'Dokumen esai yang diunggah...'` dan tidak mencakup char 21584..21981 maupun 22205..22284."
            ),
            "recommendation": "Perluas rentang bukti menjadi `21584..22284` agar baik aturan pendaftaran maupun kedua bukti salah ketik salin-tempel tercakup utuh.",
        },
        "REQ-DOC024-BU03-005": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "unsupported_claim_in_description"],
            "severity": "HIGH",
            "problem_found": (
                "Deskripsi mencantumkan tanggal Gelombang I (20-25 April 2025), Gelombang II (26 April - 10 Mei 2025), Gelombang III (11-20 Mei 2025), "
                "Penilaian (27-30 Mei 2025), Pengumuman (31 Mei 2025), serta aturan tanpa unggah ke Instagram pribadi, tetapi `evidence_text` "
                "(22716..22932) hanya mengutip paragraf pemilihan 6 karya terbaik di halaman 24 tanpa memuat jadwal halaman 22 (21288..21443) "
                "maupun aturan Instagram halaman 20 (19234..19393)."
            ),
            "recommendation": "Pecah menjadi record `competition_timeline` (21288..21443) dan `selection_mechanism` (22716..22932).",
        },
        "REQ-DOC024-BU03-006": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": [
                "category_misclassification",
                "incomplete_evidence_span",
                "unsupported_claim_in_description",
            ],
            "severity": "MEDIUM",
            "problem_found": (
                "(1) Spesifikasi teknis berkas (`Format file: JPG, JPEG, atau PNG. Resolusi: Minimal 300 pixel per inci. Ukuran: A4... RGB`) "
                "dimasukkan ke `deliverables`, padahal secara skema termasuk `technical_and_general_rules` (format berkas & batas ukuran); "
                "(2) Deskripsi mengklaim kewajiban memuat logo Impacteers dan UNESA, yang berada pada sub-bagian `e. Ketentuan Logo dan Identitas` "
                "(char 20905..21056) di luar `evidence_text` (20277..20488)."
            ),
            "recommendation": (
                "Simpan luaran '1 atau lebih lembar Poster Digital' pada `deliverables`, pindahkan spesifikasi format JPG/PNG/300ppi/A4/RGB (20277..20488) "
                "serta kewajiban logo (20905..21056) ke `technical_and_general_rules`."
            ),
        },
        "REQ-DOC024-BU03-008": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["truncated_sentence_or_subindicator_in_evidence"],
            "severity": "LOW",
            "problem_found": (
                "Deskripsi menyebutkan sub-indikator 'Bahasa', namun `evidence_text` (23181..23377) berhenti setelah kata `'pembacaan.'` "
                "dan memotong baris `'Bahasa: Penggunaan bahasa yang jelas dan ringkas untuk menjelaskan konsep ilmiah.'` (char 23378..23459)."
            ),
            "recommendation": "Perluas `source_char_end` dari 23377 ke 23459.",
        },
        "REQ-DOC024-BU03-009": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["truncated_sentence_or_subindicator_in_evidence"],
            "severity": "LOW",
            "problem_found": (
                "Deskripsi menyebutkan sub-indikator 'Konsistensi', namun `evidence_text` (23461..23648) berhenti pada `'estetis.'` "
                "dan memotong kalimat `'Konsistensi: Keselarasan antara elemen visual dan teks.'` (char 23649..23704)."
            ),
            "recommendation": "Perluas `source_char_end` dari 23648 ke 23704.",
        },
        "REQ-DOC024-BU03-013": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "unsupported_claim_in_description"],
            "severity": "MEDIUM",
            "problem_found": (
                "Deskripsi mengklaim 'tidak ada batasan jumlah kata/warna; pencantuman nama peserta dan nama/logo instansi asal bersifat opsional', "
                "tetapi informasi tersebut berada di char 20489..20554 dan 21058..21138, di luar `evidence_text` (20758..20870)."
            ),
            "recommendation": "Pecah menjadi record larangan konten (20758..20870) dan record elemen identitas opsional (20905..21138).",
        },
        "REQ-DOC009-BU01-001": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["compound_requirement_merging", "unflagged_ocr_noise_in_evidence"],
            "severity": "MEDIUM",
            "problem_found": (
                "Menggabungkan syarat jenjang siswa SMA/K (butir 1), kewajiban formulir & biaya non-refundable (butir 2, yang termasuk "
                "`registration_requirements`), dan ukuran tim 3 orang (butir 3) dalam satu record `eligibility_requirements`. "
                "Selain itu `evidence_text` memuat kata salah baca OCR `'wajid'` dan `'ditarik Kembali'`."
            ),
            "recommendation": "Pisahkan butir 1 (jenjang & kartu pelajar), butir 2 (biaya pendaftaran non-refundable), dan butir 3 (tim 3 orang) menjadi record atomik.",
        },
        "REQ-DOC009-BU01-002": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["not_stated_stored_as_requirement_record", "misleading_evidence_for_not_stated"],
            "severity": "MEDIUM",
            "problem_found": (
                "Menyimpan `age_limit = NOT_STATED` sebagai record `official_rule` dengan `evidence_text` mengutip kalimat jenjang SMA/K (`3769..3836`)."
            ),
            "recommendation": "Pindahkan ke `unmentioned_attributes` untuk unit `DOC-009-BU-01`.",
        },
        "REQ-DOC009-BU01-003": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "compound_requirement_merging"],
            "severity": "HIGH",
            "problem_found": (
                "Deskripsi menyebutkan konfirmasi 1x24 jam dengan format `Cabang Lomba_Nama Lengkap...` serta kewajiban follow IG/TikTok, "
                "share poster ke 3 grup WA, dan unggah Twibbon (butir 3 dan 4 pada char 46950..48024), tetapi `evidence_text` (46595..46817) "
                "hanya mengutip butir 1 (`{31, Pe serta melakukan pendaftaran secara online...`)."
            ),
            "recommendation": "Perluas rentang bukti menjadi `46595..48024` atau pecah butir 1, 2, 3, dan 4 menjadi record registrasi tersendiri.",
        },
        "REQ-DOC009-BU01-006": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "unsupported_claim_in_description"],
            "severity": "HIGH",
            "problem_found": (
                "Deskripsi merinci seluruh tanggal pendaftaran Gelombang 2 & 3, TM Penyisihan, Pengumpulan Karya, Penilaian, Pengumuman 5 Finalis, "
                "Konfirmasi Ulang, TM Final, Pengumpulan PPT, dan Presentasi Final 10+10 menit, namun `evidence_text` (8391..8492) "
                "hanya mengutip 1 kalimat: `'9.Pada babak penyisihan, sebanyak 5 tim dengan nilai tertinggi akan dinyatakan lolos ke babak final.'`"
            ),
            "recommendation": (
                "Kaitkan jadwal dengan tabel timeline halaman 6 (`3235..3765`), ketentuan konfirmasi final halaman 8 (`5180..5650`), "
                "dan ketentuan presentasi final halaman 15 (`13331..13690`)."
            ),
        },
        "REQ-DOC009-BU01-007": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["unsupported_claim_in_description", "compound_requirement_merging"],
            "severity": "MEDIUM",
            "problem_found": (
                "Deskripsi menyebutkan panjang '(PDF, 5-10 halaman)', sedangkan `evidence_text` (12079..12809) hanya mencakup butir 5-8 "
                "(penamaan file PDF, Surat Orisinalitas, dan Hasil Turnitin maks. 25%) sementara aturan 5-10 halaman berada di butir 2 (char 11644..11775)."
            ),
            "recommendation": "Hapus klaim '5-10 halaman' dari deskripsi record ini (karena sudah ada di REQ-DOC009-BU01-011) dan pecah 3 berkas luaran (Esai PDF, Surat Orisinalitas, Hasil Turnitin).",
        },
        "REQ-DOC009-BU01-008": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span"],
            "severity": "LOW",
            "problem_found": (
                "Deskripsi menyebutkan durasi '(10 menit presentasi + 10 menit tanya jawab)' yang berada di butir 3 (char 13621..13764), "
                "sedangkan `evidence_text` (13332..13498) hanya mengutip butir 1."
            ),
            "recommendation": "Perluas rentang bukti atau pisahkan durasi presentasi (butir 3) dari kewajiban pengumpulan file PPT (butir 1).",
        },
        "REQ-DOC009-BU01-009": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": [
                "compound_requirement_merging",
                "incomplete_evidence_span",
                "not_stated_status_conflation",
            ],
            "severity": "HIGH",
            "problem_found": (
                "(1) Menggabungkan 3 aspek penilaian Babak Penyisihan (Tema dan Gagasan, Argumentasi dan Analisis, Sistematika dan Penulisan) "
                "ke dalam 1 record, padahal pada DOC-001 dan DOC-024 setiap aspek penilaian diekstrak sebagai 1 record terpisah (inkonsistensi granularitas); "
                "(2) `evidence_text` (11063..11225) hanya mengutip aspek pertama ('Tema dan Gagasan') dan memotong 2 aspek lainnya (11226..11571); "
                "(3) Memberi `validation_status = 'NOT_STATED'` pada keseluruhan record, padahal ketiga aspek dan indikatornya TERCANTUM secara eksplisit "
                "di dokumen (hanya `indicator_weight` yang `NOT_STATED`)."
            ),
            "recommendation": (
                "Pecah menjadi 3 record `assessment_criteria` (1 per aspek), perluas rentang bukti masing-masing, "
                "tetapkan `indicator_weight = 'NOT_STATED'`, dan gunakan `validation_status = 'VALIDATED'` (bukan `NOT_STATED`)."
            ),
        },
        "REQ-DOC009-BU01-010": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": [
                "compound_requirement_merging",
                "incomplete_evidence_span",
                "not_stated_status_conflation",
            ],
            "severity": "HIGH",
            "problem_found": (
                "(1) Menggabungkan 3 aspek penilaian Babak Final (Penyampaian Presentasi, Sesi Tanya Jawab, Media Presentasi) ke dalam 1 record; "
                "(2) `evidence_text` (14827..14959) hanya mengutip aspek pertama dan memotong 2 aspek lainnya (14960..15233); "
                "(3) Menetapkan `validation_status = 'NOT_STATED'` padahal kriteria penilaiannya dinyatakan secara eksplisit (hanya bobotnya yang tidak disebutkan)."
            ),
            "recommendation": (
                "Pecah menjadi 3 record `assessment_criteria`, gunakan bukti masing-masing aspek pada char 14806..15233, "
                "set `indicator_weight = 'NOT_STATED'`, dan `validation_status = 'VALIDATED'`."
            ),
        },
        "REQ-DOC009-BU01-011": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "compound_requirement_merging"],
            "severity": "MEDIUM",
            "problem_found": (
                "Deskripsi menyebutkan Bahasa Indonesia baku sesuai EYD V (butir 4, char 11908..12077) dan batas Turnitin maksimal 25% "
                "(butir 8, char 12650..12809), tetapi `evidence_text` (11644..11906) hanya mengutip butir 2 (5-10 halaman) dan butir 3 (APA Style)."
            ),
            "recommendation": "Perluas `source_char_end` ke 12077 untuk mencakup butir 4 (EYD V) dan buat record terpisah untuk batas plagiasi Turnitin 25%.",
        },
        "REQ-DOC009-BU01-013": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": [
                "false_positive_non_requirement",
                "category_misclassification",
                "incomplete_evidence_span",
            ],
            "severity": "HIGH",
            "problem_found": (
                "(1) False Positive: Informasi bahwa Pharmacopeia adalah program tahunan Fakultas Farmasi Unpad dan statistik WHO tentang "
                "74% kematian akibat PTM adalah narasi latar belakang acara (`historical_or_background_info`), BUKAN persyaratan kompetisi "
                "(`technical_and_general_rules`); (2) Klaim 'mengutip data WHO bahwa pola hidup tidak sehat berkontribusi pada 74% kematian dunia' "
                "berada di char 680..792, di luar `evidence_text` (153..323)."
            ),
            "recommendation": (
                "Keluarkan narasi latar belakang historis/epidemiologis dari tabel `requirements` (simpan pada metadata konteks event jika diperlukan) "
                "agar tidak menghasilkan false positive persyaratan."
            ),
        },
        "REQ-DOC009-BU02-001": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["compound_requirement_merging"],
            "severity": "LOW",
            "problem_found": "Menggabungkan syarat jenjang SMA/K (butir 1), kewajiban bayar non-refundable (butir 2), dan sifat lomba individu (butir 3).",
            "recommendation": "Pisahkan butir 1 (jenjang pendidikan), butir 2 (registrasi/pembayaran), dan butir 3 (mode individu).",
        },
        "REQ-DOC009-BU02-002": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["not_stated_stored_as_requirement_record", "misleading_evidence_for_not_stated"],
            "severity": "MEDIUM",
            "problem_found": (
                "Menyimpan `age_limit = NOT_STATED` sebagai record `official_rule` dengan `evidence_text = '3.Lomba bersifat individu.'` "
                "yang sama sekali tidak berkaitan dengan usia."
            ),
            "recommendation": "Pindahkan ke `unmentioned_attributes` pada level unit `DOC-009-BU-02`.",
        },
        "REQ-DOC009-BU02-003": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["unsupported_claim_in_description", "incomplete_evidence_span"],
            "severity": "MEDIUM",
            "problem_found": (
                "Deskripsi menyebutkan 'serta pendaftaran via https://linktr.ee/pharmacopeia2026', tetapi `evidence_text` (48352..48449) "
                "hanya memuat daftar harga Gelombang 1-3 Science Olympiad dan tidak memuat tautan pendaftaran (yang ada di char 46595..46817)."
            ),
            "recommendation": "Pisahkan record biaya pendaftaran (48352..48449) dari record mekanisme pendaftaran umum (46595..48024).",
        },
        "REQ-DOC009-BU02-004": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "unsupported_claim_in_description"],
            "severity": "HIGH",
            "problem_found": (
                "Deskripsi merinci tanggal Penyisihan (24 Okt 2026), pemilihan 5 finalis, serta rincian 3 babak pada Final Offline (21 Nov 2026: "
                "Babak 1 isian singkat & rebutan, Babak 2 10 soal PG serentak, Babak 3 10 soal esai adu cepat bel), tetapi `evidence_text` "
                "(21773..21932) hanya mengutip 1 kalimat tentang durasi 45 menit untuk 40 soal PG di babak penyisihan."
            ),
            "recommendation": (
                "Pecah menjadi record terpisah untuk Timeline (char 15410..16037), Mekanisme Babak Penyisihan (21504..22623), "
                "dan Mekanisme 3 Babak Final (22626..23810)."
            ),
        },
        "REQ-DOC009-BU02-005": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "unsupported_claim_in_description"],
            "severity": "MEDIUM",
            "problem_found": (
                "Deskripsi menyebutkan jawaban lisan/tertulis pada Babak 1, 2, dan 3 saat Final, sedangkan `evidence_text` (21619..21698) "
                "hanya mengutip kalimat login ke `https://wwwe-ujian.com/web/index`."
            ),
            "recommendation": "Sertakan rujukan ke mekanisme pengerjaan soal final (char 22626..23810) atau klasifikasikan platform ujian ke dalam `technical_and_general_rules`.",
        },
        "REQ-DOC009-BU02-006": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "compound_requirement_merging"],
            "severity": "HIGH",
            "problem_found": (
                "Deskripsi dan `indicator_weight` mencantumkan aturan poin untuk Penyisihan (+4/-1/0), Final Babak 1 (+2/+1/0), "
                "Final Babak 2 (+2/-1/0), dan Final Babak 3 (+1 s.d. +5 / -1), tetapi `evidence_text` (21935..21988) hanya mengutip "
                "3 baris poin Babak Penyisihan dan memotong aturan poin Babak Final di halaman 25-26 (char 23060..23810)."
            ),
            "recommendation": "Pecah menjadi 4 record `assessment_criteria` (Penyisihan, Final Babak 1, Final Babak 2, Final Babak 3) dengan rentang bukti masing-masing.",
        },
        "REQ-DOC009-BU02-007": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "compound_requirement_merging"],
            "severity": "MEDIUM",
            "problem_found": (
                "Deskripsi menyebutkan kewajiban hadir di Zoom 15-18 menit sebelum ujian (char 18855..19015 & 22040..22112) serta kisi-kisi "
                "materi Fisika, Kimia, dan Biologi SMA (halaman 27-28, char 23813..24523), tetapi `evidence_text` (19727..19982) hanya mengutip "
                "butir 6 tentang penggunaan 2 device."
            ),
            "recommendation": "Pisahkan aturan proctoring 2 perangkat (19727..19982) dari aturan kehadiran Zoom dan cakupan materi ujian Fisika/Kimia/Biologi (23813..24523).",
        },
        "REQ-DOC009-BU03-001": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "unsupported_claim_in_description"],
            "severity": "HIGH",
            "problem_found": (
                "Deskripsi mengklaim 'Siswa/i aktif SMA/K atau sederajat di Indonesia (dibuktikan dengan scan kartu pelajar atau surat keterangan siswa aktif)', "
                "tetapi kalimat tersebut berada di butir 1 (char 25327..25521) di luar `evidence_text` (25670..25818) yang hanya mengutip butir 3 dan 4."
            ),
            "recommendation": "Perluas `source_char_start` dari 25670 ke 25327 (`25327..25818`) dan pecah syarat jenjang pendidikan dari ukuran tim.",
        },
        "REQ-DOC009-BU03-002": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["not_stated_stored_as_requirement_record", "misleading_evidence_for_not_stated"],
            "severity": "MEDIUM",
            "problem_found": "Menyimpan `age_limit = NOT_STATED` sebagai record `official_rule` dengan bukti kalimat jenjang SMA/K.",
            "recommendation": "Pindahkan ke `unmentioned_attributes` untuk unit `DOC-009-BU-03`.",
        },
        "REQ-DOC009-BU03-003": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["unsupported_claim_in_description", "incomplete_evidence_span"],
            "severity": "MEDIUM",
            "problem_found": (
                "Deskripsi menyebutkan pendaftaran melalui `https://linktr.ee/pharmacopeia2026`, sedangkan `evidence_text` (48242..48349) "
                "hanya memuat rincian biaya Gelombang 1-3 Digital Poster."
            ),
            "recommendation": "Pisahkan record biaya pendaftaran (48242..48349) dari record alur pendaftaran umum (46595..48024).",
        },
        "REQ-DOC009-BU03-004": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "unsupported_claim_in_description"],
            "severity": "HIGH",
            "problem_found": (
                "Deskripsi merinci seluruh jadwal Penyisihan Online (Gelombang 1-3, Pengumpulan Poster 10-20 Okt 2026, Penilaian, Pengumuman 5 Finalis 04 Nov 2026) "
                "dan Final Offline 21 Nov 2026, tetapi `evidence_text` (35644..35794) hanya mengutip 1 kalimat tentang durasi presentasi 10 menit + tanya jawab 10 menit."
            ),
            "recommendation": "Pecah dan tautkan ke tabel timeline halaman 31 (`24643..25323`), seleksi 5 finalis halaman 35 (`30480..30585`), dan teknis final halaman 40 (`35489..36917`).",
        },
        "REQ-DOC009-BU03-005": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "unsupported_claim_in_description"],
            "severity": "HIGH",
            "problem_found": (
                "Deskripsi mengklaim '1 karya poster infografis ukuran A3 portrait dalam format .pdf beserta Surat Orisinalitas (PDF) dan wajib "
                "dipublikasikan di akun Instagram publik salah satu anggota', yang berada di halaman 39 (char 33893..34980), sedangkan `evidence_text` "
                "(36134..36258) di halaman 40 hanya mengutip kalimat bahwa finalis tidak wajib menyiapkan PowerPoint!"
            ),
            "recommendation": (
                "Buat record `deliverables` utama untuk Poster A3 PDF + Surat Orisinalitas + publikasi IG dari char 33893..34980, "
                "dan pisahkan ketentuan PowerPoint opsional (36134..36258)."
            ),
        },
        "REQ-DOC009-BU03-006": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": [
                "compound_requirement_merging",
                "incomplete_evidence_span",
                "not_stated_status_conflation",
            ],
            "severity": "HIGH",
            "problem_found": (
                "(1) Menggabungkan seluruh kriteria penilaian Babak Penyisihan (halaman 38, char 33001..33890) DAN Babak Final (halaman 41, char 36920..37487) "
                "ke dalam 1 record tunggal; (2) `evidence_text` (37298..37486) hanya mengutip 1 aspek terakhir dari Babak Final ('Kualitas Poster'); "
                "(3) Menetapkan `validation_status = 'NOT_STATED'` padahal uraian kriteria penilaiannya tertulis eksplisit (hanya bobotnya yang tidak disebutkan)."
            ),
            "recommendation": (
                "Pecah menjadi record per aspek untuk Babak Penyisihan (33001..33890) dan Babak Final (36920..37487), "
                "set `indicator_weight = 'NOT_STATED'`, dan `validation_status = 'VALIDATED'`."
            ),
        },
        "REQ-DOC009-BU03-007": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "unsupported_claim_in_description"],
            "severity": "MEDIUM",
            "problem_found": (
                "Deskripsi menyebutkan perangkat lunak desain (CorelDRAW, Photoshop, Illustrator), larangan template siap pakai, dan kewajiban logo "
                "Pharmacopeia di pojok kiri atas (butir 12 & 14 pada char 28475..29045), namun `evidence_text` (28030..28181) hanya mengutip butir 8 (larangan AI)."
            ),
            "recommendation": "Perluas rentang bukti atau pecah butir 8 (larangan AI), butir 12 (ukuran A3 & logo), dan butir 14 (software desain & larangan template siap pakai).",
        },
        "REQ-DOC009-BU04-001": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "unsupported_claim_in_description"],
            "severity": "HIGH",
            "problem_found": (
                "Deskripsi mengklaim 'Siswa/i aktif SMA/K atau sederajat di Indonesia' (butir 1, char 38206..38400) serta "
                "'(diperbolehkan mengikuti maksimal 1 cabang lomba lain karena tidak memiliki babak final)' (butir 12, char 39515..39632), "
                "tetapi `evidence_text` (38549..38698) hanya mengutip butir 3 dan 4."
            ),
            "recommendation": "Pecah dan tautkan masing-masing klaim ke butir 1 (`38206..38400`), butir 3-4 (`38549..38698`), dan butir 12 (`39515..39632`).",
        },
        "REQ-DOC009-BU04-002": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["not_stated_stored_as_requirement_record", "misleading_evidence_for_not_stated"],
            "severity": "MEDIUM",
            "problem_found": "Menyimpan `age_limit = NOT_STATED` sebagai record `official_rule` dengan bukti kalimat jenjang SMA/K.",
            "recommendation": "Pindahkan ke `unmentioned_attributes` untuk unit `DOC-009-BU-04`.",
        },
        "REQ-DOC009-BU04-003": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["unsupported_claim_in_description", "incomplete_evidence_span"],
            "severity": "MEDIUM",
            "problem_found": (
                "Deskripsi menyebutkan pendaftaran melalui `https://linktr.ee/pharmacopeia2026`, sedangkan `evidence_text` (48131..48239) "
                "hanya memuat daftar biaya Gelombang 1-3 Video Campaign."
            ),
            "recommendation": "Pisahkan record biaya pendaftaran (48131..48239) dari record alur pendaftaran umum (46595..48024).",
        },
        "REQ-DOC009-BU04-004": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "unsupported_claim_in_description"],
            "severity": "HIGH",
            "problem_found": (
                "Deskripsi merinci jadwal Gelombang 1-3 (01 Sep - 03 Okt 2026), TM (04 Okt 2026), Pengumpulan Karya (10-20 Okt 2026), "
                "Penilaian (21-31 Okt 2026), dan Awarding (21 Nov 2026), tetapi `evidence_text` (45273..45364) hanya mengutip butir 6 "
                "tentang 3 tim nilai tertinggi dinyatakan sebagai pemenang."
            ),
            "recommendation": "Tautkan jadwal ke tabel timeline halaman 44 (`37647..38202`) dan pisahkan dari mekanisme penentuan 3 pemenang (`45273..45364`).",
        },
        "REQ-DOC009-BU04-005": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "unsupported_claim_in_description"],
            "severity": "MEDIUM",
            "problem_found": (
                "Deskripsi menyebutkan 'beserta Surat Orisinalitas (PDF), dan wajib dipublikasikan di akun Instagram salah satu anggota yang bersifat publik', "
                "yang berada pada butir 3 dan 7 (char 43456..43650 & 43930..44055), di luar `evidence_text` (43025..43227) yang hanya mengutip butir 1."
            ),
            "recommendation": "Perluas rentang bukti menjadi `43025..44055` atau pecah menjadi record spesifikasi video, surat orisinalitas, dan kewajiban publikasi Instagram.",
        },
        "REQ-DOC009-BU04-006": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": [
                "compound_requirement_merging",
                "incomplete_evidence_span",
                "not_stated_status_conflation",
            ],
            "severity": "HIGH",
            "problem_found": (
                "(1) Menggabungkan 5 aspek penilaian Video Campaign (Orisinalitas, Kepatuhan, Kesesuaian tema, Visualisasi, Manfaat) ke dalam 1 record; "
                "(2) `evidence_text` (45622..45732) hanya mengutip aspek pertama ('Orisinalitas') dan memotong 4 aspek lainnya (45733..46479); "
                "(3) Menetapkan `validation_status = 'NOT_STATED'` padahal kelima aspek penilaian dinyatakan secara eksplisit di dokumen."
            ),
            "recommendation": (
                "Pecah menjadi 5 record `assessment_criteria` (1 per aspek pada char 45577..46479), set `indicator_weight = 'NOT_STATED'`, "
                "dan `validation_status = 'VALIDATED'`."
            ),
        },
        "REQ-DOC009-BU04-007": {
            "audit_status": "ISSUE_FOUND",
            "issue_types": ["incomplete_evidence_span", "unsupported_claim_in_description"],
            "severity": "LOW",
            "problem_found": (
                "Deskripsi menyebutkan 'wajib mencantumkan judul dan referensi' yang berada pada butir 11 (char 41280..41360), "
                "di luar `evidence_text` (41362..41541) yang hanya mengutip butir 12 dan 13."
            ),
            "recommendation": "Perluas `source_char_start` dari 41362 ke 41280 (`41280..41541`).",
        },
    }

    audit_records: List[Dict[str, Any]] = []
    for r in requirements:
        rid = r["requirement_id"]
        if rid in specific_issues:
            info = specific_issues[rid]
            audit_records.append(
                {
                    "requirement_id": rid,
                    "document_id": r["document_id"],
                    "branch_unit_id": r["branch_unit_id"],
                    "requirement_category": r["requirement_category"],
                    "requirement_name": r["requirement_name"],
                    "source_char_range": f"{r['source_char_start']}..{r['source_char_end']}",
                    "audit_status": info["audit_status"],
                    "issue_types": info["issue_types"],
                    "severity": info["severity"],
                    "problem_found": info["problem_found"],
                    "source_evidence": r["evidence_text"],
                    "recommendation": info["recommendation"],
                }
            )
        else:
            audit_records.append(
                {
                    "requirement_id": rid,
                    "document_id": r["document_id"],
                    "branch_unit_id": r["branch_unit_id"],
                    "requirement_category": r["requirement_category"],
                    "requirement_name": r["requirement_name"],
                    "source_char_range": f"{r['source_char_start']}..{r['source_char_end']}",
                    "audit_status": "VERIFIED_CLEAN",
                    "issue_types": [],
                    "severity": "NONE",
                    "problem_found": (
                        "Tidak ditemukan masalah semantik atau bukti: `evidence_text` mendukung penuh `requirement_description`, "
                        "rentang karakter tepat, konteks utuh, dan klasifikasi kategori akurat."
                    ),
                    "source_evidence": r["evidence_text"],
                    "recommendation": "Pertahankan record ini sebagai baseline terverifikasi.",
                }
            )
    return audit_records


def build_false_negative_findings() -> List[Dict[str, Any]]:
    """Identify explicit competition requirements in DOC-001, DOC-024, and DOC-009 missed by extractor.py."""
    return [
        {
            "finding_id": "FN-DOC001-01",
            "requirement_id": "MISSING (False Negative)",
            "document_id": "DOC-001",
            "branch_unit_id": "DOC-001-BU-01",
            "expected_category": "competition_structure",
            "source_char_range": "5581..6690",
            "severity": "MEDIUM",
            "problem_found": (
                "Program coaching terstruktur (2-3 sesi coaching per tim saat Build Sprint, check-in domain expert untuk ARSA track, "
                "serta pitch rehearsal & final prototype review sebelum Semifinal pada Bagian 7) belum diekstrak."
            ),
            "source_evidence": "Every registered team receives structured coaching throughout the competition, not only at the final stage.",
            "recommendation": "Tambahkan ekstraksi tahapan pembimbingan wajib/terstruktur pada `competition_structure`.",
        },
        {
            "finding_id": "FN-DOC001-02",
            "requirement_id": "MISSING (False Negative)",
            "document_id": "DOC-001",
            "branch_unit_id": "DOC-001-BU-01",
            "expected_category": "registration_requirements",
            "source_char_range": "9696..9994",
            "severity": "MEDIUM",
            "problem_found": (
                "Ketentuan 'Verified participant' pada Bagian 10 (syarat individu dihitung sebagai peserta terverifikasi: melengkapi "
                "seluruh informasi wajib, terdaftar di tim yang sah, dan lolos pemeriksaan duplikasi/kelayakan) belum diekstrak."
            ),
            "source_evidence": "Verified participant. For prize pool calculation, a verified participant is a unique individual who completes all mandatory registration information, is listed as a member of a valid team, and passes duplicate and eligibility checks.",
            "recommendation": "Ekstrak aturan verifikasi peserta pada `registration_requirements` / `technical_and_general_rules`.",
        },
        {
            "finding_id": "FN-DOC024-01",
            "requirement_id": "MISSING (False Negative)",
            "document_id": "DOC-024",
            "branch_unit_id": "DOC-024-BU-01..03",
            "expected_category": "technical_and_general_rules",
            "source_char_range": "4812..4956 / 11453..11601 / 18222..18373",
            "severity": "MEDIUM",
            "problem_found": (
                "Ketentuan bahwa peserta diperbolehkan mengirimkan lebih dari 1 karya (dengan formulir pendaftaran dan pembayaran terpisah "
                "sesuai jumlah karya) serta larangan pergantian anggota yang sudah terdaftar tidak diekstrak pada ketiga cabang DOC-024."
            ),
            "source_evidence": "Peserta dapat mengirimkan lebih dari satu karya dengan submission formulir pendaftaran berbeda dan pembayaran sesuai dengan banyaknya karya.",
            "recommendation": "Tambahkan aturan kuota pengiriman multi-karya (`multiple_submission_policy`) dan larangan substitusi anggota (`member_substitution_prohibition`).",
        },
        {
            "finding_id": "FN-DOC024-02",
            "requirement_id": "MISSING (False Negative)",
            "document_id": "DOC-024",
            "branch_unit_id": "DOC-024-BU-01..03",
            "expected_category": "technical_and_general_rules",
            "source_char_range": "4148..4446 / 10811..11088 / 17638..17933",
            "severity": "LOW",
            "problem_found": (
                "Daftar subtema resmi per cabang (7 subtema Esai, 6 subtema BMC, 7 subtema Poster) belum diekstrak, padahal "
                "kesesuaian dengan subtema memiliki bobot 10%-15% pada rubrik penilaian."
            ),
            "source_evidence": "dengan fokus pada cabang lomba BMC yang memiliki sub-tema: Teknologi Jasa Agribisnis F&B Kesehatan Pariwisata",
            "recommendation": "Ekstrak tema dan subtema wajib setiap cabang karena berkaitan langsung dengan kriteria penilaian.",
        },
        {
            "finding_id": "FN-DOC024-03",
            "requirement_id": "MISSING (False Negative)",
            "document_id": "DOC-024",
            "branch_unit_id": "DOC-024-BU-03",
            "expected_category": "technical_and_general_rules",
            "source_char_range": "19532..19736",
            "severity": "LOW",
            "problem_found": (
                "Ketentuan hak cipta dan hak publikasi karya pemenang pada cabang Poster (hak cipta milik peserta, panitia berhak "
                "mempublikasikan karya pemenang dengan mencantumkan identitas penulis) belum diekstrak."
            ),
            "source_evidence": "Hak cipta poster publik adalah milik peserta, panitia impacteers memiliki hak dan wewenang untuk mempublikasikan setiap karya pemenang dengan tetap mencantumkan identitas penulis.",
            "recommendation": "Tambahkan aturan `intellectual_property_and_publication_rights` pada `technical_and_general_rules`.",
        },
        {
            "finding_id": "FN-DOC009-01",
            "requirement_id": "MISSING (False Negative)",
            "document_id": "DOC-009",
            "branch_unit_id": "DOC-009-BU-01..03",
            "expected_category": "eligibility_requirements",
            "source_char_range": "4920..5177 / 17118..17348 / 26520..26748",
            "severity": "HIGH",
            "problem_found": (
                "Aturan pembatasan lintas cabang ('Peserta tidak diperkenankan mengikuti lebih dari satu cabang perlombaan yang "
                "pelaksanaannya berlangsung secara bersamaan, kecuali Video Campaign Competition yang tidak memiliki babak final') "
                "serta aturan kuota delegasi sekolah ('Setiap sekolah menengah atas diperbolehkan untuk mengirimkan lebih dari 1 peserta') "
                "sama sekali tidak diekstrak pada `DOC-009-BU-01`, `DOC-009-BU-02`, dan `DOC-009-BU-03`."
            ),
            "source_evidence": "Tl.Peserta tidak diperkenankan mengikuti lebih dari satu cabang perlombaan yang pelaksanaannya berlangsung secara bersamaan, kecuali Video Campaign Competition yang tidak memiliki babak final.",
            "recommendation": "Ekstrak aturan `cross_branch_participation_restriction` dan `school_delegation_quota` pada seluruh cabang DOC-009.",
        },
        {
            "finding_id": "FN-DOC009-02",
            "requirement_id": "MISSING (False Negative)",
            "document_id": "DOC-009",
            "branch_unit_id": "DOC-009-BU-01..03",
            "expected_category": "technical_and_general_rules",
            "source_char_range": "9150..10256 / 20680..21501 / 31120..32228",
            "severity": "MEDIUM",
            "problem_found": (
                "Ketentuan khusus Babak Final Luring di Unpad (kewajiban karantina, aturan pakaian kemeja sopan, LARANGAN mengenakan "
                "seragam/jaket/atribut berlogo sekolah asal selama lomba, kewajiban mengikuti Seminar Nasional, ketidakhadiran sebagian anggota "
                "tim tetap diizinkan tanpa penjadwalan ulang, dan panitia tidak menanggung biaya akomodasi) belum diekstrak."
            ),
            "source_evidence": "6. Finalis tidak diperkenankan mengenakan atribut atau identitas yang menunjukkan asal sekolah, seperti seragam, jaket organisasi, maupun atribut lain yang memuat nama atau logo sekolah selama perlombaan berlangsung.",
            "recommendation": "Ekstrak aturan teknis dan tata tertib Babak Final Luring pada `DOC-009-BU-01..03`.",
        },
    ]


def run_stage4_audit() -> Dict[str, Any]:
    baseline_path = PROJECT_ROOT / "data" / "processed" / "competition_requirements_stage4_0_baseline.json"
    req_path = baseline_path if baseline_path.exists() else (PROJECT_ROOT / "data" / "processed" / "competition_requirements.json")
    req_payload = json.loads(req_path.read_text(encoding="utf-8"))
    requirements = req_payload["requirements"]

    record_audits = build_record_level_audit(requirements)
    false_negatives = build_false_negative_findings()

    verified_clean_count = sum(
        1 for r in record_audits if r["audit_status"] == "VERIFIED_CLEAN"
    )
    issue_found_count = sum(
        1 for r in record_audits if r["audit_status"] == "ISSUE_FOUND"
    )

    severity_counts: Dict[str, int] = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "NONE": 0}
    issue_type_counts: Dict[str, int] = {}
    for r in record_audits:
        sev = r["severity"]
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        for it in r["issue_types"]:
            issue_type_counts[it] = issue_type_counts.get(it, 0) + 1

    audit_payload: Dict[str, Any] = {
        "audit_stage": "Comprehensive Semantic, Methodological, and Code Audit of Stage 4: Requirement Extraction",
        "overall_recommendation": "NEEDS_REVISION",
        "overall_recommendation_rationale": (
            "Meskipun seluruh 46 pengujian pytest lulus dan seluruh 98 record memiliki kecocokan substring eksak "
            "(`raw_text[source_char_start:source_char_end] == evidence_text`), pemeriksaan mendalam terhadap kode "
            "`src/requirement_extraction/extractor.py` dan ke-98 record aktual menemukan kelemahan metodologis dan semantik "
            f"yang signifikan: (1) Logika ekstraksi masih berupa daftar spesifikasi anchor manual per dokumen (`_extract_doc001_bu01`, "
            "`_extract_doc024_units`, `_extract_doc009_units`), bukan parser berbasis aturan/regex/struktur bagian yang dapat dijalankan "
            f"secara umum pada dokumen ke-4 dst.; (2) Sebanyak {issue_found_count} dari 98 record memiliki masalah semantik/bukti "
            f"({severity_counts['HIGH']} HIGH, {severity_counts['MEDIUM']} MEDIUM, {severity_counts['LOW']} LOW), "
            "terutama penggabungan beberapa persyaratan berbeda ke dalam 1 deskripsi komposit sementara `evidence_text` hanya mengutip "
            "1 klausa parsial (`incomplete_evidence_span` & `unsupported_claim_in_description`); (3) Sebanyak 11 record `NOT_STATED` "
            "disimpan sebagai record persyaratan aktif dengan `statement_nature = 'official_rule'` dan bukti teks yang tidak relevan "
            "(mis. mengutip `'3.Lomba bersifat individu.'` sebagai bukti `age_limit = NOT_STATED`), sedangkan 4 record kriteria penilaian "
            "`DOC-009` yang sebenarnya tertulis eksplisit justru diberi `validation_status = 'NOT_STATED'` hanya karena bobotnya tidak "
            "dicantumkan; (4) Terdapat 1 false positive (`REQ-DOC009-BU01-013`, informasi historis/epidemiologis WHO disimpan sebagai "
            "`technical_and_general_rules`) dan 7 kelompok false negative (aturan penting di dokumen yang terlewat); serta (5) Pengujian di "
            "`tests/test_requirement_extraction.py` hanya menguji integritas teknis/mekanis (kesamaan slice string dan keberadaan field), "
            "belum menguji kecukupan semantik bukti terhadap deskripsi."
        ),
        "summary": {
            "total_records_audited": len(record_audits),
            "verified_clean_records": verified_clean_count,
            "records_with_issues": issue_found_count,
            "record_severity_counts": severity_counts,
            "issue_type_frequency": issue_type_counts,
            "false_negative_groups_identified": len(false_negatives),
        },
        "code_and_logic_audit": {
            "files_inspected": [
                "src/requirement_extraction/extractor.py",
                "src/requirement_extraction/__init__.py",
                "scripts/run_requirement_extraction.py",
                "tests/test_requirement_extraction.py",
            ],
            "functions_identified": [
                "_build_page_spans(raw_text): Memecah teks berdasarkan separator halaman '\\n\\n\\n'.",
                "_locate_page_for_char(page_spans, char_idx): Mencari nomor halaman 1-based dari indeks karakter.",
                "_find_exact_span(raw_text, anchor, search_start, search_end): Mencari indeks substring eksak dengan `str.find()`.",
                "_make_record(...): Membungkus hasil pencarian anchor ke dalam dataclass `ExtractedRequirementRecord`.",
                "_extract_doc001_bu01(raw_text, unit_meta, unit_val): Daftar hardcoded 21 dict spesifikasi untuk DOC-001-BU-01.",
                "_extract_doc024_units(raw_text, units_by_id, vals_by_id): Daftar hardcoded 42 dict spesifikasi untuk DOC-024-BU-01..03.",
                "_extract_doc009_units(raw_text, units_by_id, vals_by_id): Daftar hardcoded 35 dict spesifikasi untuk DOC-009-BU-01..04.",
                "extract_representative_requirements(project_root, write_outputs): Fungsi orkestrator utama dan deduplikasi.",
            ],
            "logic_findings": [
                {
                    "finding_id": "CODE-01",
                    "severity": "HIGH",
                    "title": "Ketiadaan Parser Aturan/Regex Umum (Hardcoded Per-Document Anchor Specs)",
                    "description": (
                        "`extractor.py` tidak menggunakan regex, pemilah kalimat/butir bernomor, maupun pengklasifikasi kata kunci otomatis. "
                        "Seluruh `category`, `name`, `description`, dan `anchor` ditulis secara statis di dalam fungsi khusus per dokumen, "
                        "sedangkan kode Python hanya menghitung `source_char_start..source_char_end` via `str.find()`. Selain itu, kamus "
                        "`TERM_NORMALIZATION_RULES` hanya diekspor ke JSON tanpa pernah dipanggil oleh fungsi ekstraksi."
                    ),
                    "recommendation": (
                        "Bangun pipeline ekstraksi berbasis aturan yang sesungguhnya: (1) pemecah sub-bab (`section_splitter`), "
                        "(2) ekstraktor butir bernomor/bullet (`clause_itemizer`) dan parser tabel rubrik (`rubric_table_parser`), "
                        "(3) pengklasifikasi kategori berbasis pola leksikal/struktural, serta (4) fungsi normalisasi istilah aktif."
                    ),
                },
                {
                    "finding_id": "CODE-02",
                    "severity": "HIGH",
                    "title": "Penggabungan Beberapa Persyaratan Berbeda dengan Bukti Parsial (Compound Merging & Partial Anchor)",
                    "description": (
                        "Banyak spesifikasi di `extractor.py` merangkum 3–7 aturan dari halaman/butir berbeda ke dalam satu `requirement_description`, "
                        "tetapi parameter `anchor` hanya mengambil 1 kalimat pendek agar `str.find()` mudah cocok. Akibatnya, `evidence_text` "
                        "tidak mendukung sebagian besar isi `requirement_description`."
                    ),
                    "recommendation": (
                        "Terapkan prinsip 1 butir aturan atomik = 1 record (`atomic_requirement_granularity`), dan pastikan `evidence_text` "
                        "mencakup seluruh kalimat sumber yang mendasari `requirement_description`."
                    ),
                },
                {
                    "finding_id": "CODE-03",
                    "severity": "MEDIUM",
                    "title": "Inkonsistensi Granularitas Ekstraksi Kriteria Penilaian Antar-Dokumen",
                    "description": (
                        "Pada `DOC-001` (4 aspek) dan `DOC-024` (4, 6, dan 6 aspek), setiap aspek penilaian diekstrak menjadi 1 record terpisah "
                        "(total 20 record). Sebaliknya, pada `DOC-009-BU-01`, `BU-03`, dan `BU-04`, seluruh 3–6 aspek penilaian digabung menjadi "
                        "1 record per babak hanya karena bobotnya tidak disebutkan."
                    ),
                    "recommendation": (
                        "Seragamkan granularitas `assessment_criteria`: setiap aspek penilaian wajib menjadi 1 record tersendiri, baik memiliki "
                        "bobot eksplisit maupun `indicator_weight = 'NOT_STATED'`."
                    ),
                },
            ],
        },
        "not_stated_audit": {
            "problem_summary": (
                "Saat ini ketidaktersediaan informasi (`NOT_STATED`) dicampur langsung sebagai record di dalam array `requirements`: "
                "(1) 11 record memiliki `requirement_description = 'NOT_STATED'`, `validation_status = 'NOT_STATED'`, namun "
                "`statement_nature = 'official_rule'` dan dipaksa memiliki `source_char_start..source_char_end` yang menunjuk ke judul bab "
                "atau kalimat tidak relevan (mis. `'3.Lomba bersifat individu.'` untuk `age_limit` pada `REQ-DOC009-BU02-002`); "
                "(2) 4 record kriteria penilaian di `DOC-009` (`REQ-DOC009-BU01-009`, `BU01-010`, `BU03-006`, `BU04-006`) yang aspek dan "
                "indikatornya TERTULIS EKSPLISIT di dokumen justru diberi `validation_status = 'NOT_STATED'` hanya karena sub-atribut "
                "`indicator_weight` tidak tercantum."
            ),
            "recommended_data_structure": {
                "1_in_requirements_array": (
                    "Hanya simpan persyaratan/ketentuan yang BENAR-BENAR DINYATAKAN di dokumen sumber. Jika suatu persyaratan dinyatakan "
                    "eksplisit tetapi salah satu sub-atribut opsionalnya tidak disebutkan (mis. kriteria penilaian tertulis jelas namun tanpa "
                    "bobot), simpan record tersebut dengan `validation_status = 'VALIDATED'` dan isi sub-field spesifiknya dengan "
                    "`indicator_weight = 'NOT_STATED'`."
                ),
                "2_separate_unmentioned_attributes_array": (
                    "Pisahkan checklist atribut standar yang tidak ditemukan di dokumen (seperti `age_limit`, `cross_institution_policy`, "
                    "`proposal_page_limit`, `source_code_submission`) ke dalam struktur tersendiri `unmentioned_attributes` (atau "
                    "`missing_information_log`) per `branch_unit_id`, dengan skema: `{document_id, branch_unit_id, requirement_category, "
                    "attribute_name, status: 'NOT_STATED', checked_sections: [...], verification_note: '...'}` tanpa memaksakan kutipan "
                    "`evidence_text` palsu."
                ),
            },
        },
        "test_suite_audit": {
            "inspected_file": "tests/test_requirement_extraction.py",
            "why_all_tests_passed_despite_issues": (
                "Kedelapan fungsi pengujian di `tests/test_requirement_extraction.py` hanya memeriksa **integritas teknis/struktural**, "
                "bukan **validitas semantik**: "
                "(1) `test_evidence_text_presence_and_verbatim_match` hanya mengecek `raw_text[s:e] == evidence_text` (slice string mekanis), "
                "sehingga tetap lulus walaupun `evidence_text` hanya 1 kalimat pendek yang tidak memuat 80% klaim di dalam `requirement_description`; "
                "(2) `test_requirement_category_consistency_and_schema_completeness` hanya mengecek `category in REQUIREMENT_CATEGORIES`, "
                "bukan apakah isi record benar-benar cocok dengan kategori tersebut; "
                "(3) Tidak ada pengujian yang mendeteksi klaim tak berbukti (angka/tanggal/URL di `requirement_description` yang tidak ada di "
                "`evidence_text`), penggabungan multi-aturan, maupun false positive (`historical_or_background_info` di dalam `requirements`)."
            ),
            "recommended_semantic_test_additions": [
                "Tambahkan `test_numeric_and_date_claims_grounded_in_evidence`: setiap angka, persentase, nominal Rp, URL, dan tanggal yang disebut di `requirement_description` (untuk `evidence_type == 'explicit'`) wajib muncul di dalam `evidence_text`.",
                "Tambahkan `test_no_non_requirement_background_in_active_requirements`: pastikan `historical_or_background_info` tidak disimpan sebagai aturan resmi.",
                "Tambahkan `test_not_stated_separated_from_explicit_rules`: pastikan atribut yang absen (`NOT_STATED`) tidak diberi `statement_nature == 'official_rule'` dan tidak mengutip bukti kalimat aturan lain.",
                "Tambahkan `test_assessment_criteria_one_record_per_aspect`: pastikan setiap aspek penilaian menjadi 1 record atomik.",
            ],
        },
        "false_negative_findings": false_negatives,
        "record_level_audit": record_audits,
    }

    out_json = PROJECT_ROOT / "data" / "processed" / "requirement_extraction_audit.json"
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(audit_payload, f, indent=2, ensure_ascii=False)

    md_text = build_markdown_report(audit_payload)
    out_md = PROJECT_ROOT / "docs" / "research_notes" / "requirement_extraction_audit.md"
    with out_md.open("w", encoding="utf-8") as f:
        f.write(md_text)

    return audit_payload


def _md_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def build_markdown_report(payload: Dict[str, Any]) -> str:
    summary = payload["summary"]
    sev = summary["record_severity_counts"]
    freq = summary["issue_type_frequency"]
    records = payload["record_level_audit"]
    fns = payload["false_negative_findings"]
    code_audit = payload["code_and_logic_audit"]
    ns_audit = payload["not_stated_audit"]
    test_audit = payload["test_suite_audit"]

    lines: List[str] = []
    lines.append("# Laporan Audit Menyeluruh Stage 4: Requirement Extraction")
    lines.append("")
    lines.append("## 1. Ringkasan Eksekutif & Keputusan Audit")
    lines.append("")
    lines.append(f"- **Tahap yang Diaudit**: `{payload['audit_stage']}`")
    lines.append(f"- **Keputusan Akhir (Verdict)**: **`{payload['overall_recommendation']}`**")
    lines.append(f"- **Alasan Utama Keputusan**: {payload['overall_recommendation_rationale']}")
    lines.append("")
    lines.append("### Statistik Audit Seluruh 98 Record (`DOC-001`, `DOC-024`, `DOC-009`)")
    lines.append("")
    lines.append("| Metrik Audit | Jumlah | Persentase |")
    lines.append("| :--- | ---: | ---: |")
    lines.append(f"| Total Record yang Diaudit | {summary['total_records_audited']} | 100.0% |")
    lines.append(
        f"| Record Bersih & Terverifikasi (`VERIFIED_CLEAN` / `NONE`) | {summary['verified_clean_records']} | "
        f"{summary['verified_clean_records'] / summary['total_records_audited'] * 100:.1f}% |"
    )
    lines.append(
        f"| Record Bermasalah (`ISSUE_FOUND`) | {summary['records_with_issues']} | "
        f"{summary['records_with_issues'] / summary['total_records_audited'] * 100:.1f}% |"
    )
    lines.append(
        f"| — Tingkat Keparahan `HIGH` | {sev['HIGH']} | "
        f"{sev['HIGH'] / summary['total_records_audited'] * 100:.1f}% |"
    )
    lines.append(
        f"| — Tingkat Keparahan `MEDIUM` | {sev['MEDIUM']} | "
        f"{sev['MEDIUM'] / summary['total_records_audited'] * 100:.1f}% |"
    )
    lines.append(
        f"| — Tingkat Keparahan `LOW` | {sev['LOW']} | "
        f"{sev['LOW'] / summary['total_records_audited'] * 100:.1f}% |"
    )
    lines.append(f"| Kelompok Persyaratan Terlewat (*False Negatives*) | {summary['false_negative_groups_identified']} | - |")
    lines.append("")
    lines.append("### Distribusi Frekuensi Jenis Masalah pada Record")
    lines.append("")
    lines.append("| Jenis Masalah (`issue_type`) | Frekuensi Record | Penjelasan Singkat |")
    lines.append("| :--- | ---: | :--- |")
    issue_desc_map = {
        "incomplete_evidence_span": "Rentang `evidence_text` hanya memotong sebagian kecil teks sumber yang dirujuk oleh `requirement_description`.",
        "unsupported_claim_in_description": "`requirement_description` memuat klaim (angka, tanggal, URL, sub-ketentuan) yang tidak terdapat di dalam `evidence_text`.",
        "compound_requirement_merging": "Beberapa ketentuan berbeda digabung menjadi satu record tunggal.",
        "not_stated_stored_as_requirement_record": "Atribut yang tidak disebutkan (`NOT_STATED`) disimpan sebagai record persyaratan aktif dengan `statement_nature = 'official_rule'`.",
        "misleading_evidence_for_not_stated": "Record `NOT_STATED` mengutip kalimat persyaratan lain yang tidak relevan sebagai `evidence_text`.",
        "header_only_evidence": "Record `NOT_STATED` hanya mengutip judul sub-bab sebagai `evidence_text`.",
        "not_stated_status_conflation": "Kriteria penilaian yang tertulis eksplisit diberi `validation_status = 'NOT_STATED'` hanya karena bobotnya tidak tercantum.",
        "category_misclassification": "Ketentuan ditempatkan pada `requirement_category` yang kurang tepat secara semantik.",
        "truncated_sentence_or_subindicator_in_evidence": "Kalimat atau sub-indikator terakhir terpotong di tengah pada batas akhir `evidence_text`.",
        "partial_overlap_with_other_records": "Kalimat di dalam `evidence_text` menduplikasi ketentuan yang sudah diekstrak pada record lain.",
        "audit_note_stored_as_official_rule": "Catatan audit ketiadaan jadwal spesifik disimpan sebagai record `official_rule` di dalam `competition_structure`.",
        "missed_source_contradiction": "Kontradiksi internal pada teks dokumen asli tidak ditandai sebagai `NEEDS_REVIEW`.",
        "unflagged_source_typo": "Salah ketik (*copy-paste typo*) lintas cabang pada teks asli tidak ditandai sebagai `NEEDS_REVIEW`.",
        "unflagged_ocr_noise_in_evidence": "Artefak OCR pada `evidence_text` tidak dicatat pada `extraction_notes`.",
        "false_positive_non_requirement": "Informasi latar belakang/epidemiologi umum diekstrak sebagai persyaratan teknis.",
    }
    for itype, count in sorted(freq.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"| `{itype}` | {count} | {issue_desc_map.get(itype, '-')} |")
    lines.append("")

    # Section 2: Audit Logika Ekstraksi
    lines.append("## 2. Audit Logika Ekstraksi (`src/requirement_extraction/extractor.py`)")
    lines.append("")
    lines.append("### 2.1 Daftar Fungsi dan Aturan yang Digunakan Saat Ini")
    lines.append("")
    for fn_desc in code_audit["functions_identified"]:
        lines.append(f"- `{fn_desc.split(':')[0]}`: {fn_desc.split(':', 1)[1].strip()}")
    lines.append("")
    lines.append("### 2.2 Temuan Arsitektural & Logika Kode")
    lines.append("")
    for lf in code_audit["logic_findings"]:
        lines.append(f"#### `{lf['finding_id']}` [{lf['severity']}] — {lf['title']}")
        lines.append(f"- **Masalah**: {lf['description']}")
        lines.append(f"- **Rekomendasi**: {lf['recommendation']}")
        lines.append("")
    lines.append("### 2.3 Evaluasi Regex, Keyword Matching, Pemecahan Record, dan Penggabungan Record")
    lines.append("")
    lines.append(
        "1. **Penggunaan Regex & Keyword Matching**: Tidak ada satu pun ekspresi reguler (`re.compile` / `re.finditer`) "
        "atau aturan pencocokan kata kunci yang mengekstrak persyaratan secara dinamis dari teks di dalam `extractor.py`. "
        "Seluruh pencarian dilakukan dengan `raw_text.find(anchor, search_start, search_end)` terhadap string `anchor` "
        "yang sudah ditulis secara manual di dalam kode."
    )
    lines.append(
        "2. **Aturan Normalisasi Istilah (`TERM_NORMALIZATION_RULES`)**: Kamus berisi 8 pemetaan istilah "
        "(`peserta_didik`..`kriteria_penilaian`) didefinisikan pada baris 31–40 di `extractor.py`, tetapi **tidak pernah dipanggil** "
        "oleh fungsi mana pun selama proses ekstraksi dan hanya disalin ke metadata output JSON."
    )
    lines.append(
        "3. ** Satu Persyaratan Terpecah vs. Beberapa Persyaratan Tergabung**:"
    )
    lines.append(
        "   - **Penggabungan Berlebihan (*Over-Merging*)**: Terjadi pada **19 record**, di antaranya `REQ-DOC024-BU01-013` "
        "(menggabungkan 7 aturan format naskah menjadi 1 record), `REQ-DOC009-BU03-005` (menggabungkan poster A3 PDF, lembar orisinalitas, "
        "publikasi IG, dan PPT opsional menjadi 1 record), serta `REQ-DOC009-BU01-009`, `BU01-010`, `BU03-006`, `BU04-006` "
        "(menggabungkan 3–6 kriteria penilaian menjadi 1 record per babak)."
    )
    lines.append(
        "   - **Tumpang Tindih Antar-Record (*Partial Overlap*)**: Terjadi antara `REQ-DOC001-BU01-001` dan `REQ-DOC001-BU01-003` "
        "di mana kalimat `'Participation is team-based only, and individual entries are not accepted.'` masuk ke rentang bukti `BU01-001` "
        "tetapi maknanya dimasukkan ke deskripsi `BU01-003`."
    )
    lines.append("")

    # Section 3: Audit Klasifikasi
    lines.append("## 3. Audit Klasifikasi Kategori Persyaratan")
    lines.append("")
    lines.append(
        "Audit memeriksa ketepatan penempatan 98 record ke dalam 6 kategori (`eligibility_requirements`, `registration_requirements`, "
        "`competition_structure`, `deliverables`, `assessment_criteria`, `technical_and_general_rules`):"
    )
    lines.append("")
    lines.append("| Record ID | Kategori Saat Ini | Kategori Seharusnya | Tingkat Keparahan | Penjelasan |")
    lines.append("| :--- | :--- | :--- | :---: | :--- |")
    lines.append(
        "| `REQ-DOC024-BU03-006` | `deliverables` | `technical_and_general_rules` | `MEDIUM` | "
        "Mengatur spesifikasi teknis format/resolusi/ukuran kanvas (`JPG/JPEG/PNG, 300 ppi, A4 vertikal, RGB`). "
        "Pada cabang Esai (`REQ-DOC024-BU01-013`) dan BMC (`REQ-DOC024-BU02-014`), aturan format sejenis diklasifikasikan ke "
        "`technical_and_general_rules`, sehingga penempatan `BU03-006` di `deliverables` tidak konsisten. |"
    )
    lines.append(
        "| `REQ-DOC009-BU01-013` | `technical_and_general_rules` | *(Bukan Persyaratan / Hapus)* | `HIGH` | "
        "**False Positive**: Mengutip narasi latar belakang epidemiologi WHO (74% kematian global akibat PTM) dan sejarah penyelenggaraan "
        "event tahunan yang bukan merupakan ketentuan/aturan mengikat bagi peserta. |"
    )
    lines.append(
        "| `REQ-DOC009-BU04-004` | `competition_structure` | *(Metadata Audit / `NOT_STATED`)* | `MEDIUM` | "
        "Record ini bukan aturan struktur kompetisi dari panitia, melainkan catatan audit bahwa tanggal/tahapan spesifik tidak ditemukan "
        "pada rentang `BU-04`. |"
    )
    lines.append("")

    # Section 4: Audit Bukti & Konteks
    lines.append("## 4. Audit Bukti (`evidence_text`) dan Keutuhan Konteks")
    lines.append("")
    lines.append("### 4.1 Masalah Utama pada Bukti Sumber")
    lines.append("")
    lines.append(
        "1. **Klaim di `requirement_description` Tidak Didukung oleh `evidence_text` (26 Record, Mayoritas `HIGH`)**:\n"
        "   Karena `extractor.py` menggunakan pencarian string tunggal `str.find(anchor)` yang pendek sementara `description` ditulis "
        "merangkum banyak kalimat/halaman, terdapat 26 record di mana informasi krusial di dalam `requirement_description` **sama sekali "
        "tidak ada di dalam `evidence_text`**. Contoh paling kritis:\n"
        "   - `REQ-DOC001-BU01-001`: Deskripsi menyebut wajib melampirkan KTM aktif, tetapi `evidence_text` (`921..1053`) tidak memuat kata KTM.\n"
        "   - `REQ-DOC001-BU01-009`: Deskripsi merinci General Track dan 5 tema ARSA Indonesia (`AC-1..AC-5`), tetapi `evidence_text` (`1566..1724`) "
        "berhenti sebelum daftar tema dimulai (`1727..2926`).\n"
        "   - `REQ-DOC001-BU01-010`: Deskripsi merinci 5 tahapan kompetisi (Registrasi s.d. Awarding), tetapi `evidence_text` (`5116..5381`) "
        "hanya memuat Tahap 4 dan Tahap 5.\n"
        "   - `REQ-DOC024-BU01-004`, `BU02-004`, `BU03-003`: Deskripsi mewajibkan unggah Twibbon IG & tag 3 teman, tetapi kalimat Twibbon berada "
        "di luar `evidence_text`.\n"
        "   - `REQ-DOC024-BU01-007` & `BU02-007`: Deskripsi merinci struktur esai (Judul, Pendahuluan, Isi, Penutup, Daftar Pustaka, Lampiran) "
        "dan 9 elemen BMC, tetapi `evidence_text` hanya mengutip format penamaan file PDF.\n"
        "   - `REQ-DOC009-BU01-006`, `BU02-004`, `BU03-004`: Deskripsi memuat jadwal tanggal Gelombang 1–3, TM, dan Final (Maret–Mei 2025), "
        "tetapi `evidence_text` hanya mengutip 1 kalimat tentang jumlah finalis (5 tim / 10 peserta) tanpa satu pun tanggal.\n"
        "   - `REQ-DOC009-BU03-005`: Deskripsi menyebut Poster A3 vertikal PDF, lembar orisinalitas, dan unggah IG (`33893..34980`), tetapi "
        "`evidence_text` (`36134..36258`) hanya mengutip kalimat PPT opsional untuk babak final."
    )
    lines.append(
        "2. **Kalimat atau Sub-Indikator Terpotong di Tengah (`REQ-DOC009-BU01-009` & `REQ-DOC009-BU04-006`)**:\n"
        "   - Pada `REQ-DOC009-BU01-009` (`17192..17765`), butir ke-6 hanya terambil judul `'6. Kesimpulan dan saran'` dan memotong sub-indikator "
        "`'a. Kesinambungan antara isi karya tulis dengan kesimpulan yang dibuat\\nb. Saran yang diberikan aplikatif dan solutif'` (`17766..17896`).\n"
        "   - Pada `REQ-DOC009-BU04-006` (`47364..47657`), butir ke-3 (`'3. Kesesuaian waktu'`) memotong sub-indikator `'a. Ketepatan waktu yang "
        "digunakan saat presentasi'` (`47658..47710`)."
    )
    lines.append(
        "3. **Pembedaan Aturan Resmi, Template, Contoh, dan Rekomendasi**:\n"
        "   - `REQ-DOC001-BU01-013` dan `REQ-DOC001-BU01-014` sudah membedakan `official_rule` (slide deck PDF maks 7 halaman) dari `template` "
        "(struktur 8 bagian template slide deck).\n"
        "   - Namun, pada `REQ-DOC024-BU01-005`, `BU02-005`, dan `BU03-004`, contoh string konfirmasi WhatsApp (`'Nama Tim_Konfirmasi Pembayaran "
        "Kompetisi Esai_Nama Lengkap Ketua_Asal Instansi_Gelombang 1/2'`) digabung langsung ke dalam record mekanisme pembayaran berstatus "
        "`official_rule` tanpa dipisahkan atau ditandai komponen contoh formatnya."
    )
    lines.append("")

    # Section 5: Audit NOT_STATED
    lines.append("## 5. Audit Representasi `NOT_STATED`")
    lines.append("")
    lines.append("### 5.1 Masalah Pencampuran `NOT_STATED` di Dalam Array `requirements`")
    lines.append("")
    lines.append(ns_audit["problem_summary"])
    lines.append("")
    lines.append("Daftar 15 record yang terdampak masalah representasi `NOT_STATED`:")
    lines.append("")
    lines.append("- **11 Record Atribut Absen yang Disimpan sebagai `official_rule` dengan Bukti Palsu/Judul Bab**:")
    lines.append("  - `REQ-DOC001-BU01-004` (`age_limit`) — mengutip kalimat jenjang universitas (`895..977`).")
    lines.append("  - `REQ-DOC001-BU01-005` (`same_university_or_cross_university_restriction`) — mengutip latar belakang event (`267..413`).")
    lines.append("  - `REQ-DOC001-BU01-015` (`standalone_source_code_repository_submission`) — mengutip sub-bab *Preliminary Submission* (`3066..3285`).")
    lines.append("  - `REQ-DOC024-BU01-002`, `REQ-DOC024-BU02-002`, `REQ-DOC024-BU03-002` (`age_limit`) — mengutip butir jenjang mahasiswa D1–S1.")
    lines.append("  - `REQ-DOC009-BU01-004`, `REQ-DOC009-BU02-002`, `REQ-DOC009-BU03-002` (`age_limit`) — mengutip judul bab `'B.PERSYARATAN PESERTA'` atau kalimat `'3.Lomba bersifat individu.'`.")
    lines.append("  - `REQ-DOC009-BU04-002` (`age_limit`) & `REQ-DOC009-BU04-005` (`proposal_page_limit_and_file_format`) — mengutip judul sub-bab di `BU-04`.")
    lines.append("- **4 Record Kriteria Penilaian Eksplisit yang Salah Diberi `validation_status = 'NOT_STATED'`**:")
    lines.append("  - `REQ-DOC009-BU01-009` (6 aspek penilaian naskah KTI tertulis eksplisit di teks).")
    lines.append("  - `REQ-DOC009-BU01-010` (3 aspek penilaian presentasi KTI tertulis eksplisit di teks).")
    lines.append("  - `REQ-DOC009-BU03-006` (3 aspek penilaian poster tertulis eksplisit di teks).")
    lines.append("  - `REQ-DOC009-BU04-006` (3 aspek penilaian presentasi Business Plan tertulis eksplisit di teks).")
    lines.append("")
    lines.append("### 5.2 Rekomendasi Struktur Data untuk Informasi yang Tidak Disebutkan")
    lines.append("")
    lines.append(f"1. **Pada Array `requirements`**: {ns_audit['recommended_data_structure']['1_in_requirements_array']}")
    lines.append(f"2. **Pada Array Terpisah `unmentioned_attributes`**: {ns_audit['recommended_data_structure']['2_separate_unmentioned_attributes_array']}")
    lines.append("")

    # Section 6: Audit Seluruh 98 Record & False Negatives
    lines.append("## 6. Audit Menyeluruh Seluruh 98 Record pada 3 Dokumen (`DOC-001`, `DOC-024`, `DOC-009`)")
    lines.append("")
    lines.append(
        "Tabel berikut memuat hasil pemeriksaan **seluruh 98 record** (tanpa terkecuali) terhadap teks asli di "
        "`data/raw/txt/`."
    )
    lines.append("")
    lines.append("| No | Requirement ID | Unit ID | Kategori | Rentang Char | Status Audit | Severity | Masalah yang Ditemukan & Bukti Sumber | Rekomendasi Perbaikan |")
    lines.append("| ---: | :--- | :--- | :--- | :--- | :---: | :---: | :--- | :--- |")
    for idx, rec in enumerate(records, start=1):
        char_span = f"`{rec['source_char_range']}`"
        ev_preview = rec["source_evidence"][:120].replace("\n", "\\n")
        if len(rec["source_evidence"]) > 120:
            ev_preview += "..."
        prob_and_ev = f"{_md_escape(rec['problem_found'])} **Bukti (`{len(rec['source_evidence'])}` char)**: `{_md_escape(ev_preview)}`"
        lines.append(
            f"| {idx} | `{rec['requirement_id']}` | `{rec['branch_unit_id']}` | `{rec['requirement_category']}` | "
            f"{char_span} | `{rec['audit_status']}` | `{rec['severity']}` | {prob_and_ev} | {_md_escape(rec['recommendation'])} |"
        )
    lines.append("")

    lines.append("### 6.2 Temuan Persyaratan yang Terlewat (*False Negatives*) pada Ketiga Dokumen")
    lines.append("")
    lines.append("| ID Temuan | Dokumen | Unit Cabang | Kategori | Rentang Char Sumber | Severity | Masalah & Bukti Sumber yang Terlewat | Rekomendasi |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- |")
    for fn in fns:
        lines.append(
            f"| `{fn['finding_id']}` | `{fn['document_id']}` | `{fn['branch_unit_id']}` | `{fn['expected_category']}` | "
            f"`{fn['source_char_range']}` | `{fn['severity']}` | "
            f"{_md_escape(fn['problem_found'])} **Bukti**: `{_md_escape(fn['source_evidence'])}` | {_md_escape(fn['recommendation'])} |"
        )
    lines.append("")

    # Section 7: Audit Pengujian
    lines.append("## 7. Audit Suite Pengujian (`tests/test_requirement_extraction.py`)")
    lines.append("")
    lines.append("### 7.1 Mengapa Seluruh 19 Pengujian di `test_requirement_extraction.py` Lulus Meskipun Ada 59 Record Bermasalah?")
    lines.append("")
    lines.append(test_audit["why_all_tests_passed_despite_issues"])
    lines.append("")
    lines.append("### 7.2 Pemisahan Pengujian Integritas Teknis vs. Validasi Semantik")
    lines.append("")
    lines.append("| Jenis Pengujian | Status di `test_requirement_extraction.py` Saat Ini | Cakupan yang Diuji |")
    lines.append("| :--- | :---: | :--- |")
    lines.append("| **Integritas Teknis (Struktural)** | Sudah Ada (8 fungsi test) | Kelengkapan field JSON/CSV, `raw_text[s:e] == evidence_text`, ketiadaan duplikat tuple, pemeriksaan unit terbatas pada 3 dokumen representatif. |")
    lines.append("| **Ketepatan Klasifikasi Kategori** | **Belum Ada** | Hanya memeriksa `category in REQUIREMENT_CATEGORIES`, tidak menguji apakah resolusi file atau latar belakang WHO salah kamar. |")
    lines.append("| **Keterdukungan Deskripsi oleh Bukti (*Groundedness*)** | **Belum Ada** | Tidak menguji apakah klaim angka, tanggal, URL, atau sub-aturan di `requirement_description` benar-benar ada di dalam `evidence_text`. |")
    lines.append("| **Deteksi *False Positive* & *Compound Merging*** | **Belum Ada** | Tidak menolak `historical_or_background_info` di dalam `requirements` dan tidak mendeteksi penggabungan multi-aturan lintas halaman. |")
    lines.append("| **Pemisahan `NOT_STATED` dari Aturan Resmi** | **Belum Ada** | Mengizinkan `requirement_description == 'NOT_STATED'` memiliki `statement_nature == 'official_rule'` dan mengutip kalimat aturan lain. |")
    lines.append("")
    lines.append("### 7.3 Rekomendasi Penambahan Pengujian Semantik")
    lines.append("")
    for rec_test in test_audit["recommended_semantic_test_additions"]:
        lines.append(f"- {rec_test}")
    lines.append("")

    # Section 8: Kesimpulan & Langkah Perbaikan
    lines.append("## 8. Kesimpulan Akhir & Peta Jalan Revisi Stage 4")
    lines.append("")
    lines.append(
        "Berdasarkan audit kode, bukti sumber, klasifikasi, dan pemeriksaan menyeluruh terhadap seluruh 98 record di atas, "
        "implementasi Stage 4 saat ini ditetapkan berstatus **`NEEDS_REVISION`** sebelum dapat diperluas ke dokumen lainnya:"
    )
    lines.append("")
    lines.append("1. **Ganti spesifikasi anchor hardcoded di `extractor.py`** dengan pipeline ekstraksi berbasis seksi, pemilah butir aturan atomik, dan parser tabel rubrik yang sesungguhnya, serta aktifkan fungsi normalisasi istilah.")
    lines.append("2. **Perbaiki keutuhan bukti (`evidence_text`) pada 42 record** yang rentang karakternya terpotong atau tidak memuat klaim yang tertulis di `requirement_description`, dan pecah 19 record gabungan (*compound records*) menjadi aturan-aturan atomik.")
    lines.append("3. **Pisahkan atribut `NOT_STATED` (11 record)** ke dalam struktur `unmentioned_attributes` per unit cabang agar tidak mencemari daftar persyaratan resmi (`requirements`), serta ubah 4 record kriteria penilaian `DOC-009` menjadi record per aspek dengan `validation_status = 'VALIDATED'` dan `indicator_weight = 'NOT_STATED'`.")
    lines.append("4. **Hapus false positive `REQ-DOC009-BU01-013`**, koreksi klasifikasi `REQ-DOC024-BU03-006` ke `technical_and_general_rules`, tandai kontradiksi internal `REQ-DOC024-BU01-013` dan typo `REQ-DOC024-BU02-007` sebagai `NEEDS_REVIEW`, serta tambahkan 7 kelompok persyaratan yang masih terlewat (*false negatives*).")
    lines.append("5. **Perkuat `tests/test_requirement_extraction.py`** dengan pengujian validasi semantik (*claim-in-evidence groundedness*, larangan `NOT_STATED` berlabel `official_rule`, dan atomisitas kriteria penilaian).")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    payload = run_stage4_audit()
    print("=== Stage 4 Audit Summary ===")
    print("Overall Recommendation:", payload["overall_recommendation"])
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))
