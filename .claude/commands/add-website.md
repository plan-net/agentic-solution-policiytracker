# Add Website Command

Analyze a website and generate configuration for the Political Monitoring Agent's website discovery pipeline.

**Input**: Website URL (e.g., `$ARGUMENTS` or ask user if not provided)

## Steps

1. **Validate the input URL**
   - Ensure a valid URL was provided
   - Extract the base domain (e.g., `example.de` from `https://www.example.de/path`)

2. **Discover RSS Feeds**
   - Fetch the main page and look for RSS/Atom feed links in `<link>` tags
   - Check common RSS feed paths:
     - `/feed`, `/feed.xml`, `/rss`, `/rss.xml`
     - `/feeds/all.rss.xml`, `/atom.xml`
     - `/service/rss/`, `/rss/feed.xml`
   - For each discovered feed, verify it returns valid XML
   - Note the feed category/type if identifiable from URL or content

3. **Check for Sitemap**
   - Look for `robots.txt` and extract sitemap URLs
   - Check common sitemap locations:
     - `/sitemap.xml`, `/sitemap_index.xml`
     - `/sitemaps/sitemap.xml`
   - Identify if sitemap contains news/article sections

4. **Analyze Website Structure**
   - Identify the main content sections (news, press releases, articles)
   - Look for common URL patterns for articles (e.g., `/aktuelles/`, `/news/`, `/presse/`)
   - Detect the primary language (de, en, etc.)
   - Note any pagination patterns

5. **Generate YAML Configuration**
   - Create a properly formatted YAML block for `websites.yaml`
   - Use the following template structure:

```yaml
# [Website Name]
website_key:
  domain: [extracted domain]
  name: "[Full Website Name]"
  language: [detected language, default: de]
  enabled: true
  discovery_strategies:
    # RSS Feed Discovery (if feeds found)
    - type: rss
      priority: 1
      config:
        feeds:
          - url: [feed URL]
            category: [feed category]
        check_interval: 3600
        max_age_days: 30

    # Sitemap Discovery (if sitemap found)
    - type: sitemap
      priority: 2
      config:
        sitemap_url: [sitemap URL]
        url_patterns:
          - "[article URL pattern]"
        check_interval: 86400
        max_urls_per_run: 100

    # Web Scraping (as fallback)
    - type: scraper
      priority: 3
      config:
        start_urls:
          - [main content section URL]
        content_selectors:
          article: "article, .article, .content"
          title: "h1, .title, .headline"
          date: "time, .date, .published"
        max_depth: 2
        max_pages: 50
```

6. **Output Results**
   - Display the generated YAML configuration
   - List all discovered RSS feeds with their URLs and categories
   - Show sitemap location if found
   - Provide recommendations for the best discovery strategy
   - Ask if the user wants to append this configuration to `src/etl/config/websites.yaml`

7. **Optional: Append to websites.yaml**
   - If user confirms, append the configuration to the websites.yaml file
   - Place it in the appropriate section based on the website type (government, political party, news, etc.)

## Example Output

```
🔍 Analyzing website: https://www.example-ministry.de

📡 RSS Feeds Found:
  ✅ https://www.example-ministry.de/rss/news.xml (news)
  ✅ https://www.example-ministry.de/rss/press.xml (press releases)

🗺️ Sitemap:
  ✅ https://www.example-ministry.de/sitemap.xml

📝 Generated Configuration:
[YAML block here]

💡 Recommendations:
  - Primary strategy: RSS feeds (2 feeds found)
  - Backup strategy: Sitemap for historical content
  - Language: German (de)

Would you like me to add this configuration to websites.yaml? (yes/no)
```

Use WebFetch and WebSearch tools to analyze the website. Provide clear status updates with emojis (🔍, ✅, ❌, 📡, 🗺️, 📝, 💡) throughout the process.
