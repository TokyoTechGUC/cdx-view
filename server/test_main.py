"""Tests for app/main.py.

Covers /health, /projects, /projects/{id}. Tile-serving endpoints
(/tiles, /cog) aren't covered here — exercising them needs real
geospatial fixture files (see registry/test_preprocess.py for that
kind of setup).
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_projects_empty(client):
    response = client.get("/projects")

    assert response.status_code == 200
    assert response.json() == []


def test_get_projects_returns_summaries(client, insert_project):
    insert_project(str(uuid4()), "Project", description="desc")

    response = client.get("/projects")

    assert response.status_code == 200
    [summary] = response.json()
    assert summary["title"] == "Project"
    assert summary["description"] == "desc"
    assert "datasets" not in summary


def test_get_project_by_id_found(client, insert_project, insert_dataset):
    project_id = str(uuid4())
    insert_project(project_id, "Project")
    insert_dataset(str(uuid4()), project_id, "DS", "ds.zarr")

    response = client.get(f"/projects/{project_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Project"
    assert body["datasets"][0]["name"] == "DS"


def test_get_project_by_id_not_found(client):
    response = client.get("/projects/does-not-exist")

    assert response.status_code == 404
