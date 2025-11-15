"""
Form definitions for Bundestag Person ingestion flow.
"""

from kodosumi.core import forms as F


bundestag_person_form = F.Model(
    F.Markdown(
        """
        # Bundestag Person Ingestion

        Collect German Bundestag members (MdBs) from DIP API into Neo4j.
        Uses deterministic field mapping with MERGE operations.
        """
    ),
    F.Errors(),
    F.Break(),
    # Job name
    F.InputText(
        label="Job Name",
        name="job_name",
        placeholder="e.g., Wahlperiode 20 Members",
        value="Bundestag Person Ingestion",
    ),
    F.Break(),
    # Filters
    F.Markdown("### Collection Filters"),
    F.InputText(
        label="Wahlperiode (Election Period)",
        name="wahlperiode",
        value="all",
        placeholder="Enter 19, 20, 21, or 'all'",
    ),
    F.Select(
        label="Maximum Persons",
        name="max_items",
        value="100",
        option=[
            F.InputOption(name="100", label="100 - Quick test"),
            F.InputOption(name="500", label="500 - Medium batch"),
            F.InputOption(name="1000", label="1000 - Large batch"),
            F.InputOption(name="2000", label="2000 - Very large"),
            F.InputOption(name="All", label="All - Complete ingestion (no limit)"),
        ],
    ),
    F.Break(),
    # Optional date filters
    F.Markdown("### Date Filters (Optional)"),
    F.InputText(
        label="Start Date (YYYY-MM-DD)",
        name="start_date",
        placeholder="e.g., 2024-01-01",
        value="",
    ),
    F.InputText(
        label="End Date (YYYY-MM-DD)",
        name="end_date",
        placeholder="e.g., 2024-12-31",
        value="",
    ),
    F.Break(),
    # Actions
    F.Submit("Start Collection"),
    F.Cancel("Cancel"),
)
