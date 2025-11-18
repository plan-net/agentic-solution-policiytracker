# Ray Log Analysis Skill

## Skill Type
**Autonomous Troubleshooting Skill** - Claude can invoke this proactively when detecting issues

## When to Invoke

Claude should automatically use this skill when:
- User reports "my flow failed" or "deployment error"
- User mentions "not working", "broken", "error" related to Ray/Kodosumi
- Deployment commands (`just deploy-all`) show failures
- Flow execution appears to have issues
- User asks "what went wrong" or "why did it fail"
- After detecting error messages in command output

## Core Capabilities

### 1. Error Detection
Search Ray logs for common error patterns and extract relevant context

### 2. Flow-Specific Analysis
Filter logs by specific flow name when investigating flow failures

### 3. Pattern Recognition
Identify common error categories and provide targeted solutions

### 4. Root Cause Analysis
Trace errors back to their source and provide actionable fixes

## Ray Log Structure

Ray organizes logs in `/tmp/ray/session_latest/logs/` with this structure:

```
/tmp/ray/session_latest/
├── logs/
│   ├── serve/                           # Ray Serve application logs
│   │   ├── controller_*.log             # Serve controller logs
│   │   ├── proxy_*.log                  # HTTP proxy logs
│   │   └── replica_<flow-name>_*.log    # Flow replica logs (FLOW LOGS HERE!)
│   ├── worker-*.out                     # Worker stdout (actor names, print statements)
│   ├── worker-*.err                     # Worker stderr (exceptions, errors)
│   ├── dashboard_*.log                  # Ray dashboard component logs
│   └── gcs_server.out                   # GCS (Global Control Store) logs
└── session_*/                           # Previous sessions (cleared on restart)
```

### Key Log Locations

**Flow-specific logs** (your application code):
- `logs/serve/replica_<flow-name>_<deployment-class>_<id>.log`
- Example: `replica_flow5d-bundestag-plenarprotokoll_BundestagPlenarprotokollFlow_npkj3mku.log`

**Worker logs** (actors, print statements, exceptions):
- `logs/worker-<id>.out` - stdout including actor names and print()
- `logs/worker-<id>.err` - stderr including Python exceptions

**Serve infrastructure**:
- `logs/serve/controller_*.log` - Deployment status, replica management
- `logs/serve/proxy_*.log` - HTTP request routing

## Execution Pattern

### Step 1: Initial Log Check
```bash
# Get recent Ray logs (aggregated)
uv run --active ray logs | tail -100
```

### Step 2: Error Search
```bash
# Search for errors and exceptions
uv run --active ray logs | grep -iE "(error|exception|failed|traceback)" | tail -50

# Search for warnings
uv run --active ray logs | grep -iE "(warning|warn)" | tail -30
```

### Step 3: Flow-Specific Search (if flow name known)
```bash
# Option 1: Via aggregated logs
uv run --active ray logs | grep -i "bundestag_person" | tail -50

# Option 2: Direct replica log access (RECOMMENDED for flow debugging)
# Find flow replica log
ls /tmp/ray/session_latest/logs/serve/ | grep "replica.*bundestag-person"

# View specific flow replica log
tail -100 /tmp/ray/session_latest/logs/serve/replica_flow5a-bundestag-person_*.log

# Search for errors in flow replica
grep -iE "(error|exception|failed)" /tmp/ray/session_latest/logs/serve/replica_flow5a-bundestag-person_*.log

# Option 3: Worker logs (for print statements and actor errors)
# Find worker logs for specific flow actor
grep -l "bundestag-person" /tmp/ray/session_latest/logs/worker*.out | xargs tail -50
```

### Step 4: Search for Specific Pattern (if error type known)
```bash
# Search for specific error types in all logs
uv run --active ray logs | grep -i "ImportError" -C 5
uv run --active ray logs | grep -i "Neo4j" -C 5
uv run --active ray logs | grep -i "ValidationError" -C 5

# Search in specific log locations
grep -r "ImportError" /tmp/ray/session_latest/logs/serve/
grep -r "Neo4j" /tmp/ray/session_latest/logs/worker*.err
```

### Step 5: Check Latest Session Location
```bash
# Verify session directory (symlink to actual session)
ls -la /tmp/ray/session_latest

# List all available sessions
ls -la /tmp/ray/

# Check when current session started
stat /tmp/ray/session_latest | grep Birth
```

## Error Pattern Recognition

### Category 1: Import/Module Errors
**Patterns**: `ImportError`, `ModuleNotFoundError`, `cannot import`
**Common Causes**:
- Missing dependencies
- Incorrect import paths
- PYTHONPATH issues

**Troubleshooting**:
```bash
# Check if module exists
uv run python -c "import src.flows.my_flow.app"

# Verify deployment configuration
grep -A 5 "my-flow" config.yaml

# Check PYTHONPATH
echo $PYTHONPATH
```

