"""Business-focused schema queries for political monitoring knowledge graph.

Queries are designed for Zalando's regulatory monitoring needs as an EU e-commerce platform:
- Platform and marketplace regulation (DSA, DMA, P2B)
- Consumer protection (BNPL, returns, pricing)
- Data protection (GDPR, transfers, profiling)
- Product safety (marketplace liability, CE marking)
- AI/Algorithm regulation (recommendations, automated decisions)
"""

from .models import QueryParameter, SchemaQuery

# =============================================================================
# CATEGORY 1: POLICY ANALYSIS
# =============================================================================

POLICY_QUERIES: dict[str, SchemaQuery] = {
    "platform_regulation": SchemaQuery(
        name="Platform Regulation Landscape",
        description="Track DSA, DMA, and P2B regulations affecting online marketplaces and platforms",
        cypher="""
            MATCH (p:Entity)-[r]-(e:Entity)
            WHERE p.name =~ '(?i).*(DSA|Digital Services Act|DMA|Digital Markets Act|P2B|Platform.to.Business|online platform|marketplace regulation).*'
               OR e.name =~ '(?i).*(DSA|Digital Services Act|DMA|Digital Markets Act|P2B|Platform.to.Business|online platform|marketplace regulation).*'
            RETURN p, r, e
            LIMIT $limit
        """,
        category="policy",
        parameters=[
            QueryParameter(
                name="limit",
                param_type="integer",
                default=50,
                description="Maximum results",
                min_value=10,
                max_value=200,
            )
        ],
    ),
    "consumer_protection": SchemaQuery(
        name="Consumer Protection Regulations",
        description="B2C consumer rights: BNPL, returns, refunds, pricing transparency, dark patterns, geoblocking",
        cypher="""
            MATCH (p:Entity)-[r]-(e:Entity)
            WHERE p.name =~ '(?i).*(consumer protection|consumer rights|BNPL|buy.now.pay.later|consumer credit|returns|refund|pricing|dark pattern|geoblocking|distance selling|unfair commercial).*'
               OR e.name =~ '(?i).*(consumer protection|consumer rights|BNPL|buy.now.pay.later|consumer credit|returns|refund|pricing|dark pattern|geoblocking|distance selling|unfair commercial).*'
            RETURN p, r, e
            LIMIT $limit
        """,
        category="policy",
        parameters=[
            QueryParameter(
                name="limit",
                param_type="integer",
                default=50,
                description="Maximum results",
                min_value=10,
                max_value=200,
            )
        ],
    ),
    "data_protection": SchemaQuery(
        name="Data Protection & Privacy",
        description="GDPR, data transfers, marketing consent, profiling, and privacy regulations",
        cypher="""
            MATCH (p:Entity)-[r]-(e:Entity)
            WHERE p.name =~ '(?i).*(GDPR|data protection|privacy|consent|profiling|data transfer|Schrems|marketing|personal data|DPA|EDPB).*'
               OR e.name =~ '(?i).*(GDPR|data protection|privacy|consent|profiling|data transfer|Schrems|marketing|personal data|DPA|EDPB).*'
            RETURN p, r, e
            LIMIT $limit
        """,
        category="policy",
        parameters=[
            QueryParameter(
                name="limit",
                param_type="integer",
                default=50,
                description="Maximum results",
                min_value=10,
                max_value=200,
            )
        ],
    ),
    "product_safety": SchemaQuery(
        name="Product Safety & Market Surveillance",
        description="Marketplace liability for unsafe products, CE marking, imports, recalls",
        cypher="""
            MATCH (p:Entity)-[r]-(e:Entity)
            WHERE p.name =~ '(?i).*(product safety|market surveillance|CE marking|unsafe product|recall|import control|customs|conformity|GPSR|product liability).*'
               OR e.name =~ '(?i).*(product safety|market surveillance|CE marking|unsafe product|recall|import control|customs|conformity|GPSR|product liability).*'
            RETURN p, r, e
            LIMIT $limit
        """,
        category="policy",
        parameters=[
            QueryParameter(
                name="limit",
                param_type="integer",
                default=50,
                description="Maximum results",
                min_value=10,
                max_value=200,
            )
        ],
    ),
    "ai_algorithm_regulation": SchemaQuery(
        name="AI & Algorithm Regulation",
        description="AI Act, recommendation algorithms, automated decision-making, algorithmic fairness",
        cypher="""
            MATCH (p:Entity)-[r]-(e:Entity)
            WHERE p.name =~ '(?i).*(AI Act|artificial intelligence|algorithm|automated decision|recommendation system|machine learning|algorithmic|transparency).*'
               OR e.name =~ '(?i).*(AI Act|artificial intelligence|algorithm|automated decision|recommendation system|machine learning|algorithmic|transparency).*'
            RETURN p, r, e
            LIMIT $limit
        """,
        category="policy",
        parameters=[
            QueryParameter(
                name="limit",
                param_type="integer",
                default=50,
                description="Maximum results",
                min_value=10,
                max_value=200,
            )
        ],
    ),
}

