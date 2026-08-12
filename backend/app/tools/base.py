from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Type

from pydantic import BaseModel

from app.schemas.agent import ToolPermission


@dataclass(frozen=True)
class RegisteredTool:
    name: str
    permission: ToolPermission
    handler: Callable[..., Any]
    description: str
    args_model: Type[BaseModel]
    enabled: bool = True
    requires_explicit_approval: bool = False


class PermissionDenied(Exception):
    pass
