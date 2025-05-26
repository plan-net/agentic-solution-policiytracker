# Langfuse & Prompt Management Patterns

## Prompt Management Strategy
1. **Langfuse-first**: Always try Langfuse before local files
2. **Local fallback**: Use markdown files with frontmatter if Langfuse unavailable
3. **Memory caching**: Cache prompts after first load

## Prompt File Format
```markdown
---
name: prompt_name
version: 1
description: What this prompt does
tags: ["analysis", "core"]
---

# Actual prompt content here
Use {{variable}} for substitution
```

## Key Patterns
- Upload prompts: `just upload-prompts`
- Prompts live in `/src/prompts/*.md`
- Use PromptManager.get_prompt() with fallback handling
- Variable substitution with {{variable_name}}

## Langfuse Setup
1. Start services: `just services-up`
2. Access http://localhost:3001
3. Create project and get API keys
4. Update .env with real keys
5. Upload prompts: `just upload-prompts`

## Observability
- Use @observe decorator for LLM operations
- Track with proper generation names
- Include metadata for debugging