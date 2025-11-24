"""
Form definitions for Bundestag Vorgang ingestion flow.
"""

from kodosumi.core import forms as F

bundestag_vorgang_form = F.Model(
    F.Markdown(
        """
        # Bundestag Vorgang Ingestion

        Collect German Bundestag legislative procedures (Vorgänge) from DIP API into Neo4j.
        Includes relationships to Wahlperiode, Fraktion, Deskriptor, and Sachgebiet nodes.
        """
    ),
    F.Errors(),
    F.Break(),
    # Job name
    F.InputText(
        label="Job Name",
        name="job_name",
        placeholder="e.g., WP 20 Gesetzgebung",
        value="Bundestag Vorgang Ingestion",
    ),
    F.Break(),
    # Filters
    F.Markdown("### Collection Filters"),
    F.InputText(
        label="Wahlperiode (comma-separated for multiple)",
        name="wahlperioden",
        placeholder="e.g., 19,20,21",
        value="20",
    ),
    F.InputText(
        label="Vorgangstyp",
        name="vorgangstyp",
        placeholder="Alle, Gesetzgebung, EU-Vorlage, etc.",
        value="Alle",
    ),
    F.Break(),
    # Processing options
    F.Markdown("### Processing Options"),
    F.InputNumber(
        label="Batch Size",
        name="batch_size",
        value=100,
        min_value=10,
        max_value=500,
    ),
    F.Select(
        label="Maximum Vorgänge to Process",
        name="max_vorgaenge",
        value="1000",
        option=[
            F.InputOption(name="100", label="100 - Quick test"),
            F.InputOption(name="500", label="500 - Medium batch"),
            F.InputOption(name="1000", label="1000 - Large batch"),
            F.InputOption(name="5000", label="5000 - Very large"),
            F.InputOption(name="10000", label="10000 - Extra large"),
            F.InputOption(name="All", label="All - Complete ingestion (no limit)"),
        ],
    ),
    F.Checkbox(
        label="Create relationships",
        name="create_relationships",
        value=True,
        option="Create relationships to Wahlperiode, Fraktion, Deskriptor, and Sachgebiet nodes",
    ),
    F.Break(),
    # Actions
    F.Submit("Start Collection"),
    F.Cancel("Cancel"),
)
