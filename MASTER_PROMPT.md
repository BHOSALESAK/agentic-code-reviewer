# MASTER BUILD PROMPT — Agentic AI Code Reviewer

## 1. Your Role

Act as a senior AI engineer, Python backend developer, React frontend developer, application security engineer, and software architect.

Build a complete, working, production-minded academic project titled:

**“An Agentic AI Framework for Reliable and Evidence-Based Automated Code Review.”**

I have provided my project synopsis as `Synopsis.pdf`. Read the complete synopsis before making architectural or implementation decisions. Treat it as the primary specification.

Do not merely explain how to build the project. Work directly in the current repository, create and edit files, implement features, run commands and tests, diagnose errors, and verify the resulting application.

Do not generate the entire application as an untested code dump. Work in small, coherent milestones, keep the application runnable, and report actual verification results.

## 2. Project Goal

Develop an Agentic AI code-review platform that reviews GitHub Pull Requests using multiple specialized AI agents, static-analysis tools, dependency scanners, repository context, and an independent verification stage.

The system must:

- Retrieve GitHub Pull Request information and changed code.
- Understand changes in the context of the repository.
- Detect potential security vulnerabilities, logical bugs, error-handling weaknesses, inadequate tests, and dependency vulnerabilities.
- Combine LLM reasoning with deterministic analysis tools.
- Verify potential findings before reporting them.
- Minimize unsupported findings and false positives.
- Produce structured, evidence-based review comments.
- Provide a modern web dashboard.
- Evaluate the multi-agent approach using measurable performance metrics.
- Handle large PRs, unavailable services, invalid responses, retries, and partial failures.

The primary purpose is to demonstrate that evidence-backed, multi-agent code review can be more reliable than relying on a single LLM response.

## 3. Mandatory Technology Stack

Use the following technologies unless a documented technical incompatibility requires an alternative.

### Frontend
- React.js
- TypeScript
- Vite
- React Router
- TanStack Query for server-state management
- A consistent component library or Tailwind CSS
- Recharts for evaluation visualizations
- A suitable diff viewer for changed code

### Backend
- Python
- FastAPI
- Pydantic for request validation and structured outputs
- LangGraph for agent orchestration
- GitHub REST API for PR data and review publication
- GitHub webhooks for event-driven reviews
- PostgreSQL for persistent application data
- Redis for caching and background job coordination when required

Use a lightweight local-development configuration. PostgreSQL and Redis must be optional during the earliest offline/demo stage if practical, but the production-oriented configuration should support them.

### AI and code analysis
- A configurable LLM API provider
- LangGraph
- Semgrep
- Bandit
- pip-audit
- Extensible dependency-scanning adapters

Do not hard-code an LLM provider throughout the application. Define a provider interface and configuration so a compatible model can be changed without rewriting the agent system.

### Testing and development
- pytest
- HTTPX for FastAPI tests
- Vitest and React Testing Library
- Integration tests
- Ruff for Python linting and formatting
- TypeScript type checking
- Docker Compose for optional reproducible local services

Use supported, mutually compatible stable package versions and commit the appropriate dependency lockfiles.

## 4. Required Architecture

Create a modular architecture with clear responsibilities.

### A. GitHub integration module

Implement:

1. Repository selection.
2. Pull Request metadata retrieval.
3. Changed-file retrieval.
4. Unified diff extraction.
5. Base and head commit tracking.
6. Relevant source-code retrieval.
7. Repository structure and dependency-file discovery.
8. Webhook event handling.
9. Optional publication of verified inline comments.
10. Graceful handling of unavailable repositories, permissions, rate limits, and invalid PR references.

Use minimal GitHub permissions. Verify webhook signatures using the official signing procedure. Prevent duplicate processing of the same event.

Support a manual PR-review flow in the dashboard so the system can be demonstrated without requiring a webhook for every review.

### B. Repository context builder

Create a dedicated component that:

