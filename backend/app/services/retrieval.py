from __future__ import annotations

import re
from collections import defaultdict, deque
from pathlib import Path

from app.schemas.retrieval import ContextChunk, RetrievalCandidate, RetrievalResponse
from app.services.indexing import RepositoryIndexService
from app.services.security import sanitize_repository_content
from app.services.workspace import WorkspaceService


_STOP_WORDS = {
    "a", "an", "and", "are", "be", "because", "break", "change", "code", "could",
    "does", "failing", "file", "files", "find", "fix", "for", "from", "how", "i",
    "if", "in", "is", "it", "me", "my", "of", "on", "project", "show", "the",
    "this", "to", "what", "where", "why", "will", "with", "would", "you",
}

# Small deterministic vocabulary expansion. This is intentionally bounded and explainable.
_EXPANSIONS = {
    "login": {"auth", "authenticate", "authentication", "signin", "session"},
    "auth": {"login", "authenticate", "authentication", "session", "token"},
    "authentication": {"auth", "login", "authenticate", "session", "token"},
    "endpoint": {"route", "router", "api", "handler"},
    "api": {"endpoint", "route", "router", "handler"},
    "test": {"tests", "spec", "pytest", "unittest"},
    "tests": {"test", "spec", "pytest", "unittest"},
    "validation": {"validate", "validator", "schema", "required"},
    "error": {"exception", "failure", "failed", "invalid"},
}

_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_$.-]*")


def _identifier_parts(value: str) -> set[str]:
    value = value.replace("-", "_").replace(".", "_").replace("/", "_")
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return {part.lower() for part in value.split("_") if len(part) >= 2}


