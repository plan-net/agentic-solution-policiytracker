"""Predefined schema queries for political monitoring knowledge graph."""


from .models import SchemaQuery

# Predefined schema queries for exploration
SCHEMA_QUERIES: dict[str, SchemaQuery] = {
    "policy_landscape": SchemaQuery(
        name="Policy Landscape",
        description="Overview of policy entities and their relationships in the knowledge graph",
        cypher="""
            MATCH (p)-[r]-(e)
            RETURN p, r, e
            LIMIT 50
        """,
        category="policy",
    ),
    "organization_network": SchemaQuery(
        name="Organization Network",
        description="Network of organizations and how they relate to each other",
        cypher="""
            MATCH (o:Entity)-[r]-(t:Entity)
            WHERE (o.name CONTAINS 'Inc' OR o.name CONTAINS 'Corp' OR o.name CONTAINS 'Ltd'
                   OR o.name CONTAINS 'AG' OR o.name CONTAINS 'GmbH')
            RETURN o, r, t
            LIMIT 50
        """,
        category="organization",
    ),
    "recent_relationships": SchemaQuery(
        name="Recent Relationships",
        description="Most recently created relationships in the knowledge graph",
        cypher="""
            MATCH (a:Entity)-[r]-(b:Entity)
            WHERE r.created_at IS NOT NULL
            RETURN a, r, b
            ORDER BY r.created_at DESC
            LIMIT 50
        """,
        category="temporal",
    ),
    "high_degree_entities": SchemaQuery(
        name="Most Connected Entities",
        description="Entities with the highest number of relationships (central nodes)",
        cypher="""
            MATCH (e:Entity)-[r]-()
            WITH e, count(r) as degree
            WHERE degree > 3
            ORDER BY degree DESC
            LIMIT 20
            MATCH (e)-[r]-(n:Entity)
            RETURN e, r, n
            LIMIT 100
        """,
        category="network",
    ),
    "policy_clusters": SchemaQuery(
        name="Major Policy Clusters",
        description="Key policy entities (GDPR, DSA, AI Act) and their relationship networks",
        cypher="""
            MATCH (p:Entity)-[r]-(e:Entity)
            WHERE p.name CONTAINS 'GDPR' OR p.name CONTAINS 'DSA'
                  OR p.name CONTAINS 'AI Act' OR p.name CONTAINS 'DMA'
            RETURN p, r, e
            LIMIT 100
        """,
        category="policy",
    ),
    "company_impact": SchemaQuery(
        name="Company Impact Network",
        description="How major companies (Meta, Google, Amazon, Apple) are affected by policies",
        cypher="""
            MATCH (c:Entity)-[r]-(p:Entity)
            WHERE (c.name CONTAINS 'Meta' OR c.name CONTAINS 'Google'
                   OR c.name CONTAINS 'Amazon' OR c.name CONTAINS 'Apple')
            RETURN c, r, p
            LIMIT 100
        """,
        category="organization",
    ),
    "influence_network": SchemaQuery(
        name="Influence Network",
        description="Entities connected by influence and affects relationships",
        cypher="""
            MATCH (a:Entity)-[r]-(b:Entity)
            WHERE type(r) CONTAINS 'AFFECT' OR type(r) CONTAINS 'INFLUENC'
            RETURN a, r, b
            LIMIT 75
        """,
        category="network",
    ),
    "entity_timeline": SchemaQuery(
        name="Temporal Entity Evolution",
        description="Entities and relationships created over time",
        cypher="""
            MATCH (e:Entity)
            WHERE e.created_at IS NOT NULL
            WITH e
            ORDER BY e.created_at DESC
            LIMIT 30
            MATCH (e)-[r]-(n:Entity)
            RETURN e, r, n
            LIMIT 100
        """,
        category="temporal",
    ),
    "community_detection": SchemaQuery(
        name="Dense Subgraphs",
        description="Identify densely connected communities in the graph",
        cypher="""
            MATCH (e:Entity)-[r1]-(n1:Entity)-[r2]-(n2:Entity)-[r3]-(e)
            WHERE id(e) < id(n1) AND id(n1) < id(n2)
            RETURN e, r1, n1, r2, n2, r3
            LIMIT 50
        """,
        category="network",
    ),
    "full_graph_sample": SchemaQuery(
        name="Full Graph Sample",
        description="Random sample of the entire knowledge graph structure",
        cypher="""
            MATCH (n:Entity)-[r]-(m:Entity)
            RETURN n, r, m
            LIMIT 100
        """,
        category="general",
    ),
}


def get_schema_query(query_name: str) -> SchemaQuery:
    """Get a schema query by name or display name."""
    # Try direct lookup first (by key)
    if query_name in SCHEMA_QUERIES:
        return SCHEMA_QUERIES[query_name]

    # Try by display name
    for query in SCHEMA_QUERIES.values():
        if query.name == query_name:
            return query

    return None


def list_schema_queries() -> list[SchemaQuery]:
    """List all available schema queries."""
    return list(SCHEMA_QUERIES.values())


def get_queries_by_category(category: str) -> list[SchemaQuery]:
    """Get all queries in a specific category."""
    return [q for q in SCHEMA_QUERIES.values() if q.category == category]


def get_categories() -> list[str]:
    """Get all unique query categories."""
    return list(set(q.category for q in SCHEMA_QUERIES.values()))
