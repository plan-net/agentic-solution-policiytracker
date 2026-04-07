# Excel Cost Estimation Model - Assembly Guide

## Overview

This guide explains how to assemble the Document Ingestion Cost Estimation Model Excel workbook from the provided CSV templates.

**Final Deliverable**: `Ingestion_Cost_Estimation_Model.xlsx`

## Quick Start

### Option 1: Import CSVs into Excel (Recommended)

1. **Open Excel** and create a new workbook
2. **Import each CSV file** as a separate sheet:
   - `01_Dashboard.csv` → Sheet name: "Dashboard"
   - `02_Input_Parameters.csv` → Sheet name: "Input Parameters"
   - `03_Pricing_Reference.csv` → Sheet name: "Pricing Reference"
   - `04_Cost_Calculator.csv` → Sheet name: "Cost Calculator"
   - `05_Scenario_Comparison.csv` → Sheet name: "Scenario Comparison"
   - `06_Historical_Validation.csv` → Sheet name: "Historical Validation"

3. **Apply formulas** from the Formula Reference section below
4. **Format and style** using the Formatting Guide
5. **Add charts** from the Charts and Visualizations section
6. **Save** as `Ingestion_Cost_Estimation_Model.xlsx`

### Option 2: Manual Construction

Follow the detailed Sheet-by-Sheet Guide below to build each sheet from scratch.

---

## Sheet-by-Sheet Construction Guide

### Sheet 1: Dashboard

**Purpose**: Executive summary with visual indicators and quick cost estimator

#### Key Formulas

| Cell | Formula | Description |
|------|---------|-------------|
| `B5` | `='Input Parameters'!B4` | Documents per month |
| `B6` | `='Cost Calculator'!B71` | Total monthly cost |
| `B7` | `=B6/B5` | Cost per document |
| `B13` | `='Cost Calculator'!B71` | Current month cost |
| `B14` | Manual entry | Previous month cost |
| `C14` | `=B13-B14` | Change in cost |
| `D14` | `=C14/B14` | Percentage change |
| `E14` | `=IF(D14<0.05,"🟢",IF(D14<0.15,"🟡","🔴"))` | Status indicator |

#### Chart: Cost Breakdown Pie Chart

- **Data Range**: `B20:C23` (Component names and costs)
- **Chart Type**: Pie Chart
- **Title**: "Monthly Cost Breakdown"
- **Position**: Below Key Metrics Summary

#### Chart: Annual Projection Line Chart

- **Data Range**: `A27:B39` (Months and estimated cost)
- **Chart Type**: Line Chart with markers
- **Title**: "Annual Cost Projection"
- **Position**: Below Cost Breakdown

---

### Sheet 2: Input Parameters

**Purpose**: All configurable variables that drive the model

#### Key Formulas

| Cell | Formula | Description |
|------|---------|-------------|
| `B14` | `=CEILING(B5/B11,1)` | Average chunks per document |
| `B40` | `=B37+B38` | Total schema overhead |
| `B41` | `=B40*(1-B20)` | Effective schema tokens with caching |

#### Data Validation (Dropdowns)

1. **Cell B18** (LLM Model):
   - Data validation → List
   - Source: `gpt-4o-mini, gpt-4o, claude-sonnet-4, claude-haiku`

2. **Cell B19** (Embedding Model):
   - Data validation → List
   - Source: `text-embedding-3-small, text-embedding-3-large, text-embedding-ada-002`

3. **Cell B20** (Enable Prompt Caching):
   - Data validation → List
   - Source: `YES, NO`

4. **Cell B26** (Enable Chunk Limiting):
   - Data validation → List
   - Source: `YES, NO`

#### Conditional Formatting

- **Cells B4, B5, B6** (Document volumes): Light blue background
- **Cells B18, B19** (Model selection): Light green background
- **Cell B20** (Caching): Light yellow background

---

### Sheet 3: Pricing Reference

**Purpose**: Central repository for all API pricing (updateable)

