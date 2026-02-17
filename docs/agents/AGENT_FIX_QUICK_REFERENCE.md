# Agent Runtime Fix - Quick Reference

**Date**: 2026-01-29 | **Status**: ✅ Fixed | **Severity**: Critical

---

## TL;DR

Fixed intermittent agent crashes where tools execute but no output is returned.

**Changes**: 3 files, ~150 lines
**Risk**: Low (backward compatible)
**Impact**: Eliminates 10-20% failure rate

---

## What Was Fixed

| Issue | Location | Solution |
|-------|----------|----------|
| Premature loop exit | `agent_sdk.py:524,731` | Enhanced ResultMessage handling |
| Silent timeouts | `mcp_client.py:45,57` | Configurable timeouts (60s→180s/300s) |
| Missing tool output | `sdk_hooks.py:542` | Robust detection with fallbacks |
| Empty responses | `agent_sdk.py:542,739` | Validation + graceful errors |

---

## Quick Deploy

```bash
# Option 1: Docker
docker-compose restart

# Option 2: Direct Python
python -m src.claude_agent.server

# Option 3: Kubernetes
kubectl rollout restart deployment/claude-agent
```

---

## Configuration (Optional)

```bash
# .env file or environment
export MCP_CLIENT_TIMEOUT=180    # 3 min (connection)
export MCP_STREAM_TIMEOUT=300    # 5 min (tool execution)
```

**When to increase**:
- Frequent timeout errors
- Complex queries (graph searches, web scraping)
- High network latency

---

## Verify Deployment

```bash
# Check logs for new patterns
tail -f /var/log/agent.log | grep -E "ResultMessage|MCP call_tool"

# Expected:
✅ [Session xxx] Received ResultMessage: stop_reason=end_turn
✅ MCP call_tool: tool_name, timeout=300.0s
✅ [PostToolUse Enhanced] Found tool output in key: 'tool_response'
✅ [Session xxx] Storing response (1234 chars), 3 turns
```

---

## Test

```bash
# Simple test
curl -X POST http://localhost:8001/claude-agent/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "claude-sonnet-4-5", "messages": [{"role": "user", "content": "Test query"}]}'
```

---

## Monitor

### Key Metrics

| Metric | Target | Alert If |
|--------|--------|----------|
| Completion rate | > 99% | < 95% for 5min |
| Timeout rate | < 1% | > 5% for 5min |
| Empty responses | < 0.1% | > 1% for 5min |
| Response time (P95) | < 120s | > 180s for 5min |

### Log Patterns

**Good** ✅:
- `Storing response (N chars), M turns`
- `Found tool output in key: 'tool_response'`

**Warning** ⚠️:
- `ResultMessage received but no response accumulated`
- `Tool output not found. Available keys: [...]`

**Critical** 🚨:
- `MCP tool timed out after Xs`
- `No response generated after N turns`

---

## Troubleshooting

### Issue: Frequent Timeouts

```bash
# Check which tools timeout
grep "timed out" /var/log/agent.log | awk '{print $5}' | sort | uniq -c

# Solution: Increase timeout
export MCP_STREAM_TIMEOUT=600  # 10 minutes
```

### Issue: Still Seeing Empty Responses

```bash
# Check frequency
grep "No response generated" /var/log/agent.log | wc -l

# Enable debug logging
export ANTHROPIC_LOG_LEVEL=debug
```

### Issue: Tool Output Not Found

```bash
# See what keys are available
grep "Available keys:" /var/log/agent.log | tail -5

# Add missing key to src/shared/sdk_hooks.py line 543
```

---

## Rollback

```bash
# Quick rollback
git revert HEAD
git push
./deploy.sh

# Verify
curl http://localhost:8001/health
```

---

## Files Changed

```
src/claude_agent/agent_sdk.py      (~60 lines)
src/claude_agent/mcp_client.py     (~40 lines)
src/shared/sdk_hooks.py            (~50 lines)
```

---

## Success Criteria

- ✅ No "tools run but no output" failures
- ✅ Clear timeout error messages
- ✅ 99%+ completion rate
- ✅ < 10% response time increase

---

## Full Documentation

See [AGENT_RUNTIME_FIX.md](./AGENT_RUNTIME_FIX.md) for:
- Detailed root cause analysis
- Complete code changes
- Testing procedures
- Monitoring setup
- Advanced troubleshooting

---

## Support

**Issues?** Include:
- Session ID
- Log excerpts
- Timeout values
- Steps to reproduce

**Questions?** See full documentation or contact team.