- Parses changed files and hunks.
- Associates findings with actual source locations.
- Retrieves bounded amounts of relevant surrounding code.
- Identifies relevant imports, callers, configuration, tests, and dependency manifests where feasible.
- Uses chunking for large diffs.
- Tracks file paths, line numbers, and commit SHAs.
- Enforces configurable file-count, byte-size, and token limits.
- Avoids including secrets, binary files, generated files, or irrelevant content unnecessarily.
- Clearly identifies incomplete context.

Do not send an entire large repository to an LLM.

### C. LangGraph agent workflow

Implement the following specialized agents.

**1. Security Analysis Agent**

Focus on:
- Injection risks.
- Authentication and authorization mistakes.
- Insecure secret handling.
- Unsafe deserialization.
- Path traversal.
- Insecure cryptographic practices.
- Other applicable vulnerabilities.

Use static-analysis evidence whenever available.

**2. Bug and Logic Analysis Agent**

Focus on:
- Incorrect conditions.
- Boundary errors.
- Null or missing-value handling.
- Incorrect data transformations.
- Resource lifecycle issues.
- Potential regressions introduced by the changes.
- Inconsistent assumptions between changed code and its callers.

Do not label speculative behavior as a confirmed defect.

**3. Error-Handling Agent**

Focus on:
- Swallowed exceptions.
- Incorrect exception handling.
- Missing recovery paths.
- Resource cleanup.
- Unsafe fallback behavior.
- Failure propagation and error reporting.

**4. Test Adequacy Agent**

Focus on:
- Missing tests for changed behavior.
- Boundary conditions.
- Regression scenarios.
- Negative cases.
- Failure paths.
- Tests that may not exercise the changed behavior.

Do not claim that tests are missing without checking the available repository context.

**5. Static and Dependency Analysis**

Create adapters for:
- Semgrep.
- Bandit.
- pip-audit.
- Additional dependency scanners where supported.

Normalize their outputs into a common finding format. Preserve the original rule identifier, evidence, severity, affected location, and tool provenance.

A tool being unavailable must not be silently treated as a successful scan.

**6. Critic / Verification Agent**

This is a core component, not an optional feature.

For every candidate finding, verify:

- The affected file exists in the analyzed commit.
- The line or changed hunk is valid and relevant.
- The reported behavior follows from the available evidence.
- The issue is not merely a stylistic preference.
- The explanation is consistent with the code and repository context.
- The proposed remediation addresses the identified issue.
- Static-analysis evidence is accurately represented.
- Confidence and severity are justified.

Use structured verification outcomes such as:
- Verified.
- Rejected.
- Needs manual review.

A static-analysis match is supporting evidence, not automatic proof of exploitability. A lack of static-analysis matches is not proof that the code is safe.

The verifier must not invent evidence or fabricate tool results. Preserve the reason for rejection and the verification provenance for evaluation.

### D. LangGraph workflow

Implement a graph resembling:

START
→ Validate PR request
→ Fetch PR metadata and diffs
→ Build repository context
→ Check PR size and chunk if necessary
→ Plan review tasks
→ Run applicable specialized agents and analysis tools
→ Aggregate candidate findings
→ Retry recoverable failures when appropriate
→ Verify candidate findings
→ Discard or flag unsupported findings
→ Assign final severity and confidence
→ Persist review and evaluation data
→ Return structured results
→ Optionally publish approved GitHub comments
→ END

Use conditional edges for retries, failed AI calls, incomplete context, and large PRs.

Parallelize independent analyses when practical. Bound concurrency and API usage.

Do not allow one failed agent to erase valid results from other agents. Represent partial results and failures explicitly.

## 5. Standard Finding Schema

Define a validated Pydantic model for findings.

Each finding should include:

