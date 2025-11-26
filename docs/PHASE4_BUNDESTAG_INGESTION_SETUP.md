# Phase 4: Bundestag DIP Data Ingestion Setup

**Database**: `politicalmonitoring.v3`
**Status**: ✅ Ready for Data Ingestion
**Last Updated**: 2025-11-25

---

## 📋 Overview

Phase 4 sets up structured data ingestion from the **German Bundestag DIP API** (Dokumentations- und Informationssystem für Parlamentsmaterialien). This includes 8 data sources representing the complete German parliamentary knowledge graph.

## 🗂️ Bundestag Data Sources

### 1. **Prerequisite Reference Data** (Run First)

#### Flow 5g: Wahlperiode (Electoral Periods)
- **Script**: `src/flows/bundestag_wahlperiode/load_wahlperioden.py`
- **Purpose**: Creates Wahlperiode nodes (e.g., "20. Wahlperiode")
- **Status**: ✅ Script available
- **Database**: Updated to use `politicalmonitoring.v3` ✅
- **Run Command**:
  ```bash
  uv run python src/flows/bundestag_wahlperiode/load_wahlperioden.py
  ```

#### Flow 5h: Fraktion (Parliamentary Groups)
- **Script**: `src/flows/bundestag_fraktion/load_fraktionen.py`
- **Purpose**: Creates Fraktion nodes (CDU/CSU, SPD, Grüne, FDP, AfD, Die Linke)
- **Status**: ✅ Script available
- **Database**: Updated to use `politicalmonitoring.v3` ✅
- **Run Command**:
  ```bash
  uv run python src/flows/bundestag_fraktion/load_fraktionen.py
  ```

---

### 2. **Core Entity Flows** (Run After Prerequisites)

#### Flow 5a: Bundestag Person (MPs)
- **Endpoint**: `/bundestag-person` (NOT YET DEPLOYED)
- **Purpose**: Collect all Bundestag members (MdBs) with biographical data
- **Status**: ⚠️ App configured for v3, but NOT deployed to Ray Serve
- **Database**: ✅ Updated to `politicalmonitoring.v3`
- **Dependencies**: Wahlperiode, Fraktion
- **Access**: Via Kodosumi admin when deployed

#### Flow 5b: Bundestag Vorgang (Legislative Procedures)
- **Endpoint**: `/bundestag-vorgang`
- **Purpose**: Collect legislative procedures (bills, motions, initiatives)
- **Status**: ✅ DEPLOYED and HEALTHY
- **Database**: ✅ Uses `politicalmonitoring.v3`
- **Dependencies**: Wahlperiode, Fraktion (optional)
- **Access**: http://localhost:3370

#### Flow 5c: Bundestag Drucksache (Parliamentary Documents)
- **Endpoint**: `/bundestag-drucksache` (NOT YET DEPLOYED)
- **Purpose**: Collect Drucksachen (bills, reports, inquiries) with optional PDF download
- **Status**: ⚠️ App available but NOT deployed
- **Database**: ✅ Configured for `politicalmonitoring.v3`
- **Dependencies**: Wahlperiode, Vorgang
- **Access**: Via Kodosumi admin when deployed

---

### 3. **Linking Flows** (Run After Core Entities)

#### Flow 5f: Bundestag Aktivitaet (Parliamentary Activities)
- **Endpoint**: `/bundestag-aktivitaet`
- **Purpose**: Collect activities (questions, answers, speeches) that link entities
- **Status**: ✅ DEPLOYED and HEALTHY
- **Database**: ✅ Uses `politicalmonitoring.v3`
- **Dependencies**: Person, Drucksache, Vorgang (optional)
- **Access**: http://localhost:3370

#### Flow 5d: Bundestag Plenarprotokoll (Plenary Protocols)
- **Endpoint**: `/bundestag-plenarprotokoll` (EXISTS BUT NOT IN CONFIG)
- **Purpose**: Collect plenary session transcripts
- **Status**: ⚠️ Flow exists but NOT deployed
- **Database**: Needs verification
- **Dependencies**: Person, Vorgang
- **Access**: Not currently accessible

---

## 🔄 Recommended Ingestion Order

### **Step 1: Load Prerequisites** ✅ READY
```bash
# 1. Load electoral periods (20. Wahlperiode, 21. Wahlperiode, etc.)
uv run python src/flows/bundestag_wahlperiode/load_wahlperioden.py

# 2. Load parliamentary groups (CDU/CSU, SPD, Grüne, etc.)
uv run python src/flows/bundestag_fraktion/load_fraktionen.py
```

**Expected Result**:
- ~3 Wahlperiode nodes created
- ~6 Fraktion nodes created

---

### **Step 2: Collect Core Entities** ⚠️ PARTIALLY READY

#### Option A: Start with Vorgang (Currently Deployed)
```
1. Access Kodosumi: http://localhost:3370
2. Navigate to "Flow 5b: Bundestag Vorgang"
3. Configure:
   - Wahlperiode: "20" (current period)
   - Max items: 100 (test run)
4. Submit and monitor progress
```

