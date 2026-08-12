# Security hardening and adversarial evaluation

RepoLens treats cloned repository content as untrusted data. This is enforced through multiple independent controls rather than relying on a prompt alone.

## Controls

- Sensitive filenames such as `.env`, `.npmrc`, private keys and credential files are excluded from repository reads/indexing.
- Credential-like strings are redacted before repository text is exposed to the model-facing tool path.
- Repository content is explicitly framed as `UNTRUSTED_REPOSITORY_DATA`.
- High-confidence prompt-injection indicators are detected and attached to retrieval context as security metadata.
- The investigation loop permits READ tools only.
- PROPOSE permission is limited to change/test tasks and patch files are validated against an application-selected allowlist.
- EXECUTE requires both the execution permission and an explicit user approval signal.
- WRITE remains disabled in V1 regardless of model output, repository instructions, or user-supplied permission values.
- Unknown and denied tool attempts are audit logged.
- Test execution is restricted to the trusted demo repository in V1; arbitrary-repository execution requires a hardened sandbox in a production implementation.

## Threat model

Repository files may contain malicious comments, README text, test fixtures, generated files, or source strings that attempt to instruct the model to reveal secrets or invoke capabilities. RepoLens does not trust these instructions. Prompt wording is only one layer; the effective security boundary is the tool registry, permission policy, path controls, secret filtering, patch scope validation, and execution policy.

## Evaluation coverage

The automated suite verifies path traversal denial, secret redaction, prompt-injection detection, disabled WRITE capabilities, explicit execution approval, patch-scope rejection, audit logging, bounded agent loops, and retrieval security metadata.
