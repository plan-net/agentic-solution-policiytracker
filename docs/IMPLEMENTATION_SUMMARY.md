# News Collection DAG Fixes - Implementation Summary

**Date**: 2026-01-28
**Status**: ✅ **COMPLETED**

---

## Changes Implemented

### 1. Support `client_name` in Config Loader ✅

**File**: `src/etl/utils/config_loader.py`

**Change**: Updated `get_company_names()` method to prioritize `client_name` field over `company_terms`

**Before**:
```python
def get_company_names(self) -> list[str]:
    """Get list of company names/terms to search for."""
    return self.config.get("company_terms", [])
```

**After**:
```python
def get_company_names(self) -> list[str]:
    """Get list of company names/terms to search for."""
    # Priority 1: Check for client_name (string)
    client_name = self.config.get("client_name")
    if client_name and isinstance(client_name, str):
        return [client_name]

    # Priority 2: Fall back to company_terms (list) for backward compatibility
    return self.config.get("company_terms", [])
```

**Impact**:
- Zalando config with `client_name: zalando` now returns `"zalando"` instead of `"unknown_company"`
- ASK political monitoring config with `company_terms: [...]` still works (backward compatible)

---

### 2. Update KeywordScorer ✅

**File**: `src/etl/filtering/keyword_scorer.py`

**Change**: Updated initialization to support both `client_name` and `company_terms`

**Before**:
```python
self._company_terms = self._normalize_keywords(
    client_config.get("company_terms", [])
)
```

**After**:
```python
# Support both client_name (string) and company_terms (list)
client_name = client_config.get("client_name")
company_terms = client_config.get("company_terms", [])

# Convert client_name to list if present
if client_name and isinstance(client_name, str):
    terms = [client_name]
elif company_terms:
    terms = company_terms
else:
    terms = []

self._company_terms = self._normalize_keywords(terms)
```

**Impact**:
- KeywordScorer now works with both config formats
- Maintains scoring logic for direct impact detection

---

### 3. Make DAG Fail on Zero Documents ✅

**File**: `src/etl/dags/news_collection_dag.py`

#### 3a. Fail when no collectors enabled (Lines 153-157)

**Before**:
```python
if not enabled_collectors:
    print("No collectors enabled!")
    context["task_instance"].xcom_push(key="articles", value=[])
    context["task_instance"].xcom_push(key="collector_stats", value={})
    return 0  # ← Task marked as SUCCESS
```

**After**:
```python
if not enabled_collectors:
    error_msg = "No collectors enabled! Please configure API keys."
    print(f"❌ {error_msg}")
    raise ValueError(error_msg)  # ← Task marked as FAILED
```

#### 3b. Fail when 0 articles collected (After Line 183)

**Before**:
```python
print(f"Total collected: {len(articles)} articles")
print(f"{'='*50}\n")

return len(articles)  # ← Can be 0, task marked as SUCCESS
```

**After**:
```python
print(f"Total collected: {len(articles)} articles")
print(f"{'='*50}\n")

# Fail if no articles collected
if len(articles) == 0:
    error_msg = (
        f"Failed to collect any articles. All {len(enabled_collectors)} collector(s) failed. "
        f"Check API keys and credits."
    )
    print(f"❌ {error_msg}")
    raise ValueError(error_msg)  # ← Task marked as FAILED

return len(articles)
```

**Impact**:
- DAG now fails with clear error messages when:
  - No collectors are enabled (missing API keys)
  - All collectors fail to collect any articles (invalid keys, no credits, API errors)
- Error messages guide users to check API keys and credits
- Makes failures visible in Airflow UI

---

## Test Results

### Test 1: Zalando Config with `client_name` ✅
```
=== Test 1: Zalando client.yaml ===
Primary company: zalando
Expected: zalando
All company names: ['zalando']
Status: ✅ PASS
```

**Result**: Successfully reads `client_name` field from `client.yaml`

---

### Test 2: Backward Compatibility with `company_terms` ✅
```
=== Test 2: ASK Political Monitoring client.yaml ===
Found 61 company terms
First term: Tim Klüssendorf
Primary company: Tim Klüssendorf
Status: ✅ PASS
```

**Result**: Backward compatible with existing configs using `company_terms` list

---

### Test 3: KeywordScorer with Both Config Formats ✅
```
=== Test 3: KeywordScorer with client_name ===
Config type: client_name (string)
Company terms extracted: 1 terms
Status: ✅ PASS

Config type: company_terms (list)
Company terms extracted: 2 terms
Status: ✅ PASS
```

**Result**: KeywordScorer works with both `client_name` and `company_terms` formats

---

## What This Fixes

### Before:
1. ❌ News Collection DAG searched for `"unknown_company"`
2. ❌ DAG marked as SUCCESS even when 0 articles collected
3. ❌ No visibility into collection failures in Airflow UI

### After:
1. ✅ News Collection DAG searches for `"zalando"` (or configured client name)
2. ✅ DAG marked as FAILED when 0 articles collected
3. ✅ Clear error messages explain failures (API keys, credits)
4. ✅ Backward compatible with existing political monitoring configs

---

## Files Modified

| File | Lines Changed | Purpose |
|------|---------------|---------|
| `src/etl/utils/config_loader.py` | 53-61 | Support `client_name` field |
| `src/etl/filtering/keyword_scorer.py` | 144-157 | Support `client_name` field |
| `src/etl/dags/news_collection_dag.py` | 153-157, 183-192 | Fail on 0 documents |

**Total**: 3 files, ~20 lines of code

---

## Next Steps

### To Restore News Collection:

1. **Fix DPA API Key**
   ```bash
   # Get new key from: https://article-retriever.iq.dpa-ai-hub.de/docs
   # Update in .env:
   DPA_API_KEY=<new_valid_key>

   # Test:
   python3 test_dpa_key.py
   ```

2. **Top Up Exa Credits**
   ```bash
   # Visit: https://dashboard.exa.ai/
   # Add credits to account

   # Test:
   python3 test_exa_key.py
   ```

3. **Trigger News Collection**
   ```bash
   # Trigger DAG manually
   just airflow-trigger-news

   # Or from Airflow UI: http://localhost:8080
   ```

### Expected Behavior:

**With Valid API Keys**:
- ✅ DAG collects articles for "zalando"
- ✅ Task completes successfully
- ✅ Articles saved to `data/input/news/YYYY-MM/`

**With Invalid API Keys**:
- ❌ DAG fails with error: `"Failed to collect any articles. All 2 collector(s) failed. Check API keys and credits."`
- ❌ Task marked as FAILED in Airflow UI
- ❌ Clear guidance to check API keys

---

## Rollback Instructions

If you need to rollback these changes:

```bash
# Revert all changes
git checkout src/etl/utils/config_loader.py
git checkout src/etl/filtering/keyword_scorer.py
git checkout src/etl/dags/news_collection_dag.py
```

**Note**: Changes are backward compatible, so rollback should not be needed for existing configs.

---

## Success Criteria - All Met ✅

- [x] News Collection DAG searches for `"zalando"` instead of `"unknown_company"`
- [x] Backward compatibility maintained (ASK political config still works)
- [x] DAG fails with clear error when 0 articles collected
- [x] KeywordScorer works with both `client_name` and `company_terms`
- [x] All tests pass

---

## Related Documents

- [API_KEY_TEST_REPORT.md](API_KEY_TEST_REPORT.md) - Detailed API key test results
- [test_dpa_key.py](test_dpa_key.py) - DPA API key test script
- [test_exa_key.py](test_exa_key.py) - Exa API key test script

---

**Implementation Completed**: 2026-01-28
**All Tests Passed**: ✅
