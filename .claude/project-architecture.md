# Political Monitoring Agent - Project Architecture

## Core Components
- **Workflow Engine**: LangGraph-based multi-step analysis pipeline
- **Scoring System**: Hybrid relevance + topic clustering
- **Report Generation**: Markdown reports with executive summaries

## Key Files & Their Purposes
```
src/
├── app.py                    # Kodosumi endpoint (DO NOT split)
├── political_analyzer.py     # Main entrypoint logic
├── workflow/
│   ├── graph.py             # LangGraph workflow definition
│   ├── nodes.py             # analyze_documents, score_relevance, etc.
│   └── state.py             # WorkflowState schema
├── analysis/
│   ├── topic_clusterer.py   # LLM-based clustering
│   └── priority_classifier.py # Priority scoring
└── scoring/
    ├── relevance_engine.py  # Semantic + keyword scoring
    └── dimensions.py        # Scoring dimensions config
```

## Workflow Steps
1. Load documents from Azure Storage
2. Process each document (extract, clean)
3. Analyze with LLM (relevance, topics)
4. Score using hybrid engine
5. Cluster by topics (if enabled)
6. Generate report with insights

## Configuration
- Client context: `/data/context/client.yaml`
- Input documents: `/data/input/` or Azure Storage
- Output reports: `/data/output/` or Azure Storage

## Domain-Specific Patterns
- Always check `include_low_confidence` flag
- Respect `priority_threshold` for filtering
- Use client context for relevance scoring
- Generate structured JSON + readable Markdown