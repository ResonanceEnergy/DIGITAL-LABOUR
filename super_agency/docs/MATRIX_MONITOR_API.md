# Matrix Monitor API

The `/api/matrix-monitor` endpoint provides a consolidated status of the
various monitoring subsystems.  It is intended to be consumed by the web
interface and mobile clients.

## Response schema
Refer to [matrix_monitor_schema.json](./matrix_monitor_schema.json) for
an official JSON Schema.

### Fields
- `timestamp` – ISO‑8601 time of generation
- `project_selector` – object describing repository rankings
- `qusar_sync` – availability/status of the Quantum Quasar synchronization
- `global_network` – high‑level information about the intelligence network
- `decision_optimizer` – available models in the decision optimizer
- `matrix_monitor_status` – `active`/`degraded`/`error`
- `errors` – optional list of human-readable errors encountered while
  gathering data

## Caching & performance
The endpoint caches results for 30 seconds and will return the last value if
called more frequently.  This improves responsiveness when multiple clients
poll rapidly.

## Legacy aliases
To maintain compatibility with clients developed prior to consolidation, the
following endpoints are still served:

- `/api/agents/status` → returns same as `/api/agents`
- `/api/system/metrics` → returns same as `/api/system`

Clients should migrate to the consolidated APIs where possible.
