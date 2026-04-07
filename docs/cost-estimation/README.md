# Document Ingestion Cost Estimation Model

## Overview

Comprehensive cost estimation and budget planning model for the Political Monitoring Agent document ingestion pipeline. Includes ETL collection costs, LLM processing costs (entity extraction), and embedding generation costs.

**Deliverable**: `Ingestion_Cost_Estimation_Model.xlsx` (Excel workbook)

---

## 📁 Files in This Directory

### Main Documentation
- **[EXCEL_ASSEMBLY_GUIDE.md](EXCEL_ASSEMBLY_GUIDE.md)** - Complete guide to building the Excel workbook
  - Detailed formulas and cell references
  - Chart creation instructions
  - Formatting guidelines
  - Troubleshooting tips

### CSV Templates (Ready to Import)
Located in `csv-templates/` directory:

1. **[01_Dashboard.csv](csv-templates/01_Dashboard.csv)** - Executive summary
   - Quick cost estimator
   - Key metrics summary
   - Cost breakdown pie chart data
   - Annual projection
   - Budget status indicators

2. **[02_Input_Parameters.csv](csv-templates/02_Input_Parameters.csv)** - Configurable variables
   - Document characteristics (volume, length)
   - Chunk configuration
   - Model selection (LLM, embeddings)
   - Processing settings
   - ETL collection parameters

3. **[03_Pricing_Reference.csv](csv-templates/03_Pricing_Reference.csv)** - API pricing
   - ETL costs (Exa.ai, Apify)
   - OpenAI model pricing
   - Anthropic model pricing
   - Embedding model pricing
   - Prompt caching discounts
   - Cost optimization strategies

4. **[04_Cost_Calculator.csv](csv-templates/04_Cost_Calculator.csv)** - Detailed breakdown
   - Step-by-step cost calculation
   - ETL collection cost
   - Document chunking calculation
   - LLM processing cost
   - Embedding generation cost
   - Total monthly and annual projections

5. **[05_Scenario_Comparison.csv](csv-templates/05_Scenario_Comparison.csv)** - What-if analysis
   - 5 pre-built scenarios (low/medium/high volume, premium, cost-optimized)
   - Side-by-side cost comparison
   - Quality indicators
   - Value ranking
   - Custom scenario builder

6. **[06_Historical_Validation.csv](csv-templates/06_Historical_Validation.csv)** - Tracking
   - Actual vs estimated costs (monthly/weekly)
   - Variance analysis
   - Data source instructions
   - Cost control alerts
   - Accuracy improvement recommendations

---

## 🚀 Quick Start

### Step 1: Import CSV Templates into Excel

```bash
# Option 1: Open each CSV in Excel and save as .xlsx
# Option 2: Use Excel's "Import from CSV" feature for each sheet
```

1. Open Excel and create a new workbook
2. Import each CSV file as a separate sheet (in order):
   - `01_Dashboard.csv` → Sheet: "Dashboard"
   - `02_Input_Parameters.csv` → Sheet: "Input Parameters"
   - `03_Pricing_Reference.csv` → Sheet: "Pricing Reference"
   - `04_Cost_Calculator.csv` → Sheet: "Cost Calculator"
   - `05_Scenario_Comparison.csv` → Sheet: "Scenario Comparison"
   - `06_Historical_Validation.csv` → Sheet: "Historical Validation"

3. Save as: `Ingestion_Cost_Estimation_Model.xlsx`

### Step 2: Update Required Fields

**CRITICAL**: Update placeholder values with actual pricing

| Sheet | Cell | Field | Source |
|-------|------|-------|--------|
| Pricing Reference | C7 | Exa.ai cost per query | Exa.ai pricing page or invoice |
| Pricing Reference | C8 | Apify cost per document | Apify pricing page or invoice |

### Step 3: Configure Your Scenario

Update **Input Parameters** sheet with your expected values:

| Parameter | Default | Your Value |
|-----------|---------|------------|
| Documents per Month (B4) | 500 | ? |
| Average Document Length (B5) | 5000 tokens | ? |
| LLM Model (B18) | gpt-4o-mini | ? |
| Embedding Model (B19) | text-embedding-3-small | ? |
| Enable Prompt Caching (B20) | YES | ? |

### Step 4: Review Results

Check the **Dashboard** sheet for:
- Total monthly cost estimate
- Cost per document
- Annual projection
- Budget status indicators

---

## 💡 Key Features

### 🎯 Budget Planning
- Monthly and annual cost projections
- Configurable document volumes and characteristics
- Model selection (LLM and embedding models)
- Scenario planning (what-if analysis)

