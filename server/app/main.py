from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from titiler.core.factory import ColorMapFactory
from titiler.core.factory import TilerFactory as COGTilerFactory
from titiler.xarray.extensions import DatasetMetadataExtension
from titiler.xarray.factory import TilerFactory as XArrayTilerFactory

from app.database import get_dataset, get_project, list_projects
from app.models.project import ProjectPublic, ProjectSummary


class ForwardedPrefixMiddleware:
    """Read X-Forwarded-Prefix and set ASGI root_path so titiler builds correct tile URLs."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            headers = dict(scope["headers"])
            prefix = headers.get(b"x-forwarded-prefix", b"").decode()
            if prefix:
                scope["root_path"] = prefix
        await self.app(scope, receive, send)


app = FastAPI()

app.add_middleware(ForwardedPrefixMiddleware)

# Development purpose
# TODO: avoid hardcoded port number
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5180",
    ],
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/projects", response_model=list[ProjectSummary])
def get_projects():
    return list_projects()


@app.get("/projects/{project_id}", response_model=ProjectPublic)
def get_project_by_id(project_id: str):
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return project


def DatasetPathParams(dataset_id: str = Query(..., description="Dataset ID")) -> str:
    """Resolve dataset_id to a file path via the dataset registry."""
    dataset = get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")
    return dataset.file_path


md = XArrayTilerFactory(
    path_dependency=DatasetPathParams,
    router_prefix="/tiles",
    extensions=[DatasetMetadataExtension()],
)
app.include_router(md.router, prefix="/tiles", tags=["Tiles"])

cog = COGTilerFactory(path_dependency=DatasetPathParams, router_prefix="/cog")
app.include_router(cog.router, prefix="/cog", tags=["COG"])

app.include_router(ColorMapFactory().router, tags=["ColorMaps"])