### Category 2: Neo4j Connection Errors
**Patterns**: `ServiceUnavailable`, `AuthError`, `Neo4j`, `bolt://`
**Common Causes**:
- Neo4j not running
- Wrong credentials
- Connection timeout

**Troubleshooting**:
```bash
# Check Neo4j status
docker ps | grep neo4j

# Test connection
docker logs neo4j | tail -20

# Verify credentials in .env
grep NEO4J .env
```

### Category 3: Validation Errors
**Patterns**: `InputsError`, `ValidationError`, `invalid`, `required`
**Common Causes**:
- Missing required form fields
- Invalid input values
- Type mismatches

**Troubleshooting**:
- Review form validation logic in app.py
- Check InputsError messages
- Verify form field names match validation

### Category 4: Memory/Resource Errors
**Patterns**: `OutOfMemoryError`, `ObjectStoreFullError`, `resource`
**Common Causes**:
- Insufficient Ray actor memory
- Too many large objects in Ray store
- Memory leaks

**Troubleshooting**:
```bash
# Check Ray cluster resources
uv run --active ray status

# Review memory allocation in config.yaml
grep -A 3 "ray_actor_options" config.yaml
```

### Category 5: Deployment/Configuration Errors
**Patterns**: `Failed to deploy`, `ServeDeploymentError`, `config`
**Common Causes**:
- Invalid config.yaml syntax
- Missing environment variables
- Port conflicts

**Troubleshooting**:
```bash
# Validate YAML syntax
uv run python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Check for missing env vars
just sync-config

# Check Ray serve status
uv run --active serve status
```

### Category 6: Runtime/Execution Errors
**Patterns**: `KeyError`, `AttributeError`, `TypeError`, `IndexError`
**Common Causes**:
- Logic errors in processor
- Missing data handling
- Incorrect assumptions

**Troubleshooting**:
- Review traceback for exact line number
- Check processor logic at error location
- Verify input data structure

## Response Format

When presenting log analysis results, use this format:

```markdown
## 🔍 Ray Log Analysis

**Context**: [What triggered this analysis]
**Time Range**: [Last N lines/minutes]

### 🔴 Errors Found: [N]

#### Error 1: [Error Type]
**Source**: [Flow/Service name]
**Message**: [Error message]
**Traceback**: [Key lines from traceback]

**Root Cause**: [Likely cause]
**Fix**: [Specific actionable steps]

#### Error 2: ...

### ⚠️ Warnings: [N]
[Similar format]

### 💡 Recommended Actions

1. [Immediate fix for critical error]
2. [Verification step]
3. [Prevention for future]

### 🔗 Additional Commands

- Full logs: `uv run --active ray logs | less`
- Flow status: `just status`
- Restart: `just deploy-all`
```

## Examples

### Example 1: Import Error Detection
**User**: "My bundestag_person flow isn't working"

**Claude Action**:
```bash
# Step 1: Find the replica log
ls /tmp/ray/session_latest/logs/serve/ | grep replica.*bundestag-person

# Step 2: Check replica log for errors
tail -50 /tmp/ray/session_latest/logs/serve/replica_flow5a-bundestag-person_*.log

# Step 3: Check worker errors
grep -l "bundestag-person" /tmp/ray/session_latest/logs/worker*.err | xargs tail -20
```

**Analysis**:
```
Found in worker-*.err: ImportError: cannot import name 'BundestagPersonManager'

Root Cause: Missing or renamed class in manager.py
Fix:
1. Check src/flows/bundestag_person/app.py import statement
2. Verify class exists in manager.py
3. Redeploy: just deploy-all
```

### Example 2: Neo4j Connection Issue
**User**: "Flow failed with database error"

**Claude Action**:
```bash
uv run --active ray logs | grep -iE "(neo4j|serviceun available)" -C 5
```

**Analysis**:
```
Found: Neo4j.exceptions.ServiceUnavailable: Connection refused

Root Cause: Neo4j container not running
Fix:
1. Start Neo4j: docker compose up -d neo4j
2. Wait 10 seconds for startup
3. Verify: docker ps | grep neo4j
4. Retry flow
```

### Example 3: Validation Error
**User**: "Getting validation error when submitting form"

**Claude Action**:
```bash
uv run --active ray logs | grep -i "InputsError\|ValidationError" -C 3
```

**Analysis**:
```
Found: InputsError: job_name - Job name must be at least 3 characters

Root Cause: Form validation requires job_name ≥ 3 characters
Fix:
1. Provide longer job name in form
2. Or adjust validation in app.py if requirement is wrong
```

## Integration with Other Skills

This skill works together with:
- **Deployment Status Skill**: Check if services are running
- **Flow Health Skill**: Verify flow configuration
- **Neo4j Status Skill**: Check database connectivity
- **Config Validation Skill**: Verify configuration files

## Success Metrics

