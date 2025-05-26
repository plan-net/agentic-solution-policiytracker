# Git Workflow & Version Control Patterns

## Branch Strategy (Git Flow)

### Branch Types
- **main**: Production-ready code only
- **develop**: Integration branch for features
- **feature/***: New features and enhancements
- **release/***: Release preparation
- **hotfix/***: Emergency production fixes

### Branch Naming
```
feature/add-export-functionality
feature/improve-scoring-algorithm
release/0.2.0
hotfix/fix-azure-connection-timeout
```

## Development Workflow

### Starting New Features
```bash
# Always start from develop
git checkout develop
git pull origin develop
git checkout -b feature/description-of-feature

# Work on feature...
# Commit frequently with meaningful messages
```

### Feature Complete
```bash
# Update from develop before merging
git checkout develop
git pull origin develop
git checkout feature/your-feature
git merge develop

# Push and create PR
git push origin feature/your-feature
# Create PR from feature → develop
```

## Commit Message Format
```
type: subject (max 50 chars)

Optional body explaining why this change was made.
Focus on the why, not the what (code shows what).

Footer with issue references
```

### Types
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style (formatting, missing semicolons, etc)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Maintenance tasks
- **perf**: Performance improvements

### Examples
```
feat: add PDF export functionality for reports

fix: resolve Azure timeout on large file uploads

docs: update API documentation for v0.2.0

refactor: extract scoring logic into separate module
```

## Release Process

### Creating a Release
```bash
# Start from develop
git checkout develop
git pull origin develop
git checkout -b release/0.2.0

# Update version numbers
# Update CHANGELOG.md
# Run final tests

# Merge to main
git checkout main
git merge --no-ff release/0.2.0
git tag -a v0.2.0 -m "Release version 0.2.0"
git push origin main --tags

# Back-merge to develop
git checkout develop
git merge --no-ff release/0.2.0
git push origin develop

# Delete release branch
git branch -d release/0.2.0
```

### Hotfix Process
```bash
# Start from main
git checkout main
git pull origin main
git checkout -b hotfix/fix-critical-bug

# Fix the issue
# Update version (e.g., 0.1.0 → 0.1.1)

# Merge to main
git checkout main
git merge --no-ff hotfix/fix-critical-bug
git tag -a v0.1.1 -m "Hotfix version 0.1.1"
git push origin main --tags

# Merge to develop
git checkout develop
git merge --no-ff hotfix/fix-critical-bug
git push origin develop
```

## Version Management

### Semantic Versioning
Follow MAJOR.MINOR.PATCH:
- **MAJOR**: Breaking changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes

### Version Updates
When creating a release, update version in:
- `pyproject.toml`
- `src/app.py` (both places)
- `README.md` title
- `CLAUDE.md` header

## Pull Request Guidelines

### PR Title Format
Same as commit messages: `type: description`

### PR Description Template
```markdown
## Summary
Brief description of changes

## Motivation
Why these changes are needed

## Changes
- List of specific changes
- Include screenshots if UI changes

## Testing
How to test these changes

## Checklist
- [ ] Tests pass (`just test`)
- [ ] Code formatted (`just format`)
- [ ] Type checks pass (`just typecheck`)
- [ ] Documentation updated
- [ ] Version bumped (if release)
```

## Git Commands Reference

### Useful Aliases
```bash
# Show branch graph
git log --graph --oneline --all

# Show changes in staging
git diff --staged

# Amend last commit (before push)
git commit --amend

# Interactive rebase (clean history)
git rebase -i HEAD~3
```

### Safety Rules
- Never force push to main or develop
- Always create PRs for code review
- Delete feature branches after merge
- Tag all releases with version number
- Keep commits atomic and focused