- Stable finding ID.
- Review ID.
- Repository identifier.
- Pull Request number.
- Commit SHA.
- Issue category.
- Title.
- Description.
- Severity: Critical, High, Medium, Low, or Informational.
- Confidence score from 0 to 1.
- File path.
- Start and end line numbers.
- Evidence or code excerpt.
- Explanation of the potential impact.
- Recommended remediation.
- Verification status.
- Verification explanation.
- Supporting tool names and rule IDs.
- Whether the finding is on a changed line or hunk.
- Publication status.
- Timestamps.

Use explicit nullable fields where appropriate. Do not invent values to satisfy a schema.

Validate every finding before persistence or publication. Keep raw tool results and normalized findings distinguishable.

## 6. Evidence and Reliability Requirements

The system must prioritize trustworthy results over producing a large number of findings.

Implement:

1. Structured LLM outputs with validation.
2. Bounded retries for transient failures.
3. Configurable timeouts.
4. Backoff for rate limits and temporary service errors.
5. Chunking and aggregation for large PRs.
6. Duplicate-finding detection.
7. Finding provenance and evidence tracking.
8. Verification rejection reasons.
9. Partial-result reporting.
10. Request and token usage tracking where available.
11. Review latency measurement.
12. Configurable confidence thresholds.
13. A clear distinction between unverified candidates and verified findings.

Do not treat the model's confidence score as a calibrated probability unless calibration has actually been evaluated.

Never claim that the framework eliminates false positives. The objective is to reduce them and measure the reduction.

## 7. GitHub Comment Publication

Support two modes:

**Mode A: Safe demonstration mode**

- Analyze PRs and display findings in the dashboard.
- Do not modify GitHub.
- Allow the user to inspect evidence before taking action.

**Mode B: Explicit publication mode**

- Publish verified findings as appropriate GitHub PR review comments.
- Restrict inline comments to valid locations supported by the GitHub API.
- Use the correct commit SHA and diff position requirements.
- Provide clear handling for outdated lines, rejected comments, and API failures.
- Record publication status and avoid duplicate comments.

Publication must be disabled by default and require explicit configuration and user authorization.

Do not merge PRs, push commits, edit repository code, or approve PRs automatically.

## 8. Frontend Requirements

Build a polished, responsive developer-facing dashboard. Avoid a generic landing page that does not connect to working backend functionality.

### Page 1: Overview Dashboard

Display:
- Total reviews.
- Findings by severity.
- Verified versus rejected findings.
- Recent reviews.
- Review latency.
- Recent errors or incomplete analyses.
- A clear action to start a review.

Use real API data when available and clearly labelled sample data in demo mode.

### Page 2: Repository and Pull Request Review

Provide:
- Repository input or selection.
- Pull Request number or URL input.
- PR metadata and changed-file list.
- Review status.
- Progress and failure states.
- Start-review action.
- Existing review history.

Validate inputs and display useful error messages.

### Page 3: Review Findings

Provide:
- Severity and category filters.
- Verification-status filters.
- Search.
- Finding cards or a structured table.
- File paths and line numbers.
- Confidence and evidence.
- Recommended fixes.
- Supporting tool information.
- Verification explanations.

### Page 4: Finding Details

Show:
- Issue description.
- Relevant code excerpt.
- File and line location.
- Why the behavior may be defective.
- Security or functional impact.
- Recommended remediation.
- Verification decision and reason.
- Supporting scanner output.
- Related findings where applicable.

### Page 5: Code Diff Viewer

Display base-versus-head changes with line numbers and findings anchored to relevant changed lines when supported.

Handle outdated or missing diff locations gracefully.

### Page 6: Agent Execution Trace

Show:
- Agents executed.
- Start and completion times.
- Tool execution statuses.
- Retry counts.
- Candidate finding counts.
- Verification decisions.
- Partial failures.

Expose useful execution metadata, not private internal chain-of-thought or hidden reasoning.

### Page 7: Evaluation and Analytics

Display:
- Precision.
- Recall.
- F1-score.
- False-positive rate.
- False-negative rate.
- Defect detection rate.
- Review latency.
- Estimated or recorded model/API cost.
- Comparison between single-LLM and multi-agent review.