- ✅ Identify error within 30 seconds of invocation
- ✅ Provide specific fix (not generic advice)
- ✅ Include relevant log excerpts (not full dumps)
- ✅ Suggest verification steps after fix
- ✅ Prevent repeated errors with recommendations

## Understanding Log Types

### Replica Logs (Flow Application Logs)
**Location**: `/tmp/ray/session_latest/logs/serve/replica_<flow-name>_*.log`

**Contains**:
- HTTP request logs (GET, POST with status codes and timing)
- Replica initialization/shutdown
- Application-level info from your flow code
- Request IDs for tracing

**When to use**: Troubleshooting HTTP requests, request routing, replica health

**Example log entry**:
```
INFO 2025-11-17 15:38:44,506 flow5d-bundestag-plenarprotokoll_BundestagPlenarprotokollFlow npkj3mku d902e6bf-8b7b-4059-a044-61c45996bce4 -- POST /bundestag-plenarprotokoll/ 200 173.9ms
```

### Worker Logs (Actor Execution Logs)
**Location**: `/tmp/ray/session_latest/logs/worker-<id>.{out,err}`

**Contains**:
- Python print() statements (in .out)
- Python exceptions and tracebacks (in .err)
- Actor names and job IDs
- Low-level Ray task execution

**When to use**: Debugging Python exceptions, tracing print statements, actor crashes

**Finding the right worker**:
```bash
# Find worker for specific flow
grep -l "ServeReplica:flow5d-bundestag-plenarprotokoll" /tmp/ray/session_latest/logs/worker*.out

# Check worker errors
tail -50 /tmp/ray/session_latest/logs/worker-<id>.err
```

### Controller Logs (Deployment Management)
**Location**: `/tmp/ray/session_latest/logs/serve/controller_*.log`

**Contains**:
- Deployment status changes
- Replica scaling events
- Application deployment/deletion
- Serve controller errors

**When to use**: Troubleshooting deployment failures, replica management issues

## Limitations

- Cannot access logs older than Ray session (cleared on restart)
- `session_latest` is a symlink - points to current session directory
- Some flows may log to separate files (check logs/ directory)
- Real-time streaming not available (use Ray Dashboard for that)
- Truncated output if logs are very large
- Worker log filenames are hashed - need to search by content

## Best Practices

1. **Start with error search** - Most issues show clear error messages
2. **Check timestamps** - Ensure errors are recent and relevant
3. **Read tracebacks bottom-up** - Root cause is usually at the bottom
4. **Correlate with actions** - Match errors to recent deployments/changes
5. **Verify fixes** - Always suggest running `just status` after fix

## Continuous Improvement

As new error patterns emerge:
1. Document the pattern here
2. Add to error recognition categories
3. Include troubleshooting steps
4. Update examples with real cases

## Quick Reference: Common Commands

### Flow Troubleshooting Cheat Sheet

```bash
# 1. Find all flow replica logs
ls /tmp/ray/session_latest/logs/serve/replica*

# 2. Check specific flow (replace flow5d-bundestag-plenarprotokoll)
tail -50 /tmp/ray/session_latest/logs/serve/replica_flow5d-bundestag-plenarprotokoll_*.log

# 3. Search for errors in flow
grep -iE "(error|exception)" /tmp/ray/session_latest/logs/serve/replica_flow5d-*

# 4. Find worker for specific flow
grep -l "ServeReplica:flow5d" /tmp/ray/session_latest/logs/worker*.out

# 5. Check worker errors
tail -50 /tmp/ray/session_latest/logs/worker-*.err | grep -iE "(error|exception)" -C 3

# 6. Check all serve errors
grep -r "ERROR" /tmp/ray/session_latest/logs/serve/

# 7. Check controller for deployment issues
tail -50 /tmp/ray/session_latest/logs/serve/controller_*.log

# 8. Recent Ray logs (aggregated)
uv run --active ray logs | tail -100

# 9. Search all logs for pattern
grep -r "Neo4j" /tmp/ray/session_latest/logs/ | tail -20

# 10. Monitor logs in real-time
tail -f /tmp/ray/session_latest/logs/serve/replica_<flow-name>_*.log
```

### Log Location Decision Tree

```
Issue with flow not starting?
└─> Check controller logs: logs/serve/controller_*.log

Issue with HTTP requests (404, 500)?
└─> Check replica logs: logs/serve/replica_<flow-name>_*.log

Python exception/traceback?
└─> Check worker stderr: logs/worker-*.err

Missing print() output?
└─> Check worker stdout: logs/worker-*.out

Deployment failing?
└─> Check: uv run --active ray logs | grep -i error

Flow running but producing wrong results?
└─> Check replica + worker logs for your specific flow
```

---

**Version**: 1.1
**Created**: 2025-11-17
**Updated**: 2025-11-17 (Added Ray log structure details)
**Status**: Active - Claude can invoke autonomously
