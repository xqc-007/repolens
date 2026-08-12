from __future__ import annotations

from app.schemas.agent import TaskType, ToolPermission
from app.schemas.tools import ToolExecutionContext
from app.tools.base import PermissionDenied


class ToolPermissionPolicy:
    """Application-enforced capability policy.

    The model can request capabilities, but this policy is the authority that decides
    whether a tool may execute. WRITE remains disabled in V1 regardless of model/user text.
    """

    def authorize(self, permission: ToolPermission, context: ToolExecutionContext) -> None:
        if permission is ToolPermission.READ:
            return

        if permission is ToolPermission.WRITE:
            raise PermissionDenied("WRITE tools are disabled in RepoLens V1")

        if permission is ToolPermission.PROPOSE:
            if context.task_type not in {TaskType.CHANGE, TaskType.TESTS}:
                raise PermissionDenied(
                    "PROPOSE tools are allowed only for change or test-generation tasks"
                )
            if ToolPermission.PROPOSE not in context.approved_permissions:
                raise PermissionDenied("PROPOSE permission has not been granted for this run")
            return

        if permission is ToolPermission.EXECUTE:
            if ToolPermission.EXECUTE not in context.approved_permissions:
                raise PermissionDenied("EXECUTE permission has not been granted for this run")
            if not context.explicit_execution_approval:
                raise PermissionDenied("EXECUTE tools require explicit user approval")
            return

        raise PermissionDenied(f"Unsupported permission: {permission.value}")