Clearly distinguish measured results from sample values. Do not fabricate performance claims.

### Page 8: Configuration

Provide safe configuration for:
- LLM provider and model selection.
- Review thresholds.
- Supported analysis tools.
- Maximum PR size and chunk limits.
- GitHub integration status.
- Comment-publication mode.
- Retry and timeout settings.

Never return secret values to the browser.

### UI design

Use a professional developer-tool aesthetic:
- Consistent typography and spacing.
- Clear visual severity hierarchy.
- Responsive layouts.
- Accessible controls.
- Loading, empty, error, and partial-result states.
- Useful tables, charts, badges, and code panels.
- A coherent sidebar and navigation structure.

Every visible action must perform a real operation or be clearly disabled with an explanation. Avoid fake buttons and hard-coded dashboards presented as live data.

## 9. Database Design

Design migrations and relational models for:

- Repositories.
- Pull Requests.
- Review runs.
- Review findings.
- Agent executions.
- Tool executions.
- Verification decisions.
- Evaluation runs and ground-truth labels.
- Publication attempts.

Use appropriate primary keys, foreign keys, indexes, timestamps, and uniqueness constraints.

Store review status, partial failures, provenance, and model/tool usage where available.

Use PostgreSQL in the persistent deployment configuration. Provide a lightweight development mode if the full service stack is not initially available.

Do not store GitHub tokens or LLM API keys in ordinary database fields.

## 10. Security Requirements

Implement secure-by-default behavior.

- Keep credentials in environment variables.
- Provide `.env.example` with placeholders only.
- Never commit real tokens, passwords, API keys, or webhook secrets.
- Validate webhook signatures.
- Enforce GitHub permission boundaries.
- Sanitize paths and prevent path traversal.
- Treat repository content, comments, and source files as untrusted data.
- Defend against prompt injection embedded in repository files and PR descriptions.
- Do not execute arbitrary repository code as part of the review.
- Do not execute generated remediation patches automatically.
- Run static-analysis tools with appropriate timeouts and resource limits.
- Avoid logging secrets or unnecessarily sensitive source code.
- Apply input validation, safe error responses, and appropriate access controls.
- Prevent cross-repository data exposure.
- Protect against duplicate webhook processing and concurrent review conflicts.
- Add appropriate CORS configuration and request limits.

When scanning an untrusted repository, use isolated, read-only processing where possible. Do not give analysis agents unrestricted shell access or arbitrary network access.

## 11. Evaluation Framework

This project must demonstrate research value, not just application functionality.

Create an evaluation subsystem capable of comparing:

**Baseline A:** A single LLM reviewing the same PR context.

**Proposed system B:** The multi-agent LangGraph pipeline with static analysis and verification.

Use identical input revisions, equivalent review scopes, and documented configurations wherever practical.

Support labeled findings or ground-truth defects from historical PRs, known vulnerability examples, and controlled test cases.

For each evaluation, record:
- Ground-truth defect labels.
- Predicted findings.
- Matched true positives.
- False positives.
- False negatives.
- Precision.
- Recall.
- F1-score.
- False-positive rate.
- False-negative rate.
- Detection rate.
- Review latency.
- Model/API cost where measurable.

Define how findings are matched to ground-truth defects, including category and location tolerances.

Use standard metric definitions and handle zero denominators explicitly.

Implement reproducible evaluation scripts and machine-readable result exports.

Do not invent benchmark results. If no real labeled dataset is available, create a small, clearly labelled synthetic fixture dataset for pipeline testing and explain that it is not evidence of real-world performance.

Include a way to measure whether verification reduces false positives, while also tracking whether it rejects true defects.

## 12. Testing Requirements

Create tests at multiple levels.

### Backend unit tests
- Finding schema validation.
- Diff parsing and line mapping.
- Context chunking.
- Severity normalization.
- Duplicate detection.
- Verification decisions.
- Retry logic.
- Metric calculations.
- GitHub API response handling.

