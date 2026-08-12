import re, subprocess
from pathlib import Path
from app.services.workspace import WorkspaceService
from app.services.security import safe_resolve

class PatchService:
    def __init__(self): self.workspace=WorkspaceService()
    def validate_scope(self, repository_id:str, diff:str, allowed_files:list[str]) -> list[str]:
        touched=[]
        for line in diff.splitlines():
            if line.startswith("+++ b/") or line.startswith("--- a/"):
                p=line[6:].strip()
                if p!="/dev/null" and p not in touched: touched.append(p)
        extra=[p for p in touched if p not in set(allowed_files)]
        if extra: raise ValueError(f"Patch touches files outside approved scope: {', '.join(extra)}")
        root=self.workspace.get_repo_path(repository_id)
        for p in touched: safe_resolve(root,p)
        return touched

    def apply_to(self, target:Path, diff:str):
        proc=subprocess.run(["git","apply","--whitespace=nowarn","-"],cwd=target,input=diff,text=True,capture_output=True,timeout=15)
        if proc.returncode!=0: raise RuntimeError(proc.stderr.strip() or "Patch could not be applied")
