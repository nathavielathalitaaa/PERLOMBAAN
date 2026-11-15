# Database Design — AI Competition Mentor (V0.1)

## 1. Entity-Relationship Diagram

```mermaid
erDiagram
    COMPETITION ||--o{ SOURCE_DOCUMENT : "has"
    COMPETITION ||--o{ REQUIREMENT : "defines"
    SOURCE_DOCUMENT ||--o{ EVIDENCE : "contains"
    REQUIREMENT ||--o{ EVIDENCE : "grounded_by"
    INDICATOR ||--o{ EVIDENCE : "supported_by"
    REQUIREMENT ||--o{ REQUIREMENT_INDICATOR : "associates"
    INDICATOR ||--o{ REQUIREMENT_INDICATOR : "referenced_in"
    REQUIREMENT ||--o{ REQUIREMENT_COMPETENCY : "requires"
    COMPETENCY ||--o{ REQUIREMENT_COMPETENCY : "mapped_to"
    EVIDENCE ||--o{ REQUIREMENT_COMPETENCY : "justifies"

    COMPETITION {
        string id PK "UUIDv4"
        string name "Competition Title"
        string category "Domain Category"
        string organizer "Organizing Institution"
        int year "Competition Year"
        text description "Scope & Overview"
        string official_url "Website Portal"
        datetime created_at "UTC Timestamp"
        datetime updated_at "UTC Timestamp"
    }

    SOURCE_DOCUMENT {
        string id PK "UUIDv4"
        string competition_id FK "References COMPETITION(id)"
        string title "Document Title"
        string document_type "guidebook, rubric, faq, etc."
        string file_path "Path to PDF/File"
        string file_hash "SHA-256 Checksum"
        string version "Document Version"
        date publication_date "Official Release Date"
        datetime collected_at "UTC Timestamp"
    }

    REQUIREMENT {
        string id PK "UUIDv4"
        string competition_id FK "References COMPETITION(id)"
        text description "Requirement Clause"
        string requirement_type "administrative, technical, output, etc."
        string classification "eligibility, criteria, disqualification, etc."
        string source_status "explicit, inferred, unverified"
        datetime created_at "UTC Timestamp"
        datetime updated_at "UTC Timestamp"
    }

    INDICATOR {
        string id PK "UUIDv4"
        string code UK "Unique Taxonomy Code"
        string name "Indicator Name"
        text definition "Rubric Criteria Definition"
        string category "Evaluation Domain"
        string indicator_type "quantitative, qualitative, rubric_scale, etc."
        datetime created_at "UTC Timestamp"
        datetime updated_at "UTC Timestamp"
    }

    REQUIREMENT_INDICATOR {
        string id PK "UUIDv4"
        string requirement_id FK "References REQUIREMENT(id)"
        string indicator_id FK "References INDICATOR(id)"
        float weight "Percentage weight if stated"
        string relation_type "primary_criterion, sub_criterion"
        string mapping_status "explicit, inferred, unverified"
        datetime created_at "UTC Timestamp"
    }

    EVIDENCE {
        string id PK "UUIDv4"
        string source_document_id FK "References SOURCE_DOCUMENT(id)"
        string requirement_id FK "References REQUIREMENT(id)"
        string indicator_id FK "References INDICATOR(id)"
        int page_number "Page in source PDF (1-indexed)"
        string section "Header / Section / Clause"
        text excerpt "Verbatim Citation"
        string evidence_type "direct_quote, table, figure, summary"
        string confidence_level "high, medium, low"
        datetime created_at "UTC Timestamp"
    }

    COMPETENCY {
        string id PK "UUIDv4"
        string code UK "Unique Competency Code"
        string name "Competency Name"
        text definition "Behavioral / Technical Definition"
        string category "Technical, Domain, Interpersonal, etc."
        datetime created_at "UTC Timestamp"
        datetime updated_at "UTC Timestamp"
    }

    REQUIREMENT_COMPETENCY {
        string id PK "UUIDv4"
        string requirement_id FK "References REQUIREMENT(id)"
        string competency_id FK "References COMPETENCY(id)"
        string mapping_basis "direct_text, inferred, expert_judgment"
        string mapping_status "explicit, inferred, unverified"
        string evidence_id FK "References EVIDENCE(id)"
        datetime created_at "UTC Timestamp"
    }
```

## 2. Table Specifications & Constraints

### 2.1 `competitions`
* Primary Key: `id` (VARCHAR(36))
* Indexes: `name`, `category`, `organizer`, `year`

### 2.2 `source_documents`
* Primary Key: `id` (VARCHAR(36))
* Foreign Key: `competition_id` REFERENCES `competitions(id)` ON DELETE CASCADE
* Integrity: `file_hash` stores SHA-256 for physical file verification.

### 2.3 `requirements`
* Primary Key: `id` (VARCHAR(36))
* Foreign Key: `competition_id` REFERENCES `competitions(id)` ON DELETE CASCADE
* Indexes: `source_status` (`explicit`, `inferred`, `unverified`)

### 2.4 `indicators`
* Primary Key: `id` (VARCHAR(36))
* Unique Constraint: `code` (e.g., `IND_INNOVATION_TECH`)
* Indexes: `code`, `category`

### 2.5 `requirement_indicators`
* Primary Key: `id` (VARCHAR(36))
* Unique Constraint: `(requirement_id, indicator_id)`
* Foreign Keys: `requirement_id` ON DELETE CASCADE, `indicator_id` ON DELETE CASCADE

### 2.6 `evidences`
* Primary Key: `id` (VARCHAR(36))
* Check Constraint: `requirement_id IS NOT NULL OR indicator_id IS NOT NULL`
* Foreign Keys: `source_document_id` ON DELETE CASCADE, `requirement_id` ON DELETE CASCADE, `indicator_id` ON DELETE CASCADE

### 2.7 `competencies`
* Primary Key: `id` (VARCHAR(36))
* Unique Constraint: `code` (e.g., `COMP_SOFTWARE_ENG`)
* Indexes: `code`, `category`

### 2.8 `requirement_competencies`
* Primary Key: `id` (VARCHAR(36))
* Unique Constraint: `(requirement_id, competency_id)`
* Foreign Keys: `requirement_id` ON DELETE CASCADE, `competency_id` ON DELETE CASCADE, `evidence_id` ON DELETE SET NULL