### Integration tests
- Complete review pipeline using a mocked LLM.
- Multiple agent outputs.
- Static-analysis adapter outputs.
- Partial agent failures.
- Failed model calls and retries.
- Large PR chunking.
- Invalid file and line locations.
- Duplicate webhook delivery.
- Publication-disabled behavior.
- GitHub publication failures.
- Persistence and retrieval.

### Frontend tests
- Navigation.
- Form validation.
- Review submission.
- Findings rendering.
- Filters and search.
- Loading and error states.
- API failure handling.
- Evaluation charts.
- Responsive core layouts where feasible.

### End-to-end acceptance test

Demonstrate a complete workflow using a local fixture repository and mocked external services:

1. Load a sample PR.
2. Extract its changes.
3. Run specialist agents and scanner adapters.
4. Aggregate candidate findings.
5. Verify findings.
6. Display the review.
7. Persist results.
8. Calculate evaluation metrics against known fixture labels.

The test must not require a paid LLM API or a live GitHub repository.

Use mocked services for automated tests. Keep a separate optional integration test for real provider credentials.

## 13. Required Repository Structure

Use a clear monorepo structure similar to:

agentic-code-reviewer/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── github/
│   │   ├── context/
│   │   ├── agents/
│   │   ├── graphs/
│   │   ├── analyzers/
│   │   ├── verification/
│   │   ├── evaluation/
│   │   ├── persistence/
│   │   └── main.py
│   ├── tests/
│   ├── migrations/
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
│   ├── sample_repositories/
│   ├── pull_requests/
│   └── ground_truth/
├── scripts/
├── docs/
├── .env.example
├── .gitignore
├── compose.yaml
├── Makefile
└── README.md

Adjust this structure when justified, but keep agent logic, API routes, database models, GitHub integration, evaluation, and UI responsibilities separated.

## 14. Implementation Milestones

Build the project in the following order.

### Milestone 1 — Repository and environment
- Inspect the current directory before modifying anything.
- Read the synopsis.
- Detect the operating system and available tools.
- Propose the architecture and final file tree.
- Create the frontend and backend scaffolding.
- Configure dependencies and environment variables.
- Implement health-check endpoints.
- Start the frontend and backend.
- Verify both run successfully.

### Milestone 2 — Backend foundations
- Define core models and schemas.
- Add configuration and structured logging.
- Add database models and migrations.
- Implement API error handling.
- Add unit tests.

### Milestone 3 — GitHub PR and context extraction
- Implement manual PR input.
- Fetch metadata, files, and diffs.
- Build the repository-context pipeline.
- Add size limits and chunking.
- Test with fixtures and mocked GitHub responses.

### Milestone 4 — Analysis tools and agents
- Integrate Semgrep and Bandit.
- Add dependency scanning.
- Implement the four specialist agents.
- Add the LangGraph workflow.
- Use a configurable LLM provider and deterministic mocked mode.
- Validate structured outputs.

### Milestone 5 — Verification and reliability
- Implement the critic/verifier.
- Add finding deduplication and provenance.
- Implement bounded retries and partial-result handling.
- Test false-positive rejection and failure scenarios.

### Milestone 6 — Frontend integration
- Implement all required dashboard pages.
- Connect them to actual backend endpoints.
- Implement review progress and finding details.
- Add diff visualization, filtering, analytics, and error states.
- Verify the complete local workflow.

### Milestone 7 — GitHub publication
- Add signed webhook handling.
- Add idempotency.
- Implement optional verified inline comments.
- Keep publication disabled by default.
- Test permissions and failure cases.

### Milestone 8 — Evaluation
- Build the baseline and multi-agent comparison pipeline.
- Add ground-truth matching.
- Calculate evaluation metrics.
- Produce reproducible reports and visualizations.
- Clearly label synthetic versus real evaluation data.

