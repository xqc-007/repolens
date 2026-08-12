# RepoLens interview notes

These are the implementation decisions worth being able to explain without looking at the code.

## The core idea

RepoLens is not a model with a GitHub token. The model proposes what it wants to inspect; application code owns the workspace, tool registry, permissions and validation.

## Retrieval before reasoning

Sending a whole repository is expensive and noisy. RepoLens first builds a small structural index, then ranks files using lexical, path, symbol and dependency signals. The model sees only bounded evidence from the strongest candidates.

## Why the agent loop is bounded

The loop has maximum step and file-read counts. It also records executed tool calls and stops duplicate requests. This gives predictable cost and prevents a stuck planner from repeatedly reading the same files.

## Tool permissions

READ tools are available during investigation. PROPOSE is used for patch validation. EXECUTE requires a user approval path. WRITE exists as a permission type but the GitHub write tool is disabled.

The permission check is deterministic Python code, not a prompt instruction.

## Repository content is untrusted

A repository can contain comments or Markdown telling an AI to ignore its rules. RepoLens scans for common prompt-injection patterns, redacts secret-like values and wraps repository text in an explicit untrusted-data boundary.

That is defence in depth; the actual capability boundary remains the tool registry.

## Patch flow

A change request does not mean “write to GitHub”. The model can produce a unified diff. RepoLens validates that the diff only touches allowed files. Tests can then run in a disposable copy after approval.

## Why SQLite is enough here

The data is local run history, events, patches and audit information for a portfolio demo. SQLite keeps setup simple. PostgreSQL would be the natural move for a hosted multi-user version.

## What I would improve next

- GitHub App auth instead of a developer PAT
- Tree-sitter parsers for more accurate multi-language symbols
- BM25 plus optional semantic retrieval for larger repos
- commit-SHA based incremental indexing
- proper container/microVM test isolation
- background jobs for large repository ingestion and long test runs
- persisted frontend history across sessions

## Things to be ready to show in the code

- `backend/app/agents/orchestrator.py` — loop limits and tool flow
- `backend/app/tools/registry.py` — permission enforcement
- `backend/app/services/retrieval.py` — ranking/context selection
- `backend/app/services/security.py` — redaction and untrusted-data handling
- `backend/app/services/patches.py` — patch scope validation
- `evals/` — behavioural checks that are separate from unit tests
