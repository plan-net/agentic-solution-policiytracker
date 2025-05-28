#!/usr/bin/env python3
"""
Quick verification script to check if custom entity types are working in Neo4j.
"""

import asyncio
import os
from neo4j import AsyncGraphDatabase

async def verify_entity_types():
    """Check what entity types were created in the Neo4j graph."""
    
    # Connection details
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password123")
    
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    
    try:
        # Query to get all entity types and sample entities
        query = """
        MATCH (n:Entity) 
        WHERE n.group_id = 'test_custom_entities'
        RETURN DISTINCT labels(n) as labels, n.name as name 
        ORDER BY labels[0], n.name
        LIMIT 30
        """
        
        records, _, _ = await driver.execute_query(query)
        
        print("🔍 Entity Types and Examples Found:")
        print("=" * 50)
        
        entity_types = set()
        type_examples = {}
        
        for record in records:
            labels = record["labels"]
            name = record["name"]
            
            # Add to entity types set
            for label in labels:
                entity_types.add(label)
                
                # Track examples for each type
                if label not in type_examples:
                    type_examples[label] = []
                if len(type_examples[label]) < 3:  # Limit examples per type
                    type_examples[label].append(name)
        
        print(f"📊 Total Entity Types Found: {len(entity_types)}")
        print(f"📈 Entity Types: {sorted(entity_types)}")
        print()
        
        # Check if we have our custom political entity types
        expected_types = {"Policy", "Company", "Politician", "GovernmentAgency", "Regulation", "LobbyGroup", "LegalFramework"}
        found_political_types = entity_types & expected_types
        
        if found_political_types:
            print(f"✅ SUCCESS: Found custom political entity types!")
            print(f"   Political types: {sorted(found_political_types)}")
        else:
            print("⚠️  No custom political entity types found")
            print("   This might indicate entities are using generic 'Entity' labels")
        
        print()
        print("📝 Sample Entities by Type:")
        print("-" * 30)
        
        for entity_type in sorted(entity_types):
            examples = type_examples.get(entity_type, [])
            examples_str = ", ".join(examples[:3])
            if len(type_examples.get(entity_type, [])) > 3:
                examples_str += "..."
            print(f"  {entity_type}: {examples_str}")
        
        # Also check relationship types
        rel_query = """
        MATCH ()-[r:RELATES_TO]->()
        WHERE r.group_id = 'test_custom_entities'
        RETURN DISTINCT r.name as relationship_type
        ORDER BY r.name
        LIMIT 20
        """
        
        rel_records, _, _ = await driver.execute_query(rel_query)
        
        print()
        print("🔗 Relationship Types Found:")
        print("-" * 25)
        
        for record in rel_records:
            rel_type = record["relationship_type"]
            print(f"  • {rel_type}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        await driver.close()

if __name__ == "__main__":
    asyncio.run(verify_entity_types())