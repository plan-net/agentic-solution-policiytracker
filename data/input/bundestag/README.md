# Bundestag Data Storage

This directory contains data collected from the German Bundestag DIP API.

## Directory Structure

```
bundestag/
└── drucksache/
    ├── pdf/                      # Original PDF documents
    │   ├── wahlperiode_19/       # Electoral period 19 (2017-2021)
    │   ├── wahlperiode_20/       # Electoral period 20 (2021-2025)
    │   └── wahlperiode_21/       # Electoral period 21 (2025+)
    └── markdown/                 # Extracted markdown with page headers
        ├── wahlperiode_19/
        ├── wahlperiode_20/
        └── wahlperiode_21/
```

## File Naming Convention

- **PDF Files**: `{wahlperiode}_{nummer}.pdf`
  - Example: `20_1234.pdf` (Drucksache 20/1234)

- **Markdown Files**: `{wahlperiode}_{nummer}.md`
  - Example: `20_1234.md` (Drucksache 20/1234)

## Storage Purpose

### PDF Directory
Stores original PDF documents downloaded from the Bundestag server for:
- **Archival**: Permanent local copy for audit and reference
- **Offline Access**: Documents available without API dependency
- **Reprocessing**: Ability to re-extract if schema or extraction logic changes
- **Compliance**: Local data governance and retention policies

### Markdown Directory
Stores extracted text in markdown format with:
- **Frontmatter**: Metadata (drucksache_nummer, wahlperiode, page_count, extraction_date)
- **Page Headers**: Each page marked with `## Page N`
- **Page Separators**: Pages separated by `---`
- **UTF-8 Encoding**: Universal text compatibility

## Usage

### Collected by Flow 5c
Files are automatically created and managed by **Flow 5c: Bundestag Drucksache Ingestion**.

### Manual Access
Documents can be accessed directly from the filesystem for:
- Manual review
- External processing
- Backup and archival
- Integration with other tools

## Storage Management

### Disk Space Estimates
- **Average PDF**: 1-5 MB per document
- **1000 Documents**: 1-5 GB disk space
- **Markdown**: 10-50 KB per document (minimal overhead)

### Cleanup
Use Flow 5c cleanup utilities to remove old PDFs while preserving metadata in Neo4j.

## Neo4j Integration

Document locations are tracked in Neo4j:
- `Drucksache.local_pdf_path`: Path to stored PDF
- `Drucksache.local_markdown_path`: Path to extracted markdown
- `Drucksache.file_size_bytes`: PDF file size

## Related Documentation

- [Flow 5c Documentation](../../../docs/flows/bundestag_drucksache.md)
- [Bundestag Flows Overview](../../../src/flows/README.md#bundestag-flows-flow-5-series)
