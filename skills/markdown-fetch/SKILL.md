---
name: markdown-fetch
description: Fetch web content as clean markdown using Cloudflare's markdown.new service. Use this whenever you need to read HTML content from any website - it automatically converts pages to markdown for easier processing.
---

# Markdown Fetch

This skill uses Cloudflare's `markdown.new` service to fetch any web page as clean markdown instead of raw HTML.

## How It Works

Instead of fetching a URL directly, prepend `https://markdown.new/` to the target URL. The service automatically:
- Fetches the original page
- Strips unnecessary HTML, scripts, and styling
- Returns clean, readable markdown

## Usage

When you need to fetch content from a website, ALWAYS use this pattern:

```
Original URL: https://example.com/article
Markdown URL: https://markdown.new/https://example.com/article
```

## Example

To read content from `https://margaretstorey.com/blog/2026/02/09/cognitive-debt/`:

Use WebFetch with:
- URL: `https://markdown.new/https://margaretstorey.com/blog/2026/02/09/cognitive-debt/`
- Prompt: Extract the main content (or whatever analysis you need)

## When to Use

- Fetching blog posts or articles
- Reading documentation pages
- Extracting content from any HTML page
- When you need clean text without HTML noise

## Benefits

- Cleaner output than raw HTML
- Smaller response size (no scripts/styles)
- Better for text analysis and summarization
- Works with most public websites