### 📊 Cost Components
1. **ETL Collection Costs** (Exa.ai, Apify)
   - Per-query and per-document pricing
   - Average 20% of total cost

2. **LLM Processing Costs** (Entity Extraction)
   - Graphiti entity/relationship extraction
   - Prompt caching optimization (50-90% savings)
   - Average 1-10% of total cost (with caching)

3. **Embedding Generation Costs**
   - Episode embeddings (document content)
   - Entity embeddings (entity names)
   - Relationship embeddings (relationship facts)
   - Average 66-70% of total cost

4. **Overhead & Retry Costs**
   - Default 15% buffer for errors and retries
   - Configurable

### 🔄 Scenario Comparison

5 pre-built scenarios:
- **Scenario A**: Low volume (100 docs/month) → ~$52/month
- **Scenario B**: Medium volume (500 docs/month) → ~$259/month
- **Scenario C**: High volume (1000 docs/month) → ~$517/month
- **Scenario D**: Premium quality (claude-sonnet + ada-002) → ~$788/month
- **Scenario E**: Cost optimized (aggressive chunk limiting) → ~$259/month

### ✅ Validation & Tracking
- Compare estimated vs actual costs monthly
- Track accuracy over time
- Identify variance drivers
- Improve estimation parameters

---

## 📈 Cost Optimization Strategies

Based on implemented cost reduction strategies:

### 1. Chunk Limiting Strategy
- **Savings**: 39-85% for large documents (>50K tokens)
- **Implementation**: Max 20 chunks per document
- **Status**: ✅ IMPLEMENTED
- **Configuration**: Input Parameters!B26 = YES

### 2. Prompt Caching
- **Savings**: 50-90% on schema tokens (18,600 tokens per chunk)
- **OpenAI**: 50% discount (automatic)
- **Anthropic**: 90% discount (explicit cache_control)
- **Status**: ✅ IMPLEMENTED
- **Configuration**: Input Parameters!B20 = YES

### 3. Embedding Model Selection
- **text-embedding-3-small**: $0.02/1M tokens (current, cost-optimized)
- **text-embedding-ada-002**: $0.10/1M tokens (5x more expensive, 100% multilingual)
- **text-embedding-3-large**: $0.13/1M tokens (6.5x more expensive, moderate multilingual)

**Recommendation**: Use `text-embedding-3-small` for budget-conscious production, switch to `ada-002` if multilingual quality is critical.

---

## 🔍 Validation Against Actual Costs

### Get Actual Cost Data

#### Option 1: Cost Analytics API
```bash
# Get total LLM costs for last 30 days
curl http://localhost:8090/api/costs/summary?days=30

# Get cost breakdown by model
curl http://localhost:8090/api/costs/by-model

# Get cost breakdown by agent
curl http://localhost:8090/api/costs/by-agent
```

#### Option 2: TimescaleDB Direct Query
```sql
SELECT
    DATE(timestamp) as date,
    SUM(total_cost_usd) as daily_cost,
    COUNT(*) as requests
FROM llm_requests
WHERE timestamp >= NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp)
ORDER BY date DESC;
```

#### Option 3: Grafana Dashboard
Visual cost trends available at: `http://localhost:3002/dashboards`

### Update Historical Validation

1. Open **Historical Validation** sheet
2. Enter actual costs in column C (Actual Cost)
3. Variance automatically calculates
4. Review summary statistics
5. Adjust Input Parameters if variance > 20%

---

## 📚 Detailed Documentation

### Formula Reference
See **[EXCEL_ASSEMBLY_GUIDE.md](EXCEL_ASSEMBLY_GUIDE.md)** for:
- Complete formula listing for all cells
- Named range definitions
- VLOOKUP table structures
- Conditional formatting rules
- Data validation setups

