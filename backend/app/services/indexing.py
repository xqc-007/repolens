from __future__ import annotations

import ast
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from app.schemas.intelligence import (
    DependencyEdge,
    DependencyReport,
    FileIndexEntry,
    ImportInfo,
    RepositoryIndex,
    SymbolInfo,
)
from app.services.security import is_allowed_path
from app.services.workspace import WorkspaceService


LANGUAGE_BY_SUFFIX = {
    ".py": "Python",
    ".pyi": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".json": "JSON",
    ".md": "Markdown",
    ".css": "CSS",
    ".scss": "SCSS",
    ".html": "HTML",
    ".sql": "SQL",
    ".java": "Java",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".toml": "TOML",
}

INDEXABLE_LANGUAGES = {"Python", "TypeScript", "JavaScript"}

_JS_IMPORT_RE = re.compile(
    r"^\s*import\s+(?P<body>.+?)\s+from\s+['\"](?P<module>[^'\"]+)['\"]|"
    r"^\s*import\s+['\"](?P<side_effect>[^'\"]+)['\"]|"
    r"require\(\s*['\"](?P<require>[^'\"]+)['\"]\s*\)"
)
_JS_CLASS_RE = re.compile(r"^\s*(?:export\s+(?:default\s+)?)?class\s+([A-Za-z_$][\w$]*)")
_JS_FUNCTION_RE = re.compile(
    r"^\s*(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\("
)
_JS_ARROW_RE = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::[^=]+)?=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>"
)
_JS_INTERFACE_RE = re.compile(r"^\s*export\s+interface\s+([A-Za-z_$][\w$]*)")
_JS_TYPE_RE = re.compile(r"^\s*export\s+type\s+([A-Za-z_$][\w$]*)\s*=")


@dataclass(frozen=True)
class _RawImport:
    module: str
    names: list[str]
    line: int


