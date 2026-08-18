"""Repository module for managing projects and datasets in the database."""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import UUID

import app.models.dataset as dataset_models
import app.models.project as project_models

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "/storage"))
DB_PATH = Path(os.getenv("DB_PATH", f"{STORAGE_DIR}/datasets.db"))


@contextmanager
def _get_connection():
    """Open a readonly SQLite connection. The server never writes to the DB."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        yield conn
    finally:
        conn.close()


def list_projects() -> list[project_models.ProjectSummary]:
    """Retrieve all projects (id, title, description only)."""
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, description FROM projects ORDER BY created_at DESC"
        ).fetchall()

    return [
        project_models.ProjectSummary(id=UUID(row[0]), title=row[1], description=row[2])
        for row in rows
    ]


def get_project(project_id: str) -> project_models.ProjectPublic | None:
    """Retrieve a single project with its datasets and variable stats."""
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT p.id, p.title, p.description,
                   d.id, d.name, d.description, d.file_path, d.is_background,
                   vs.variable, vs.vmin, vs.vmax, vs.units, vs.long_name, vs.colormap
            FROM projects p
            LEFT JOIN datasets d ON d.project_id = p.id
            LEFT JOIN variable_stats vs ON vs.dataset_id = d.id
            WHERE p.id = ?
            ORDER BY d.created_at DESC, vs.variable
        """,
            (project_id,),
        ).fetchall()

    if not rows:
        return None

    return _rows_to_projects(rows)[0]


def get_dataset(dataset_id: str) -> dataset_models.Dataset | None:
    """Retrieve a dataset by its ID (used internally to resolve tile paths)."""
    with _get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, name, file_path, description, created_at
            FROM datasets
            WHERE id = ?
        """,
            (dataset_id,),
        ).fetchone()

    if row is None:
        return None

    dataset_id, name, file_path, description, created_at = row
    return dataset_models.Dataset(
        id=UUID(dataset_id),
        name=name,
        file_path=f"{STORAGE_DIR}/{file_path}",
        description=description,
        created_at=datetime.fromisoformat(created_at),
    )


def _rows_to_projects(rows: list[tuple]) -> list[project_models.ProjectPublic]:
    """Build a list of ProjectPublic from flat JOIN rows."""
    projects: dict[str, project_models.ProjectPublic] = {}
    datasets: dict[str, dataset_models.DatasetPublic] = {}

    for (
        proj_id,
        proj_title,
        proj_desc,
        ds_id,
        ds_name,
        ds_desc,
        ds_file_path,
        ds_is_background,
        variable,
        vmin,
        vmax,
        units,
        long_name,
        colormap,
    ) in rows:
        if proj_id not in projects:
            projects[proj_id] = project_models.ProjectPublic(
                id=UUID(proj_id),
                title=proj_title,
                description=proj_desc,
                datasets=[],
                background_layers=[],
            )

        if ds_id is not None and ds_id not in datasets:
            ds = dataset_models.DatasetPublic(
                id=UUID(ds_id),
                name=ds_name,
                description=ds_desc,
                variables=[],
                format=dataset_models._format_from_path(ds_file_path),
            )
            datasets[ds_id] = ds
            if ds_is_background:
                projects[proj_id].background_layers.append(ds)
            else:
                projects[proj_id].datasets.append(ds)

        if ds_id is not None and variable is not None:
            datasets[ds_id].variables.append(
                dataset_models.VariableStats(
                    name=variable,
                    vmin=vmin,
                    vmax=vmax,
                    units=units,
                    long_name=long_name,
                    colormap=colormap,
                )
            )

    return list(projects.values())
