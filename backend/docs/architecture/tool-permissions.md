# Tool Registry and Permission Engine

RepoLens treats model tool requests as untrusted requests for capabilities. The model does not receive direct filesystem, shell, or GitHub write access.

## Permission classes

- **READ** — repository-scoped inspection. Allowed by default after argument and path validation.
- **PROPOSE** — creates or validates a reviewable change artifact. Allowed only for change/test tasks and only when the run has PROPOSE permission.
- **EXECUTE** — can execute an allowlisted command in a disposable workspace. Requires explicit user approval for each execution flow.
- **WRITE** — mutates the source repository or remote provider. Disabled in V1 regardless of requested permissions.

## Enforcement path

`model request -> tool registry -> enabled check -> permission policy -> Pydantic argument validation -> application-injected repository scope -> handler -> audit log`

The repository ID is supplied by application state, not model arguments. This prevents a tool call from changing its target repository. Paths are still resolved through the workspace security boundary, which blocks traversal and secret files.

## Auditability

When an agent run invokes a tool, RepoLens records the tool name, permission class, redacted argument summary, status, and timestamp. Raw file contents, tokens, and API keys are not intentionally persisted in the audit record.

## V1 execution boundary

Arbitrary cloned repositories remain untrusted. V1 test execution is therefore limited to the bundled trusted demo repository. Production arbitrary-repository execution should run in an isolated container/microVM with network, CPU, memory, filesystem, and secret restrictions.
