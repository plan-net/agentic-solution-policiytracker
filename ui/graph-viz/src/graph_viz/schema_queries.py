"""Predefined schema queries for graph exploration."""

from src.graph_viz.models import SchemaQuery

# 10 predefined queries for political monitoring knowledge graph exploration
SCHEMA_QUERIES = {
    "policy_landscape": SchemaQuery(
        name="Policy Landscape",
        description="Overview of all policy-related entities and their relationships",
        category="policy",
        cypher="""
            MATCH (p:Entity)-[r]-(e:Entity)
            WHERE p.name CONTAINS 'Act' OR p.name CONTAINS 'Regulation' OR p.name CONTAINS 'Directive'
            RETURN p, r, e LIMIT 50
        """,
    ),
    "organization_network": SchemaQuery(
        name="Organization Network",
        description="Network of organizations and their relationships",
        category="organization",
        cypher="""
            MATCH (o:Entity)-[r]-(e:Entity)
            WHERE o.name CONTAINS 'Company' OR o.name CONTAINS 'Organization' OR o.name CONTAINS 'Corp'
            RETURN o, r, e LIMIT 50
        """,
    ),
    "recent_relationships": SchemaQuery(
        name="Recent Relationships",
        description="Recently created relationships (last 30 days)",
        category="temporal",
        cypher="""
            MATCH (n:Entity)-[r]-(m:Entity)
            WHERE r.created_at > datetime() - duration('P30D')
            RETURN n, r, m 
            ORDER BY r.created_at DESC 
            LIMIT 50
        """,
    ),
    "high_degree_entities": SchemaQuery(
        name="Most Connected Entities",
        description="Entities with the highest number of connections (degree > 3)",
        category="network",
        cypher="""
            MATCH (e:Entity)-[r]-()
            WITH e, count(r) as degree
            WHERE degree > 3
            ORDER BY degree DESC LIMIT 20
            MATCH (e)-[r]-(n:Entity)
            RETURN e, r, n LIMIT 100
        """,
    ),
    "major_policy_clusters": SchemaQuery(
        name="Major Policy Clusters",
        description="Key policy areas like GDPR, DSA, AI Act and their networks",
        category="policy",
        cypher="""
            MATCH (p:Entity)-[r*1..2]-(e:Entity)
            WHERE p.name IN ['GDPR', 'Digital Services Act', 'AI Act', 'DMA', 'Data Act']
            RETURN p, r, e LIMIT 100
        """,
    ),
    "company_impact": SchemaQuery(
        name="Company Impact Analysis",
        description="Analysis of major tech companies (Meta, Google, Amazon, Apple) and policy impact",
        category="organization",
        cypher="""
            MATCH (c:Entity)-[r]-(p:Entity)
            WHERE c.name IN ['Meta', 'Google', 'Amazon', 'Apple', 'Microsoft']
              AND (p.name CONTAINS 'Act' OR p.name CONTAINS 'Regulation')
            RETURN c, r, p LIMIT 50
        """,
    ),
    "influence_network": SchemaQuery(
        name="Influence Network",
        description="Network of AFFECTS and INFLUENCES relationships",
        category="network",
        cypher="""
            MATCH (n:Entity)-[r]-(m:Entity)
            WHERE type(r) IN ['AFFECTS', 'INFLUENCES', 'IMPACTS']
            RETURN n, r, m LIMIT 50
        """,
    ),
    "temporal_evolution": SchemaQuery(
        name="Temporal Evolution",
        description="How entities and relationships evolve over time",
        category="temporal",
        cypher="""
            MATCH (n:Entity)-[r]-(m:Entity)
            WHERE r.valid_from IS NOT NULL
            RETURN n, r, m
            ORDER BY r.valid_from DESC
            LIMIT 50
        """,
    ),
    "dense_subgraphs": SchemaQuery(
        name="Dense Subgraphs",
        description="Find densely connected communities of entities",
        category="network",
        cypher="""
            MATCH (n:Entity)-[r]-(m:Entity)
            WITH n, count(DISTINCT m) as neighbors
            WHERE neighbors >= 5
            MATCH (n)-[r]-(connected:Entity)
            RETURN n, r, connected LIMIT 100
        """,
    ),
    "full_graph_sample": SchemaQuery(
        name="Full Graph Sample",
        description="Random sample of the entire graph (100 nodes)",
        category="network",
        cypher="""
            MATCH (n:Entity)-[r]-(m:Entity)
            RETURN n, r, m
            ORDER BY rand()
            LIMIT 100
        """,
    ),
}


def get_all_queries() -> list[SchemaQuery]:
    """Get list of all predefined schema queries."""
    return list(SCHEMA_QUERIES.values())


def get_query_by_name(name: str) -> SchemaQuery | None:
    """Get a specific schema query by name."""
    return SCHEMA_QUERIES.get(name)


def get_queries_by_category(category: str) -> list[SchemaQuery]:
    """Get all queries in a specific category."""
    return [q for q in SCHEMA_QUERIES.values() if q.category == category]
