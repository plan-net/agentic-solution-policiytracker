# API Key Test Report
**Generated**: 2026-01-28
**News Collection DAG Error Analysis**

---

## Test Results Summary

| API Provider | Status | Issue | Action Required |
|--------------|--------|-------|-----------------|
| **DPA** | ❌ FAILED | 401 - Invalid/expired API key | Get new key |
| **Exa.ai** | ❌ FAILED | 402 - Credits exhausted | Top up credits |

---

## Detailed Test Results

### 1. DPA API Key Test

**Status**: ❌ **AUTHENTICATION FAILED (401)**

**Error Details**:
```json
{"detail":"Invalid or missing (internal) API Key."}
```

**Current Key** (in `.env`):
```
DPA_API_KEY=sk-aYMFNWknZ0bpYfEejnD1354Yvc8mARgo
```

**Issue**: The API key is invalid or expired

**Resolution Steps**:
1. Visit: https://article-retriever.iq.dpa-ai-hub.de/docs
2. Sign in or create an account
3. Generate a new API key
4. Update the key in `agentic-solution-policiytracker/.env`
5. Re-run the test: `python3 test_dpa_key.py`

---

### 2. Exa.ai API Key Test

**Status**: ❌ **PAYMENT REQUIRED (402)**

**Error Details**:
```json
{
  "requestId": "988c0981d4fc5a9b0260869c4d4a3137",
  "error": "You have exceeded your credits limit. Please top up to keep using Exa at dashboard.exa.ai",
  "tag": "NO_MORE_CREDITS"
}
```

**Current Key** (in `.env`):
```
EXA_API_KEY=cc1fea87-d577-4b91-b81f-efe42dc06218
```

**Issue**: The API key is **VALID** but the account has **zero credits**

**Resolution Steps**:
1. Visit: https://dashboard.exa.ai/
2. Sign in to your account
3. Navigate to billing/credits section
4. Top up your account with credits
5. Re-run the test: `python3 test_exa_key.py`

---

## Impact on News Collection DAG

The News Collection DAG (`news_collection`) is currently configured to use **both** collectors:

From `.env` line 136:
```bash
NEWS_COLLECTORS=dpa,exa_direct
```

**Current Behavior**:
- ✅ DAG executes without errors
- ❌ Both collectors fail (DPA: 401, Exa: 402)
- ❌ 0 articles collected
- ⚠️  Task marked as SUCCESS despite failures
- ⚠️  Searching for "unknown_company" instead of actual client name

**Log Evidence**:
```
Collecting from dpa...
  ✗ Failed to collect from dpa: DPA API error 401: {"detail":"Invalid or missing (internal) API Key."}

Collecting from exa_direct...
  ✗ Failed to collect from exa_direct: Exa API error 402: {"requestId":"...","error":"You have exceeded your credits limit..."}

Total collected: 0 articles
```

---

## Additional Issue: Wrong Search Query

**Problem**: DAG is searching for `"unknown_company"` instead of `"zalando"`

**Root Cause**: Missing `company_terms` field in `client.yaml`

**Current client.yaml**:
```yaml
client_name: zalando
industry:
  primary: "E-commerce / Online Retail"
# Missing: company_terms field
```

**Expected format**:
```yaml
client_name: zalando
company_terms:  # <-- ADD THIS
  - zalando
  - "Zalando SE"
industry:
  primary: "E-commerce / Online Retail"
```

**Code Reference**:
- [config_loader.py:53-60](agentic-solution-policiytracker/src/etl/utils/config_loader.py#L53-L60) - Reads `company_terms`, defaults to `["example_company"]`
- [config_loader.py:57-60](agentic-solution-policiytracker/src/etl/utils/config_loader.py#L57-L60) - Returns first term or `"unknown_company"`

---

## Recommended Actions (Priority Order)

### 🔴 Critical (Blocks News Collection)

1. **Fix DPA API Key**
   - Get new key from: https://article-retriever.iq.dpa-ai-hub.de/docs
   - Update in `.env`
   - Test: `python3 test_dpa_key.py`

2. **Top Up Exa Credits**
   - Visit: https://dashboard.exa.ai/
   - Add credits to account
   - Test: `python3 test_exa_key.py`

3. **Fix client.yaml Configuration**
   - Add `company_terms` field with company names
   - This will fix the "unknown_company" query issue

### 🟡 Medium (Improves Reliability)

4. **Improve DAG Error Handling**
   - Currently: DAG succeeds even when all collectors fail
   - Recommendation: Fail the task if all collectors return 0 articles
   - This will make failures more visible in Airflow UI

### 🟢 Optional (Nice to Have)

5. **Add API Key Validation on Startup**
   - Test API keys when DAG initializes
   - Fail fast with clear error messages
   - Could use the test scripts created here

---

## Test Scripts Created

Two test scripts have been created for your convenience:

1. **`test_dpa_key.py`** - Tests DPA API key
2. **`test_exa_key.py`** - Tests Exa API key

**Usage**:
```bash
# Test DPA key
python3 test_dpa_key.py

# Test Exa key
python3 test_exa_key.py
```

Both scripts will:
- ✅ Load key from `.env`
- ✅ Make a real API request
- ✅ Report detailed error messages
- ✅ Provide next steps

---

## Questions?

If you need help with:
- Getting new API keys
- Fixing the `client.yaml` configuration
- Improving the DAG error handling

Just let me know!
