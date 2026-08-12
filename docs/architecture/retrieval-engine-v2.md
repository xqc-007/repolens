# Retrieval Engine V2

RepoLens does not send an entire repository to the model. Retrieval V2 builds a bounded evidence set before any LLM call.

## Ranking signals

1. **Path relevance** — query terms in filenames and directories.
2. **Symbol relevance** — exact or partial matches against indexed classes/functions/methods/types.
3. **Lexical relevance** — query-term matches in source code with term-coverage rewards.
4. **Dependency expansion** — direct and second-degree import neighbours of the strongest files.

The signals are deterministic and deliberately interpretable. Each candidate includes reasons explaining why it was selected.

## Query expansion

A small application-owned vocabulary expands high-value engineering terms such as `login -> auth/authentication/session`. This is bounded and auditable. It is not allowed to generate arbitrary model context.

## Context construction

Only the highest-ranked files are read. RepoLens selects bounded line windows around matching symbols/lines, applies secret redaction, honours the configured maximum context character budget, and reports whether truncation occurred.

## Why no embeddings yet

V1 prioritises exact identifiers, filenames, imports, error strings and call relationships. These signals are cheap, deterministic and strong for code. Semantic embeddings are a production extension for conceptual queries that do not share repository vocabulary.
