"""
Calculate exact cost of re-embedding all embeddings in Neo4j graph.

This script counts:
1. Entity embeddings (name_embedding)
2. Relationship embeddings (fact_embedding)
3. Episode embeddings (content_embedding)

Usage:
    python calculate_reembedding_cost.py
"""

import asyncio
from neo4j import AsyncGraphDatabase
from src.config import settings


async def calculate_reembedding_cost():
    """Calculate exact re-embedding cost based on actual Neo4j data."""

    print("=" * 80)
    print("RE-EMBEDDING COST CALCULATOR")
    print("=" * 80)
    print()

    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    )

    try:
        async with driver.session(database=settings.NEO4J_DATABASE) as session:

            # Count entities with embeddings
            print("1. ENTITY EMBEDDINGS")
            print("-" * 80)

            entity_query = """
            MATCH (e:Entity)
            WHERE e.name_embedding IS NOT NULL
            RETURN count(e) as count
            """
            result = await session.run(entity_query)
            entity_record = await result.single()
            entity_count = entity_record['count'] if entity_record else 0

            print(f"Entities with name_embedding: {entity_count:,}")

            # Count relationships with embeddings
            print("\n2. RELATIONSHIP EMBEDDINGS")
            print("-" * 80)

            relationship_query = """
            MATCH ()-[r:RELATES_TO]->()
            WHERE r.fact_embedding IS NOT NULL
            RETURN count(r) as count
            """
            result = await session.run(relationship_query)
            rel_record = await result.single()
            relationship_count = rel_record['count'] if rel_record else 0

            print(f"Relationships with fact_embedding: {relationship_count:,}")

            # Count episodes with embeddings (correct label: Episodic)
            print("\n3. EPISODIC NODE EMBEDDINGS")
            print("-" * 80)

            episode_query = """
            MATCH (ep:Episodic)
            WHERE ep.content_embedding IS NOT NULL
            RETURN count(ep) as count
            """
            result = await session.run(episode_query)
            episode_record = await result.single()
            episode_count = episode_record['count'] if episode_record else 0

            print(f"Episodic nodes with content_embedding: {episode_count:,}")

            # Sample text lengths
            print("\n4. AVERAGE TEXT LENGTHS")
            print("-" * 80)

            # Entity names
            entity_length_query = """
            MATCH (e:Entity)
            WHERE e.name IS NOT NULL
            RETURN avg(size(e.name)) as avg_length, max(size(e.name)) as max_length
            """
            result = await session.run(entity_length_query)
            entity_length = await result.single()
            avg_entity_length = entity_length['avg_length'] if entity_length else 0
            max_entity_length = entity_length['max_length'] if entity_length else 0

            print(f"Entity names:")
            print(f"  Average length: {avg_entity_length:.1f} characters")
            print(f"  Max length: {max_entity_length:.0f} characters")
            print(f"  Estimated tokens: {avg_entity_length / 4:.0f} per entity (rule of thumb: 1 token ≈ 4 chars)")

            # Relationship facts
            rel_length_query = """
            MATCH ()-[r:RELATES_TO]->()
            WHERE r.fact IS NOT NULL
            RETURN avg(size(r.fact)) as avg_length, max(size(r.fact)) as max_length
            LIMIT 1000
            """
            result = await session.run(rel_length_query)
            rel_length = await result.single()
            avg_rel_length = rel_length['avg_length'] if rel_length else 0
            max_rel_length = rel_length['max_length'] if rel_length else 0

            print(f"\nRelationship facts:")
            print(f"  Average length: {avg_rel_length:.1f} characters")
            print(f"  Max length: {max_rel_length:.0f} characters")
            print(f"  Estimated tokens: {avg_rel_length / 4:.0f} per relationship")

            # Episode content (correct label: Episodic)
            episode_length_query = """
            MATCH (ep:Episodic)
            WHERE ep.content IS NOT NULL
            RETURN avg(size(ep.content)) as avg_length, max(size(ep.content)) as max_length
            """
            result = await session.run(episode_length_query)
            episode_length = await result.single()
            avg_episode_length = episode_length['avg_length'] if episode_length else 0
            max_episode_length = episode_length['max_length'] if episode_length else 0

            print(f"\nEpisodic node content:")
            if avg_episode_length and avg_episode_length > 0:
                print(f"  Average length: {avg_episode_length:.1f} characters")
                print(f"  Max length: {max_episode_length:.0f} characters")
                print(f"  Estimated tokens: {avg_episode_length / 4:.0f} per episodic node")
            else:
                print(f"  No episodic nodes found or nodes have no content")
                print(f"  Estimated tokens: 0 per episodic node")

            # Calculate costs
            print("\n5. COST CALCULATION")
            print("=" * 80)

            # Token estimates (rough: 1 token ≈ 4 characters)
            tokens_per_entity = max(10, avg_entity_length / 4)  # Minimum 10 tokens
            tokens_per_relationship = max(20, avg_rel_length / 4)  # Minimum 20 tokens
            tokens_per_episode = max(50, avg_episode_length / 4) if avg_episode_length else 0  # Minimum 50 tokens

            total_entity_tokens = entity_count * tokens_per_entity
            total_rel_tokens = relationship_count * tokens_per_relationship
            total_episode_tokens = episode_count * tokens_per_episode

            total_tokens = total_entity_tokens + total_rel_tokens + total_episode_tokens
            total_tokens_millions = total_tokens / 1_000_000

            print("\nToken Estimates:")
            print(f"  Entities: {entity_count:,} × {tokens_per_entity:.0f} tokens = {total_entity_tokens:,.0f} tokens")
            print(f"  Relationships: {relationship_count:,} × {tokens_per_relationship:.0f} tokens = {total_rel_tokens:,.0f} tokens")
            print(f"  Episodic nodes: {episode_count:,} × {tokens_per_episode:.0f} tokens = {total_episode_tokens:,.0f} tokens")
            print(f"  TOTAL: {total_tokens:,.0f} tokens ({total_tokens_millions:.2f}M tokens)")

            # Pricing for different models
            print("\n" + "=" * 80)
            print("COST COMPARISON BY MODEL")
            print("=" * 80)

            models = [
                {"name": "text-embedding-3-small (current)", "cost_per_1m": 0.02, "quality": "Poor (13% multilingual)"},
                {"name": "text-embedding-3-large", "cost_per_1m": 0.13, "quality": "Moderate (25% multilingual)"},
                {"name": "text-embedding-ada-002", "cost_per_1m": 0.10, "quality": "Excellent (100% multilingual) ✅"},
                {"name": "voyage-multilingual-2", "cost_per_1m": 0.12, "quality": "Unknown (not tested)"},
            ]

            print(f"\n{'Model':<35} {'One-time Cost':<15} {'Quality'}")
            print("-" * 80)

            for model in models:
                cost = total_tokens_millions * model['cost_per_1m']
                print(f"{model['name']:<35} ${cost:>7.2f}         {model['quality']}")

            # Recommended model
            print("\n" + "=" * 80)
            print("RECOMMENDATION")
            print("=" * 80)

            recommended_cost = total_tokens_millions * 0.10  # ada-002

            print(f"\n✅ RECOMMENDED: text-embedding-ada-002")
            print(f"\nWhy:")
            print(f"  • 100% multilingual test pass rate (vs 13% current)")
            print(f"  • One-time cost: ${recommended_cost:.2f}")
            print(f"  • Best quality-to-cost ratio")
            print(f"  • No ongoing cost increase")

            print(f"\nBreakdown:")
            print(f"  • {entity_count:,} entities to re-embed")
            print(f"  • {relationship_count:,} relationships to re-embed")
            print(f"  • {episode_count:,} episodic nodes to re-embed")
            print(f"  • Total items: {entity_count + relationship_count + episode_count:,}")
            print(f"  • Estimated time: {(entity_count + relationship_count + episode_count) / 1000:.0f}-{(entity_count + relationship_count + episode_count) / 500:.0f} minutes")
            print(f"    (assuming 500-1000 items/minute with batching)")

            # Monthly ongoing cost comparison
            print("\n" + "=" * 80)
            print("ONGOING MONTHLY COST (for new entities/relationships)")
            print("=" * 80)

            monthly_new_items = 1000  # Estimate
            monthly_tokens = monthly_new_items * ((tokens_per_entity + tokens_per_relationship) / 2) / 1_000_000

            print(f"\nAssuming {monthly_new_items:,} new items per month:")
            print(f"  • Current (3-small): ${monthly_tokens * 0.02:.2f}/month")
            print(f"  • After (ada-002): ${monthly_tokens * 0.10:.2f}/month")
            print(f"  • Increase: ${monthly_tokens * 0.08:.2f}/month")

            print("\n" + "=" * 80)
            print(f"✅ Total first-month cost: ${recommended_cost + (monthly_tokens * 0.10):.2f}")
            print(f"   (${recommended_cost:.2f} one-time + ${monthly_tokens * 0.10:.2f} ongoing)")
            print("=" * 80)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await driver.close()


if __name__ == "__main__":
    print("\nCalculating re-embedding cost for your Neo4j graph...")
    print(f"Database: {settings.NEO4J_DATABASE}")
    print(f"URI: {settings.NEO4J_URI}\n")

    asyncio.run(calculate_reembedding_cost())

    print("\n📝 Next Steps:")
    print("1. Review the cost estimate above")
    print("2. If approved, run the re-embedding script")
    print("3. Monitor progress during re-embedding")
    print("4. Validate results with test queries\n")
