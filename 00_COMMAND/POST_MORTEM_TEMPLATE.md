# POST-MORTEM TEMPLATE  
**Doctrine Version:** 2.0  
**Severity:** P0 / P1 / P2 / P3 *(circle one)*

---

## 1. Incident Summary

| Field | Value |
|---|---|
| **Incident ID** | _INC-YYYY-MM-DD-NNN_ |
| **Date / Time (UTC)** | _YYYY-MM-DD HH:MM_ |
| **Duration** | _X hours Y minutes_ |
| **Severity** | _P0 / P1 / P2 / P3_ |
| **Affected Agent(s)** | _agent_name_ |
| **Lineage IDs** | _uuid, uuid, …_ |
| **Author** | _Name_ |

---

## 2. Impact

- **Client(s) affected:** 
- **Tasks disrupted / failed:** 
- **Revenue at risk (USD):**  
- **Data exposure:** Yes / No

---

## 3. Timeline

| Time (UTC) | Event |
|---|---|
| HH:MM | First alert / detection |
| HH:MM | Incident owner assigned |
| HH:MM | Root cause identified |
| HH:MM | Mitigation applied |
| HH:MM | Service restored |

---

## 4. Root Cause

> Describe the root cause in 2–3 sentences. Be precise — name the file, function, and line.

**File:** `path/to/file.py`  
**Function:** `function_name()`  
**Failure mode from registry:** _(e.g., llm_timeout, schema_violation, qa_fail)_

---

## 5. Contributing Factors

1. 
2. 
3. 

---

## 6. Resolution

### Immediate fix
> What was done to stop the bleeding?

### Root-cause fix
> What code / config change prevents recurrence?

**Commit:** `git sha`

---

## 7. What Went Well

- 
- 

## 8. What Went Poorly

- 
- 

---

## 9. Action Items

| # | Action | Owner | Due Date | Status |
|---|---|---|---|---|
| 1 | | | | Open |
| 2 | | | | Open |

---

## 10. Doctrine Update Required?

- [ ] Yes — open PR to update `00_COMMAND/DOCTRINE_CHANGELOG.md`
- [ ] No

---

*Template version: BRS 2.0 — `00_COMMAND/POST_MORTEM_TEMPLATE.md`*
