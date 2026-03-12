# Digital Labour PRD

## Tasks

- [ ] Add health check tests: create tests/test_health.py that hits /health and /v1/agents endpoints, asserts 200 and correct JSON structure
- [ ] Add agent dispatch tests: create tests/test_dispatch.py that tests route_task for all 24 agent types
- [ ] Add input validation to /v1/run: validate task_type is one of 24 known types, description is non-empty, return 422 on bad input
- [ ] Add rate limiting middleware to api/rapidapi.py: 100 requests per minute per IP using in-memory counter
- [ ] Add structured logging: replace print() calls in automation/nerve.py and automation/orchestrator.py with logging module
- [ ] Add /v1/errors endpoint in api/rapidapi.py that returns last 50 errors from a deque buffer
- [ ] Add agent execution metrics: track call count and avg response time per agent in dispatcher/router.py, expose via /v1/metrics
- [ ] Add smoke test for all agents: create tests/test_agents_smoke.py that imports every agent module and verifies run() exists
- [ ] Add HEALTHCHECK instruction to Dockerfile that curls /health
- [ ] Ensure FastAPI /docs is accessible and all endpoints have docstrings