#### Key Formulas

| Cell | Formula | Description |
|------|---------|-------------|
| `B45` | `=B8/1000` | Cost per 1K tokens (gpt-4o-mini input) |
| `B46` | `=C8/1000` | Cost per 1K tokens (gpt-4o-mini output) |
| `B47` | `=B18/1000` | Cost per 1K tokens (embedding-3-small) |
| `B48` | `=18600*B45` | Schema cost per chunk (no cache) |
| `B49` | `=18600*(1-0.85)*B45` | Schema cost per chunk (85% cache) |

#### Important: Update Required Fields

Mark cells **C7** and **C8** (Exa.ai and Apify costs) with:
- **Fill color**: Orange
- **Comment**: "UPDATE REQUIRED - Add actual API pricing"

---

### Sheet 4: Cost Calculator

**Purpose**: Detailed step-by-step cost calculation with formulas

#### Critical Formulas (Full Formula Reference)

**STEP 1: ETL Collection Cost**
| Cell | Formula | Description |
|------|---------|-------------|
| `B5` | `='Input Parameters'!B4` | Documents to collect |
| `B6` | `='Input Parameters'!B29` | Exa.ai queries per doc |
| `B7` | `=B5*B6` | Total Exa.ai queries |
| `B8` | `='Pricing Reference'!C7` | Exa.ai cost per query |
| `B9` | `=B7*B8` | Total Exa.ai cost |
| `B11` | `=B5*0.5` | Apify documents (assume 50%) |
| `B12` | `='Pricing Reference'!C8` | Apify cost per document |
| `B13` | `=B11*B12` | Total Apify cost |
| `B15` | `=B9+B13` | **Total ETL Collection Cost** |

**STEP 2: Document Chunking**
| Cell | Formula | Description |
|------|---------|-------------|
| `B18` | `='Input Parameters'!B5` | Average document length |
| `B19` | `='Input Parameters'!B11` | Default chunk size |
| `B20` | `=CEILING(B18/B19,1)` | Chunks per document (raw) |
| `B21` | `='Input Parameters'!B26` | Chunk limiting enabled? |
| `B22` | `='Input Parameters'!B13` | Max chunks per document |
| `B23` | `=IF(B21="YES",MIN(B20,B22),B20)` | Effective chunks per document |
| `B24` | `=B5*B23` | Total chunks to process |

**STEP 3: LLM Processing Cost**
| Cell | Formula | Description |
|------|---------|-------------|
| `B28` | `='Pricing Reference'!B49` | Schema overhead per chunk (from pricing sheet, line 49 has 18600) |
| `B29` | `='Input Parameters'!B19` | Prompt caching enabled? |
| `B30` | `='Input Parameters'!B20` | Cache hit rate |
| `B31` | `=B28*(1-B30)` | Effective schema tokens |
| `B32` | `=B24*B31` | Total schema input tokens |
| `B33` | `=B24*B19` | Content input tokens |
| `B34` | `=B32+B33` | Total input tokens |
| `B36` | `='Input Parameters'!B18` | Selected LLM model |
| `B37` | `=VLOOKUP(B36,'Pricing Reference'!$A$8:$C$11,2,FALSE)` | LLM input price per 1M |
| `B38` | `=VLOOKUP(B36,'Pricing Reference'!$A$8:$C$11,3,FALSE)` | LLM output price per 1M |
| `B39` | `=B34*0.2` | Estimated output tokens (20% of input) |
| `B41` | `=B34*B37/1000000` | LLM input cost |
| `B42` | `=B39*B38/1000000` | LLM output cost |
| `B43` | `=B41+B42` | **Total LLM Processing Cost** |

