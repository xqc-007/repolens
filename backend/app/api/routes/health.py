from fastapi import APIRouter
from app.core.config import get_settings
router=APIRouter(prefix="/health",tags=["Health"])
@router.get("")
def health():
    s=get_settings(); return {"status":"ok","service":s.app_name,"environment":s.app_environment,"repository_mode":s.repository_mode,"llm_mode":s.llm_mode}
