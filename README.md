# Agentic AI Code Reviewer

Foundation for an evidence-based, multi-agent GitHub Pull Request reviewer.

## Milestone 1

This milestone provides a local demo foundation only:

- FastAPI backend with `GET /api/v1/health`
- React + TypeScript + Vite frontend
- Frontend-to-backend health status check
- Demo mode with no GitHub, LLM, PostgreSQL, or Redis credentials

The synopsis was supplied as `Synopsis.pdf (2).pdf` in this workspace. It describes a GitHub PR review system combining repository context, specialist security/logic/error-handling/test agents, Semgrep/Bandit/dependency scanning, a critic verification stage, resilience controls, and evaluation metrics.

## Run locally

### Backend

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate  # Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install -e '.[dev]'
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The frontend expects the backend at http://localhost:8000.

## Verification

```bash
cd backend && pytest
cd frontend && npm run typecheck && npm run build
curl http://localhost:8000/api/v1/health
```

## Planned milestones

- [x] Milestone 1: scaffolding, dependencies, health endpoints, local servers
- [ ] Milestone 2: backend foundations, models, persistence abstractions, tests
- [ ] Milestone 3: GitHub PR retrieval and repository context extraction
- [ ] Milestone 4: scanners, specialist agents, and LangGraph workflow
- [ ] Milestone 5: verification, deduplication, retries, and partial results
- [ ] Milestone 6: complete dashboard and review workflow
- [ ] Milestone 7: signed webhooks and optional comment publication
- [ ] Milestone 8: baseline comparison and evaluation metrics
- [ ] Milestone 9: final verification and documentation