**STEP 4: Embedding Generation Cost**
| Cell | Formula | Description |
|------|---------|-------------|
| `B46` | `=B5*B18` | Total document length (tokens) |
| `B47` | `='Input Parameters'!B19` | Selected embedding model |
| `B48` | `=VLOOKUP(B47,'Pricing Reference'!$A$18:$B$20,2,FALSE)` | Embedding price per 1M |
| `B50` | `=B46*B48/1000000` | Episode embedding cost |
| `B51` | `=B5*200` | Entity embeddings (200 per doc) |
| `B52` | `10` | Average entity name length |
| `B53` | `=B51*B52` | Total entity tokens |
| `B54` | `=B53*B48/1000000` | Entity embedding cost |
| `B56` | `=B5*500` | Relationship embeddings (500 per doc) |
| `B57` | `20` | Average relationship fact length |
| `B58` | `=B56*B57` | Total relationship tokens |
| `B59` | `=B58*B48/1000000` | Relationship embedding cost |
| `B61` | `=B50+B54+B59` | **Total Embedding Cost** |

**STEP 5: Total Cost Calculation**
| Cell | Formula | Description |
|------|---------|-------------|
| `B64` | `=B15` | ETL collection cost |
| `B65` | `=B43` | LLM processing cost |
| `B66` | `=B61` | Embedding generation cost |
| `B69` | `='Input Parameters'!B27/100*SUM(B64:B66)` | Retry/error overhead (15%) |
| `B71` | `=SUM(B64:B66)+B69` | **TOTAL MONTHLY COST** |

**Per-Document Metrics**
| Cell | Formula | Description |
|------|---------|-------------|
| `B74` | `=B71/B5` | Cost per document |
| `B75` | `=B71/B24` | Cost per chunk |
| `B76` | `=B43/B34` | Cost per token (input) |

**Annual Projection**
| Cell | Formula | Description |
|------|---------|-------------|
| `B80` | `=B71*12` | Annual cost |
| `B81` | `=B5*12` | Annual documents |
| `B82` | `=B80/B81` | Annual cost per document |

---

### Sheet 5: Scenario Comparison

**Purpose**: Side-by-side comparison of different configurations

#### Scenario Configuration Approach

Each scenario (columns C through G) represents a different set of input parameters. The formulas should reference the **Cost Calculator** sheet but with adjusted inputs.

**Recommended Approach**: Create 5 hidden "scratch" sheets for each scenario with adjusted parameters, or use direct value entry for simplicity.

#### Key Formulas for Scenario Columns

For **Scenario A** (Column C) - Example:
| Cell | Formula | Description |
|------|---------|-------------|
| `C4` | `100` | Documents per month (hardcoded for scenario) |
| `C5` | `gpt-4o-mini` | LLM model (hardcoded) |
| `C6` | `embedding-3-small` | Embedding model (hardcoded) |
| `C13` | Formula based on C4-C10 | ETL collection cost |
| `C14` | Formula based on C4-C10 | LLM processing cost |
| `C15` | Formula based on C4-C10 | Embedding cost |
| `C16` | `=(C13+C14+C15)*0.15` | Overhead (15%) |
| `C17` | `=SUM(C13:C16)` | Total monthly cost |

**Simpler Approach**: Manually enter calculated costs for each scenario, then formulas only needed for totals and percentages.

#### Comparison Chart Data

- **Data Range**: `A41:F44` (Components × Scenarios)
- **Chart Type**: Clustered Column Chart
- **Title**: "Cost Comparison Across Scenarios"

---

### Sheet 6: Historical Validation

**Purpose**: Track actual vs estimated costs over time

#### Key Formulas

| Cell | Formula | Description |
|------|---------|-------------|
| `B13` | `='Cost Calculator'!B71` | Estimated cost (from calculator) |
| `C13` | Manual entry | Actual cost (enter from cost analytics API) |
| `D13` | `=C13-B13` | Variance ($) |
| `E13` | `=IF(B13>0,D13/B13,0)` | Variance (%) |
| `H13` | `=IF(F13>0,C13/F13,0)` | Cost per doc (actual) |
| `I13` | `=IF(G13>0,B13/G13,0)` | Cost per doc (estimated) |

#### Summary Statistics

