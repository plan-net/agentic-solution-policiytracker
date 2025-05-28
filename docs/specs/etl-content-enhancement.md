# ETL Content Enhancement - Addressing Missing Article Content

## Current Issue
The Apify actor `eWUEW5YpCaCBAa0Zs` only returns RSS metadata, not full article content, despite `fetchArticleDetails: True`.

## Solutions Overview

### Option 1: Use Full Content Scraping Actor ✅ RECOMMENDED
Replace with Apify's web scraper that fetches full content:

```python
# In apify_news.py
ACTOR_ID = "apify/web-scraper"  # Full content scraper

run_input = {
    "startUrls": [{"url": f"https://news.google.com/search?q={query}"}],
    "pageFunction": """
        async function pageFunction(context) {
            const { page, request } = context;
            const title = await page.$eval('h1', el => el.textContent);
            const content = await page.$eval('article', el => el.textContent);
            return {
                title,
                content,
                url: request.url
            };
        }
    """,
    "maxConcurrency": 5
}
```

### Option 2: Two-Step Process (Current + Content Fetch)
Keep current RSS actor for discovery, add content fetching:

```python
async def fetch_full_content(self, url: str) -> str:
    """Fetch full article content from URL."""
    try:
        # Use newspaper3k, beautifulsoup, or another scraper
        from newspaper import Article
        
        article = Article(url)
        article.download()
        article.parse()
        
        return article.text
    except Exception as e:
        logger.warning(f"Failed to fetch content from {url}: {e}")
        return ""
```

### Option 3: Accept RSS Headlines Only
Use current setup for trend monitoring rather than full content analysis.

## Improved Markdown Format ✅ IMPLEMENTED

**Before (redundant):**
```markdown
---
title: Article Title
url: https://example.com
source: Source Name
---

# Article Title

## Article Information
**Source:** Source Name
**URL:** https://example.com

## Content
*Content not available*
```

**After (clean):**
```markdown
---
title: Article Title
url: https://example.com
source: Source Name
---

# Article Title

Article description/summary here...

**Note:** Full content not available. RSS headline only.
📰 **Read full article:** [Link](https://example.com)
```

## Implementation Plan

### Phase 1: Test Alternative Actors ⏳
```bash
# Test different Apify actors for full content
curl -X POST "https://api.apify.com/v2/acts/apify~web-scraper/runs"
```

### Phase 2: Implement Content Fetching ⏳
Add newspaper3k or similar library to fetch full content:
```bash
uv add newspaper3k
```

### Phase 3: Content Quality Assessment ⏳
- Compare content quality between actors
- Measure processing time vs content value
- Assess impact on Flow 1 entity extraction

## Trade-offs

| Approach | Pros | Cons |
|----------|------|------|
| RSS Only | Fast, reliable, low cost | Limited content for analysis |
| Full Scraper | Complete content | Slower, higher cost, fragile |
| Two-step | Best of both | Complex, dual points of failure |

## Recommendation

**Start with Option 2 (Two-step)** for maximum flexibility:
1. Keep current RSS discovery for trends
2. Add selective full content fetching for high-priority articles
3. Let Flow 1 processing determine which articles need full content

This provides both speed and depth when needed.