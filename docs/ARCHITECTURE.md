# RepoLens architecture

## Request lifecycle

1. The API creates an `agent_run` and emits safe activity events.
2. The orchestrator obtains a safe repository tree.
3. The LLM provider produces a typed `AgentPlan` containing bounded tool requests.
4. `ToolRegistry` validates the requested tool against the permission set.
5. Retrieval searches repository content locally, excludes sensitive paths and redacts secrets.
6. Only bounded, relevant excerpts are passed back to the model as **untrusted repository data**.
7. The answer is validated into a Pydantic `AgentAnswer`.
8. Change requests may produce a `PatchProposal`; the patch service rejects files outside retrieved scope.
9. The UI renders summary, findings, evidence, impact, confidence and a collapsible diff.
10. An explicit user action may run an allowlisted test command on a disposable copy of the trusted demo repository.

## Why explicit orchestration

RepoLens intentionally avoids hiding the workflow behind a large agent framework. The portfolio implementation exposes state, tool policy, retrieval, patch validation and audit events as ordinary Python components. This makes failure modes testable and interview explanations concrete.

## Production evolution

For larger repositories, replace the simple lexical scan with an incremental index keyed by commit SHA: Tree-sitter AST parsing, symbols/references, dependency graph, BM25 and optional embeddings. Queue ingestion and agent runs separately, use PostgreSQL for durable run state, object storage for indexes, and isolate arbitrary execution in hardened containers or microVMs.

## Structured agent loop

RepoLens uses an application-owned bounded investigation loop rather than granting the model an unrestricted shell or filesystem. A typed planner classifies the task and selects an initial READ action. After each validated tool result, the provider may request one additional READ tool or finish. The runtime rejects repeated calls, caps investigation steps at eight, caps unique file reads at twelve, and routes every tool through the permission registry and audit layer. PROPOSE actions happen only after evidence synthesis; EXECUTE remains user-approved; WRITE remains disabled in V1.

Tool/activity events shown in the UI are safe high-level statuses such as "Reading auth.py". They are not hidden model chain-of-thought.
