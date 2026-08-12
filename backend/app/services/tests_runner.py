import os, shlex, subprocess, time, shutil
from app.core.config import get_settings
from app.services.workspace import WorkspaceService
from app.services.patches import PatchService

class TestService:
    def __init__(self): self.settings=get_settings(); self.workspace=WorkspaceService(); self.patches=PatchService()
    def run(self, repository_id:str, command:str, diff:str|None=None):
        if repository_id != "demo": raise ValueError("V1 executes tests only for the trusted demo repository. Production arbitrary-repo execution requires a hardened sandbox.")
        if command not in self.settings.allowed_test_command_list: raise ValueError("Test command is not allowlisted")
        target=self.workspace.copy_for_execution(repository_id)
        try:
            if diff: self.patches.apply_to(target,diff)
            env={"PATH":os.environ.get("PATH","") ,"PYTHONPATH":str(target)}
            start=time.perf_counter()
            p=subprocess.run(shlex.split(command),cwd=target,capture_output=True,text=True,timeout=self.settings.test_timeout_seconds,env=env)
            ms=int((time.perf_counter()-start)*1000)
            output=(p.stdout+"\n"+p.stderr).strip()[-6000:]
            return {"status":"passed" if p.returncode==0 else "failed","command":command,"exit_code":p.returncode,"duration_ms":ms,"output_summary":output}
        finally:
            shutil.rmtree(target,ignore_errors=True)
