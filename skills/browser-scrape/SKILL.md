---
name: browser-scrape
description: Extract structured data, clean reader-mode markdown, search results, and batch-fill forms via agents-browser MCP without writing custom ad-hoc scraping scripts. Runs headless by default.
---

# Browser Scrape & Search Skill

Use this skill for web information retrieval, structured table extraction, search queries, and form automation.

**Headless is default.** Do not call `visible=True` or `browser_system_open` unless the human explicitly asks for a desktop window.

## High-Level Operations

1. **Direct Web Search**:
   - `browser_search(query="python packaging guide")`
   - Returns top organic results with Title, URL, and Snippet in one call.

2. **Clean Article Reader Mode**:
   - `browser_read_article()`
   - Removes navbars, headers, footers, ads, and sidebars. Returns clean markdown article content.

3. **Structured Selector Scraping**:
   - `browser_scrape(selector="table.stats", mode="table")` $\rightarrow$ Markdown table
   - `browser_scrape(selector=".doc-links", mode="links")` $\rightarrow$ Link list
   - `browser_scrape(selector="main", mode="text")` $\rightarrow$ Clean text

4. **Batch Form Filling**:
   - `browser_fill_form(fields_json='{"@1": "admin", "@2": "password123"}', submit_selector="@3")`