**Expected Result**:
- ~100 Vorgang nodes created
- Relationships to Wahlperiode
- Deskriptor and Sachgebiet nodes

#### Option B: Deploy Missing Flows First
```bash
# Add flow5a-bundestag-person to config.yaml
# Add flow5c-bundestag-drucksache to config.yaml
# Add flow5d-bundestag-plenarprotokoll to config.yaml

# Then redeploy
just sync-config
uv run --active serve deploy config.yaml
```

---

### **Step 3: Link Entities with Activities** ✅ READY (After Step 2)
```
1. Access Kodosumi: http://localhost:3370
2. Navigate to "Flow 5f: Bundestag Aktivitaet"
3. Configure:
   - Wahlperiode: "20"
   - Aktivitätsart: "Alle" (all types)
   - Max items: 100 (test run)
4. Submit and monitor progress
```

**Expected Result**:
- ~100 Aktivität nodes created
- PERFORMED_BY relationships to Persons
- REFERENCES_DOCUMENT relationships to Drucksachen
- RELATED_TO_VORGANG relationships

---

## 📊 Current Deployment Status

### ✅ Currently Deployed (4 services)
1. **chat-server** - Chat interface (uses v3)
2. **flow5b-bundestag-vorgang** - Legislative procedures (uses v3)
3. **flow5f-bundestag-aktivitaet** - Parliamentary activities (uses v3)
4. **graph-viz-server** - Graph visualization (uses v3)

### ⚠️ Available But Not Deployed
- **flow5a-bundestag-person** - Bundestag members
- **flow5c-bundestag-drucksache** - Parliamentary documents
- **flow5d-bundestag-plenarprotokoll** - Plenary transcripts
- **flow1-data-ingestion** - Unstructured markdown documents (for later)

---

## 🎯 Phase 4 Completion Checklist

### Immediate Actions (To Start Ingestion)

- [ ] **Load reference data**:
  - [ ] Run `load_wahlperioden.py` script
  - [ ] Run `load_fraktionen.py` script
  - [ ] Verify nodes created in Neo4j

- [ ] **Test Flow 5b (Vorgang)** - Already deployed:
  - [ ] Access http://localhost:3370
  - [ ] Run small test (100 items, Wahlperiode 20)
  - [ ] Verify data in `politicalmonitoring.v3`

- [ ] **Test Flow 5f (Aktivitaet)** - Already deployed:
  - [ ] Run after Vorgang test
  - [ ] Verify relationships created

### Optional - Deploy Additional Flows

- [ ] **Deploy Flow 5a (Person)**:
  - [ ] Add to config.yaml
  - [ ] Sync and redeploy
  - [ ] Test ingestion

- [ ] **Deploy Flow 5c (Drucksache)**:
  - [ ] Add to config.yaml
  - [ ] Sync and redeploy
  - [ ] Test ingestion (with/without PDF download)

- [ ] **Deploy Flow 5d (Plenarprotokoll)**:
  - [ ] Add to config.yaml
  - [ ] Verify database configuration
  - [ ] Sync and redeploy
  - [ ] Test ingestion

---

## 🔍 Verification Queries

### Check Reference Data
```cypher
// Check Wahlperiode nodes
MATCH (w:Wahlperiode)
RETURN w.name, w.number, w.start_date, w.end_date
ORDER BY w.number DESC

// Check Fraktion nodes
MATCH (f:Fraktion)
RETURN f.name, f.abbreviation, f.color
ORDER BY f.name
```

### Check Ingested Data
```cypher
// Count nodes by type
MATCH (n)
WHERE n:Vorgang OR n:BundestagPerson OR n:Drucksache OR n:Aktivitaet
RETURN labels(n)[0] AS type, count(n) AS count
ORDER BY count DESC

// Check relationships
MATCH (a:Aktivitaet)-[r]->(b)
RETURN type(r) AS relationship_type, count(r) AS count
ORDER BY count DESC
LIMIT 20
```

---

## 📝 Notes

### API Rate Limits
- Bundestag DIP API may have rate limits
- Start with small test batches (100 items)
- Monitor for 429 (Too Many Requests) responses

### Data Volume Estimates
- **Persons**: ~1,000 MPs across all Wahlperioden
- **Vorgänge**: ~50,000 legislative procedures (20th Wahlperiode alone)
- **Drucksachen**: ~200,000 documents
- **Aktivitäten**: ~500,000 activities

### Performance Considerations
- Use batch processing for large ingestions
- Consider running during off-hours
- Monitor Neo4j memory usage
- Ray actor memory: 4-8GB per flow

---

## 🚀 Next Steps (Phase 5)

After completing Bundestag ingestion, proceed to:

**Phase 5: Unstructured Document Ingestion**
- Markdown documents from `data/input/`
- News articles
- Policy documents
- Using document_processor.py with EntityRegistry Phase 2

---

**Phase 4 Version**: 1.0
**Last Updated**: 2025-11-25
**Status**: Ready to begin with Flows 5b and 5f (deployed)
**Next Action**: Load prerequisite reference data (Wahlperiode + Fraktion)
