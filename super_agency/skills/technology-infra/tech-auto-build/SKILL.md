# SKILL: tech-auto-build
## Autonomous Build Pipeline

Combines OpenClaw code generation with QForge optimization to create a
fully autonomous build pipeline. From natural language specification to
tested, deployed code — zero human intervention required.

### Triggers
- Manual: "build [feature]", "create [component]", "implement [spec]"
- Event: STATE.yaml milestone marked "ready for implementation"
- Event: REPO DEPOT identifies code pattern needing refactor
- Cron: Nightly regression build across all repos

### What It Does
1. Accepts feature specification (natural language or structured)
2. Decomposes into implementation tasks (files, functions, tests)
3. Generates code using OpenClaw's code generation capabilities
4. Runs test suite against generated code
5. If tests fail: analyzes failures, iterates on code (up to 5 cycles)
6. On success: creates PR with full description and test results
7. QForge optimizes generated code for performance
8. Notifies requesting agent/department of completion

### Build Pipeline Stages
```
Specification (NL or structured)
  ↓
Task Decomposition (OpenClaw analyzes scope)
  ↓
Code Generation (OpenClaw + context from NCL knowledge base)
  ↓
Testing (pytest / jest / cargo test)
  ↓ fail? → iterate (max 5 cycles)
QForge Optimization (performance pass)
  ↓
PR Creation (GitHub API)
  ↓
Review Assignment (route to appropriate agent)
  ↓
Auto-Merge (if CI passes + agent approves)
```

### Integration Points
| System | Role in Pipeline |
|---|---|
| OpenClaw | Code generation + iteration |
| QForge | Performance optimization |
| NCL Knowledge Base | Context for code generation (existing patterns) |
| REPO DEPOT | Repo selection, branch management |
| GitHub Actions | CI/CD execution |
| Matrix Monitor | Build performance tracking |
| STATE.yaml | Progress tracking per milestone |

### Output Format
```
AUTO-BUILD REPORT — [feature name]

Specification: "Add WebSocket support to Matrix Monitor dashboard"
Decomposed into: 4 files, 12 functions, 8 tests

Build Cycles:
  Cycle 1: Generated code → 6/8 tests passed → 2 failures analyzed
  Cycle 2: Fixed WebSocket handler → 7/8 tests passed
  Cycle 3: Fixed event serialization → 8/8 tests passed ✅

QForge Optimization:
  - Reduced memory allocation by 23%
  - Improved message throughput by 41%

PR Created: #147 "feat: Add WebSocket support to Matrix Monitor"
  Files changed: 4 (+342, -12)
  Tests: 8/8 passing
  Coverage: 94%
  Assigned to: @tech-infra-reviewer

Status: AWAITING REVIEW
```

### Dependencies
- OpenClaw code generation (built-in)
- QForge executor + optimizer
- REPO DEPOT github_sync (for branch/PR operations)
- NCL knowledge base (for code context)
- GitHub API token (for PR creation)
- CI/CD pipeline (GitHub Actions)
