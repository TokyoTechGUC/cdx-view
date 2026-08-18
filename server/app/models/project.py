from uuid import UUID
from pydantic import BaseModel

from .dataset import DatasetPublic


class ProjectSummary(BaseModel):
    """Lightweight project listing — id, title, description only."""
    id: UUID
    title: str
    description: str | None = None


class ProjectPublic(BaseModel):
    """Full project detail with all datasets and variable stats."""
    id: UUID
    title: str
    description: str | None = None
    datasets: list[DatasetPublic]
    background_layers: list[DatasetPublic] = []