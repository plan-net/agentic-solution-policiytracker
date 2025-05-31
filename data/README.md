# Data Directory

This directory contains all data assets for the Political Monitoring Agent v0.2.0, including input documents, analysis results, configuration, and system state.

## 📁 Directory Structure

### `/context/` - **Client Configuration** 🔧
Contains organization-specific configuration that drives the entire analysis system.

- **`client.yaml`** - **CRITICAL CONFIGURATION FILE**
  - Defines your organization's monitoring priorities
  - Controls relevance scoring and document filtering
  - Must be customized for your specific use case
  - See [Client Configuration Guide](#client-configuration-guide) below

### `/input/` - **Source Documents** 📄
Documents to be analyzed by the system.

- **`examples/`** - Sample political documents for testing
  - Pre-curated examples covering various regulatory topics
  - Use these to test system functionality
  - Includes EU AI Act, GDPR enforcement, cybersecurity directives

- **`news/`** - Automated news collection (ETL)
  - Organized by date (`2025-05/`)
  - Collected daily via automated ETL pipeline
  - Format: `YYYYMMDD_source_title-snippet.md`

- **`policy/`** - Policy documents and regulatory content
  - Manual uploads or ETL-collected policy documents
  - Organized by date and source
  - Focus on regulatory changes and enforcement actions

### `/output/` - **Analysis Results** 📊
Generated reports and analysis outputs from document processing.

- Format: `{job_name}_job_{date}_{time}_{id}_report.md`
- Contains relevance scores, topic classifications, and executive summaries
- Organized chronologically for tracking analysis history

### `/execution/` - **System State** ⚙️
Internal system state and execution tracking.

- Contains SQLite databases for workflow state management
- Organized by execution session IDs
- Used by Kodosumi flows for progress tracking and checkpointing

## 🔧 Client Configuration Guide

The `context/client.yaml` file is the **most important configuration** in the system. It defines:

### **Organization Profile**
```yaml
company_terms:
  - your-company-name
  - subsidiary-names

core_industries:
  - your-primary-industry
  - related-sectors
```

### **Geographic Focus**
```yaml
primary_markets:
  - european union
  - specific-countries

secondary_markets:
  - additional-regions
```

### **Strategic Priorities**
```yaml
strategic_themes:
  - data privacy
  - artificial intelligence
  - sustainability
  - your-key-themes
```

### **Topic Classification**
```yaml
topic_patterns:
  data-protection:
    - gdpr
    - privacy policy
    - data processing
    
  your-custom-topic:
    - relevant-keywords
    - industry-terms
```

### **Impact Detection**
```yaml
direct_impact_keywords:
  - must comply
  - required to
  - penalty
  - enforcement

exclusion_terms:
  - irrelevant-industries
  - topics-to-ignore
```

## ⚙️ How Configuration Affects Analysis

### **Relevance Scoring**
- Documents mentioning `company_terms` get higher relevance scores
- `core_industries` keywords boost industry relevance
- `strategic_themes` influence topical scoring

### **Geographic Filtering**
- `primary_markets` documents receive priority scoring
- `secondary_markets` get moderate attention
- Other regions scored lower unless highly relevant

### **Topic Classification**
- `topic_patterns` automatically categorize documents
- Enables filtering and grouping in results
- Powers the chat interface's domain knowledge

### **Impact Assessment**
- `direct_impact_keywords` flag high-priority documents
- `exclusion_terms` filter out irrelevant content
- Drives executive summary generation

## 🚀 Getting Started

### **1. Customize Client Configuration**
```bash
# Edit the client configuration for your organization
nano data/context/client.yaml
```

### **2. Add Test Documents**
```bash
# Place documents in input directory
cp your-documents/* data/input/
```

### **3. Run Analysis**
- Via Chat Interface: http://localhost:3000
- Via Document Processing: http://localhost:3370
- Via ETL Pipeline: http://localhost:8080

### **4. Review Results**
```bash
# Check generated reports
ls -la data/output/
```

## 📊 Data Flow

```
Input Documents → Client Configuration → Analysis Engine → Results
     ↓                    ↓                     ↓            ↓
  Raw Text          Organization        Relevance        Reports
  Documents           Priorities        Scoring          + Scores
```

## 🔄 ETL Data Collection

The system automatically collects data via ETL pipelines:

- **News Collection**: Daily at 6 AM UTC
- **Policy Collection**: Weekly on Sundays at 2 AM UTC
- **Storage**: Organized by date in `input/news/` and `input/policy/`
- **Deduplication**: Automatic detection and removal of duplicate content

## 🛡️ Data Security

- **Local Storage**: All data stays on your infrastructure
- **Azure Option**: Optional Azure Blob Storage for production deployments
- **No External Sharing**: Client configuration and documents remain private
- **Encryption**: Data at rest encryption via storage provider settings

## 📝 File Naming Conventions

### **Input Documents**
- News: `YYYYMMDD_source_title-snippet.md`
- Policy: `YYYYMMDD_source_title-description.md`

### **Output Reports**  
- Format: `{job_name}_job_{YYYYMMDD}_{HHMMSS}_{random_id}_report.md`
- Example: `EU_Analysis_job_20250531_143025_A1b2C3_report.md`

## 🚨 Important Notes

1. **Always Customize client.yaml**: The default configuration is for demonstration only
2. **Regular Backups**: Back up your configuration and important analysis results
3. **Monitor Storage**: Large document collections can consume significant disk space
4. **Data Privacy**: Ensure compliance with your organization's data handling policies

## 🔗 Related Documentation

- **[User Guide](../docs/USER_GUIDE.md)** - Complete usage instructions
- **[Setup Guide](../docs/SETUP.md)** - Installation and configuration
- **[Quick Reference](../docs/QUICK_REFERENCE.md)** - Commands and troubleshooting