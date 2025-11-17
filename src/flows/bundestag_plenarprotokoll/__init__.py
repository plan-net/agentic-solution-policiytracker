"""
Flow 5d: Bundestag Plenarprotokoll Ingestion

Collects and processes German Bundestag plenary session protocols (Plenarprotokolle)
from the DIP API into the Neo4j knowledge graph.

Features:
- Metadata collection for all plenary protocols
- Optional full transcript text extraction
- Complete session records with all speeches and debates
- Agenda items (Tagesordnungspunkte) parsing
- Neo4j graph relationships to Vorgänge and Drucksachen
- Temporal tracking of parliamentary discussions

Components:
- app.py: Kodosumi flow endpoint with form validation
- forms.py: User input form with warnings about resource intensity
- processor.py: Core processing logic using PlenarprotokollCollector
- report_generator.py: Markdown report formatting
"""

__version__ = "1.0.0"
__author__ = "political-monitoring@example.com"
__flow__ = "Flow 5d: Bundestag Plenarprotokoll Ingestion"
