from app.schemas.agent import (
    AgentAnswer,
    AgentDecisionType,
    AgentObservation,
    AgentPlan,
    AgentStepDecision,
    FileReference,
    PatchProposal,
    TaskType,
    ToolCall,
)


class MockLLMProvider:
    def plan(self, question, tree, tools):
        q = question.lower()
        if any(x in q for x in ["generate test", "generate tests", "add tests", "write tests"]):
            task = TaskType.TESTS
        elif any(x in q for x in ["fix", "add ", "change", "validate"]):
            task = TaskType.CHANGE
        elif any(x in q for x in ["why", "failing", "error", "bug"]):
            task = TaskType.DIAGNOSE
        elif "break" in q or "depend" in q or "impact" in q:
            task = TaskType.IMPACT
        else:
            task = TaskType.EXPLAIN
        terms = "login auth authentication" if any(x in q for x in ["login", "auth"]) else question
        return AgentPlan(
            goal=question,
            task_type=task,
            calls=[
                ToolCall(
                    tool="search_code",
                    arguments={"query": terms, "limit": 20},
                    reason="Searching for the strongest implementation and test evidence",
                )
            ],
        )

    def next_action(self, question, plan, observations, tools, *, step, max_steps, files_read):
        if step >= max_steps:
            return AgentStepDecision(action=AgentDecisionType.FINISH, activity="Evidence budget reached; preparing the answer")

        search_obs = next((o for o in observations if o.tool == "search_code" and o.status == "ok"), None)
        if not search_obs:
            return AgentStepDecision(
                action=AgentDecisionType.TOOL,
                activity="Searching the repository",
                tool_call=ToolCall(
                    tool="search_code",
                    arguments={"query": question, "limit": 20},
                    reason="Locate relevant code",
                ),
            )

        # Read the best search hits one at a time. Results are normalised by the orchestrator.
        hits = search_obs.result if isinstance(search_obs.result, list) else []
        for hit in hits[:4]:
            path = hit.get("path") if isinstance(hit, dict) else None
            if path and path not in files_read:
                return AgentStepDecision(
                    action=AgentDecisionType.TOOL,
                    activity=f"Reading {path}",
                    tool_call=ToolCall(
                        tool="read_file",
                        arguments={"relative": path, "max_chars": 14000},
                        reason=f"Inspect the high-ranking evidence in {path}",
                    ),
                )

        if plan.task_type in {TaskType.IMPACT, TaskType.CHANGE, TaskType.TESTS}:
            inspected = {
                o.arguments.get("relative")
                for o in observations
                if o.tool == "inspect_dependencies" and o.status == "ok"
            }
            for path in files_read[:3]:
                if path not in inspected:
                    return AgentStepDecision(
                        action=AgentDecisionType.TOOL,
                        activity=f"Checking dependencies for {path}",
                        tool_call=ToolCall(
                            tool="inspect_dependencies",
                            arguments={"relative": path},
                            reason="Identify direct and reverse dependency impact",
                        ),
                    )

        return AgentStepDecision(action=AgentDecisionType.FINISH, activity="Evidence is sufficient; preparing findings")

    def answer(self, question, context):
        joined = "\n".join(c.get("content", "") for c in context)
        paths = [c["path"] for c in context]
        refs = [
            FileReference(
                path=c["path"],
                start_line=c.get("start_line"),
                end_line=c.get("end_line"),
                reason=c.get("reason", "Relevant repository evidence"),
            )
            for c in context
        ]
        if "username" in joined and "email" in joined and any("login" in p.lower() or "auth" in p.lower() for p in paths):
            return AgentAnswer(
                summary="The login flow has a request-field mismatch.",
                what_i_found=[
                    "The frontend sends `username`.",
                    "The backend login endpoint expects `email`.",
                    "The existing authentication test documents the backend contract.",
                ],
                why="The request reaches the backend without the field its login schema expects, so authentication is rejected before credential verification.",
                suggested_fix="Change the login form payload to send `email`, keeping the backend contract unchanged.",
                impact=[
                    "Login form only",
                    "Authentication service contract stays stable",
                    "Existing backend tests should continue to pass",
                ],
                confidence=0.96,
                files=refs,
                can_propose_patch=True,
            )
        return AgentAnswer(
            summary="I found the most relevant repository areas for your question.",
            what_i_found=[f"Reviewed {len(context)} focused code regions instead of sending the whole repository."],
            why="RepoLens used bounded search, file reads, and dependency inspection to collect evidence.",
            suggested_fix=None,
            impact=[],
            confidence=0.72,
            files=refs,
            can_propose_patch=any(x in question.lower() for x in ["fix", "add", "change", "generate"]),
        )

    def patch(self, question, context):
        paths = {c["path"] for c in context}
        if "frontend/src/LoginForm.tsx" in paths:
            diff = '''diff --git a/frontend/src/LoginForm.tsx b/frontend/src/LoginForm.tsx
--- a/frontend/src/LoginForm.tsx
+++ b/frontend/src/LoginForm.tsx
@@ -1,8 +1,8 @@
 export async function submitLogin(email: string, password: string) {
   const response = await fetch("/api/login", {
     method: "POST",
     headers: { "Content-Type": "application/json" },
-    body: JSON.stringify({ username: email, password }),
+    body: JSON.stringify({ email, password }),
   });
   return response.json();
 }
'''
            return PatchProposal(
                summary="Align the frontend login payload with the backend contract.",
                unified_diff=diff,
                affected_files=["frontend/src/LoginForm.tsx"],
                risk_level="low",
                confidence=0.97,
            )
        return PatchProposal(
            summary="No safe deterministic demo patch is available for this request.",
            unified_diff="",
            affected_files=[],
            risk_level="unknown",
            confidence=0.2,
        )
