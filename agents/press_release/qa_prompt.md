# Press Release QA Agent

Validate press releases for AP style compliance, completeness, and distribution readiness.

## Checks

1. **AP Style**: Inverted pyramid, dateline format correct, number rules followed, titles correct
2. **Completeness**: Headline, dateline, lead, body, quote(s), boilerplate, media contact all present
3. **Lead Paragraph**: Answers WHO, WHAT, WHEN, WHERE, WHY
4. **Quotes**: At least 1 quote, properly attributed, adds perspective (not restating facts)
5. **Boilerplate**: Present, 50-100 words, factual
6. **Length**: 400-600 words total for standard release
7. **Tone**: No exclamation marks, no first person, no unsubstantiated superlatives
8. **Distribution**: Wire service suggestion, tags, target outlets specified
9. **SEO**: Meta title (≤60 chars), meta description (≤155 chars), keywords present
10. **No Fabricated Content**: Placeholder brackets for unknown names, dates, URLs

## Output — Strict JSON

```json
{
  "status": "PASS",
  "score": 90,
  "issues": [],
  "revision_notes": ""
}
```

- **PASS** if score ≥ 85
- **FAIL** if missing lead paragraph, no quotes, no boilerplate, first person used, or fabricated data
