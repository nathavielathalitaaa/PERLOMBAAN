# Methodology: Data Collection & Staging

## 1. Principles of Empirical Data Collection

In the **AI Competition Mentor** research framework, all data must be collected adhering to **scientific integrity** and **reproducibility**:

1. **Original Source Preservation**: Raw files (PDFs, official rubrics) must remain unaltered in `data/raw/competitions/` or `data/raw/research/`.
2. **Cryptographic Integrity**: As soon as a document is acquired, a SHA-256 hash is computed and recorded in the database.
3. **No Automated Ingestion into Verified State**: Information extracted via NLP or document parsers (`pymupdf`) is strictly classified as `unverified` staging data until reviewed by human researchers.

## 2. Standard Operating Procedure (SOP)

```
[Acquire Guidebook PDF]
          │
          ▼
[Store in data/raw/competitions/]
          │
          ▼
[Register SourceDocument via RequirementService]
          │
          ├── Compute SHA-256 Hash
          └── Record Document Metadata (Title, Type, Publication Date)
          │
          ▼
[Extract Text via PDFExtractor]
          │
          ├── Retain Page Numbers (1-indexed)
          ├── Retain Word & Character Counts
          └── Mark is_verified = False (Staging)
          │
          ▼
[Researcher Review & Evidence Annotation]
          │
          ├── Identify Explicit Clauses -> Create Requirement (Status: EXPLICIT)
          ├── Attach Verbatim Excerpt -> Create Evidence (Doc, Page, Section, Quote)
          └── Identify Scoring Indicators -> Create Indicator & Link Weight
          │
          ▼
[Competency Mapping (Expert Judgment / Deduction)]
          │
          └── Map Requirement to Competency (Status: INFERRED or EXPLICIT)
          │
          ▼
[Run DataIntegrityAuditor]
          │
          └── Verify that all explicit items have valid evidence citations
```

## 3. Handling Missing or Ambiguous Data
- **Unknown Scoring Weights**: If the official guidebook does not specify numerical percentages, the `weight` column must remain `NULL`. Never invent or estimate weights without explicit proof.
- **Unverified Rules**: Information obtained from forums, blogs, or informal discussions must have `source_status = 'unverified'` and cannot be used as primary evaluation truth.

