# Client.yaml Schema Documentation

## Overview

The `client.yaml` file is the central configuration for the policy tracker system, used by both ETL pipelines and AI agents. It defines what content to collect, how to score relevance, and what context to provide to agents.

**Location**: `data/context/client.yaml`

---

## Schema Format

The current schema supports a **nested, principle-based format** that is more expressive than the legacy flat list format. All ETL components have been updated to read this nested format through helper utilities.

---

## Required Fields for ETL

These fields are **mandatory** for the ETL pipeline to function correctly:

### 1. `client_name` (string)
Single identifier for the client.

```yaml
client_name: zalando
```

### 2. `company_terms` (list of strings)
**Weight in scoring: 40%**

List of entities, brands, competitors, and related terms to monitor. This is the most important field for relevance scoring.

```yaml
company_terms:
  # Primary brand
  - "Zalando"
  - "Zalando SE"

  # Related services
  - "Zalando Plus"
  - "Zalando Lounge"

  # Competitors
  - "ASOS"
  - "About You"

  # Industry terms
  - "online fashion marketplace"
  - "e-commerce platform"
```

**Best Practice**: Include 15-30 terms covering primary brand, services, competitors, and industry-specific phrases.

### 3. `core_industries` (nested object)
**Weight in scoring: 25%**

Industries the client operates in. Uses nested format with primary and secondary.

```yaml
core_industries:
  primary: "E-commerce / Online Retail"
  secondary:
    - fashion retail
    - marketplace operator
    - digital platform
    - apparel
```

**ETL Behavior**: Extracts as flat list `[primary] + secondary` for keyword matching.

**Legacy Format** (still supported):
```yaml
core_industries:
  - "E-commerce / Online Retail"
  - "fashion retail"
  - "marketplace operator"
```

### 4. `primary_markets` and `secondary_markets` (lists)
**Weight in scoring: 15%**

Geographic markets where the client operates.

```yaml
primary_markets:
  - european union
  - eu
  - germany
  - poland

secondary_markets:
  - uk
  - switzerland
  - sweden
```

**Nested Format** (also supported):
```yaml
markets:
  primary:
    - european union
    - germany
  secondary:
    - uk
    - switzerland
```

### 5. `strategic_themes` (list of strings)
**Weight in scoring: 10%**

High-level topics of strategic importance to the client.

```yaml
strategic_themes:
  - digital transformation
  - sustainability
  - customer experience
  - data privacy
  - payment systems
```

### 6. `direct_impact_keywords` (list of strings)
**Weight in scoring: 40% (direct impact component)**

High-urgency keywords indicating content that requires immediate attention.

```yaml
direct_impact_keywords:
  - must comply
  - required to
  - obligation
  - penalty
  - enforcement
  - violation
  - deadline
```

### 7. `topic_patterns` (nested object)
Dictionary of topic categories with associated keywords.

```yaml
topic_patterns:
  data-protection:
    - gdpr
    - data privacy
    - personal information

  ecommerce-regulation:
    - digital services act
    - dsa
    - online platform
    - marketplace regulation

  sustainability:
    - esg
    - environmental
    - circular economy
```

### 8. `exclusion_terms` (list of strings)
Content to filter out from results.

```yaml
exclusion_terms:
  - sports
  - automotive
  - real estate
  - agriculture
```

**Nested Format** (also supported):
```yaml
exclusions:
  industries:
    - sports
    - automotive
```

---

## Optional Fields for Agents

These fields enhance agent responses but are not used by ETL:

### `business_model` (object)
Describes how the client operates (principle-based, not keywords).

```yaml
business_model:
  description: "Online marketplace connecting consumers with fashion brands, operating B2C sales and enabling third-party sellers across EU markets"

  key_activities:
    - "Operates online marketplace with third-party sellers"
    - "Direct B2C sales of fashion and apparel"
    - "Offers payment options including deferred payment / buy-now-pay-later"
```

### `regulatory_relevance` (object)
Principle-based regulatory monitoring structure.

```yaml
regulatory_relevance:
  high_relevance:
    - area: "Platform and marketplace regulation"
      why: "Core business is operating an online marketplace"
      watch_for:
        - "Obligations for online platforms and marketplaces"
        - "Liability for third-party seller content"

  medium_relevance:
    - area: "Competition and antitrust"
      why: "Market position may attract scrutiny"
      watch_for:
        - "Platform competition enforcement"

  monitor:
    - area: "Sustainability and environmental regulation"
      why: "Fashion industry increasingly subject to sustainability rules"
```

**ETL Note**: The policy query generator can fall back to building topic_patterns from regulatory_relevance if topic_patterns is not provided.

### `impact_indicators` (object)
Helps agents gauge urgency and relevance.

```yaml
impact_indicators:
  high_impact_signals:
    - "Creates new compliance obligation"
    - "Enforcement action or penalty"
    - "Deadline or implementation date"

  medium_impact_signals:
    - "Proposal or draft legislation"
    - "Consultation or public comment period"

  context_signals:
    - "Agency reorganization affecting digital policy"
    - "Political priorities"
```

---

