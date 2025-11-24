# Data Validation Scripts

This directory contains scripts for validating database state and data integrity.

## Scripts

### Episode Data Validation
- **check_episode_data.py** - Check episode data structure in Neo4j
  - Validate episode nodes
  - Check episode relationships
  - Verify data structure

- **check_episodic_data.py** - Check episodic data consistency
  - Data integrity checks
  - Temporal data validation
  - Entity-episode relationships

- **check_episodic_source.py** - Validate episode source information
  - Source attribution verification
  - Episode metadata validation
  - Source tracking checks

## Usage

Run validation scripts to check database state:

```bash
# From project root
python tests/validation/check_episode_data.py

# With specific Neo4j instance
NEO4J_URI=bolt://localhost:7687 python tests/validation/check_episodic_data.py
```

## When to Use

Run these scripts:
- ✅ After data ingestion to verify success
- ✅ When debugging data issues
- ✅ Before/after database migrations
- ✅ To verify episode structure
- ✅ For data quality audits

## Environment Variables

- `NEO4J_URI` - Neo4j connection URI (default: bolt://localhost:7687)
- `NEO4J_USER` - Neo4j username (default: neo4j)
- `NEO4J_PASSWORD` - Neo4j password (default: password123)
- `NEO4J_DATABASE` - Database name (default: politicalmonitoring)

## Output

Scripts typically output:
- Number of episodes found
- Data structure validation results
- Any anomalies or issues detected
- Summary statistics

## Purpose

These scripts ensure:
- 📊 Data integrity in Neo4j
- 🔍 Episode structure correctness
- ✅ Source attribution accuracy
- 🎯 Temporal data consistency
