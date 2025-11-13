# Bundestag Ingestion Flow Patterns (Flow 5)

## Overview
Flow 5 provides comprehensive German parliamentary data ingestion from the Bundestag Document and Information System (DIP) API. It collects 8 different types of parliamentary data and transforms them into knowledge graph entities and relationships.

## Architecture Patterns

### 8 Data Source Collectors
```python
# All collectors extend BaseCollector
class VorgangCollector(BaseCollector):
    endpoint = "vorgang"
    entity_type = "Vorgang"

class DrucksacheCollector(BaseCollector):
    endpoint = "drucksache"
    entity_type = "Drucksache"

# Plus: Person, Plenarprotokoll, Vorgangsposition, Aktivitaet, Wahlperiode, Fraktion
```

### Collector Pattern Structure
```python
class BaseCollector(ABC):
    """
    Abstract base with common functionality:
    - fetch_with_pagination()
    - collect_with_filters()
    - health_check()
    - _transform_to_entities()
    - _transform_to_edges()
    """

    @abstractmethod
    async def collect_and_transform(self, inputs: Dict) -> Dict:
        """Subclasses implement specific collection logic."""
        pass
```

### Transformation Pipeline
```
Bundestag API → Collector → Entity Builder → Edge Builder → Knowledge Graph
                    ↓
              Statistics Tracking
```

## API Client Pattern

### Robust HTTP Client
```python
class BundestagAPIClient:
    """
    Async HTTP client with:
    - Automatic retry with exponential backoff
    - Rate limit handling (429 responses)
    - Configurable timeout and max retries
    - Health check support
    """

    BASE_URL = "https://search.dip.bundestag.de/api/v1/"
    DEFAULT_API_KEY = "PUBLIC_KEY"  # Valid until 05/2026

    async def get(self, endpoint: str, params: Dict) -> Dict:
        # Implements retry logic with exponential backoff
        # Handles 429 rate limiting automatically
        # Returns JSON response
```

### Rate Limiting Strategy
- **Default**: 100 requests/minute, 20 requests/second burst
- **Handler**: Automatic retry with Retry-After header
- **Backoff**: Exponential: 1s, 2s, 4s, 8s...

## Pagination Pattern

### Cursor-Based Pagination
```python
class PaginationHelper:
    """
    Async iterator for paginated API responses.

    Usage:
        async for item in pagination.paginate(endpoint, filters):
            process(item)
    """

    async def paginate(self, endpoint: str, filters: Dict):
        cursor = None
        collected = 0

        while True:
            response = await self.api_client.get(endpoint, {
                **filters,
                "cursor": cursor
            })

            for item in response["documents"]:
                yield item
                collected += 1
                if self.max_items and collected >= self.max_items:
                    return

            cursor = response.get("cursor")
            if not cursor:  # Last page
                break
```

### Pagination Best Practices
- Always use cursor-based pagination (not offset)
- Set reasonable max_items limits
- Handle empty responses gracefully
- Track total items collected

## Filter Building Pattern

### Flexible Filter Construction
```python
class FilterBuilder:
    """
    Builds DIP API filter parameters from high-level inputs.
    """

    def build_filters(
        self,
        wahlperiode: Optional[str] = None,
        datum_von: Optional[str] = None,
        datum_bis: Optional[str] = None,
        limit: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        # Converts to DIP API format: f.wahlperiode, f.datum, etc.
```

### Common Filters
- `f.wahlperiode`: Electoral period (19, 20, 21)
- `f.datum`: Date filter (ISO 8601)
- `f.vorgangstyp`: Procedure type
- `f.beratungsstand`: Status filter
- `num`: Results per page (max 100)

## Entity and Edge Transformation

### Entity Builder Pattern
```python
class BundestagEntityBuilder:
    """
    Creates Pydantic entities from raw API data.
    Supports all 8 entity types from political_schema_v4.
    """

    async def create_vorgang_entity(self, **kwargs) -> Vorgang:
        return Vorgang(**kwargs)

    async def create_person_entity(self, **kwargs) -> BundestagPerson:
        return BundestagPerson(**kwargs)

    async def build(self, raw_data: Dict) -> Any:
        # Generic method that routes to specific builder
```

