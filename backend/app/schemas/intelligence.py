from typing import Literal

from pydantic import BaseModel, Field


class SymbolInfo(BaseModel):
    name: str
    kind: Literal["class", "function", "method", "interface", "type", "variable"]
    path: str
    line: int
    end_line: int | None = None
    exported: bool = False


class ImportInfo(BaseModel):
    path: str
    module: str
    names: list[str] = Field(default_factory=list)
    line: int
    local: bool = False
    resolved_path: str | None = None


class FileIndexEntry(BaseModel):
    path: str
    language: str
    size_bytes: int
    line_count: int
    symbols: list[SymbolInfo] = Field(default_factory=list)
    imports: list[ImportInfo] = Field(default_factory=list)


class DependencyEdge(BaseModel):
    source: str
    target: str
    kind: Literal["import"] = "import"


class RepositoryIndex(BaseModel):
    repository_id: str
    file_count: int
    indexed_file_count: int
    symbol_count: int
    dependency_count: int
    languages: dict[str, int] = Field(default_factory=dict)
    files: list[FileIndexEntry] = Field(default_factory=list)
    dependencies: list[DependencyEdge] = Field(default_factory=list)


class SymbolSearchResponse(BaseModel):
    query: str
    matches: list[SymbolInfo] = Field(default_factory=list)


class DependencyReport(BaseModel):
    path: str
    imports: list[ImportInfo] = Field(default_factory=list)
    imported_by: list[str] = Field(default_factory=list)