# =============================================================================
# CATEGORY 2: ORGANIZATIONS
# =============================================================================

ORGANIZATION_QUERIES: dict[str, SchemaQuery] = {
    "ecommerce_competitors": SchemaQuery(
        name="E-commerce Platform Competitors",
        description="Track similar platforms for regulatory precedents and competitive intelligence",
        cypher="""
            MATCH (c:Entity)-[r]-(p:Entity)
            WHERE c.name =~ '(?i).*(Amazon|eBay|AliExpress|Shein|Temu|Otto|AboutYou|ASOS|Wish|Alibaba|JD\\.com|Rakuten|Etsy|Wayfair).*'
            RETURN c, r, p
            LIMIT $limit
        """,
        category="organization",
        parameters=[
            QueryParameter(
                name="limit",
                param_type="integer",
                default=50,
                description="Maximum results",
                min_value=10,
                max_value=200,
            )
        ],
    ),
    "german_regulators": SchemaQuery(
        name="German Regulatory Bodies",
        description="German authorities: BKartA, BNetzA, BfDI, Verbraucherzentrale, ministries",
        cypher="""
            MATCH (a:Entity)-[r]-(e:Entity)
            WHERE a.name =~ '(?i).*(Bundeskartellamt|BKartA|BNetzA|BfDI|Verbraucherzentrale|BMAS|BMJ|BMWK|Bundestag|Bundesrat|Bundesministerium).*'
               OR a.name =~ '(?i).*(Federal Cartel Office|Federal Network Agency|Data Protection Commissioner|German).*'
            RETURN a, r, e
            LIMIT $limit
        """,
        category="organization",
        parameters=[
            QueryParameter(
                name="limit",
                param_type="integer",
                default=50,
                description="Maximum results",
                min_value=10,
                max_value=200,
            )
        ],
    ),
    "eu_institutions": SchemaQuery(
        name="EU Institutions & Policy Actors",
        description="European Commission, Parliament, Council, DGs, and key EU bodies",
        cypher="""
            MATCH (i:Entity)-[r]-(e:Entity)
            WHERE i.name =~ '(?i).*(European Commission|EU Commission|European Parliament|Council of the EU|DG CONNECT|DG JUST|DG GROW|DG COMP|EDPB|ENISA|Europarl|CJEU|Court of Justice).*'
            RETURN i, r, e
            LIMIT $limit
        """,
        category="organization",
        parameters=[
            QueryParameter(
                name="limit",
                param_type="integer",
                default=50,
                description="Maximum results",
                min_value=10,
                max_value=200,
            )
        ],
    ),
    "payment_fintech": SchemaQuery(
        name="Payment & Fintech Actors",
        description="BNPL providers, payment services, fintech regulators (BaFin, EBA, PSD2)",
        cypher="""
            MATCH (p:Entity)-[r]-(e:Entity)
            WHERE p.name =~ '(?i).*(Klarna|PayPal|AfterPay|Clearpay|Affirm|BaFin|EBA|PSD2|payment service|fintech|Stripe|Adyen).*'
               OR e.name =~ '(?i).*(Klarna|PayPal|AfterPay|Clearpay|Affirm|BaFin|EBA|PSD2|payment service|fintech|Stripe|Adyen).*'
            RETURN p, r, e
            LIMIT $limit
        """,
        category="organization",
        parameters=[
            QueryParameter(
                name="limit",
                param_type="integer",
                default=50,
                description="Maximum results",
                min_value=10,
                max_value=200,
            )
        ],
    ),
    "industry_associations": SchemaQuery(
        name="Industry Associations & Trade Bodies",
        description="Trade associations representing e-commerce and consumer interests",
        cypher="""
            MATCH (a:Entity)-[r]-(e:Entity)
            WHERE a.name =~ '(?i).*(EuroCommerce|Ecommerce Europe|BEVH|HDE|Digital Europe|BEUC|consumer association|trade association|industry group|lobby).*'
               OR e.name =~ '(?i).*(EuroCommerce|Ecommerce Europe|BEVH|HDE|Digital Europe|BEUC|consumer association|trade association|industry group|lobby).*'
            RETURN a, r, e
            LIMIT $limit
        """,
        category="organization",
        parameters=[
            QueryParameter(
                name="limit",
                param_type="integer",
                default=50,
                description="Maximum results",
                min_value=10,
                max_value=200,
            )
        ],
    ),
}

