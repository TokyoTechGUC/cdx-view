"""Shared fixtures for server tests.

Sets up a temp SQLite DB with the same schema registry/register.py
creates, so app.database.repository (and anything built on it) can be
tested without a real deployment.
"""

import sqlite3

import pytest

from app.database import repository

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


@pytest.fixture
def insert_project(tmp_db):
    def _insert(project_id, title, description=None, created_at="2024-01-01T00:00:00"):
        with sqlite3.connect(tmp_db) as conn:
            conn.execute(
                "INSERT INTO projects (id, title, description, created_at) VALUES (?, ?, ?, ?)",
                (project_id, title, description, created_at),
            )
            conn.commit()

    return _insert


@pytest.fixture
def insert_dataset(tmp_db):
    def _insert(
        dataset_id,
        project_id,
        name,
        file_path,
        description=None,
        is_background=False,
        created_at="2024-01-01T00:00:00",
    ):
        with sqlite3.connect(tmp_db) as conn:
            conn.execute(
                "INSERT INTO datasets"
                " (id, name, file_path, description, project_id, is_background, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    dataset_id,
                    name,
                    file_path,
                    description,
                    project_id,
                    int(is_background),
                    created_at,
                ),
            )
            conn.commit()

    return _insert


@pytest.fixture
def insert_variable_stats(tmp_db):
    def _insert(dataset_id, variable, vmin, vmax, units=None, long_name=None, colormap=None):
        with sqlite3.connect(tmp_db) as conn:
            conn.execute(
                "INSERT INTO variable_stats"
                " (dataset_id, variable, vmin, vmax, units, long_name, colormap)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (dataset_id, variable, vmin, vmax, units, long_name, colormap),
            )
            conn.commit()

    return _insert
