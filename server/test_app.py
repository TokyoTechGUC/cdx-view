"""Tests for the database repository layer and the FastAPI endpoints built on it.

Uses a temp file DB with the same schema registry/register.py creates, so
these run without a real deployment. Tile-serving endpoints (/tiles, /cog)
are not covered here — exercising them needs real geospatial fixture files
(see registry/test_preprocess.py for that kind of setup).
"""

import sqlite3
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import repository
from app.main import app

_SCHEMA = """
CREATE TABLE projects (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT,
    created_at  TEXT NOT NULL
);
CREATE TABLE datasets (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    file_path     TEXT NOT NULL,
    description   TEXT,
    project_id    TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    is_background INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL
);
CREATE TABLE variable_stats (
    dataset_id TEXT NOT NULL,
    variable   TEXT NOT NULL,
    vmin       REAL NOT NULL,
    vmax       REAL NOT NULL,
    units      TEXT,
    long_name  TEXT,
    colormap   TEXT,
    PRIMARY KEY (dataset_id, variable),
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);
"""


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(_SCHEMA)
    conn.commit()
    conn.close()
    monkeypatch.setattr(repository, "DB_PATH", db_path)
    monkeypatch.setattr(repository, "STORAGE_DIR", tmp_path)
    return db_path


def insert_project(db_path, project_id, title, description=None, created_at="2024-01-01T00:00:00"):
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO projects (id, title, description, created_at) VALUES (?, ?, ?, ?)",
            (project_id, title, description, created_at),
        )
        conn.commit()


def insert_dataset(
    db_path,
    dataset_id,
    project_id,
    name,
    file_path,
    description=None,
    is_background=False,
    created_at="2024-01-01T00:00:00",
):
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO datasets"
            " (id, name, file_path, description, project_id, is_background, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (dataset_id, name, file_path, description, project_id, int(is_background), created_at),
        )
        conn.commit()


def insert_variable_stats(
    db_path, dataset_id, variable, vmin, vmax, units=None, long_name=None, colormap=None
):
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO variable_stats"
            " (dataset_id, variable, vmin, vmax, units, long_name, colormap)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (dataset_id, variable, vmin, vmax, units, long_name, colormap),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# repository.list_projects
# ---------------------------------------------------------------------------


def test_list_projects_empty(tmp_db):
    assert repository.list_projects() == []


def test_list_projects_orders_newest_first(tmp_db):
    insert_project(tmp_db, str(uuid4()), "Older", created_at="2024-01-01T00:00:00")
    insert_project(tmp_db, str(uuid4()), "Newer", created_at="2024-06-01T00:00:00")

    result = repository.list_projects()

    assert [p.title for p in result] == ["Newer", "Older"]


def test_list_projects_omits_datasets(tmp_db):
    project_id = str(uuid4())
    insert_project(tmp_db, project_id, "Project")
    insert_dataset(tmp_db, str(uuid4()), project_id, "DS", "ds.zarr")

    (project,) = repository.list_projects()

    assert not hasattr(project, "datasets")


# ---------------------------------------------------------------------------
# repository.get_project
# ---------------------------------------------------------------------------


def test_get_project_missing_returns_none(tmp_db):
    assert repository.get_project(str(uuid4())) is None


def test_get_project_separates_background_layers(tmp_db):
    project_id = str(uuid4())
    insert_project(tmp_db, project_id, "Project")
    insert_dataset(tmp_db, str(uuid4()), project_id, "Foreground", "fg.zarr", is_background=False)
    insert_dataset(tmp_db, str(uuid4()), project_id, "Background", "bg.zarr", is_background=True)

    project = repository.get_project(project_id)

    assert [d.name for d in project.datasets] == ["Foreground"]
    assert [d.name for d in project.background_layers] == ["Background"]


def test_get_project_includes_variable_stats(tmp_db):
    project_id = str(uuid4())
    dataset_id = str(uuid4())
    insert_project(tmp_db, project_id, "Project")
    insert_dataset(tmp_db, dataset_id, project_id, "DS", "ds.zarr")
    insert_variable_stats(tmp_db, dataset_id, "T2", vmin=250.0, vmax=310.0, units="K")

    project = repository.get_project(project_id)

    (variable,) = project.datasets[0].variables
    assert variable.name == "T2"
    assert variable.vmin == 250.0
    assert variable.units == "K"


def test_get_project_detects_cog_format_from_extension(tmp_db):
    project_id = str(uuid4())
    insert_project(tmp_db, project_id, "Project")
    insert_dataset(tmp_db, str(uuid4()), project_id, "DS", "ds.tif")

    project = repository.get_project(project_id)

    assert project.datasets[0].format == "cog"


def test_get_project_defaults_to_zarr_format(tmp_db):
    project_id = str(uuid4())
    insert_project(tmp_db, project_id, "Project")
    insert_dataset(tmp_db, str(uuid4()), project_id, "DS", "ds.zarr")

    project = repository.get_project(project_id)

    assert project.datasets[0].format == "zarr"


# ---------------------------------------------------------------------------
# repository.get_dataset
# ---------------------------------------------------------------------------


def test_get_dataset_missing_returns_none(tmp_db):
    assert repository.get_dataset(str(uuid4())) is None


def test_get_dataset_resolves_path_under_storage_dir(tmp_db):
    project_id = str(uuid4())
    dataset_id = str(uuid4())
    insert_project(tmp_db, project_id, "Project")
    insert_dataset(tmp_db, dataset_id, project_id, "DS", "sub/ds.zarr")

    dataset = repository.get_dataset(dataset_id)

    assert dataset.file_path == f"{tmp_db.parent}/sub/ds.zarr"


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_projects_empty(client, tmp_db):
    response = client.get("/projects")

    assert response.status_code == 200
    assert response.json() == []


def test_get_projects_returns_summaries(client, tmp_db):
    insert_project(tmp_db, str(uuid4()), "Project", description="desc")

    response = client.get("/projects")

    assert response.status_code == 200
    [summary] = response.json()
    assert summary["title"] == "Project"
    assert summary["description"] == "desc"
    assert "datasets" not in summary


def test_get_project_by_id_found(client, tmp_db):
    project_id = str(uuid4())
    insert_project(tmp_db, project_id, "Project")
    insert_dataset(tmp_db, str(uuid4()), project_id, "DS", "ds.zarr")

    response = client.get(f"/projects/{project_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Project"
    assert body["datasets"][0]["name"] == "DS"


def test_get_project_by_id_not_found(client, tmp_db):
    response = client.get("/projects/does-not-exist")

    assert response.status_code == 404
