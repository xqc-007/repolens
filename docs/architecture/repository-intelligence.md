# Repository Intelligence Engine

RepoLens V1 builds a deterministic repository index before involving an LLM.

## Why this exists

Sending an entire repository to a model is expensive, noisy and difficult to audit. The intelligence engine creates a bounded structural representation that later retrieval and agent planning can query.

## V1 index

For every allowed repository file RepoLens records:

- path
- language
- byte size
- line count
- symbols where supported
- imports where supported
- resolved local dependency edges

Python uses the standard library AST. TypeScript and JavaScript use a conservative static parser for common import/export/class/function forms. Repository files are read as untrusted text and are never imported or executed during indexing.

## Supported structural extraction

- Python: classes, functions, methods, imports
- TypeScript/JavaScript: classes, functions, exported functions, arrow functions, interfaces, types, ES imports and common `require()` calls

Other languages still appear in repository metadata and language counts, but do not yet receive symbol extraction.

## API

- `GET /api/repositories/{repository_id}/index`
- `GET /api/repositories/{repository_id}/symbols?q=login`
- `GET /api/repositories/{repository_id}/dependencies?path=backend/auth.py`

## Security boundary

The indexer only sees files already allowed by `WorkspaceService` and `is_allowed_path`. It does not execute repository code, install packages or follow paths outside the workspace.

## Production evolution

The parser layer is intentionally replaceable. A production implementation can introduce Tree-sitter language adapters, persistent symbol indexes, incremental indexing keyed by commit SHA and semantic embeddings without changing the public repository-intelligence contract.