### Chart Creation
See **[EXCEL_ASSEMBLY_GUIDE.md - Charts Section](EXCEL_ASSEMBLY_GUIDE.md#charts-and-visualizations)** for:
- Pie chart: Monthly cost breakdown
- Line chart: Annual projection
- Column chart: Scenario comparison
- Dual-line chart: Estimated vs actual costs

### Troubleshooting
See **[EXCEL_ASSEMBLY_GUIDE.md - Troubleshooting](EXCEL_ASSEMBLY_GUIDE.md#troubleshooting)** for:
- Common formula errors (#REF!, #DIV/0!, #VALUE!)
- Calculation mode issues
- Chart update problems
- VLOOKUP errors

---

## 💰 Cost Assumptions and Notes

### Token Estimation
- **Rule of thumb**: 1 token ≈ 4 characters
- **Average document**: 5,000 tokens (~20,000 characters)
- **Average chunks per document**: 4-10 (with chunk limiting)
- **Schema overhead**: 18,600 tokens per chunk (cacheable)

### Processing Estimates
- **Entities per document**: ~200 entities
- **Relationships per document**: ~500 edges
- **Entity name length**: ~10 tokens average
- **Relationship fact length**: ~20 tokens average
- **LLM output**: ~20% of input tokens

### Cache Effectiveness
- **Cache hit rate**: 85% with warm cache (production)
- **Cold start**: 50-60% cache hit rate
- **Cache discount (OpenAI)**: 50% on cached tokens
- **Cache discount (Anthropic)**: 90% on cached tokens

### Overhead Assumptions
- **Retry/Error buffer**: 15% of total cost
- **ETL overhead**: Included in per-query/per-document costs
- **Network failures**: Included in retry buffer

---

## 🎯 Budget Scenarios (Examples)

### Scenario: Startup/Testing Phase
- **Documents**: 100/month
- **Models**: gpt-4o-mini + text-embedding-3-small
- **Caching**: Enabled (85% hit rate)
- **Monthly Cost**: ~$52
- **Annual Cost**: ~$621
- **Cost per Document**: $0.52

### Scenario: Production (Medium Volume)
- **Documents**: 500/month
- **Models**: gpt-4o-mini + text-embedding-3-small
- **Caching**: Enabled (85% hit rate)
- **Monthly Cost**: ~$259
- **Annual Cost**: ~$3,102
- **Cost per Document**: $0.52

### Scenario: High Volume Production
- **Documents**: 1,000/month
- **Models**: gpt-4o-mini + text-embedding-3-small
- **Caching**: Enabled (85% hit rate)
- **Monthly Cost**: ~$517
- **Annual Cost**: ~$6,205
- **Cost per Document**: $0.52

### Scenario: Premium Multilingual
- **Documents**: 500/month
- **Models**: claude-sonnet + text-embedding-ada-002
- **Caching**: Enabled (90% hit rate)
- **Monthly Cost**: ~$788
- **Annual Cost**: ~$9,453
- **Cost per Document**: $1.58

---

## 🔄 Monthly Update Workflow

### Step 1: Update Pricing (Quarterly)
1. Check OpenAI pricing page
2. Check Anthropic pricing page
3. Update **Pricing Reference** sheet
4. Verify Exa.ai and Apify costs

### Step 2: Enter Actual Costs (Monthly)
1. Query Cost Analytics API
2. Enter in **Historical Validation** sheet column C
3. Review variance analysis
4. Investigate if variance > 20%

### Step 3: Adjust Parameters (As Needed)
1. Update **Input Parameters** based on:
   - Actual document volumes
   - Observed cache hit rates
   - Changed processing requirements
2. Review **Dashboard** for updated projections

### Step 4: Report & Plan (Monthly)
1. Review **Dashboard** metrics
2. Compare against budget
3. Adjust future plans based on trends
4. Share with stakeholders

---

## 📊 Success Metrics

### Model Accuracy
- **Target**: < 15% variance from actual costs
- **Good**: 10-15% variance
- **Excellent**: < 10% variance

### Cost Efficiency
- **Target**: < $0.60 per document (with caching)
- **Good**: $0.40-$0.60 per document
- **Excellent**: < $0.40 per document

### Budget Utilization
- **Target**: 70-90% of allocated budget
- **Alert if**: > 95% (approaching limit)
- **Review if**: < 60% (underutilized)

---

## 🆘 Support

### Questions?
- Review **[EXCEL_ASSEMBLY_GUIDE.md](EXCEL_ASSEMBLY_GUIDE.md)** for detailed instructions
- Check **Troubleshooting** section for common issues
- Consult **[Cost Analytics Documentation](../observability/COST_ANALYTICS.md)**

### Issues?
- Verify all CSV files imported correctly
- Check formulas reference correct sheets
- Ensure pricing data is up to date
- Validate against actual costs from API

### Need Help?
- Cost Analytics API: `http://localhost:8090/api/costs/`
- Grafana Dashboard: `http://localhost:3002`
- Project Documentation: `docs/INDEX.md`

---

## 📄 Version History

- **v1.0** (2025-01-XX): Initial release
  - 6 comprehensive sheets
  - Based on production configuration
  - Includes cost reduction strategies
  - Supports budget planning and tracking

---

**Status**: ✅ Ready for Use
**Last Updated**: 2025-01-XX
**Maintainer**: Political Monitoring Agent Team