### Edge Builder Pattern
```python
class BundestagEdgeBuilder:
    """
    Creates relationship edges between entities.
    Supports 15 edge types from political_schema_v4.
    """

    async def build(self, raw_data: Dict, entity: Any) -> List[Edge]:
        # Extracts relationships from raw data
        # Returns list of edge objects
```

### 15 Edge Types
1. Vorgang → Wahlperiode (IN_WAHLPERIODE)
2. Vorgang → Drucksache (HAS_DRUCKSACHE)
3. Person → Fraktion (MEMBER_OF_FRAKTION)
4. Person → Wahlperiode (ACTIVE_IN_WAHLPERIODE)
5. Fraktion → Wahlperiode (EXISTS_IN_WAHLPERIODE)
6. Vorgangsposition → Vorgang (POSITION_OF_VORGANG)
7. Aktivitaet → Vorgang (ACTIVITY_OF_VORGANG)
8. Aktivitaet → Plenarprotokoll (DOCUMENTED_IN_PROTOKOLL)
9. Plenarprotokoll → Wahlperiode (IN_WAHLPERIODE)
10. Person → Vorgang (INITIATES_VORGANG)
11. Person → Aktivitaet (PARTICIPATES_IN_ACTIVITY)
12. Drucksache → Person (AUTHORED_BY)
13. Drucksache → Wahlperiode (IN_WAHLPERIODE)
14. Vorgang → Vorgang (RELATED_TO_VORGANG)
15. Fraktion → Vorgang (FRAKTION_POSITION_ON)

## Testing Patterns

### Following Good Test Practices
✅ **DO**: Mock only external dependencies (HTTP API calls)
✅ **DO**: Test real internal logic (transformers, builders)
✅ **DO**: Use interface contract validation
✅ **DO**: Test with realistic sample data

❌ **DON'T**: Over-mock internal interfaces
❌ **DON'T**: Mock the transformation logic you're testing
❌ **DON'T**: Skip interface validation

### Test Structure
```
tests/
├── fixtures/
│   └── bundestag_sample_data.py       # Realistic API responses
├── unit/flows/bundestag_ingestion/
│   ├── test_collectors.py             # All 8 collectors
│   ├── test_transformers.py           # Entity/edge builders
│   └── test_utils.py                  # API client, pagination, filters
└── integration/flows/
    └── test_bundestag_ingestion_flow.py  # End-to-end flow
```

### Sample Data Pattern
```python
# tests/fixtures/bundestag_sample_data.py
SAMPLE_VORGANG_RESPONSE = {
    "documents": [{
        "id": "287654",
        "titel": "Gesetz zur...",
        "vorgangstyp": "Gesetzgebung",
        "wahlperiode": 20,
        # ... realistic field values
    }],
    "numFound": 1,
    "cursor": "AoE/cursor_string"
}
```

### Interface Contract Testing
```python
def test_all_collectors_have_consistent_interface():
    """Validate all collectors implement required interface."""
    collectors = [
        VorgangCollector(...),
        DrucksacheCollector(...),
        # ... all 8 collectors
    ]

    for collector in collectors:
        assert hasattr(collector, 'endpoint')
        assert hasattr(collector, 'entity_type')
        assert hasattr(collector, 'collect_and_transform')
        assert hasattr(collector, 'health_check')
```

### Real Logic Testing
```python
@pytest.mark.asyncio
async def test_collect_with_real_transformation():
    """Test real collection with actual transformation logic."""
    # Mock only external API
    api_client.get = AsyncMock(return_value=SAMPLE_VORGANG_RESPONSE)

    # Use real transformers (not mocked!)
    entity_builder = BundestagEntityBuilder()
    edge_builder = BundestagEdgeBuilder()

    collector = VorgangCollector(api_client, entity_builder, edge_builder)

    # Test real logic
    result = await collector.collect_and_transform(inputs)

    # This would catch method name bugs!
    assert result["entities_created"] >= 0
```

## Statistics and Reporting

### Standard Statistics Format
```python
{
    "entities_created": 42,
    "edges_created": 156,
    "duration": 12.34,
    "items_collected": 42,
    "collector_type": "VorgangCollector",
    "endpoint": "vorgang",
    "entity_type": "Vorgang",
    "errors": []
}
```

