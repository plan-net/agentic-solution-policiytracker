"""
Flow 1: Data Ingestion Analyzer - Main entrypoint logic

Ray-based processing workflow for document ingestion with Graphiti.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import structlog
from kodosumi import core
from kodosumi.core import Tracer

from src.flows.data_ingestion.document_tracker import DocumentTracker
from src.flows.data_ingestion.document_processor import SimpleDocumentProcessor, find_documents
from src.flows.shared.graphiti_client import SharedGraphitiClient

logger = structlog.get_logger()


async def execute_ingestion(inputs: dict, tracer: Tracer):
    """Main entrypoint for data ingestion flow."""
    
    start_time = datetime.now()
    
    # Extract inputs
    job_name = inputs.get("job_name", "Document Ingestion")
    source_path = inputs.get("source_path", "data/input/policy/")
    document_limit = inputs.get("document_limit", 10)
    clear_data = inputs.get("clear_data", False)
    enable_communities = inputs.get("enable_communities", False)  # Now disabled by default
    
    await tracer.markdown(f"""
# 📄 {job_name} - Starting

**Configuration:**
- Source Path: `{source_path}` (policy documents)
- Document Limit: {document_limit}
- Clear Data: {'✅ Yes' if clear_data else '❌ No'}
- Build Communities: ❌ No (use `just build-communities` command)

---
""")
    
    try:
        # Validate source path and count documents
        source_path_obj = Path(source_path)
        available_docs = find_documents(source_path_obj, document_limit)
        
        if not available_docs:
            await tracer.markdown("❌ **Error:** No supported documents found (.txt, .md)")
            return {"error": "No documents found"}
        
        await tracer.markdown(f"""
## 📊 Document Discovery

Found **{len(available_docs)}** documents to process:
{chr(10).join(f"- {doc.name}" for doc in available_docs[:5])}
{'...' if len(available_docs) > 5 else ''}

---
""")
        
        # Start document processing directly (no Ray actors)
        await tracer.markdown("🚀 **Starting document processing...**")
        
        # Initialize components
        tracker = DocumentTracker()
        processor = SimpleDocumentProcessor(tracker, clear_data)
        
        # Clear data if requested
        if clear_data:
            await tracer.markdown("🧹 **Clearing existing data...**")
            async with SharedGraphitiClient() as graphiti_client:
                cleared = await graphiti_client.clear_graph()
                if cleared:
                    tracker.clear_all()
                    logger.info("Graph and tracking data cleared")
                else:
                    logger.warning("Failed to clear graph data")
        
        # Process documents with progress updates
        processing_result = await processor.process_documents(
            source_path_obj, 
            document_limit,
            tracer=tracer
        )
        
        # Format result for compatibility with existing code
        processing_result = {
            "status": "success",
            "results": processing_result,
            "stats": processor.get_processing_stats(),
            "tracker_stats": tracker.get_stats()
        }
        
        # Report processing results
        if processing_result["status"] == "success":
            stats = processing_result["stats"]
            tracker_stats = processing_result["tracker_stats"]
            
            await tracer.markdown(f"""
## ✅ Document Processing Complete

**Processing Statistics:**
- **Total Documents:** {stats.get('total_documents', 0)}
- **Processed:** {stats.get('processed', 0)}
- **Skipped:** {stats.get('skipped', 0)}
- **Failed:** {stats.get('failed', 0)}
- **Success Rate:** {stats.get('success_rate', 0):.1f}%

**Knowledge Graph Growth:**
- **Total Entities:** {stats.get('total_entities', 0)}
- **Total Relationships:** {stats.get('total_relationships', 0)}
- **Avg Entities/Doc:** {stats.get('avg_entities_per_doc', 0):.1f}
- **Processing Time:** {stats.get('total_processing_time', 0):.2f}s

---
""")
        else:
            error_msg = processing_result.get("error", "Unknown error")
            await tracer.markdown(f"""
## ❌ Document Processing Failed

**Error:** {error_msg}

