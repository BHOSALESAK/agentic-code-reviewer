# Architecture

## Proposed final file tree

```text
agentic-code-reviewer/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── agents/
│   │   ├── analyzers/
│   │   ├── context/
│   │   ├── core/
│   │   ├── evaluation/
│   │   ├── github/
│   │   ├── graphs/
│   │   ├── models/
│   │   ├── persistence/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── verification/
│   │   └── main.py
│   ├── migrations/
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── routes/
│   │   └── types/
│   └── package.json
├── fixtures/
│   ├── ground_truth/
│   ├── pull_requests/
│   └── sample_repositories/
├── scripts/
├── docs/
├── .env.example
├── .gitignore
├── compose.yaml
├── Makefile
└── README.md
```

## LangGraph workflow

The graph starts by validating the pull request request. It then fetches pull
request metadata and diffs, builds bounded repository context, and checks the
pull request size so large changes can be chunked safely.

Next, the planner selects review tasks. Independent specialized agents and
static-analysis tools run with bounded concurrency. Their candidate findings
are aggregated while recoverable failures are retried. A failed agent is
represented as a partial failure and does not discard valid results from other
agents.

Every candidate finding enters the verification stage. The verifier checks the
file, changed location, evidence, behavior, remediation, tool provenance,
severity, and confidence. Unsupported candidates are rejected or marked for
manual review. Verified findings receive final severity and confidence, then
review and evaluation data are persisted.

The graph returns structured results and may optionally publish approved GitHub
comments. Publication is disabled by default and runs only after explicit
authorization. The graph then ends with review status, findings, provenance,
partial failures, and execution metadata.