class RetrievalService:
    """Rank repository evidence using lexical, path, symbol and dependency signals.

    No repository code is executed. The service consumes the deterministic repository
    index and returns bounded, redacted context suitable for a model/tool call.
    """

    def __init__(
        self,
        workspace: WorkspaceService | None = None,
        indexer: RepositoryIndexService | None = None,
    ):
        self.workspace = workspace or WorkspaceService()
        self.indexer = indexer or RepositoryIndexService(self.workspace)

    def retrieve(
        self,
        repository_id: str,
        query: str,
        *,
        max_candidates: int = 10,
        max_files: int = 6,
        radius: int = 18,
    ) -> RetrievalResponse:
        terms = self.query_terms(query)
        index = self.indexer.build(repository_id)
        root = self.workspace.get_repo_path(repository_id)

        file_scores: dict[str, float] = defaultdict(float)
        reasons: dict[str, list[str]] = defaultdict(list)
        matched_terms: dict[str, set[str]] = defaultdict(set)
        hit_lines: dict[str, list[int]] = defaultdict(list)
        matched_symbols: dict[str, set[str]] = defaultdict(set)

        entry_by_path = {entry.path: entry for entry in index.files}

        # 1. Filename/path signal.
        for entry in index.files:
            path_lower = entry.path.lower()
            path_parts = _identifier_parts(entry.path)
            for term in terms:
                if term in path_lower:
                    file_scores[entry.path] += 5.0
                    matched_terms[entry.path].add(term)
                    self._reason(reasons[entry.path], f"path matches '{term}'")
                elif term in path_parts:
                    file_scores[entry.path] += 3.0
                    matched_terms[entry.path].add(term)
                    self._reason(reasons[entry.path], f"path token matches '{term}'")

        # 2. Symbol signal. Exact symbol matches are high value.
        for entry in index.files:
            for symbol in entry.symbols:
                symbol_lower = symbol.name.lower()
                symbol_parts = _identifier_parts(symbol.name)
                for term in terms:
                    if symbol_lower == term:
                        file_scores[entry.path] += 12.0
                        matched_terms[entry.path].add(term)
                        matched_symbols[entry.path].add(symbol.name)
                        hit_lines[entry.path].append(symbol.line)
                        self._reason(reasons[entry.path], f"exact symbol '{symbol.name}'")
                    elif term in symbol_lower or term in symbol_parts:
                        file_scores[entry.path] += 7.0
                        matched_terms[entry.path].add(term)
                        matched_symbols[entry.path].add(symbol.name)
                        hit_lines[entry.path].append(symbol.line)
                        self._reason(reasons[entry.path], f"symbol '{symbol.name}' matches '{term}'")

        # 3. Lexical code signal. Score by term coverage while recording useful lines.
        for entry in index.files:
            path = root.joinpath(*Path(entry.path).parts)
            if not path.is_file() or entry.size_bytes > self.workspace.settings.max_file_bytes:
                continue
            try:
                lines = path.read_text(errors="replace").splitlines()
            except OSError:
                continue
            seen_for_file: set[str] = set()
            for line_number, line in enumerate(lines, 1):
                low = line.lower()
                line_terms = {term for term in terms if term in low}
                if not line_terms:
                    continue
                hit_lines[entry.path].append(line_number)
                matched_terms[entry.path].update(line_terms)
                for term in line_terms:
                    # First occurrence contributes more than repeated occurrences.
                    file_scores[entry.path] += 3.0 if term not in seen_for_file else 0.75
                    seen_for_file.add(term)
                if len(line_terms) >= 2:
                    file_scores[entry.path] += 2.0
                self._reason(reasons[entry.path], "code contains " + ", ".join(sorted(line_terms)[:4]))

        # 4. Query-term coverage reward.
        if terms:
            for path, found in matched_terms.items():
                coverage = len(found) / len(terms)
                file_scores[path] += 6.0 * coverage
                if coverage >= 0.5:
                    self._reason(reasons[path], f"matches {len(found)}/{len(terms)} query terms")

        # 5. Structural dependency expansion from the strongest direct evidence.
        direct_ranked = sorted(file_scores, key=lambda p: (-file_scores[p], p))
        seeds = [path for path in direct_ranked[:4] if file_scores[path] > 0]
        dependency_distance: dict[str, int] = {}
        adjacency: dict[str, set[str]] = defaultdict(set)
        for edge in index.dependencies:
            adjacency[edge.source].add(edge.target)
            adjacency[edge.target].add(edge.source)

        queue: deque[tuple[str, int]] = deque((seed, 0) for seed in seeds)
        visited = set(seeds)
        while queue:
            current, distance = queue.popleft()
            if distance >= 2:
                continue
            for neighbor in sorted(adjacency.get(current, set())):
                next_distance = distance + 1
                if neighbor not in dependency_distance or next_distance < dependency_distance[neighbor]:
                    dependency_distance[neighbor] = next_distance
                if next_distance == 1:
                    file_scores[neighbor] += 4.0
                    self._reason(reasons[neighbor], f"direct dependency of relevant file '{current}'")
                elif next_distance == 2:
                    file_scores[neighbor] += 1.5
                    self._reason(reasons[neighbor], "second-degree dependency of relevant code")
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, next_distance))

        ranked_paths = sorted(
            (path for path, score in file_scores.items() if score > 0 and path in entry_by_path),
            key=lambda path: (-file_scores[path], path),
        )[:max_candidates]

        candidates = [
            RetrievalCandidate(
                path=path,
                score=round(file_scores[path], 3),
                reasons=reasons[path][:6],
                matched_terms=sorted(matched_terms[path]),
                symbols=sorted(matched_symbols[path]),
                dependency_distance=dependency_distance.get(path),
            )
            for path in ranked_paths
        ]

        context, truncated = self._build_context(
            repository_id,
            candidates[:max_files],
            hit_lines,
            radius=radius,
        )

        return RetrievalResponse(
            repository_id=repository_id,
            query=query,
            query_terms=terms,
            candidates=candidates,
            context=context,
            context_chars=sum(len(chunk.content) for chunk in context),
            truncated=truncated,
        )

    def search(self, repository_id: str, query: str, limit: int = 20):
        """Compatibility shim for the existing tool registry/agent."""
        result = self.retrieve(repository_id, query, max_candidates=limit, max_files=min(6, limit))
        hits = []
        for chunk in result.context:
            hits.append(
                type(
                    "SearchHit",
                    (),
                    {
                        "path": chunk.path,
                        "line": chunk.start_line,
                        "snippet": chunk.content[:320],
                        "score": chunk.score,
                    },
                )()
            )
        return hits

    def context_for_hits(self, repository_id: str, hits: list, max_files: int = 6, radius: int = 18) -> list[dict]:
        # Existing agent compatibility. The V2 engine is authoritative for new requests.
        if not hits:
            return []
        root = self.workspace.get_repo_path(repository_id)
        budget = self.workspace.settings.max_context_chars
        used = 0
        out: list[dict] = []
        seen: set[str] = set()
        for hit in hits:
            if hit.path in seen or len(seen) >= max_files:
                continue
            seen.add(hit.path)
            path = root.joinpath(*Path(hit.path).parts)
            source = path.read_text(errors="replace").splitlines()
            start = max(1, int(hit.line) - radius)
            end = min(len(source), int(hit.line) + radius)
            chunk = "\n".join(f"{n}: {source[n - 1]}" for n in range(start, end + 1))
            chunk, redactions, security_flags = sanitize_repository_content(chunk)
            if used + len(chunk) > budget:
                chunk = chunk[: max(0, budget - used)]
            if not chunk:
                break
            out.append(
                {
                    "path": hit.path,
                    "start_line": start,
                    "end_line": end,
                    "content": chunk,
                    "redactions": redactions,
                    "security_flags": security_flags,
                }
            )
            used += len(chunk)
        return out

    def dependencies(self, repository_id: str, relative: str) -> dict:
        report = self.indexer.dependency_report(repository_id, relative)
        return {
            "file": relative,
            "imports": [item.model_dump() for item in report.imports],
            "referenced_by": report.imported_by,
        }

    def query_terms(self, query: str) -> list[str]:
        base: list[str] = []
        for token in _IDENTIFIER_RE.findall(query):
            for part in _identifier_parts(token):
                if len(part) >= 2 and part not in _STOP_WORDS and part not in base:
                    base.append(part)

        expanded = list(base)
        for term in base:
            for extra in sorted(_EXPANSIONS.get(term, set())):
                if extra not in expanded:
                    expanded.append(extra)

        # Bounded so broad natural-language prompts cannot explode retrieval work.
        return expanded[:14]

    def _build_context(
        self,
        repository_id: str,
        candidates: list[RetrievalCandidate],
        hit_lines: dict[str, list[int]],
        *,
        radius: int,
    ) -> tuple[list[ContextChunk], bool]:
        root = self.workspace.get_repo_path(repository_id)
        budget = self.workspace.settings.max_context_chars
        used = 0
        truncated = False
        chunks: list[ContextChunk] = []

        for candidate in candidates:
            path = root.joinpath(*Path(candidate.path).parts)
            try:
                source = path.read_text(errors="replace").splitlines()
            except OSError:
                continue
            if not source:
                continue

            lines = sorted(set(hit_lines.get(candidate.path, [])))
            anchor = lines[0] if lines else 1
            start = max(1, anchor - radius)
            end = min(len(source), anchor + radius)

            # Expand enough to include clustered hits, but never turn one file into a full-repo dump.
            nearby = [line for line in lines if line <= start + radius * 3]
            if nearby:
                end = min(len(source), max(end, max(nearby) + radius))
            max_window = max(40, radius * 4)
            end = min(end, start + max_window - 1)

            content = "\n".join(f"{line_no}: {source[line_no - 1]}" for line_no in range(start, end + 1))
            content, redactions, security_flags = sanitize_repository_content(content)
            remaining = budget - used
            if remaining <= 0:
                truncated = True
                break
            if len(content) > remaining:
                content = content[:remaining]
                truncated = True
            if not content:
                break

            chunks.append(
                ContextChunk(
                    path=candidate.path,
                    start_line=start,
                    end_line=end,
                    content=content,
                    reason="; ".join(candidate.reasons[:3]) or "ranked repository evidence",
                    score=candidate.score,
                    redactions=redactions,
                    security_flags=security_flags,
                )
            )
            used += len(content)

        return chunks, truncated

    @staticmethod
    def _reason(target: list[str], reason: str) -> None:
        if reason not in target and len(target) < 10:
            target.append(reason)
