"""
Kodosumi form definition for Bundestag Drucksache Ingestion (Flow 5c).
"""

from kodosumi.core import forms as F

bundestag_drucksache_form = F.Model(
    F.Markdown("""# Bundestag Drucksache Ingestion

Collect German parliamentary documents (Drucksachen) including bills, motions, reports, and inquiries.

**Features:**
- Metadata collection from Bundestag DIP API
- Optional PDF download and local storage
- Page-by-page text extraction using PyPDF
- Markdown export with page headers
- Neo4j graph relationships

**Document Types:** Gesetzentwurf (Bill), Antrag (Motion), Bericht (Report), Kleine/Große Anfrage (Inquiry)
"""),

    F.Errors(),
    F.Break(),

    F.InputText(
        label="Job Name",
        name="job_name",
        value="Drucksache Collection",
        placeholder="Descriptive name for this collection run"
    ),

    F.Break(),
    F.Markdown("### 📋 Collection Filters"),

    F.InputText(
        label="Wahlperiode (comma-separated)",
        name="wahlperioden",
        value="20",
        placeholder="Electoral periods: e.g., '20' or '19,20,21'"
    ),

    F.InputText(
        label="Dokumentart",
        name="dokumentart",
        value="Alle",
        placeholder="Options: Gesetzentwurf, Antrag, Bericht, Kleine Anfrage, Große Anfrage, or Alle"
    ),

    F.InputText(
        label="Start Date (YYYY-MM-DD)",
        name="start_date",
        value="",
        placeholder="Filter documents published on or after this date"
    ),

    F.InputText(
        label="End Date (YYYY-MM-DD)",
        name="end_date",
        value="",
        placeholder="Filter documents published on or before this date"
    ),

    F.Break(),
    F.Markdown("### ⚙️ Processing Options"),

    F.InputNumber(
        label="Batch Size",
        name="batch_size",
        value=100,
        min_value=10,
        max_value=500,
        step=1,
        placeholder="Number of documents to process per API request"
    ),

    F.InputNumber(
        label="Maximum Documents",
        name="max_drucksachen",
        value=100,
        min_value=1,
        max_value=10000,
        step=1,
        placeholder="Total number of documents to collect"
    ),

    F.Break(),
    F.Markdown("""### 📄 Full-Text Extraction

**⚠️ Warning:** Full-text extraction is **SLOW** (10-20 documents/minute) due to:
- PDF downloads (~1-5 MB each)
- Page-by-page text extraction
- File system storage

**Recommendation:** Collect metadata first (fast), then run full-text extraction selectively.
"""),

    F.Checkbox(
        label="Extract Full Text from PDFs",
        name="extract_full_text",
        value=False,
        option="Download PDFs, extract text page-by-page, and store locally"
    ),

    F.InputNumber(
        label="Max Concurrent PDF Downloads",
        name="max_concurrent_downloads",
        value=5,
        min_value=1,
        max_value=10,
        step=1,
        placeholder="Limit concurrent downloads to manage memory"
    ),

    F.Break(),
    F.Markdown("### 🔗 Graph Relationships"),

    F.Checkbox(
        label="Create Relationships",
        name="create_relationships",
        value=True,
        option="Create Neo4j relationships to Wahlperiode and Vorgang entities"
    ),

    F.Break(),
    F.Submit("Start Collection"),
    F.Cancel("Cancel")
)
