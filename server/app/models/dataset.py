from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Dataset(BaseModel):
    """Internal dataset record, including fields not exposed by the public API."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    file_path: str
    description: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VariableStats(BaseModel):
    """Per-variable statistics used to render colorbars."""

    name: str
    vmin: float
    vmax: float
    units: str | None = None
    long_name: str | None = None
    times: list[str] | None = None
    colormap: str | None = None


def _format_from_path(file_path: str) -> str:
    return "cog" if Path(file_path).suffix.lower() in (".tif", ".tiff") else "zarr"


class DatasetPublic(BaseModel):
    """Public-facing dataset view returned by the API."""

    id: UUID
    name: str
    description: str | None = None
    variables: list[VariableStats]
    format: Literal["zarr", "cog"]