### Milestone 9 — Final verification and documentation
- Run backend tests and linting.
- Run frontend tests, type checking, and build.
- Run the end-to-end fixture workflow.
- Fix issues found.
- Document setup, architecture, APIs, configuration, limitations, evaluation, and demo instructions.
- Confirm all claimed commands and features against actual results.

## 15. How You Must Work

Follow these operating rules.

1. First inspect the existing repository and environment. Do not overwrite existing user work.
2. Read and follow the provided synopsis.
3. Present a short architecture plan and identify genuine blockers.
4. Start with Milestone 1 and make the smallest complete set of changes.
5. Create real source files rather than only displaying code in chat.
6. Run relevant commands and tests after each milestone.
7. Diagnose errors using their actual output.
8. Never report a test, build, integration, or deployment as successful unless it was actually verified.
9. Do not silently replace a required technology with a different one.
10. Keep changes modular and maintainable.
11. Avoid unnecessary dependencies and oversized implementations.
12. Do not require Docker for the first local demonstration if equivalent native execution is feasible.
13. Do not assume external API credentials exist.
14. Do not expose secrets in code, logs, screenshots, or documentation.
15. When credentials are missing, implement the integration, provide a mock/demo path, and document the exact configuration needed for live use.
16. If a feature cannot be completed in the current environment, document the blocker and finish all independent work that can be verified.
17. Keep the application runnable after each milestone.
18. Do not stop after writing a plan or generating a project skeleton. Continue implementation until a meaningful working milestone is complete.

## 16. Local Developer Experience

Provide a clear, copy-pasteable setup guide for Windows and Linux/WSL2.

Include:
- Prerequisites.
- Python virtual environment creation.
- Backend dependency installation.
- Frontend dependency installation.
- Environment-file setup.
- Optional PostgreSQL and Redis startup.
- Backend startup.
- Frontend startup.
- Unit-test commands.
- Lint and type-check commands.
- Production build command.
- Mock/demo review instructions.
- Optional live GitHub and LLM configuration.

Provide a Makefile or equivalent scripts with commands such as:

make bootstrap
make dev
make test
make lint

Ensure these commands match the actual repository implementation. Do not provide commands that have not been created or validated.

Use sensible resource limits for a development laptop. Avoid unnecessary local model downloads or GPU requirements; use an external LLM API when configured and mocked responses otherwise.

## 17. Definition of Done

The initial complete implementation is acceptable when:

- The React frontend starts and builds.
- The FastAPI backend starts and its health endpoint responds.
- A user can initiate a review using a fixture PR without external credentials.
- The system processes diffs and repository context.
- The four specialist agents and analysis-tool adapters have implemented responsibilities.
- The LangGraph pipeline coordinates review, aggregation, and verification.
- Findings are structured, evidence-backed, and traceable.
- Unsupported candidates can be rejected.
- Large PRs and failed operations are handled gracefully.
- Review results are stored and displayed.
- The evaluation pipeline calculates the specified metrics.
- The single-LLM baseline and multi-agent comparison are implemented.
- GitHub publication is optional, permission-limited, and disabled by default.
- Automated tests run successfully in the available environment.
- Setup instructions are reproducible.
- Remaining limitations and unverified integrations are documented honestly.

## 18. Your First Response and First Action

Begin by:

1. Reading `Synopsis.pdf` and identifying its requirements.
2. Inspecting the current repository, terminal environment, and installed tools.
3. Reporting the requirements and the proposed architecture.
4. Identifying any missing credentials or dependencies without blocking mock-mode development.
5. Creating a milestone checklist.
6. Implementing Milestone 1 immediately.
7. Running the initial setup and health-check tests.

Do not merely tell me what commands I should execute if you can execute them in the available environment.

When you reach a stopping point, report:
- Files created or modified.
- Features actually implemented.
- Commands executed.
- Tests and builds that passed or failed.
- Known blockers.
- The next concrete implementation step.

**Start now. Prioritize a working, testable end-to-end foundation, then expand toward the full specification without sacrificing reliability or evidence quality.**