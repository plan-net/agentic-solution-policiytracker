#!/usr/bin/env python3
"""
Test Approach A: Graphiti Custom Entity Types - FIXED VERSION

This script tests the implementation of custom entity types with the upgraded Graphiti v0.12.0rc1.
We now have access to the entity_types parameter in add_episode().
"""

import asyncio
import os
import logging
from datetime import datetime, UTC
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_approach_a_fixed():
    """Test Approach A implementation with the correct Graphiti version."""
    
    try:
        from src.graphrag.political_document_processor import (
            PoliticalDocumentProcessor,
            GraphitiConfig
        )
        from src.llm.base_client import BaseLLMClient
        
        # Simple mock LLM client since Graphiti handles extraction in Approach A
        class MockLLMClient(BaseLLMClient):
            def __init__(self):
                super().__init__(provider="mock")
                
            async def generate_response(self, prompt: str, **kwargs) -> str:
                return '{"entities": [], "relationships": [], "metadata": {"extraction_confidence": 0.8}}'
            
            async def analyze_document(self, content: str, **kwargs) -> dict:
                return {"summary": "Mock analysis", "confidence": 0.8}
            
            async def analyze_topics(self, content: str, **kwargs) -> dict:
                return {"topics": ["mock_topic"], "confidence": 0.8}
            
            async def complete(self, prompt: str, **kwargs) -> str:
                return "Mock completion"
            
            async def generate_report_insights(self, content: str, **kwargs) -> dict:
                return {"insights": ["Mock insight"], "confidence": 0.8}
            
            async def score_dimension(self, content: str, dimension: str, **kwargs) -> float:
                return 0.8
        
        # Configuration
        config = GraphitiConfig(
            neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.getenv("NEO4J_USERNAME", "neo4j"),
            neo4j_password=os.getenv("NEO4J_PASSWORD", "password123"),
            group_id="test_custom_entities"
        )
        
        # Test document path
        test_doc = Path("data/input/examples/apple_ai_act_compliance_response_2024.md")
        
        if not test_doc.exists():
            logger.error(f"Test document not found: {test_doc}")
            return False
            
        logger.info("🚀 Starting Approach A test with custom entity types...")
        
        # Initialize processor
        llm_client = MockLLMClient()
        
        async with PoliticalDocumentProcessor(llm_client, config) as processor:
            logger.info("✅ Processor initialized successfully")
            
            # Process test document 
            result = await processor.process_document(test_doc)
            
            if result.success:
                logger.info(f"✅ Document processed successfully!")
                logger.info(f"   Episode ID: {result.episode_id}")
                logger.info(f"   Entities extracted: {result.entities_extracted}")
                logger.info(f"   Relationships extracted: {result.relationships_extracted}")
                logger.info(f"   Processing time: {result.processing_time_seconds:.2f}s")
                
                # Verify in Neo4j that we have proper entity types
                await verify_custom_entity_types(processor, config.group_id)
                
                return True
            else:
                logger.error(f"❌ Document processing failed: {result.error_message}")
                return False
                
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

async def verify_custom_entity_types(processor, group_id: str):
    """Verify that custom entity types were created in Neo4j."""
    try:
        if not processor.graphiti_client:
            logger.warning("No Graphiti client available for verification")
            return
            
        # Search for recently added entities using search method
        search_results = await processor.graphiti_client.search(
            query="Apple AI Act compliance",
            group_ids=[group_id],
            num_results=20
        )
        
        logger.info(f"🔍 Found {len(search_results)} edges in the graph")
        
        # For search results, we get EntityEdge objects
        # Let's get the source and target nodes to check entity types
        entity_names = set()
        for edge in search_results[:10]:
            if hasattr(edge, 'source_node_name'):
                entity_names.add(f"Source: {edge.source_node_name}")
            if hasattr(edge, 'target_node_name'):
                entity_names.add(f"Target: {edge.target_node_name}")
            if hasattr(edge, 'fact'):
                logger.info(f"   Relationship: {edge.fact}")
                
        logger.info(f"🏷️  Sample entities found: {list(entity_names)[:10]}")
        
        # Try to search for nodes specifically to see entity types
        try:
            from graphiti_core.nodes import EntityNode
            
            # Let's query Neo4j directly to see the entity types
            query = """
            MATCH (n:Entity) 
            WHERE n.group_id = $group_id 
            RETURN DISTINCT labels(n) as labels, n.name as name 
            LIMIT 20
            """
            
            records, _, _ = await processor.graphiti_client.driver.execute_query(
                query, group_id=group_id, database_="neo4j"
            )
            
            entity_types = set()
            sample_entities = []
            for record in records:
                labels = record["labels"]
                name = record["name"]
                entity_types.update(labels)
                sample_entities.append(f"{name} ({', '.join(labels)})")
                
            logger.info(f"🏷️  Entity types found: {sorted(entity_types)}")
            
            # Check if we have our custom political entity types
            expected_types = {"Policy", "Company", "Politician", "GovernmentAgency", "Regulation", "LobbyGroup", "LegalFramework"}
            found_political_types = entity_types & expected_types
            
            if found_political_types:
                logger.info(f"✅ SUCCESS: Found custom political entity types: {sorted(found_political_types)}")
            else:
                logger.warning("⚠️  No custom political entity types found - entities may be using generic types")
                
            # Show some example entities
            for i, entity in enumerate(sample_entities[:5]):
                logger.info(f"   Entity {i+1}: {entity}")
                
        except Exception as e:
            logger.warning(f"Could not query entity types directly: {e}")
            
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_approach_a_fixed())