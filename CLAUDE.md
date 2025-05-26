# Political Monitoring Agent v0.1.0

AI-powered document analysis system for political and regulatory monitoring.

## Project Context
- **Purpose**: Analyze political documents for relevance, priority, and topic clustering
- **Stack**: Kodosumi v0.9.2 + Ray + LangGraph + Azure Storage + Langfuse
- **Python**: 3.12.6 (strict requirement)

## Key Instructions
1. Read specifications in `/docs/specs/` before making changes
2. Follow two-file Kodosumi pattern: `src/app.py` + `src/political_analyzer.py`
3. Check existing code patterns before creating new files
4. Run `just format && just typecheck` before committing
5. Version is 0.1.0 - ensure consistency across all files

## Architecture & Patterns
@.claude/kodosumi-patterns.md
@.claude/azure-integration.md
@.claude/langfuse-prompts.md
@.claude/testing-standards.md
@.claude/development-workflow.md
@.claude/git-workflow.md

## Project-Specific Details
@.claude/project-architecture.md

## Quick Reference
- **Admin Panel**: http://localhost:3370 (admin/admin)
- **Main Commands**: `just dev`, `just dev-quick`, `just test`
- **Logs**: `just kodosumi-logs`
- **Custom Commands**: `/deploy`, `/status`, `/test [scope]`