| Cell | Formula | Description |
|------|---------|-------------|
| `C29` | `=SUM(B13:B24)` | Total estimated (YTD) |
| `C30` | `=SUM(C13:C24)` | Total actual (YTD) |
| `C31` | `=C30-C29` | Total variance |
| `C32` | `=AVERAGE(E13:E24)` | Average variance % |
| `C33` | `=1-ABS(C32)` | Accuracy rate |

#### Trend Chart

- **Data Range**: `A13:C24` (Months, Estimated, Actual)
- **Chart Type**: Line chart with two series
- **Title**: "Estimated vs Actual Costs Over Time"

---

## Advanced Excel Features

### Named Ranges (Recommended)

Create named ranges for easier formula management:

| Name | Range | Usage |
|------|-------|-------|
| `DocsPerMonth` | `'Input Parameters'!B4` | Total documents |
| `ChunkSize` | `'Input Parameters'!B11` | Default chunk size |
| `CacheRate` | `'Input Parameters'!B20` | Cache hit rate |
| `LLMModel` | `'Input Parameters'!B18` | Selected LLM model |
| `EmbedModel` | `'Input Parameters'!B19` | Selected embedding model |
| `TotalMonthlyCost` | `'Cost Calculator'!B71` | Total monthly cost |

**Benefit**: Can use `=TotalMonthlyCost` instead of `='Cost Calculator'!B71`

### Conditional Formatting Rules

#### 1. Dashboard - Budget Status Indicators

**Rule**: Traffic light colors for variance percentage
- **Applies to**: `E14:E17`
- **Formula**:
  - Green (`#00B050`): `=E14<0.05` (< 5% variance)
  - Yellow (`#FFC000`): `=AND(E14>=0.05,E14<0.15)` (5-15% variance)
  - Red (`#FF0000`): `=E14>=0.15` (> 15% variance)

#### 2. Pricing Reference - Update Required

**Rule**: Highlight cells that need updating
- **Applies to**: `C7:C8` (Exa.ai and Apify costs)
- **Format**: Orange fill (`#FFC000`), bold font
- **Cell comment**: "UPDATE REQUIRED"

#### 3. Historical Validation - Variance Alerts

**Rule**: Highlight high variances
- **Applies to**: `E13:E24` (Variance %)
- **Formula**:
  - Red text: `=ABS(E13)>0.25` (> 25% variance)
  - Yellow text: `=AND(ABS(E13)>0.1,ABS(E13)<=0.25)` (10-25% variance)

### Data Validation

#### Input Parameters Sheet

1. **Cell B18** - LLM Model Selection
   - **Type**: List
   - **Source**: `gpt-4o-mini,gpt-4o,claude-sonnet-4,claude-haiku`
   - **Error Alert**: "Please select a valid LLM model"

2. **Cell B19** - Embedding Model Selection
   - **Type**: List
   - **Source**: `text-embedding-3-small,text-embedding-3-large,text-embedding-ada-002`
   - **Error Alert**: "Please select a valid embedding model"

3. **Cell B20** - Enable Prompt Caching
   - **Type**: List
   - **Source**: `YES,NO`

4. **Cell B4** - Documents per Month
   - **Type**: Whole number
   - **Minimum**: 1
   - **Maximum**: 10000
   - **Error Alert**: "Documents must be between 1 and 10,000"

5. **Cell B5** - Average Document Length
   - **Type**: Whole number
   - **Minimum**: 100
   - **Maximum**: 50000
   - **Error Alert**: "Document length must be between 100 and 50,000 tokens"

---

## Charts and Visualizations

### Chart 1: Monthly Cost Breakdown (Dashboard)

**Type**: Pie Chart
- **Data**: Dashboard!B20:C23 (Component names and costs)
- **Title**: "Monthly Cost Breakdown"
- **Legend**: Right side
- **Data Labels**: Show percentages
- **Colors**:
  - ETL: Blue (`#4472C4`)
  - LLM: Green (`#70AD47`)
  - Embeddings: Orange (`#FFC000`)
  - Overhead: Gray (`#A5A5A5`)

