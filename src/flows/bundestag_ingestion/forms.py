"""Form definitions for Bundestag ingestion flow v0.2.0"""

from kodosumi.core import forms as F

# Define comprehensive form for all 8 Bundestag data types
bundestag_ingestion_form = F.Model(
    F.Markdown(
        """
        # Bundestag Data Ingestion Flow v0.2.0

        Collect and ingest German parliamentary data from the Bundestag DIP API.
        Select which data types to collect, configure parameters, and monitor
        real-time progress as data flows into the Neo4j knowledge graph.

        **8 Available Data Sources:**
        - Vorgänge (Legislative processes)
        - Drucksachen (Printed matter/documents)
        - Vorgangspositionen (Process positions)
        - Aktivitäten (Activities)
        - Plenarprotokolle (Plenary protocols)
        - Personen (Politicians)
        - Wahlperioden (Election periods)
        - Fraktionen (Parliamentary groups)
        """
    ),
    F.Errors(),
    F.Break(),

    # Job Configuration
    F.InputText(
        label="Job Name",
        name="job_name",
        placeholder="e.g., Wahlperiode 20 Full Import, Q4 2024 Update",
        value="Bundestag Data Import",
    ),

    # Data Type Selection
    F.Markdown("### Data Types to Collect"),
    F.Checkbox(
        label="Core Legislative Data",
        name="collect_vorgang",
        value=True,
        option="Vorgänge - Legislative processes and procedures",
    ),
    F.Checkbox(
        label="Documents",
        name="collect_drucksache",
        value=True,
        option="Drucksachen - Printed parliamentary documents",
    ),
    F.Checkbox(
        label="Process Positions",
        name="collect_vorgangsposition",
        value=False,
        option="Vorgangspositionen - Detailed positions within processes (large dataset)",
    ),
    F.Checkbox(
        label="Activities",
        name="collect_aktivitaet",
        value=False,
        option="Aktivitäten - Parliamentary activities and actions",
    ),
    F.Checkbox(
        label="Plenary Protocols",
        name="collect_plenarprotokoll",
        value=False,
        option="Plenarprotokolle - Transcripts of parliamentary sessions",
    ),
    F.Checkbox(
        label="Politicians",
        name="collect_person",
        value=True,
        option="Personen - Members of parliament and other persons",
    ),
    F.Checkbox(
        label="Reference Data",
        name="collect_reference_data",
        value=True,
        option="Wahlperioden & Fraktionen - Election periods and parliamentary groups",
    ),

    F.Break(),

    # Collection Parameters
    F.Markdown("### Collection Parameters"),
    F.InputText(
        label="Wahlperiode (Election Period) - Current: 20 (2021-2025)",
        name="wahlperiode",
        value="20",
        placeholder="Enter 19, 20, 21, or 'all'",
    ),

    F.InputNumber(
        label="Maximum Items per Type",
        name="max_items_per_type",
        min_value=1,
        max_value=10000,
        step=1,
        value=100,
        placeholder="Limit items collected per data type (1-10000)",
    ),

    F.Checkbox(
        label="Full Text Content",
        name="include_full_text",
        value=False,
        option="Include full text content for documents (slower, larger dataset)",
    ),

    F.Break(),

    # Processing Options
    F.Markdown("### Processing Options"),
    F.InputNumber(
        label="Batch Size",
        name="batch_size",
        min_value=10,
        max_value=500,
        step=10,
        value=50,
        placeholder="Items to process per batch (affects memory usage)",
    ),

    F.Checkbox(
        label="Clear Existing Data",
        name="clear_data",
        value=False,
        option="⚠️ Clear existing Bundestag data before import (irreversible)",
    ),

    # Date Range Filters (Optional)
    F.Break(),
    F.Markdown("### Date Filters (Optional)"),
    F.InputText(
        label="Start Date (YYYY-MM-DD)",
        name="start_date",
        placeholder="e.g., 2024-01-01 (leave empty for no filter)",
        value="",
    ),
    F.InputText(
        label="End Date (YYYY-MM-DD)",
        name="end_date",
        placeholder="e.g., 2024-12-31 (leave empty for no filter)",
        value="",
    ),

    # Action Buttons
    F.Submit("Start Collection"),
    F.Cancel("Cancel"),
)