---
""")
            return {"error": error_msg}
        
        # Get relationship distribution from the graph
        relationship_distribution = {}
        try:
            async with SharedGraphitiClient() as graphiti_client:
                relationship_distribution = await graphiti_client.get_relationship_distribution()
        except Exception as e:
            logger.warning(f"Failed to get relationship distribution: {e}")
        
        # Build communities if enabled
        communities_result = {"status": "skipped", "communities": [], "community_count": 0}
        
        if enable_communities and processing_result["status"] == "success":
            await tracer.markdown("🏘️ **Building document communities...**")
            await tracer.markdown("⏳ _Running community detection algorithm (max 60s)..._")
            
            try:
                import asyncio
                community_start_time = asyncio.get_event_loop().time()
                
                async with SharedGraphitiClient() as graphiti_client:
                    communities = await graphiti_client.build_communities(timeout_seconds=60)
                    
                    end_time = asyncio.get_event_loop().time()
                    duration = end_time - community_start_time
                    
                    if communities:
                        await tracer.markdown(f"✅ **Built {len(communities)} communities** in {duration:.1f}s")
                        communities_result = {
                            "status": "success",
                            "communities": communities,
                            "community_count": len(communities)
                        }
                    else:
                        await tracer.markdown("⚠️ **No communities built** (may have timed out or no clusters found)")
                        communities_result = {
                            "status": "completed_no_communities",
                            "communities": [],
                            "community_count": 0
                        }
                        
            except Exception as e:
                logger.error(f"Community building failed: {e}")
                await tracer.markdown(f"❌ **Community building failed**: {str(e)}")
                communities_result = {
                    "status": "failed",
                    "error": str(e),
                    "communities": [],
                    "community_count": 0
                }
            
            if communities_result["status"] == "success":
                community_count = communities_result["community_count"]
                await tracer.markdown(f"""
## 🏘️ Communities Created

**Community Statistics:**
- **Total Communities:** {community_count}
- **Status:** {'✅ Success' if community_count > 0 else '⚠️ No communities found'}

---
""")
            else:
                await tracer.markdown(f"""
## ⚠️ Community Building Issues

**Error:** {communities_result.get('error', 'Unknown error')}

---
""")
        
        # Calculate total execution time
        try:
            total_time = (datetime.now() - start_time).total_seconds()
        except Exception as e:
            logger.error(f"Datetime calculation failed - start_time type: {type(start_time)}, value: {start_time}")
            logger.error(f"datetime.now() type: {type(datetime.now())}, value: {datetime.now()}")
            logger.error(f"Calculation error: {e}")
            total_time = 0.0  # Fallback value
        
        # Generate comprehensive final report
        await tracer.markdown("### ✅ Analysis Complete! Report ready for viewing.")
        
        # Generate final report content
        stats = processing_result.get('stats', {})
        processed_docs = stats.get('processed', 0)
        total_entities = stats.get('total_entities', 0)
        total_relationships = stats.get('total_relationships', 0)
        communities_count = communities_result.get('community_count', 0)
        success_rate = stats.get('success_rate', 0)
        
        # Extract top entities and date info from processing results
        top_entities = []
        document_dates = []
        for result in processing_result.get('results', []):
            if result.get('status') == 'success':
                # Collect entity information
                if result.get('entities'):
                    for entity in result.get('entities', [])[:3]:  # Top 3 per document
                        entity_name = getattr(entity, 'name', 'Unknown')
                        entity_type = entity.labels[0] if hasattr(entity, 'labels') and entity.labels else 'Unknown'
                        top_entities.append({'name': entity_name, 'type': entity_type})
                
                # Collect document date information
                if result.get('document_date'):
                    document_dates.append(result['document_date'])
        
        # Remove duplicates and limit to top 10
        seen_entities = set()
        unique_entities = []
        for entity in top_entities:
            entity_key = (entity['name'], entity['type'])
            if entity_key not in seen_entities:
                seen_entities.add(entity_key)
                unique_entities.append(entity)
                if len(unique_entities) >= 10:
                    break
        
        # Calculate date range
        docs_with_dates = len(document_dates)
        earliest_date = min(document_dates) if document_dates else None
        latest_date = max(document_dates) if document_dates else None
        
        # Create execution summary
        execution_summary = f"""# 📄 {job_name} - Final Report

**Execution Summary:**
- **⏱️ Total Time:** {total_time:.2f} seconds
- **📁 Documents Processed:** {processed_docs}
- **✅ Success Rate:** {success_rate:.1f}%
- **🧠 Entities Extracted:** {total_entities}
- **🔗 Relationships Created:** {total_relationships}
- **🏘️ Communities:** Use `just build-communities` to create

---

"""
        
        # Create detailed report content
        report_content = f"""## 🔍 Processing Details

### Document Processing Results
- **Total Documents:** {stats.get('total_documents', 0)}
- **Successfully Processed:** {processed_docs}
- **Skipped:** {stats.get('skipped', 0)}
- **Failed:** {stats.get('failed', 0)}
- **Average Entities per Document:** {stats.get('avg_entities_per_doc', 0):.1f}