### Chart 2: Annual Projection (Dashboard)

**Type**: Line Chart with Markers
- **Data**: Dashboard!A27:B39 (Months and costs)
- **Title**: "Annual Cost Projection"
- **X-axis**: Month names
- **Y-axis**: Cost ($)
- **Line color**: Blue (`#4472C4`)
- **Markers**: Circles, size 5

### Chart 3: Scenario Comparison (Scenario Comparison Sheet)

**Type**: Clustered Column Chart
- **Data**: Scenario Comparison!A41:F44 (Components × Scenarios)
- **Title**: "Cost Comparison Across Scenarios"
- **X-axis**: Components (ETL, LLM, Embeddings, Overhead)
- **Y-axis**: Cost ($)
- **Legend**: Scenario names
- **Colors**: Different color for each scenario

### Chart 4: Estimated vs Actual (Historical Validation)

**Type**: Line Chart with Two Series
- **Data**: Historical Validation!A13:C24 (Months, Estimated, Actual)
- **Title**: "Estimated vs Actual Costs"
- **Series 1 (Estimated)**: Dashed line, blue
- **Series 2 (Actual)**: Solid line, green
- **Legend**: Top right

---

## Formatting Guide

### Color Scheme

| Element | Color | Hex Code |
|---------|-------|----------|
| Header rows | Dark Blue | `#4472C4` |
| Input cells | Light Blue | `#D9E1F2` |
| Calculated cells | Light Gray | `#F2F2F2` |
| Important totals | Light Green | `#E2EFDA` |
| Update required | Orange | `#FFC000` |
| Alerts/Warnings | Light Red | `#FCE4D6` |

### Font Styles

- **Headers**: Bold, 12pt, White text on dark blue background
- **Section titles**: Bold, 11pt, Dark blue text
- **Data cells**: Regular, 10pt, Black text
- **Formula cells**: Italic, 10pt, Dark gray text
- **Important totals**: Bold, 11pt, Dark green text

### Cell Borders

- **Header rows**: Thick bottom border
- **Section separators**: Medium bottom border
- **Data tables**: Thin borders around all cells
- **Total rows**: Double bottom border

### Number Formatting

| Cell Type | Format | Example |
|-----------|--------|---------|
| Currency | `$#,##0.00` | $1,234.56 |
| Percentage | `0.0%` | 85.0% |
| Large numbers | `#,##0` | 1,234 |
| Tokens | `#,##0` | 18,600 |

### Column Widths

- **Column A** (Labels): 30 characters
- **Column B** (Values): 15 characters
- **Column C+** (Additional data): 12 characters

---

## Testing Your Workbook

### Validation Checklist

- [ ] **Formula integrity**: All formulas reference correct cells
- [ ] **Cross-sheet references**: Links between sheets work correctly
- [ ] **Data validation**: Dropdowns function properly
- [ ] **Conditional formatting**: Colors update based on values
- [ ] **Charts**: Update when underlying data changes
- [ ] **Named ranges**: Work correctly in formulas (if used)
- [ ] **Circular references**: None present (check with Formulas → Error Checking)

### Test Scenarios

1. **Change document volume**: Update Input Parameters!B4 to 1000
   - [ ] Dashboard total cost updates
   - [ ] Cost Calculator recalculates
   - [ ] Charts reflect new values

2. **Change LLM model**: Select different model in Input Parameters!B18
   - [ ] Cost Calculator pricing updates via VLOOKUP
   - [ ] Total cost changes accordingly

3. **Toggle prompt caching**: Set Input Parameters!B20 to NO
   - [ ] LLM processing cost increases significantly
   - [ ] Dashboard shows higher total

4. **Enter actual costs**: Add data to Historical Validation!C13
   - [ ] Variance columns calculate automatically
   - [ ] Summary statistics update

### Common Formula Errors to Check

