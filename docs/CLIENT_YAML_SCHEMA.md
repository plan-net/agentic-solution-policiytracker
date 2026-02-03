# Client.yaml Schema Documentation

## Overview

The `client.yaml` file is the central configuration for the policy tracker system, used by both ETL pipelines and AI agents. It defines what content to collect, how to score relevance, and what context to provide to agents.

**Location**: `data/context/client.yaml`

---

## Schema Format

The current schema supports a **nested, principle-based format** that is more expressive than the legacy flat list format. All ETL components have been updated to read this nested format through helper utilities.

---

## Key Usage Summary

### Legend
- 🟢 **ETL** = Used by ETL pipeline components
- 🔵 **Agent** = Used by Claude Agent / Chat system
- ⚪ **Unused** = Not currently used by any component

### Quick Reference Table

| Key | Format | Scoring Weight | ETL | Agent | Primary Purpose |
|-----|--------|---------------|-----|-------|-----------------|
| `client_name` | `string` | Fallback | 🟢 | 🔵 | Client identifier |
| `company_terms` | `list[str]` | **40%** | 🟢 | - | Brand/competitor monitoring |
| `core_industries` | `{primary, secondary}` | **25%** | 🟢 | 🔵 | Industry context |
| `primary_markets` | `list[str]` | **15%** | 🟢 | 🔵 | Geographic focus |
| `secondary_markets` | `list[str]` | (part of 15%) | 🟢 | 🔵 | Additional markets |
| `strategic_themes` | `list[str]` | **10%** | 🟢 | 🔵 | Strategic alignment |
| `topic_patterns` | `dict[str, list]` | (strategic) | 🟢 | - | Keyword patterns |
| `direct_impact_keywords` | `list[str]` | **40%** | 🟢 | - | Urgency indicators |
| `exclusion_terms` | `list[str]` | Filter | 🟢 | - | Content filtering |
| `business_model` | `{description, key_activities}` | - | - | 🔵 | How client operates |
| `regulatory_relevance` | `{high/medium/monitor}` | (fallback) | 🟢* | 🔵 | Regulatory areas to watch |
| `competitive_awareness` | `{principle, similar_businesses}` | - | - | 🔵 | Competitive context |
| `markets` (nested) | `{primary, secondary, monitoring_only}` | (fallback) | 🟢* | 🔵 | Geographic scope tiers |
| `geographic_priority` | `{principle}` | - | - | 🔵 | Market prioritization |
| `impact_indicators` | `{high/medium/context signals}` | - | - | 🔵 | Urgency assessment |
| `exclusions` (nested) | `{principles, industries}` | - | - | 🔵 | Principle-based exclusions |

*🟢* = Used as fallback when primary field is missing

---

## Required Fields for ETL

These fields are **mandatory** for the ETL pipeline to function correctly:

### 1. `client_name` (string)
Single identifier for the client.

```yaml
client_name: zalando
```

**Used by**:
- `config_loader.py` → `get_company_names()` (fallback)
- `client_context.py` → `get_client_name()`

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

**Used by**:
- `keyword_scorer.py` → `_company_terms` (40% direct impact weight)
- `config_loader.py` → `get_company_names()`

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

**Used by**:
- `keyword_scorer.py` → `_core_industries` (25% industry relevance weight)
- `llm_analyzer.py` → `_industries` (LLM prompt context)
- `policy_query_generator.py` → industry-based query generation
- `client_context.py` → `get_client_context_for_prompt()` as "client_industry"

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

**Used by**:
- `keyword_scorer.py` → `_primary_markets`, `_secondary_markets` (15% geographic weight)
- `llm_analyzer.py` → `_markets` (LLM prompt context)
- `policy_query_generator.py` → market-based query generation
- `client_context.py` → `get_primary_markets()`

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

**Used by**:
- `keyword_scorer.py` → `_strategic_themes` (10% strategic alignment weight)
- `llm_analyzer.py` → `_themes` (LLM prompt context)
- `policy_query_generator.py` → strategic query generation

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

**Used by**:
- `keyword_scorer.py` → `_direct_impact_keywords` (40% direct impact weight)

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

**Used by**:
- `keyword_scorer.py` → `_topic_patterns` (pattern matching for strategic alignment)
- `policy_query_generator.py` → category-based query generation

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

**Used by**:
- `keyword_scorer.py` → `_exclusion_terms` (content filtering)
- `config_loader.py` → `get_exclusion_terms()`, `should_exclude_article()`
- `relevance_filter.py` → filtering logic

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

