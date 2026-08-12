from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.schemas.agent import ToolPermission
from app.schemas.tools import (
    DependencyArgs,
    ReadFileArgs,
    RepositoryTreeArgs,
    RunTestsArgs,
    SearchCodeArgs,
    ToolDescriptor,
    ToolExecutionContext,
    ToolExecutionResult,
    ValidatePatchArgs,
    WritePlaceholderArgs,
)
from app.services.database import Database
from app.services.patches import PatchService
from app.services.retrieval import RetrievalService
from app.services.tests_runner import TestService
from app.services.workspace import WorkspaceService
from app.tools.base import PermissionDenied, RegisteredTool
from app.tools.permissions import ToolPermissionPolicy


class ToolRegistry:
    def __init__(self, database: Database | None = None):
        self.workspace = WorkspaceService()
        self.retrieval = RetrievalService(self.workspace)
        self.patches = PatchService()
        self.tests = TestService()
        self.db = database or Database()
        self.policy = ToolPermissionPolicy()
        self.tools: dict[str, RegisteredTool] = {
            "repository_tree": RegisteredTool(
                "repository_tree",
                ToolPermission.READ,
                self.workspace.tree,
                "List repository files allowed by the security policy.",
                RepositoryTreeArgs,
            ),
            "search_code": RegisteredTool(
                "search_code",
                ToolPermission.READ,
                self.retrieval.search,
                "Rank code evidence using lexical, symbol, path and dependency signals.",
                SearchCodeArgs,
            ),
            "read_file": RegisteredTool(
                "read_file",
                ToolPermission.READ,
                self.workspace.read_file,
                "Read one security-approved file inside the selected repository.",
                ReadFileArgs,
            ),
            "inspect_dependencies": RegisteredTool(
                "inspect_dependencies",
                ToolPermission.READ,
                self.retrieval.dependencies,
                "Inspect imports and reverse dependencies for a repository file.",
                DependencyArgs,
            ),
            "validate_patch": RegisteredTool(
                "validate_patch",
                ToolPermission.PROPOSE,
                self.patches.validate_scope,
                "Validate that a proposed diff touches only approved repository files.",
                ValidatePatchArgs,
            ),
            "run_tests": RegisteredTool(
                "run_tests",
                ToolPermission.EXECUTE,
                self.tests.run,
                "Run an allowlisted test command in a disposable trusted workspace.",
                RunTestsArgs,
                requires_explicit_approval=True,
            ),
            "github_write": RegisteredTool(
                "github_write",
                ToolPermission.WRITE,
                self._disabled_write,
                "Reserved future GitHub write capability. Disabled in V1.",
                WritePlaceholderArgs,
                enabled=False,
                requires_explicit_approval=True,
            ),
        }

    @staticmethod
    def _disabled_write(**_: Any) -> None:
        raise PermissionDenied("WRITE tools are disabled in RepoLens V1")

    def execute(
        self,
        name: str,
        context: ToolExecutionContext,
        arguments: dict[str, Any] | None = None,
    ) -> ToolExecutionResult:
        tool = self.tools.get(name)
        if not tool:
            self._audit(context, name, "unknown", arguments or {}, "denied")
            raise KeyError(f"Unknown tool: {name}")

        raw_args = dict(arguments or {})
        try:
            if not tool.enabled:
                raise PermissionDenied(f"Tool {name} is disabled in RepoLens V1")
            self.policy.authorize(tool.permission, context)
            validated = tool.args_model.model_validate(raw_args)
            kwargs = validated.model_dump(exclude_none=True)
            # The caller owns repository scope; tool arguments cannot override it.
            kwargs["repository_id"] = context.repository_id
            result = tool.handler(**kwargs)
            self._audit(context, name, tool.permission.value, raw_args, "ok")
            return ToolExecutionResult(
                tool=name,
                permission=tool.permission,
                status="ok",
                result=result,
            )
        except (PermissionDenied, ValidationError, ValueError, FileNotFoundError, RuntimeError) as exc:
            self._audit(context, name, tool.permission.value, raw_args, "denied" if isinstance(exc, PermissionDenied) else "error")
            raise

    def catalogue(self) -> list[dict]:
        return [descriptor.model_dump(mode="json") for descriptor in self.descriptors()]

    def descriptors(self) -> list[ToolDescriptor]:
        return [
            ToolDescriptor(
                name=tool.name,
                permission=tool.permission,
                description=tool.description,
                enabled=tool.enabled,
                requires_explicit_approval=tool.requires_explicit_approval,
            )
            for tool in self.tools.values()
        ]

    def _audit(
        self,
        context: ToolExecutionContext,
        tool: str,
        permission: str,
        arguments: dict[str, Any],
        status: str,
    ) -> None:
        if context.run_id:
            self.db.audit(context.run_id, tool, permission, arguments, status)
