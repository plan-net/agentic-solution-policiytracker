# Documentation

This directory contains user-facing documentation for the Political Monitoring Agent v0.2.0.

## 🚨 Recent Critical Fixes & Features (2026-01-29)

### Agent Runtime Crash Fix
**Resolved intermittent failures where tools execute but no output is returned.**

- 📖 **[Full Documentation](./AGENT_RUNTIME_FIX.md)** - Complete technical guide
- ⚡ **[Quick Reference](./AGENT_FIX_QUICK_REFERENCE.md)** - TL;DR and deployment
- 📝 **[Changelog](../CHANGELOG_AGENT_FIX.md)** - Version history

**Start here if deploying the fix**: [Quick Reference](./AGENT_FIX_QUICK_REFERENCE.md)

### Query Decomposition Feature
**Automatic complexity analysis and guidance for handling complex multi-faceted queries.**

- 📖 **[Full Documentation](./QUERY_DECOMPOSITION.md)** - Feature guide and examples
- 🎯 **[Max Turns Analysis](./AGENT_MAX_TURNS_ANALYSIS.md)** - The issue that led to this feature

**Key Benefits**: Prevents incomplete responses, improves quality, transparent complexity tracking

### Weekly Report Agent Fix
**Same runtime crash fixes applied to the weekly report generation agent.**

- 📖 **[Full Documentation](./WEEKLY_REPORT_AGENT_FIX.md)** - Complete fix guide
- ✅ **Includes**: Enhanced error handling, response validation, increased max_turns (30→50), query decomposition

**Key Benefits**: No more silent failures, graceful error messages, sufficient turns for comprehensive reports

---

## 📚 Available Guides

### [USER_GUIDE.md](USER_GUIDE.md)
**For business users, analysts, and decision makers**
- Complete system overview and business use cases
- Step-by-step instructions for document analysis
- Understanding results and reports
- Automated data collection guidance
- Best practices and limitations

### [SETUP.md](SETUP.md) 
**For administrators and developers**
- Complete installation and configuration guide
- Docker setup and service configuration
- Open WebUI chat interface setup
- Environment variables and authentication
- Troubleshooting common setup issues

### [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
**For daily operators and developers**
- Essential commands cheat sheet
- Service URLs and access credentials
- Key directories and configuration files
- Common tasks and troubleshooting tips

## 🔗 Related Documentation

- **Component Documentation**: See `README.md` files in each `/src/` subdirectory
- **Development Patterns**: See pattern files in `/.claude/` directory
- **API Documentation**: Available at service endpoints when running