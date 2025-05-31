# Testing Patterns & Anti-Patterns

## Core Testing Philosophy

**Golden Rule**: Mock external services, test real internal interfaces.

## ❌ **Anti-Patterns (What We Did Wrong)**

### 1. Over-Mocking Internal Interfaces
```python
# BAD: Mocks away the code we're trying to test
with patch('pathlib.Path.mkdir'), \
     patch('builtins.open', create=True) as mock_open:
    
    collector.transformer.transform_to_markdown = MagicMock()  # Hides method name bugs!
    result = await collector.collect_documents()
```

**Problem**: The test never executes real internal logic, hiding bugs like wrong method names.

### 2. Mocking Behavior Instead of Testing It
```python
# BAD: Mocks the storage interface we want to test
collector.storage_client = None
with patch('builtins.open'):
    # File I/O behavior is never tested
```

**Problem**: We never test if files are actually created correctly.

### 3. No Interface Contract Validation
```python
# BAD: Never validates method names exist
collector.transformer = MagicMock()  # Any method call "works"
```

**Problem**: Missing methods or wrong method names are never caught.

## ✅ **Good Patterns (What We Should Do)**

### 1. Mock Only External Dependencies
```python
# GOOD: Mock external API, test internal logic
@patch('aiohttp.ClientSession.post')
async def test_collector(mock_post):
    # Mock external API response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = test_data
    mock_post.return_value.__aenter__.return_value = mock_response
    
    # Test real internal interfaces
    collector = PolicyLandscapeCollector(...)  # Real object
    result = await collector.collect_documents()  # Real method calls
    
    # Verify real behavior
    assert result['documents_saved'] > 0
```

### 2. Test Real File I/O with Temporary Directories
```python
# GOOD: Test actual file creation
async def test_document_saving():
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = LocalStorage(base_path=temp_dir)
        
        # Test real file operations
        success = await storage.save_document(content, path, metadata)
        
        # Verify real files exist
        files = list(Path(temp_dir).rglob("*.md"))
        assert len(files) == 1
        
        # Verify real content
        with open(files[0]) as f:
            assert "expected content" in f.read()
```

### 3. Interface Contract Testing
```python
# GOOD: Validate that required methods exist
def test_transformer_interface():
    transformer = MarkdownTransformer()
    
    # Verify correct method exists
    assert hasattr(transformer, 'transform_article')
    
    # Verify wrong method does NOT exist (catches bugs!)
    assert not hasattr(transformer, 'transform_to_markdown')
    
    # Test method signature
    sig = inspect.signature(transformer.transform_article)
    assert 'article' in sig.parameters
```

### 4. Component Integration Testing
```python
# GOOD: Test real interactions between components
async def test_collector_transformer_integration():
    collector = PolicyLandscapeCollector(...)
    
    # Mock only external API
    collector.exa_collector.collect_news = AsyncMock(return_value=test_articles)
    
    # Test real transformer usage (would catch method name bugs)
    result = await collector._save_policy_documents(test_articles)
    
    # Verify real behavior
    assert result[0]['filename'].endswith('.md')
```

### 5. End-to-End Integration Tests
```python
# GOOD: Test complete flow with minimal mocking
async def test_end_to_end_collection():
    with tempfile.TemporaryDirectory() as temp_dir:
        collector = PolicyLandscapeCollector(
            storage_type="local",
            base_path=temp_dir
        )
        
        # Mock only external API calls
        collector.exa_collector.collect_news = AsyncMock(return_value=test_data)
        
        # Test complete real flow
        result = await collector.collect_policy_documents()
        
        # Verify real end-to-end behavior
        md_files = list(Path(temp_dir).rglob("*.md"))
        json_files = list(Path(temp_dir).rglob("*.json"))
        
        assert len(md_files) > 0, "Should create markdown files"
        assert len(json_files) == 0, "Should not create JSON files"
```

## 🎯 **What to Mock vs What to Test**

### Mock These (External Dependencies):
- ✅ HTTP API calls (`aiohttp.ClientSession`)
- ✅ External service responses (Exa, Apify APIs)
- ✅ Network timeouts and errors
- ✅ Authentication tokens

### Test These (Internal Logic):
- ✅ Method calls between components
- ✅ File I/O operations (use temp directories)
- ✅ Data transformations
- ✅ Error handling and validation
- ✅ Configuration loading
- ✅ Interface contracts

## 📊 **Test Hierarchy**

### 1. Contract Tests (High Value)
Validate interfaces between components exist and work correctly.

### 2. Integration Tests (Highest Value)
Test multiple components working together with minimal mocking.

### 3. Unit Tests (Medium Value)
Test individual methods with real inputs/outputs.

### 4. End-to-End Tests (Validation)
Test complete workflows to validate everything works together.

## 🚨 **Red Flags in Tests**

- **Too many mocks**: If you're mocking more than external dependencies
- **Mocking internal interfaces**: Never mock your own code's interfaces
- **Tests pass but production fails**: Sign of over-mocking
- **Brittle tests**: Tests break when refactoring working code
- **False confidence**: High coverage but bugs slip through

## 💡 **Testing Mantras**

1. **"If it's not tested, it's broken"** - Don't mock away the behavior you want to test
2. **"Test interfaces, not implementations"** - Focus on contracts between components
3. **"Mock at the boundaries"** - Only mock external systems
4. **"Integration tests find the real bugs"** - Component interactions matter most
5. **"Test what can break"** - Focus on error-prone integration points

## 📝 **Testing Checklist**

Before writing a test, ask:

- [ ] Am I testing real internal logic or just mocks?
- [ ] Would this test catch interface mismatches?
- [ ] Am I only mocking external dependencies?
- [ ] Does this test validate actual file/data creation?
- [ ] Would this test fail if I use the wrong method name?
- [ ] Am I testing the integration points between components?

**Remember**: The goal is to catch bugs like the `transform_to_markdown` vs `transform_article` issue we just encountered!