# Methodology: Data Provenance & Epistemic Tracking

## 1. Epistemic Provenance Categories

To avoid mixing official competition regulations with researcher interpretations, all data points in the system carry an explicit provenance status:

| Status | Definition | Criteria for Assignment |
| :--- | :--- | :--- |
| **`EXPLICIT`** | Informasi tertulis secara langsung dalam sumber resmi. | Ada kutipan verbatim langsung dari dokumen resmi (`SourceDocument`), tercatat nomor halaman dan nomor seksi/pasal. |
| **`INFERRED`** | Hasil interpretasi, deduksi, atau pemetaan logis. | Dirumuskan berdasarkan analisis ahli, ekstrapolasi indikator, atau pemetaan kompetensi tersirat. Wajib mencatat `mapping_basis`. |
| **`UNVERIFIED`** | Informasi belum diverifikasi atau hasil ekstraksi draft. | Berasal dari sumber tidak resmi, hasil parsing draft, atau belum ditelaah oleh peneliti. |

## 2. Evidence Citation Protocol

Every official requirement or indicator grounded in a source document must point to a corresponding `Evidence` entity.

### Evidence Attributes:
1. `source_document_id`: Relational link to the registered document.
2. `page_number`: Exact 1-indexed page in the original PDF file.
3. `section`: Header or paragraph clause (e.g., "Bab III Ketentuan Khusus, Butir 2").
4. `excerpt`: Verbatim string quoted directly from the source text.
5. `evidence_type`: Classification of the excerpt form (`direct_quote`, `table`, `figure`, `summary`).
6. `confidence_level`: Epistemic certainty level (`high`, `medium`, `low`).

## 3. Auditing & Research Health Verification

The system provides `DataIntegrityAuditor.audit_competition(competition_id, session)`:
- Scans all requirements marked `EXPLICIT`.
- If an explicit requirement has zero linked evidence citations, it is flagged as a **Critical Scientific Violation**.
- Recalculates SHA-256 of physical files on disk and compares against stored hash to detect file tampering or silent PDF version drift.
- Calculates citation coverage percentage:
  $$\text{Coverage Rate} = \frac{\text{Requirements with Evidence}}{\text{Total Requirements}} \times 100\%$$

