## Escalation Rules — Support Resolver Agent
### Hard-Coded Policy (Non-Negotiable)

These rules override agent judgment. If ANY condition is met, escalation.required = true.

### ALWAYS ESCALATE:
1. **Refund / chargeback threat** → team: billing
2. **Legal threat** → team: legal
3. **Security or privacy concern** → team: engineering
4. **Critical outage claim** → team: engineering
5. **Account access compromise** → team: engineering
6. **3+ previous contacts on same issue** → team: management
7. **Agent confidence < 0.6** → team: support (senior)
8. **Customer requests to speak to a human/manager** → team: management

### NEVER ESCALATE:
- Routine questions answerable from KB
- Feature requests (log them, don't escalate)
- General feedback / compliments

### ESCALATION FORMAT:
```json
{
  "required": true,
  "reason": "specific trigger from list above",
  "team": "support|engineering|billing|legal|management"
}
```