# =============================================================================
# CATEGORY 3: NETWORK ANALYSIS
# =============================================================================

NETWORK_QUERIES: dict[str, SchemaQuery] = {
    "influence_network": SchemaQuery(
        name="Influence Networks on Platform Policy",
        description="Who influences platform/e-commerce policy? Track lobbying and advocacy relationships",
        cypher="""
            MATCH (a:Entity)-[r]-(b:Entity)
            WHERE (type(r) CONTAINS 'INFLUENCE' OR type(r) CONTAINS 'LOBBY'
                   OR type(r) CONTAINS 'AFFECT' OR type(r) CONTAINS 'ADVOCATE')
              AND (a.name =~ '(?i).*(platform|e-commerce|marketplace|digital service|online).*'
                   OR b.name =~ '(?i).*(platform|e-commerce|marketplace|digital service|online).*')
            RETURN a, r, b
            LIMIT $limit
        """,
        category="network",
        parameters=[
            QueryParameter(
                name="limit",
                param_type="integer",
                default=75,
                description="Maximum results",
                min_value=10,
                max_value=200,
            )
        ],
    ),
    "enforcement_network": SchemaQuery(
        name="Enforcement Action Network",
        description="Track penalties, fines, and enforcement actions against platforms and e-commerce",
        cypher="""
            MATCH (e:Entity)-[r]-(t:Entity)
            WHERE type(r) CONTAINS 'ENFORCE' OR type(r) CONTAINS 'FINE'
                  OR type(r) CONTAINS 'PENALT' OR type(r) CONTAINS 'SANCTION'
                  OR type(r) CONTAINS 'INVESTIGATE'
               OR e.name =~ '(?i).*(enforcement|fine|penalty|sanction|investigation|infringement).*'
               OR t.name =~ '(?i).*(enforcement|fine|penalty|sanction|investigation|infringement).*'
            RETURN e, r, t
            LIMIT $limit
        """,
        category="network",
        parameters=[
            QueryParameter(
                name="limit",
                param_type="integer",
                default=50,
                description="Maximum results",
                min_value=10,
                max_value=200,
            )
        ],
    ),
    "compliance_chains": SchemaQuery(
        name="Compliance Obligation Chains",
        description="Trace compliance requirements from regulations through implementation",
        cypher="""
            MATCH (r:Entity)-[rel]-(c:Entity)
            WHERE r.name =~ '(?i).*(DSA|DMA|GDPR|AI Act|Product Safety|PSD2|NIS2).*'
              AND (type(rel) CONTAINS 'REQUIRE' OR type(rel) CONTAINS 'OBLIGAT'
                   OR type(rel) CONTAINS 'IMPLEMENT' OR type(rel) CONTAINS 'COMPLY'
                   OR type(rel) CONTAINS 'AFFECT')
            RETURN r, rel, c
            LIMIT $limit
        """,
        category="network",
        parameters=[
            QueryParameter(
                name="limit",
                param_type="integer",
                default=75,
                description="Maximum results",
                min_value=10,
                max_value=200,
            )
        ],
    ),
    "cross_border_regulation": SchemaQuery(
        name="Cross-Border Regulatory Connections",
        description="EU vs member state implementation: Germany, France, Poland, Italy, Spain",
        cypher="""
            MATCH (eu:Entity)-[r]-(nat:Entity)
            WHERE (eu.name =~ '(?i).*(European|EU |Directive|Regulation).*')
              AND (nat.name =~ '(?i).*(Germany|German|Bundestag|France|French|Poland|Polish|Italy|Italian|Spain|Spanish|Austria|Austrian|Netherlands|Dutch|Belgium|Czech).*')
            RETURN eu, r, nat
            LIMIT $limit
        """,
        category="network",
        parameters=[
            QueryParameter(
                name="limit",
                param_type="integer",
                default=75,
                description="Maximum results",
                min_value=10,
                max_value=200,
            )
        ],
    ),
    "high_impact_hubs": SchemaQuery(
        name="High-Impact Entity Hubs",
        description="Find most connected entities - central nodes in the regulatory network",
        cypher="""
            MATCH (e:Entity)-[r]-()
            WITH e, count(r) as degree
            WHERE degree > $min_degree
            ORDER BY degree DESC
            LIMIT $top_n
            MATCH (e)-[r]-(n:Entity)
            RETURN e, r, n
            LIMIT $limit
        """,
        category="network",
        parameters=[
            QueryParameter(
                name="min_degree",
                param_type="integer",
                default=3,
                description="Minimum connections",
                min_value=1,
                max_value=20,
            ),
            QueryParameter(
                name="top_n",
                param_type="integer",
                default=20,
                description="Top N hubs",
                min_value=5,
                max_value=50,
            ),
            QueryParameter(
                name="limit",
                param_type="integer",
                default=100,
                description="Maximum results",
                min_value=20,
                max_value=300,
            ),
        ],
    ),
}