class RepositoryIndexService:
    """Build the lightweight file, symbol and dependency index."""

    def __init__(self, workspace: WorkspaceService | None = None):
        self.workspace = workspace or WorkspaceService()
        self._cache: dict[str, RepositoryIndex] = {}

    def invalidate(self, repository_id: str) -> None:
        self._cache.pop(repository_id, None)

    def build(self, repository_id: str, *, force: bool = False) -> RepositoryIndex:
        if not force and repository_id in self._cache:
            return self._cache[repository_id]

        root = self.workspace.get_repo_path(repository_id)
        files: list[FileIndexEntry] = []
        languages: Counter[str] = Counter()

        for rel_text in self.workspace.tree(repository_id):
            rel = PurePosixPath(rel_text)
            path = root.joinpath(*rel.parts)
            if not path.is_file() or not is_allowed_path(Path(rel_text)):
                continue

            language = LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "Other")
            languages[language] += 1
            size = path.stat().st_size

            if size > self.workspace.settings.max_file_bytes:
                files.append(
                    FileIndexEntry(
                        path=rel_text,
                        language=language,
                        size_bytes=size,
                        line_count=0,
                    )
                )
                continue

            try:
                text = path.read_text(errors="replace")
            except OSError:
                continue

            symbols: list[SymbolInfo] = []
            imports: list[ImportInfo] = []
            if language == "Python":
                symbols, raw_imports = self._parse_python(rel_text, text)
                imports = [self._resolve_import(root, rel_text, item) for item in raw_imports]
            elif language in {"TypeScript", "JavaScript"}:
                symbols, raw_imports = self._parse_javascript_like(rel_text, text)
                imports = [self._resolve_import(root, rel_text, item) for item in raw_imports]

            files.append(
                FileIndexEntry(
                    path=rel_text,
                    language=language,
                    size_bytes=size,
                    line_count=text.count("\n") + (1 if text else 0),
                    symbols=symbols,
                    imports=imports,
                )
            )

        dependencies: list[DependencyEdge] = []
        seen_edges: set[tuple[str, str]] = set()
        for entry in files:
            for item in entry.imports:
                if not item.local or not item.resolved_path:
                    continue
                edge = (entry.path, item.resolved_path)
                if edge in seen_edges:
                    continue
                seen_edges.add(edge)
                dependencies.append(DependencyEdge(source=edge[0], target=edge[1]))

        result = RepositoryIndex(
            repository_id=repository_id,
            file_count=len(self.workspace.tree(repository_id)),
            indexed_file_count=len(files),
            symbol_count=sum(len(file.symbols) for file in files),
            dependency_count=len(dependencies),
            languages=dict(sorted(languages.items(), key=lambda item: (-item[1], item[0]))),
            files=files,
            dependencies=sorted(dependencies, key=lambda edge: (edge.source, edge.target)),
        )
        self._cache[repository_id] = result
        return result

    def search_symbols(self, repository_id: str, query: str, limit: int = 30) -> list[SymbolInfo]:
        needle = query.strip().lower()
        if not needle:
            return []
        index = self.build(repository_id)
        ranked: list[tuple[int, SymbolInfo]] = []
        for entry in index.files:
            for symbol in entry.symbols:
                name = symbol.name.lower()
                if needle not in name:
                    continue
                score = 100 if name == needle else 70 if name.startswith(needle) else 40
                ranked.append((score, symbol))
        ranked.sort(key=lambda item: (-item[0], item[1].path, item[1].line))
        return [symbol for _, symbol in ranked[:limit]]

    def dependency_report(self, repository_id: str, relative_path: str) -> DependencyReport:
        normalized = PurePosixPath(relative_path).as_posix()
        index = self.build(repository_id)
        entry = next((file for file in index.files if file.path == normalized), None)
        if entry is None:
            raise FileNotFoundError(normalized)
        reverse = sorted({edge.source for edge in index.dependencies if edge.target == normalized})
        return DependencyReport(path=normalized, imports=entry.imports, imported_by=reverse)

    def _parse_python(self, path: str, text: str) -> tuple[list[SymbolInfo], list[_RawImport]]:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return [], []

        symbols: list[SymbolInfo] = []
        imports: list[_RawImport] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                parent_is_class = any(
                    isinstance(parent, ast.ClassDef) and node in parent.body
                    for parent in ast.walk(tree)
                    if isinstance(parent, ast.ClassDef)
                )
                symbols.append(
                    SymbolInfo(
                        name=node.name,
                        kind="method" if parent_is_class else "function",
                        path=path,
                        line=node.lineno,
                        end_line=getattr(node, "end_lineno", None),
                        exported=not node.name.startswith("_"),
                    )
                )
            elif isinstance(node, ast.ClassDef):
                symbols.append(
                    SymbolInfo(
                        name=node.name,
                        kind="class",
                        path=path,
                        line=node.lineno,
                        end_line=getattr(node, "end_lineno", None),
                        exported=not node.name.startswith("_"),
                    )
                )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(_RawImport(alias.name, [alias.asname or alias.name], node.lineno))
            elif isinstance(node, ast.ImportFrom):
                module = "." * node.level + (node.module or "")
                names = [alias.asname or alias.name for alias in node.names]
                imports.append(_RawImport(module, names, node.lineno))

        symbols.sort(key=lambda item: (item.line, item.name))
        imports.sort(key=lambda item: item.line)
        return symbols, imports

    def _parse_javascript_like(self, path: str, text: str) -> tuple[list[SymbolInfo], list[_RawImport]]:
        symbols: list[SymbolInfo] = []
        imports: list[_RawImport] = []

        for line_number, line in enumerate(text.splitlines(), 1):
            import_match = _JS_IMPORT_RE.search(line)
            if import_match:
                module = import_match.group("module") or import_match.group("side_effect") or import_match.group("require")
                body = import_match.group("body") or ""
                names = re.findall(r"[A-Za-z_$][\w$]*", body)
                imports.append(_RawImport(module, names[:20], line_number))

            exported = line.lstrip().startswith("export ")
            for regex, kind in (
                (_JS_CLASS_RE, "class"),
                (_JS_FUNCTION_RE, "function"),
                (_JS_ARROW_RE, "function"),
                (_JS_INTERFACE_RE, "interface"),
                (_JS_TYPE_RE, "type"),
            ):
                match = regex.search(line)
                if match:
                    symbols.append(
                        SymbolInfo(
                            name=match.group(1),
                            kind=kind,
                            path=path,
                            line=line_number,
                            exported=exported,
                        )
                    )
                    break

        return symbols, imports

    def _resolve_import(self, root: Path, source_path: str, raw: _RawImport) -> ImportInfo:
        module = raw.module
        resolved: str | None = None
        local = module.startswith(".")

        if source_path.endswith(('.py', '.pyi')):
            resolved = self._resolve_python_module(root, source_path, module)
            local = local or resolved is not None
        elif source_path.endswith((".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")):
            resolved = self._resolve_js_module(root, source_path, module)
            local = local or resolved is not None

        return ImportInfo(
            path=source_path,
            module=module,
            names=raw.names,
            line=raw.line,
            local=local,
            resolved_path=resolved,
        )

    def _resolve_python_module(self, root: Path, source_path: str, module: str) -> str | None:
        source = PurePosixPath(source_path)
        if module.startswith("."):
            level = len(module) - len(module.lstrip("."))
            suffix = module[level:]
            base = source.parent
            for _ in range(max(0, level - 1)):
                base = base.parent
            parts = [part for part in suffix.split(".") if part]
            candidate = PurePosixPath(base, *parts)
        else:
            candidate = PurePosixPath(*module.split("."))

        options = [
            PurePosixPath(str(candidate) + ".py"),
            candidate / "__init__.py",
        ]
        return self._first_existing(root, options)

    def _resolve_js_module(self, root: Path, source_path: str, module: str) -> str | None:
        if not module.startswith("."):
            return None
        base = PurePosixPath(source_path).parent / module
        extensions = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
        options = [PurePosixPath(str(base) + ext) for ext in extensions]
        options.extend(base / f"index{ext}" for ext in extensions)
        return self._first_existing(root, options)

    @staticmethod
    def _first_existing(root: Path, options: list[PurePosixPath]) -> str | None:
        for option in options:
            normalized = PurePosixPath(option).as_posix()
            candidate = root.joinpath(*PurePosixPath(normalized).parts)
            if candidate.is_file():
                return normalized
        return None
