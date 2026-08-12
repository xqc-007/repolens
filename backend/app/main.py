from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.agent_runs import router as agent_router
from app.api.routes.health import router as health_router
from app.api.routes.intelligence import router as intelligence_router
from app.api.routes.repositories import router as repositories_router
from app.api.routes.retrieval import router as retrieval_router
from app.api.routes.tools import router as tools_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.4.0",
        debug=settings.app_debug,
        description="Controlled AI repository assistant",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router, prefix="/api")
    app.include_router(repositories_router, prefix="/api")
    app.include_router(intelligence_router, prefix="/api")
    app.include_router(retrieval_router, prefix="/api")
    app.include_router(tools_router, prefix="/api")
    app.include_router(agent_router, prefix="/api")
    return app


app = create_app()