### Progress Tracking
Collectors track:
- Items collected from API
- Entities created in knowledge graph
- Edges created between entities
- Processing duration
- Error messages (if any)

## Error Handling Patterns

### API Error Handling
```python
try:
    response = await api_client.get(endpoint, params)
except aiohttp.ClientError as e:
    logger.error("API request failed", error=str(e))
    # Retry with exponential backoff
    # Or report error in statistics
```

### Transformation Error Handling
```python
for item in items:
    try:
        entity = await entity_builder.build(item)
        entities.append(entity)
    except Exception as e:
        logger.error("Failed to transform item", item_id=item.get("id"), error=str(e))
        errors.append(str(e))
        continue  # Continue with next item
```

### Health Check Pattern
```python
async def health_check(self) -> bool:
    """Verify collector can access API."""
    try:
        items = await self.fetch_with_pagination(filters={}, limit=1)
        return True
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return False
```

## Integration with Kodosumi

### Flow Integration Pattern
Collectors integrate with Kodosumi flows:
- Return standardized statistics dictionary
- Support progress tracking via tracer
- Generate markdown reports
- Handle batch processing

### Knowledge Graph Integration
Entities and edges are stored via Kodosumi interface:
- Entities → Neo4j nodes
- Edges → Neo4j relationships
- Maintains schema consistency with political_schema_v4

## Performance Patterns

### Batch Collection
```python
# Collect multiple sources in parallel
import asyncio

results = await asyncio.gather(*[
    vorgang_collector.collect_with_filters(...),
    drucksache_collector.collect_with_filters(...),
    person_collector.collect_with_filters(...)
])
```

### Memory Management
```python
# Process in smaller batches for large collections
batch_size = 100
for offset in range(0, total_items, batch_size):
    result = await collector.collect_with_filters(limit=batch_size)
    # Process batch before loading next
```

### Caching Strategy
```python
# Cache rarely-changing reference data
wahlperiode_cache = {}  # Electoral periods
fraktion_cache = {}     # Parliamentary groups per period
```

## Documentation Pattern

### Documentation Structure
```
docs/flows/bundestag_ingestion.md
├── Overview & Purpose
├── Architecture Diagram
├── 8 Data Sources (detailed)
├── Entity Relationships (15 edge types)
├── Configuration Options
├── Usage Examples
├── API Endpoint Reference
├── Troubleshooting Guide
├── Performance Optimization
├── Integration with Knowledge Graph
└── Testing & References
```

### Code Comments
```python
"""
Brief description of module/class/function.

Detailed explanation of:
- What it does
- Why it's designed this way
- Key patterns used
- Integration points

Args:
    param: Description

Returns:
    Description of return value

Raises:
    ExceptionType: When and why
"""
```

## Common Anti-Patterns to Avoid

❌ **Over-mocking in tests**: Don't mock internal transformation logic
❌ **Ignoring pagination**: Always handle multi-page responses
❌ **Hardcoded values**: Use configuration for API URLs, keys, limits
❌ **No error handling**: Always handle API and transformation errors
❌ **Missing interface validation**: Always test method signatures exist
❌ **Blocking operations**: Use async/await throughout
❌ **No health checks**: Always implement health check methods

## Success Metrics

### Test Coverage
- Overall: >90%
- Collectors: 95%
- Transformers: 92%
- Utils: 93%
- Integration: 88%

### Performance Targets
- API response time: <2s per request
- Pagination handling: Support 10,000+ items
- Transformation rate: >100 entities/second
- Memory usage: <500MB per collector

### Data Quality
- Entity extraction accuracy: >95%
- Edge creation accuracy: >90%
- Error rate: <5%
- Deduplication effectiveness: >99%

## References

- [Bundestag DIP API Documentation](https://dip.bundestag.de/documents/informationen-zur-dip-api.pdf)
- [Political Schema v4](../src/graphrag/political_schema_v4.py)
- [Flow 5 Documentation](../docs/flows/bundestag_ingestion.md)
- [Test Patterns](./test-patterns.md)
- [Testing Standards](./testing-standards.md)

---

**Version**: 0.2.0
**Last Updated**: 2025-11-12
**Status**: Production Ready
