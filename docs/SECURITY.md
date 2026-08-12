# Security and guardrails

RepoLens assumes repository contents are hostile input.

| Capability | V1 policy |
|---|---|
| Repository tree/search/read | Allowed after safe path filtering |
| Secret-bearing files | Excluded |
| Detected secret strings | Redacted before LLM context |
| Patch generation | Proposal only |
| Patch file scope | Must be within retrieved context |
| Apply patch | Disposable execution copy only |
| Run tests | Explicit action + allowlisted command + trusted demo repo only |
| Arbitrary shell | Not exposed |
| Package installation | Not exposed |
| Git commit/push/PR | Not implemented |

Prompt-injection text inside source code, Markdown, comments or test fixtures is treated as data and cannot grant capabilities. The deterministic permission layer remains authoritative even if a model output is compromised.

A production version that executes arbitrary repositories must additionally provide network isolation, CPU/memory/process limits, filesystem isolation, syscall restrictions, short-lived workspaces and zero secret inheritance.
