# RepoLens

**Ask your codebase.**

RepoLens is a full-stack repository assistant that can inspect a GitHub project, find relevant code, trace simple dependencies, explain likely problems, propose a patch and run approved tests against that proposal.

The main design rule is simple: the model does not get unrestricted access to the repository. Application code decides what can be read, what can be proposed and what can be executed.

## Current status

This is the portfolio V1. It supports the complete demo flow and real GitHub repositories, while deliberately stopping short of automatic commits or pushes.

- FastAPI backend
- React + TypeScript + Vite frontend
- public and private GitHub repository connection
- local isolated repository workspaces
- repository tree and language detection
- Python/TypeScript/JavaScript symbol indexing
- import and reverse-dependency discovery
- ranked lexical + symbol + path + dependency retrieval
- bounded model context
- structured planning and a multi-step investigation loop
- READ / PROPOSE / EXECUTE / WRITE permission classes
- patch scope validation
- reviewable Git diffs
- explicit approval before test execution
- secret filtering and prompt-injection checks
- SQLite run/event/tool audit history
- mock and real LLM modes
- deterministic eval cases

Backend verification for this release: **41 tests passing**. The eval harness currently passes **4/4 labelled end-to-end cases**.

## Demo flow

The bundled demo repository contains a small login bug on purpose.

Try:

- `Why is login failing?`
- `What will break if I change authentication?`
- `Fix the login bug and show me the diff`

For a change request, RepoLens should investigate first, explain what it found, produce a scoped diff, then wait for you to approve test execution.

## Run locally

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m pytest
python -m uvicorn app.main:app --reload
```

API: `http://127.0.0.1:8000`

Swagger: `http://127.0.0.1:8000/docs`

### Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

For a production frontend check:

```bash
npm run build
```

## GitHub connection

For local development, RepoLens uses a fine-grained GitHub personal access token on the backend.

Create a token with access only to repositories you want RepoLens to inspect and set **Contents: Read-only**. Put it in `backend/.env`:

```env
GITHUB_TOKEN=github_pat_...
```

Restart FastAPI and check:

`http://127.0.0.1:8000/api/repositories/github/status`

The token stays server-side. It is not returned to React and is not stored in SQLite.

A hosted production version should use a GitHub App with short-lived installation tokens instead of a developer PAT.

## LLM modes

Mock mode is the default so the project can be demonstrated without API billing:

```env
LLM_MODE=mock
```

Real mode uses the OpenAI provider:

```env
LLM_MODE=real
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5-mini
```

The provider sits behind a small interface so the rest of the agent does not depend directly on one SDK.

## How an investigation works

```text
question
  ↓
structured plan
  ↓
registered READ tools
  ↓
repository search / file reads / dependency checks
  ↓
bounded evidence
  ↓
answer
  ↓
optional patch proposal
  ↓
file-scope validation
  ↓
user approves test execution
  ↓
disposable workspace + allowlisted test command
```

The investigation loop has hard step and file-read limits. Repeated tool calls are skipped rather than allowing an open-ended agent loop.

## Retrieval

RepoLens does not send the whole repository to the model.

V1 combines:

1. filename/path matches
2. lexical code matches
3. indexed symbol matches
4. import/dependency relationships

Candidate files receive explainable scores. Only bounded snippets from the strongest candidates are placed into model context.

This works well for code because many useful queries contain exact identifiers, routes, error strings, filenames or symbols. A larger production implementation could add Tree-sitter for broader language support, BM25 and optional embeddings without replacing the current retrieval service contract.

## Permission model

Tools are registered with one of four permission levels:

- **READ** — repository tree, search, file read, dependency inspection
- **PROPOSE** — validate a proposed patch
- **EXECUTE** — run an allowlisted test command after explicit approval
- **WRITE** — reserved but disabled in V1

Repository scope is injected by application code. The model cannot choose an arbitrary workspace ID or promote its own permissions.

## Security choices

Repository content is treated as untrusted input, including comments and README files.

The current safeguards include:

- workspace path traversal checks
- blocked secret/key filenames
- credential-pattern redaction
- prompt-injection indicators
- explicit untrusted-data framing before repository text reaches the model
- bounded context and file sizes
- patch file-scope validation
- no GitHub write tool in V1
- test commands restricted to an allowlist
- GitHub/OpenAI credentials removed from child test processes
- audit records for tool attempts, including denied calls

The local V1 test runner is intentionally conservative. Arbitrary untrusted code execution in a hosted product should move into a hardened container or microVM with network, CPU, memory and filesystem restrictions.

## Tests and evals

Run normal tests:

```bash
cd backend
python -m pytest
```

Run the labelled end-to-end evals from the repository root:

```bash
PYTHONPATH=backend python evals/run_evals.py
```

Current eval fixtures cover:

- login root-cause retrieval
- dependency impact
- patch scope
- prompt-injection/security behaviour

The distinction matters: pytest checks application behaviour; evals check whether the agent retrieves and uses the evidence expected for known tasks.

## Project structure

```text
backend/app/
  agents/          agent orchestration
  api/routes/      FastAPI endpoints
  integrations/    GitHub and LLM providers
  schemas/         Pydantic request/result models
  services/        workspace, retrieval, indexing, patching, tests
  tools/           registry and permission policy

frontend/src/
  components/
  features/
  lib/
  types/

 demo_repo/        deterministic repository used for demos/evals
 evals/            labelled agent cases
 docs/             architecture and security notes
```

## Deliberate V1 limits

A few things are intentionally not implemented:

- automatic commits or pushes
- automatic pull requests
- arbitrary shell access
- package installation by the agent
- multi-agent swarms
- a vector database
- background worker infrastructure

They are not required to demonstrate the main engineering problem: controlled repository reasoning with a human review boundary.

## Useful interview questions

**Why not send the entire repository to the model?**  
It increases cost and latency, exposes irrelevant data and usually makes code reasoning worse by diluting the useful context. RepoLens retrieves evidence first.

**Why is tool permission enforcement outside the prompt?**  
A prompt is guidance, not a security boundary. The registry and permission policy decide what the model can actually do.

**Why propose a diff before changing files?**  
Generated code can be plausible and still be wrong. A diff is reviewable, scope-checkable and can be tested before any write action.

**Why no embeddings in V1?**  
Exact identifiers and dependency structure are strong signals for code. Lexical and structural retrieval are cheaper and easier to debug. Embeddings make sense as an additional signal for larger or more conceptual searches.

**What would change for a large monorepo?**  
Index by commit SHA, update only changed files, use a proper lexical index, build AST/symbol/reference graphs asynchronously, cache retrieval results and isolate test execution in dedicated workers.

More implementation detail is in `docs/ARCHITECTURE.md`, `docs/SECURITY.md` and `docs/SECURITY_HARDENING.md`.
