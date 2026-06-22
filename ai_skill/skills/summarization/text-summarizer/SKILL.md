---
name: Text Summarizer
description: Summarize long texts and articles using the web_fetch tool.
---

Use the `web_fetch` tool to summarize content from URLs.

## How to summarize

### Fetch article text (via Plain Text API):

```
web_fetch(url="https://r.jina.ai/http://example.com/long-article")
```

This returns clean markdown text stripped of HTML.

### Alternative: Mercury Parser (via webxdc):

```
web_fetch(url="https://mercury.postlight.com/parser?url=http://example.com/long-article")
```

## Instructions

1. When the user provides a URL, fetch the article content first
2. Then present a concise summary covering the key points
3. If the user asks in a specific format (bullet points, single paragraph), follow that
4. Always mention the source URL in the summary