**Used by**:
- `client_context.py` → `get_client_context_for_prompt()` as "client_description"
- `agent_sdk.py` → system prompt personalization
- `report_agent_sdk.py` → report context

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

**Used by**:
- `policy_query_generator.py` → FALLBACK: builds `topic_patterns` if missing
- `client_context.py` → "regulatory_focus" in agent context
- `agent_sdk.py` → agent understanding of regulatory areas
- `report_agent_sdk.py` → report structure

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

**Used by**:
- `client_context.py` → agent context
- `agent_sdk.py` → urgency assessment in responses

### `competitive_awareness` (object)
Contextual competitive intelligence.

```yaml
competitive_awareness:
  principle: "Enforcement against or regulatory treatment of similar platforms may set precedents"

  similar_businesses:
    - "Other EU e-commerce platforms and marketplaces"
    - "Fashion retail platforms"
    - "Companies offering BNPL/deferred payment"
```

**Used by**:
- `client_context.py` → competitive context for agent
- `agent_sdk.py` → contextual responses

### `geographic_priority` (object)
Helps prioritize by geography.

```yaml
geographic_priority:
  principle: "German implementation of EU law is highest priority, followed by EU-level developments, then other member states"
```

**Used by**:
- `client_context.py` → geographic prioritization
- `agent_sdk.py` → response prioritization

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

## Component-to-Key Mapping

### ETL Pipeline Components

#### 1. `config_loader.py` - `ClientConfigLoader`
```
Reads:
├── client_name        → get_company_names() fallback
├── company_terms      → get_company_names()
├── core_industries    → get_core_industries()
├── primary_markets    → get_markets()
├── secondary_markets  → get_markets()
└── exclusion_terms    → get_exclusion_terms(), should_exclude_article()
```

#### 2. `keyword_scorer.py` - `KeywordScorer`
```
Reads (via schema_helpers):
├── company_terms      → _company_terms (40% weight - direct impact)
├── core_industries    → _core_industries (25% weight - industry relevance)
├── primary_markets    → _primary_markets (15% weight - geographic relevance)
├── secondary_markets  → _secondary_markets (part of geographic)
├── strategic_themes   → _strategic_themes (10% weight - strategic alignment)
├── direct_impact_keywords → _direct_impact_keywords (40% weight)
├── topic_patterns     → _topic_patterns (pattern matching)
└── exclusion_terms    → _exclusion_terms (filter out)
```

#### 3. `llm_analyzer.py` - `LLMAnalyzer`
```
Reads (via schema_helpers):
├── core_industries    → _industries (context for LLM prompt)
├── primary_markets    → _markets (context for LLM prompt)
├── secondary_markets  → _markets (context for LLM prompt)
└── strategic_themes   → _themes (context for LLM prompt)
```

#### 4. `policy_query_generator.py` - `PolicyQueryGenerator`
```
Reads (via schema_helpers):
├── core_industries       → industries for query generation
├── primary_markets       → markets for query generation
├── secondary_markets     → markets for query generation
├── topic_patterns        → category queries
├── regulatory_relevance  → FALLBACK: builds topic_patterns if missing
└── strategic_themes      → strategic queries
```

#### 5. `relevance_filter.py` - `RelevanceFilter`
```
Reads:
├── company_terms      → via KeywordScorer
├── core_industries    → via KeywordScorer
├── exclusion_terms    → filtering logic
└── (all KeywordScorer fields)
```

#### 6. DAG Files (news_collection, policy_collection, website_discovery)
```
Use via ConfigLoader:
├── company_terms      → news search queries
├── exclusion_terms    → article filtering
└── (all ConfigLoader methods)
```

### Agent Components

#### 1. `client_context.py` - `load_client_context()`
```
Reads:
├── client_name           → get_client_name()
├── core_industries       → get_client_context_for_prompt() as "client_industry"
├── primary_markets       → get_primary_markets()
├── business_model        → get_client_context_for_prompt() as "client_description"
├── regulatory_relevance  → "regulatory_focus"
├── exclusions            → is_relevant_industry() check
└── (entire config)       → passed to agent prompts
```

#### 2. `agent_sdk.py` - `ClaudeAgentSDK`
```
Uses via client_context:
├── client_name           → system prompt personalization
├── business_model        → agent context
├── regulatory_relevance  → agent understanding
└── (full context)        → injected into prompts
```

#### 3. `report_agent_sdk.py` - `WeeklyReportAgent`
```
Uses via client_context:
├── client_name           → report personalization
├── primary_markets       → geographic focus
├── regulatory_relevance  → report structure
└── (full context)        → report generation
```