| Error | Likely Cause | Solution |
|-------|--------------|----------|
| `#REF!` | Deleted row/column referenced in formula | Update formula references |
| `#DIV/0!` | Division by zero | Add `IF` check: `=IF(B5>0,B6/B5,0)` |
| `#VALUE!` | Text in numeric formula | Verify data types |
| `#NAME?` | Typo in sheet name or named range | Correct spelling |
| `#N/A` | VLOOKUP not finding match | Check lookup value exists |

---

## Maintenance and Updates

### Quarterly Tasks

1. **Update API pricing** (Pricing Reference sheet)
   - Check OpenAI pricing page
   - Check Anthropic pricing page
   - Update cells as needed

2. **Validate estimates** (Historical Validation sheet)
   - Enter actual costs from last quarter
   - Review variance trends
   - Adjust input parameters if needed

3. **Review scenarios** (Scenario Comparison sheet)
   - Update scenarios based on new use cases
   - Recalculate with latest pricing

### Annual Tasks

1. **Audit formulas**
   - Check all formulas still reference correct cells
   - Remove unused sheets/ranges

2. **Archive historical data**
   - Save previous year's validation data
   - Reset for new year

3. **Update assumptions**
   - Review average document length
   - Update chunk size if changed
   - Verify cache hit rates

---

## Troubleshooting

### Issue: Formulas Not Calculating

**Solution**: Check calculation mode
- Formulas → Calculation Options → Set to "Automatic"

### Issue: Charts Not Updating

**Solution**: Refresh chart data
1. Right-click chart → Select Data
2. Verify data range is correct
3. Click OK to refresh

### Issue: VLOOKUP Returns #N/A

**Solution**: Check lookup table
1. Verify lookup value exists in first column of table
2. Ensure table range is absolute (`$A$8:$C$11`)
3. Check spelling matches exactly

### Issue: Cross-Sheet References Break

**Solution**: Use full sheet name syntax
- Incorrect: `=Sheet1!A1`
- Correct: `='Input Parameters'!A1` (with quotes if name has spaces)

---

## Quick Reference: Key Cells

### Most Important Cells to Update

| Cell | Description | Update Frequency |
|------|-------------|------------------|
| `'Input Parameters'!B4` | Documents per month | Monthly |
| `'Input Parameters'!B18` | LLM model selection | As needed |
| `'Input Parameters'!B19` | Embedding model selection | As needed |
| `'Pricing Reference'!C7` | Exa.ai cost per query | Quarterly |
| `'Pricing Reference'!C8` | Apify cost per document | Quarterly |
| `'Historical Validation'!C13:C24` | Actual monthly costs | Monthly |

### Most Important Output Cells

| Cell | Description |
|------|-------------|
| `'Cost Calculator'!B71` | Total monthly cost |
| `'Cost Calculator'!B74` | Cost per document |
| `'Cost Calculator'!B80` | Annual cost projection |
| `'Dashboard'!B6` | Quick monthly cost estimate |

---

## Support and Documentation

### Related Files

- CSV templates in `docs/cost-estimation/csv-templates/`
- Formula reference in this document
- Source data from `apisix/config/llm_pricing.yaml`
- Cost tracking API at `http://localhost:8090/api/costs/summary`

### Getting Actual Cost Data

```bash
# Get LLM costs from Cost Analytics API
curl http://localhost:8090/api/costs/summary?days=30

# Get cost breakdown by model
curl http://localhost:8090/api/costs/by-model

# Get cost breakdown by agent
curl http://localhost:8090/api/costs/by-agent
```

### Grafana Dashboard

Access visual cost trends at: `http://localhost:3002/dashboards`

---

## Version History

- **v1.0** (2025-01-XX): Initial release
  - 6 sheets with comprehensive cost modeling
  - Based on actual production configuration
  - Includes prompt caching and chunk limiting strategies

---

**Questions or Issues?** Review the Troubleshooting section or check the related documentation in `docs/cost-estimation/`.