# =============================================================================
# CATEGORY 4: TEMPORAL EVOLUTION
# =============================================================================

TEMPORAL_QUERIES: dict[str, SchemaQuery] = {
    "recent_developments": SchemaQuery(
        name="Recent Policy Developments",
        description="New entities and relationships added in the past N days",
        cypher="""
            MATCH (e:Entity)-[r]-(n:Entity)
            WHERE e.created_at > datetime() - duration({days: $days_back})
               OR r.created_at > datetime() - duration({days: $days_back})
            RETURN e, r, n
            ORDER BY coalesce(e.created_at, r.created_at) DESC
            LIMIT $limit
        """,
        category="temporal",
        parameters=[
            QueryParameter(
                name="days_back",
                param_type="integer",
                default=30,
                description="Days to look back",
                min_value=7,
                max_value=365,
            ),
            QueryParameter(
                name="limit",
                param_type="integer",
                default=50,
                description="Maximum results",
                min_value=10,
                max_value=200,
            ),
        ],
    ),
    "policy_timeline": SchemaQuery(
        name="Policy Implementation Timeline",
        description="Track implementation dates and deadlines for key regulations",
        cypher="""
            MATCH (p:Entity)-[r]-(e:Entity)
            WHERE p.name =~ '(?i).*(DSA|DMA|AI Act|GDPR|Digital|NIS2|DORA|Product Safety).*'
            RETURN p, r, e
            ORDER BY p.created_at DESC
            LIMIT $limit
        """,
        category="temporal",
        parameters=[
            QueryParameter(
                name="limit",
                param_type="integer",
                default=50,
                description="Maximum results",
                min_value=10,
                max_value=200,
            )
        ],
    ),
    "regulatory_changes": SchemaQuery(
        name="Regulatory Change Sequence",
        description="Track amendments, supersessions, and updates to regulations",
        cypher="""
            MATCH (old:Entity)-[r]->(new:Entity)
            WHERE type(r) CONTAINS 'SUPERSEDE' OR type(r) CONTAINS 'AMEND'
                  OR type(r) CONTAINS 'REPLACE' OR type(r) CONTAINS 'UPDATE'
                  OR type(r) CONTAINS 'REPEAL'
            RETURN old, r, new
            ORDER BY new.created_at DESC
            LIMIT $limit
        """,
        category="temporal",
        parameters=[
            QueryParameter(
                name="limit",
                param_type="integer",
                default=50,
                description="Maximum results",
                min_value=10,
                max_value=200,
            )
        ],
    ),
    "emerging_areas": SchemaQuery(
        name="Emerging Policy Areas",
        description="Recently added entities that may signal new regulatory focus areas",
        cypher="""
            MATCH (e:Entity)
            WHERE e.created_at > datetime() - duration({days: $days_back})
            WITH e
            ORDER BY e.created_at DESC
            LIMIT $top_n
            MATCH (e)-[r]-(n:Entity)
            RETURN e, r, n
            LIMIT $limit
        """,
        category="temporal",
        parameters=[
            QueryParameter(
                name="days_back",
                param_type="integer",
                default=60,
                description="Days to look back",
                min_value=14,
                max_value=365,
            ),
            QueryParameter(
                name="top_n",
                param_type="integer",
                default=30,
                description="Top N newest entities",
                min_value=10,
                max_value=100,
            ),
            QueryParameter(
                name="limit",
                param_type="integer",
                default=100,
                description="Maximum results",
                min_value=20,
                max_value=300,
            ),
        ],
    ),
    "legislative_tracking": SchemaQuery(
        name="Legislative Process Tracking",
        description="Track proposals through legislative stages: submission, examination, voting, adoption",
        cypher="""
            MATCH (proposal:Entity)-[r]-(stage:Entity)
            WHERE type(r) CONTAINS 'SUBMIT' OR type(r) CONTAINS 'EXAMINE'
                  OR type(r) CONTAINS 'VOTE' OR type(r) CONTAINS 'ADOPT'
                  OR type(r) CONTAINS 'AMEND' OR type(r) CONTAINS 'BECOME'
               OR proposal.name =~ '(?i).*(proposal|draft|bill|directive|regulation|Entwurf|Gesetzentwurf).*'
            RETURN proposal, r, stage
            ORDER BY proposal.created_at DESC
            LIMIT $limit
        """,
        category="temporal",
        parameters=[
            QueryParameter(
                name="limit",
                param_type="integer",
                default=50,
                description="Maximum results",
                min_value=10,
                max_value=200,
            )
        ],
    ),
}

# =============================================================================
# COMBINED QUERIES DICTIONARY
# =============================================================================

SCHEMA_QUERIES: dict[str, SchemaQuery] = {
    **POLICY_QUERIES,
    **ORGANIZATION_QUERIES,
    **NETWORK_QUERIES,
    **TEMPORAL_QUERIES,
}


def get_schema_query(query_name: str) -> SchemaQuery | None:
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


def get_default_parameters(query_name: str) -> dict[str, any]:
    """Get default parameter values for a query."""
    query = get_schema_query(query_name)
    if not query:
        return {}
    return {param.name: param.default for param in query.parameters}