## ETL Relevance Scoring Weights

The keyword scorer uses these weights:

| Dimension | Weight | Source Fields |
|-----------|--------|---------------|
| **Direct Impact** | 40% | `direct_impact_keywords` + `company_terms` |
| **Industry Relevance** | 25% | `core_industries` |
| **Geographic Relevance** | 15% | `primary_markets` + `secondary_markets` |
| **Strategic Alignment** | 10% | `strategic_themes` + `topic_patterns` |
| **Temporal Urgency** | 10% | Built-in temporal keywords |

**Total Score**: 0-100 (weighted average)

**Relevance Threshold**: Typically 50+ for inclusion

---

## Schema Helper Utilities

All ETL components use helper functions from `src/etl/utils/schema_helpers.py`:

```python
from src.etl.utils.schema_helpers import (
    extract_industries,      # Handles nested/flat core_industries
    extract_markets,          # Handles nested/flat markets
    extract_company_terms,    # Handles company_terms or client_name
    extract_exclusion_terms,  # Handles exclusion_terms or exclusions
    validate_required_fields, # Validates all required fields present
)
```

These helpers automatically handle both nested and flat formats, making the code more maintainable.

---

## Migration from Legacy Format

If you have a legacy flat format config, it will still work:

### Legacy Format
```yaml
company_terms: ["Company Name"]
core_industries: ["industry1", "industry2"]
primary_markets: ["market1", "market2"]
secondary_markets: ["market3"]
```

### New Nested Format (Recommended)
```yaml
company_terms: ["Company Name"]

core_industries:
  primary: "industry1"
  secondary: ["industry2"]

markets:
  primary: ["market1", "market2"]
  secondary: ["market3"]
```

Both formats work because ETL components use schema helpers that support both.

---

## Example: Complete Minimal Config

```yaml
client_name: example_company

company_terms:
  - "Example Company"
  - "Example Corp"

core_industries:
  primary: "Technology"
  secondary:
    - software
    - cloud services

primary_markets:
  - united states
  - european union

secondary_markets:
  - uk
  - canada

strategic_themes:
  - digital transformation
  - cybersecurity

direct_impact_keywords:
  - must comply
  - required to
  - obligation

topic_patterns:
  data-protection:
    - data privacy
    - gdpr
  cybersecurity:
    - cyber attack
    - security breach

exclusion_terms:
  - sports
  - entertainment
```

---

## Validation

Use the validation helper to check your config:

```python
from src.etl.utils.schema_helpers import validate_required_fields
import yaml

with open('data/context/client.yaml') as f:
    config = yaml.safe_load(f)

is_valid, missing_fields = validate_required_fields(config)

if not is_valid:
    print(f"Missing required fields: {missing_fields}")
else:
    print("✅ Configuration is valid")
```

---

## Components Using client.yaml

### ETL Pipeline
- **Config Loader**: `src/etl/utils/config_loader.py`
- **Keyword Scorer**: `src/etl/filtering/keyword_scorer.py`
- **LLM Analyzer**: `src/etl/filtering/llm_analyzer.py`
- **Policy Query Generator**: `src/etl/utils/policy_query_generator.py`
- **News Collection DAG**: `src/etl/dags/news_collection_dag.py`
- **Policy Collection DAG**: `src/etl/dags/policy_collection_dag.py`
- **Website Discovery DAG**: `src/etl/dags/website_discovery_dag.py`

### AI Agents
- **Client Context Module**: `src/shared/client_context.py`
- **Claude Agent SDK**: `src/claude_agent/agent_sdk.py`
- **Weekly Report Agent SDK**: `src/flows/weekly_report_sdk/agent/report_agent_sdk.py`
- **Weekly Digest V2 Processor**: `src/flows/weekly_digest_v2/processor.py`

---

## Best Practices

1. **Company Terms**: Include 15-30 terms covering brand, services, competitors
2. **Industries**: Use descriptive phrases, not just single words
3. **Markets**: Include both broad (EU) and specific (Germany) geographic terms
4. **Strategic Themes**: 5-10 high-level topics that matter to your business
5. **Direct Impact Keywords**: Focus on urgency/compliance language
6. **Topic Patterns**: Organize by regulatory area, 5-10 keywords per area
7. **Exclusions**: Be specific about what to filter out

---

## Troubleshooting

### "No company terms found" error
- Ensure either `company_terms` list or `client_name` string is present
- Check YAML syntax is correct

### "core_industries returns empty list"
- Verify nested format has `primary` and/or `secondary` keys
- Or use flat list format

### "Markets not found"
- Use either flat (`primary_markets`, `secondary_markets`) or nested (`markets.primary`, `markets.secondary`)
- Schema helpers support both formats

### YAML parsing fails
- Check for syntax errors (colons, indentation)
- Common error: Using `=` instead of `:` for key-value pairs
- Validate with: `python -c "import yaml; yaml.safe_load(open('data/context/client.yaml'))"`

---

## Version History

- **Version 2**: Current nested schema format with principle-based regulatory relevance
- **Version 1**: Legacy flat list format

All components support both formats for backward compatibility.