---

## Visual Key Usage Matrix

```
                        │ ETL │ Agent │ Scoring │ Query Gen │
────────────────────────┼─────┼───────┼─────────┼───────────┤
client_name             │  ✓  │   ✓   │  (fb)   │     -     │
company_terms           │  ✓  │   -   │  40%    │     -     │
core_industries         │  ✓  │   ✓   │  25%    │     ✓     │
primary_markets         │  ✓  │   ✓   │  15%    │     ✓     │
secondary_markets       │  ✓  │   ✓   │  (15%)  │     ✓     │
strategic_themes        │  ✓  │   ✓   │  10%    │     ✓     │
topic_patterns          │  ✓  │   -   │   ✓     │     ✓     │
direct_impact_keywords  │  ✓  │   -   │  40%    │     -     │
exclusion_terms         │  ✓  │   -   │ filter  │     -     │
────────────────────────┼─────┼───────┼─────────┼───────────┤
business_model          │  -  │   ✓   │    -    │     -     │
regulatory_relevance    │ (fb)│   ✓   │    -    │    (fb)   │
competitive_awareness   │  -  │   ✓   │    -    │     -     │
markets (nested)        │ (fb)│   ✓   │    -    │     -     │
geographic_priority     │  -  │   ✓   │    -    │     -     │
impact_indicators       │  -  │   ✓   │    -    │     -     │
exclusions (nested)     │  -  │   ✓   │    -    │     -     │
────────────────────────┴─────┴───────┴─────────┴───────────┘

Legend: ✓ = used, - = not used, (fb) = fallback, (%) = weight contribution
```

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

### Helper Function Details

| Helper Function | Input Keys | Output | Used By |
|-----------------|------------|--------|---------|
| `extract_company_terms()` | `company_terms`, `client_name` | `List[str]` | config_loader, keyword_scorer |
| `extract_industries()` | `core_industries` (nested or flat) | `List[str]` | config_loader, keyword_scorer, llm_analyzer, policy_query_generator |
| `extract_markets()` | `markets` or `primary_markets`/`secondary_markets` | `Tuple[List, List]` | config_loader, keyword_scorer, llm_analyzer, policy_query_generator |
| `extract_exclusion_terms()` | `exclusion_terms` or `exclusions.industries` | `List[str]` | config_loader, keyword_scorer |

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
| Component | File Path | Keys Used |
|-----------|-----------|-----------|
| **Config Loader** | `src/etl/utils/config_loader.py` | client_name, company_terms, core_industries, primary_markets, secondary_markets, exclusion_terms |
| **Keyword Scorer** | `src/etl/filtering/keyword_scorer.py` | All ETL-required fields |
| **LLM Analyzer** | `src/etl/filtering/llm_analyzer.py` | core_industries, primary_markets, secondary_markets, strategic_themes |
| **Policy Query Generator** | `src/etl/utils/policy_query_generator.py` | core_industries, primary_markets, secondary_markets, topic_patterns, regulatory_relevance (fallback), strategic_themes |
| **Relevance Filter** | `src/etl/filtering/relevance_filter.py` | Via KeywordScorer |
| **News Collection DAG** | `src/etl/dags/news_collection_dag.py` | Via ConfigLoader |
| **Policy Collection DAG** | `src/etl/dags/policy_collection_dag.py` | Via PolicyQueryGenerator |
| **Website Discovery DAG** | `src/etl/dags/website_discovery_dag.py` | Via ConfigLoader |

### AI Agents
| Component | File Path | Keys Used |
|-----------|-----------|-----------|
| **Client Context Module** | `src/shared/client_context.py` | All fields (full config passed to agents) |
| **Claude Agent SDK** | `src/claude_agent/agent_sdk.py` | Via client_context |
| **Weekly Report Agent SDK** | `src/flows/weekly_report_sdk/agent/report_agent_sdk.py` | Via client_context |
| **Weekly Digest V2 Processor** | `src/flows/weekly_digest_v2/processor.py` | Via client_context |

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

### DAG fails with "TypeError: 'type' object is not subscriptable"
- This occurs when running on Python < 3.9
- Ensure `schema_helpers.py` uses `from __future__ import annotations`
- Use `Dict`, `List`, `Tuple` from `typing` module instead of `dict`, `list`, `tuple`

---

## Version History

- **Version 2**: Current nested schema format with principle-based regulatory relevance
- **Version 1**: Legacy flat list format

All components support both formats for backward compatibility.
