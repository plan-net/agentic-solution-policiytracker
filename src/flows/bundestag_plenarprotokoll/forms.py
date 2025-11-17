"""
Kodosumi form definition for Bundestag Plenarprotokoll Ingestion (Flow 5d).
"""

from kodosumi.core import forms as F

bundestag_plenarprotokoll_form = F.Model(
    F.Markdown("""# Bundestag Plenarprotokoll Ingestion

Collect German plenary session protocols (Plenarprotokolle) including complete transcripts of parliamentary debates.

**Features:**
- Metadata collection from Bundestag DIP API
- Optional full transcript text extraction
- Complete session records with all speeches
- Agenda items (Tagesordnungspunkte) parsing
- Neo4j graph relationships

**Content:** Complete plenary session transcripts with all debates, votes, and procedural actions

**Note:** Plenarprotokoll transcripts are **VERY LARGE** (typically 100-200 pages each)
"""),

    F.Errors(),
    F.Break(),

    F.InputText(
        label="Job Name",
        name="job_name",
        value="Plenarprotokoll Collection",
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
        label="Start Date (YYYY-MM-DD)",
        name="start_date",
        value="",
        placeholder="Filter protocols published on or after this date"
    ),

    F.InputText(
        label="End Date (YYYY-MM-DD)",
        name="end_date",
        value="",
        placeholder="Filter protocols published on or before this date"
    ),

    F.Break(),
    F.Markdown("### ⚙️ Processing Options"),

    F.InputNumber(
        label="Batch Size",
        name="batch_size",
        value=50,
        min_value=10,
        max_value=200,
        step=1,
        placeholder="Number of protocols to process per batch (smaller for large documents)"
    ),

    F.Select(
        label="Maximum Protocols",
        name="max_protocols",
        value="100",
        option=[
            F.InputOption(name="10", label="10 - Quick test"),
            F.InputOption(name="50", label="50 - Small batch"),
            F.InputOption(name="100", label="100 - Medium batch"),
            F.InputOption(name="258", label="258 - All WP 20 (current)"),
            F.InputOption(name="305", label="305 - All WP 20 & 21"),
            F.InputOption(name="All", label="All - Complete ingestion (no limit)"),
        ],
    ),

    F.Break(),
    F.Markdown("""### 📄 Full-Text Extraction

**⚠️⚠️ IMPORTANT WARNING:** Plenarprotokoll full-text extraction is **EXTREMELY RESOURCE INTENSIVE**

**Why protocols are different from Drucksachen:**
- Each protocol is 100-200+ pages (vs. 5-20 for Drucksachen)
- Transcripts contain complete debates with all speeches
- File sizes are 10-50MB each (vs. 1-5MB for Drucksachen)
- Processing time: ~5-10 minutes per protocol (vs. 6-12 seconds for Drucksachen)

**Estimated processing times:**
- **10 protocols**: ~1 hour
- **100 protocols**: ~10 hours
- **305 protocols (all)**: ~25-50 hours

**Storage requirements:**
- **305 protocols**: ~3-6 GB

**Recommendation:**
1. **Metadata only** for initial collection (fast: ~5-10 minutes for all 305)
2. **Selective full-text** for specific sessions of interest later
3. Consider processing overnight for large batches
"""),

    F.Checkbox(
        label="Fetch Full Transcript Text",
        name="fetch_full_text",
        value=False,
        option="Extract complete transcript text (WARNING: Very slow and storage-intensive!)"
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
