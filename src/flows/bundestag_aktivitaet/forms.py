"""
Form definitions for Bundestag Aktivitaet ingestion flow.
"""

from kodosumi.core import forms as F


bundestag_aktivitaet_form = F.Model(
    F.Markdown(
        """
        # Bundestag Aktivitaet Ingestion

        Collect parliamentary activities (questions, answers, speeches) from DIP API into Neo4j.
        Creates Aktivitaet nodes with relationships to persons, procedures, and documents.
        """
    ),
    F.Errors(),
    F.Break(),
    # Job name
    F.InputText(
        label="Job Name",
        name="job_name",
        placeholder="e.g., WP20 Activities Q1 2025",
        value="Bundestag Aktivitaet Ingestion",
    ),
    F.Break(),
    # Filters
    F.Markdown("### Collection Filters"),
    F.InputText(
        label="Wahlperiode (Election Period)",
        name="wahlperiode",
        value="20",
        placeholder="Enter 19, 20, 21, or multiple: 19,20",
    ),
    F.Select(
        label="Aktivitaetsart (Activity Type)",
        name="aktivitaetsart",
        value="Alle",
        option=[
            F.InputOption(name="Alle", label="All activity types"),
            F.InputOption(name="Kleine Anfrage", label="Written Questions"),
            F.InputOption(name="Antwort", label="Government Answers"),
            F.InputOption(name="Frage", label="Parliamentary Questions"),
            F.InputOption(name="Rede", label="Speeches"),
            F.InputOption(name="Rede (zu Protokoll gegeben)", label="Speeches for Record"),
        ],
    ),
    F.InputNumber(
        label="Maximum Activities",
        name="max_aktivitaeten",
        min_value=1,
        max_value=5000,
        step=1,
        value=100,
        placeholder="Maximum activities to fetch",
    ),
    F.InputNumber(
        label="Batch Size",
        name="batch_size",
        min_value=10,
        max_value=500,
        step=10,
        value=100,
        placeholder="API batch size",
    ),
    F.Break(),
    # Relationship options
    F.Markdown("### Relationship Creation"),
    F.Checkbox(
        label="Create relationships to Persons, Vorgänge, and Documents",
        name="create_relationships",
        option="create_relationships",
        value=True,
    ),
    F.Break(),
    # Optional date filters
    F.Markdown("### Date Filters (Optional)"),
    F.InputText(
        label="Start Date (YYYY-MM-DD)",
        name="start_date",
        placeholder="e.g., 2025-01-01",
        value="",
    ),
    F.InputText(
        label="End Date (YYYY-MM-DD)",
        name="end_date",
        placeholder="e.g., 2025-03-31",
        value="",
    ),
    F.Break(),
    # Actions
    F.Submit("Start Collection"),
    F.Cancel("Cancel"),
)
