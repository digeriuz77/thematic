import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.database import engine, Base
from backend.app.config import get_settings
from backend.app.routers import projects, sources, analysis

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure upload/report directories exist
    for dir_path in [settings.uploads_dir, settings.reports_dir, settings.maps_dir]:
        os.makedirs(dir_path, exist_ok=True)
    # Create database tables
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    description="Hosted thematic analysis toolkit following Braun & Clarke (2006)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])


@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": settings.app_name}


# Serve frontend static files for non-API routes
frontend_build_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")

if os.path.exists(frontend_build_dir):
    # Mount static assets directory
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_build_dir, "assets"), html=False), name="assets")

    @app.get("/{path:path}")
    async def serve_frontend(path: str, request: Request):
        # Don't interfere with API routes
        if path.startswith("api/"):
            return {"detail": "Not Found"}
        # Serve index.html for all non-API, non-asset routes (SPA routing)
        index_path = os.path.join(frontend_build_dir, "index.html")
        return FileResponse(index_path)
