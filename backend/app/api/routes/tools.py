from fastapi import APIRouter, HTTPException

from app.services.database import Database
from app.tools.registry import ToolRegistry

router = APIRouter(prefix="/tools", tags=["Tools"])
registry = ToolRegistry()
db = Database()


@router.get("")
def list_tools():
    return {"tools": registry.descriptors()}


@router.get("/audit/{run_id}")
def tool_audit(run_id: str):
    if not db.get_run(run_id):
        raise HTTPException(404, "Run not found")
    return {"run_id": run_id, "entries": db.audits(run_id)}