### Knowledge Graph Growth
- **Total Entities Created:** {total_entities}
- **Total Relationships Created:** {total_relationships}
- **Entity Types:** Policy, Company, GovernmentAgency, Politician, Regulation, LobbyGroup, LegalFramework
- **Processing Time:** {stats.get('total_processing_time', 0):.2f}s

### Key Entities Discovered
{chr(10).join([f"- **{entity['name']}** ({entity['type']})" for entity in unique_entities[:8]]) if unique_entities else "- No entities extracted"}

### Relationship Types Found
{chr(10).join([f"- **{rel_type}**: {count} relationships" for rel_type, count in list(relationship_distribution.items())[:5]]) if relationship_distribution else "- No relationships analyzed"}

### Document Timeline
- **Documents with dates**: {docs_with_dates}/{processed_docs}
- **Date range**: {f"{earliest_date} to {latest_date}" if earliest_date and latest_date else "No dates extracted"}

### Community Detection
- **Status:** ⏸️ Manual (run `just build-communities`)
- **Algorithm:** Graphiti temporal community detection
- **Trigger:** Use command when you have sufficient documents

---

## 🎯 Next Steps

### 1. Explore the Knowledge Graph
Access your temporal knowledge graph:
- **Neo4j Browser:** [http://localhost:7474](http://localhost:7474)
- **Username:** `neo4j`
- **Password:** `password123`

### 2. Query Examples
Try these Cypher queries in Neo4j Browser:

```cypher
// View all political entities
MATCH (n) WHERE NOT n:Community AND NOT n:Episode
RETURN labels(n)[0] as Type, count(n) as Count
ORDER BY Count DESC

// View communities and their members
MATCH (c:Community)<-[:MEMBER_OF]-(n)
RETURN c.title as Community, count(n) as Members

// Find policy relationships
MATCH (p:Policy)-[r]->(o)
RETURN p.policy_name, type(r), labels(o)[0], o.name
LIMIT 10
```

### 3. Build Communities (Optional)
Run community detection when you have sufficient documents:
```bash
just build-communities
```

### 4. Continue Analysis
- **Flow 2:** Company Context Analysis (coming soon)
- **Flow 3:** Relevance Assessment (coming soon)

---

## 📊 Technical Details

**Data Ingestion Pipeline v0.2.0**
- **Engine:** Graphiti Temporal Knowledge Graph
- **LLM:** OpenAI GPT-4o-mini with custom political entity types
- **Entity Extraction:** Advanced political schema with 7 entity types
- **Community Detection:** Graph-based clustering algorithms
- **Retry Logic:** 3-attempt strategy for LLM reliability

**Episode IDs:**"""

        # Add episode details if available
        if processing_result.get('results'):
            for result in processing_result['results']:
                if result.get('status') == 'success':
                    episode_id = result.get('episode_id', 'N/A')
                    path = result.get('path', 'Unknown')
                    entities = result.get('entity_count', 0)
                    relationships = result.get('relationship_count', 0)
                    doc_date = result.get('document_date', 'No date')
                    content_preview = result.get('content_preview', '')[:150] + "..." if result.get('content_preview') else 'No preview'
                    
                    report_content += f"""
- **{Path(path).name}:** `{episode_id}` ({entities} entities, {relationships} relationships)
  - **Date**: {doc_date}
  - **Preview**: {content_preview}"""

        report_content += f"""

---

🎉 **Data ingestion pipeline completed successfully!**

*Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*
"""

        # Return the complete report as a Kodosumi Markdown response for proper FINAL display
        return core.response.Markdown(execution_summary + report_content)
        
    except Exception as e:
        error_msg = f"Ingestion flow failed: {e}"
        logger.error(error_msg)
        
        await tracer.markdown(f"""
# ❌ Data Ingestion Flow Failed

**Error:** {error_msg}

Please check the logs for more details and try again.
""")
        
        # Return error as Markdown response for proper display
        error_report = f"""# ❌ Data Ingestion Flow Failed

**Error Details:**
```
{error_msg}
```

**Troubleshooting Steps:**
1. Check that Neo4j is running: `docker ps | grep neo4j`
2. Verify environment variables in `.env` file
3. Check document paths exist and contain supported files (.txt, .md)
4. Review logs for detailed error information

**Need Help?**
- Check the logs for more detailed error information
- Verify your configuration meets the requirements
- Try with a smaller document limit first

*Failed on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*
"""
        
        return core.response.Markdown(error_report)