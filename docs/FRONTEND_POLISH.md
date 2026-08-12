# Frontend portfolio polish

RepoLens V1 presents the coding agent as a review-oriented product rather than an IDE.

## Navigation

- Home explains the product and its engineering boundaries.
- Repositories exposes server-side GitHub connection and repository selection.
- Ask is the primary natural-language workflow.
- Changes shows the current session's proposed patch without implying a write occurred.
- Test Runs shows explicitly approved validation for the current session.
- System exposes runtime mode and the tool permission catalogue without exposing secrets.

## Agent activity

The timeline displays high-level application/tool events only. It intentionally does not expose model chain-of-thought.

## V1 history scope

Changes and Test Runs are current-session views in the portfolio demo. A production version would persist/query user-scoped history with access control, retention rules, and pagination.
