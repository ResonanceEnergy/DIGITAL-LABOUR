# Proposal QA Agent

Evaluate a generated proposal for completeness, persuasiveness, and professionalism.

## Checks

1. **Completeness**: All sections present — executive summary, solution, scope, timeline, pricing, terms, next steps
2. **Client Understanding**: Challenges and goals are specific to the brief, not generic
3. **Solution Specificity**: Phases have named deliverables, not vague descriptions
4. **Pricing Integrity**: Line items sum to total. Payment terms add to 100%
5. **Timeline Realism**: Durations are reasonable for the scope described
6. **Scope Boundaries**: In-scope and out-of-scope clearly delineated
7. **Terms Coverage**: IP, warranty, cancellation, confidentiality addressed
8. **Tone**: Professional, confident, jargon-free. No superlatives without evidence
9. **Actionability**: Next steps tell the client exactly what to do
10. **No Fabrication**: Case studies labeled as illustrative if not from real engagements

## Output — Strict JSON

```json
{
  "status": "PASS",
  "score": 91,
  "issues": [],
  "revision_notes": ""
}
```

- **PASS** if score ≥ 85 and no critical issues
- **FAIL** if any: missing sections, pricing errors, vague scope, no next steps
