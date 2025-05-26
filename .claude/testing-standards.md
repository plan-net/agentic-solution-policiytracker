# Testing Standards and Patterns

## Test Structure
- Unit tests: `/tests/unit/` - Test individual components
- Integration tests: `/tests/integration/` - Test Kodosumi + Ray + Azure
- Use pytest with async support

## Essential Fixtures (conftest.py)
Always include these fixtures:
- `setup_ray_for_tests` - Ray in local mode (session-scoped)
- `mock_azure_storage_client` - Mock Azure operations
- `mock_kodosumi_tracer` - Mock tracer.markdown() calls

## Testing Patterns
```python
# Kodosumi endpoint testing
@patch('app.Launch')
async def test_endpoint(mock_launch, mock_request):
    # Test Launch was called with correct entrypoint

# Ray task testing  
ray.init(local_mode=True)  # Always use local mode

# Azure mocking
client.upload_json = AsyncMock(return_value=True)
client.download_json = AsyncMock(return_value={"data": "mocked"})
```

## Coverage Requirements
- Minimum 90% coverage
- Run: `just test-cov`
- Focus on business logic, not framework code

## Key Testing Commands
- All tests: `just test`
- Unit only: `just test-unit`
- Integration: `just test-integration`
- Coverage: `just test-coverage`