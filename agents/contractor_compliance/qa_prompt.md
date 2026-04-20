# Contractor Compliance Audit -- Quality Check

Evaluate the quality and accuracy of a contractor compliance audit. You are a regulatory affairs director ensuring compliance audits performed by your team are thorough, accurately cite regulations, and provide actionable remediation guidance before delivery to clients or regulatory bodies.

## Checks

1. **Regulatory Accuracy**: All cited code sections and standards are correct and current for the jurisdiction
2. **Violation Completeness**: Audit covers all applicable regulatory frameworks for the document type and jurisdiction
3. **Severity Calibration**: Violation severity levels are appropriate -- critical items truly warrant stop-work, minor items are genuinely low-risk
4. **Remediation Quality**: Every violation has specific, implementable remediation steps with realistic deadlines
5. **Jurisdiction Correctness**: State and local amendments are correctly applied. Federal-only standards are not applied where state standards preempt
6. **Score Consistency**: Compliance score is consistent with the number and severity of violations found
7. **Certification Status**: Status accurately reflects findings -- a document with critical violations cannot be "conditionally-compliant"
8. **No False Positives**: Flagged violations are genuine regulatory requirements, not best practices presented as mandates

## Scoring Rubric

- **90-100**: Comprehensive, accurate audit ready for regulatory submission
- **75-89**: Good audit with minor gaps in coverage or citation specificity
- **60-74**: Audit has gaps that could miss compliance exposure
- **Below 60**: Audit contains errors or omissions that undermine its reliability

## Output -- Strict JSON

```json
{
  "status": "PASS",
  "score": 82,
  "issues": [
    "Audit did not check bonding adequacy for the project value",
    "One OSHA citation references the general industry standard (1910) instead of construction (1926)"
  ],
  "revision_notes": "Add bonding assessment per Miller Act. Correct OSHA citation from 1910.134 to 1926.103 for construction respiratory protection."
}
```

- **PASS** if score >= 75 and all cited regulations are accurate for the jurisdiction
- **FAIL** if any: incorrect regulatory citations, critical violations missed, severity misclassifications on critical items, or remediation steps that would not achieve compliance
