import asyncio
import json

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.orchestrator import AgentOrchestrator
from app.schemas.agent import AgentAnswer, PatchProposal, TaskType, ToolPermission
from app.schemas.api import AskRequest, AgentRunResponse, TestRunRequest, TestRunResponse
from app.schemas.tools import ToolExecutionContext
from app.services.database import Database
from app.tools.registry import ToolRegistry

router = APIRouter(prefix="/agent/runs", tags=["Agent"])
db = Database()
agent = AgentOrchestrator()
tools = ToolRegistry(db)


@router.post("", response_model=AgentRunResponse)
def create(req: AskRequest, bg: BackgroundTasks):
    rid = agent.start(req.repository_id, req.question)
    bg.add_task(agent.execute, rid)
    return AgentRunResponse(id=rid, status="queued", question=req.question)


def serialize(r):
    return AgentRunResponse(
        id=r["id"],
        status=r["status"],
        question=r["question"],
        answer=AgentAnswer.model_validate_json(r["answer_json"]) if r.get("answer_json") else None,
        patch=PatchProposal.model_validate_json(r["patch_json"]) if r.get("patch_json") else None,
        error=r.get("error"),
    )


@router.get("/{run_id}", response_model=AgentRunResponse)
def get(run_id: str):
    r = db.get_run(run_id)
    if not r:
        raise HTTPException(404, "Run not found")
    return serialize(r)


@router.get("/{run_id}/events")
async def events(run_id: str):
    async def stream():
        last = 0
        for _ in range(240):
            rows = db.events(run_id, last)
            for e in rows:
                last = e["id"]
                yield f"data: {json.dumps(e)}\n\n"
            r = db.get_run(run_id)
            if r and r["status"] in {"completed", "failed"} and not rows:
                break
            await asyncio.sleep(0.35)

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.post("/{run_id}/tests", response_model=TestRunResponse)
def run_tests(run_id: str, req: TestRunRequest):
    r = db.get_run(run_id)
    if not r:
        raise HTTPException(404, "Run not found")
    patch = PatchProposal.model_validate_json(r["patch_json"]) if r.get("patch_json") else None
    if req.apply_patch and not patch:
        raise HTTPException(400, "No proposed patch exists")
    try:
        tool_result = tools.execute(
            "run_tests",
            ToolExecutionContext(
                repository_id=r["repository_id"],
                run_id=run_id,
                task_type=TaskType.TESTS,
                approved_permissions={ToolPermission.EXECUTE},
                explicit_execution_approval=True,
            ),
            {
                "command": req.command,
                "diff": patch.unified_diff if req.apply_patch and patch else None,
            },
        )
        return TestRunResponse.model_validate(tool_result.result)
    except Exception as e:
        raise HTTPException(400, str(e))
