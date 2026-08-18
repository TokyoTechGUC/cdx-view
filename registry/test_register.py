"""Tests for project/dataset DB operations in register.py.

Uses a temp file DB so the real storage is never touched.
Preprocessing is not tested here — only DB logic.
"""

import sqlite3
import uuid
from datetime import datetime

import pytest

import register


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr(register, "DB_PATH", db)
    monkeypatch.setattr(register, "STORAGE_DIR", tmp_path)
    register.init_database()


def _query(sql, params=()):
    with sqlite3.connect(register.DB_PATH) as conn:
        return conn.execute(sql, params).fetchall()


def _insert_dataset(project_id: str, ds_id: str | None = None) -> str:
    """Insert a dataset row directly, bypassing preprocessing."""
    ds_id = ds_id or str(uuid.uuid4())
    with sqlite3.connect(register.DB_PATH) as conn:
        conn.execute(
            "INSERT INTO datasets (id, name, file_path, description, project_id, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (ds_id, "DS", "fake.zarr", None, project_id, datetime.now().isoformat()),
        )
        conn.commit()
    return ds_id


# ---------------------------------------------------------------------------
# init_database
# ---------------------------------------------------------------------------

def test_init_creates_all_tables():
    tables = {r[0] for r in _query("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"projects", "datasets", "variable_stats"} <= tables


# ---------------------------------------------------------------------------
# create_project
# ---------------------------------------------------------------------------

def test_create_project_returns_uuid():
    pid = register.create_project("Tokyo Heat")
    assert uuid.UUID(pid)  # valid UUID


def test_create_project_inserts_row():
    pid = register.create_project("Tokyo Heat", "some desc")
    rows = _query("SELECT title, description FROM projects WHERE id = ?", (pid,))
    assert rows == [("Tokyo Heat", "some desc")]


def test_create_project_description_defaults_to_none():
    pid = register.create_project("No Desc")
    rows = _query("SELECT description FROM projects WHERE id = ?", (pid,))
    assert rows[0][0] is None


# ---------------------------------------------------------------------------
# delete_project
# ---------------------------------------------------------------------------

def test_delete_project_removes_row():
    pid = register.create_project("To Delete")
    register.delete_project(pid)
    rows = _query("SELECT id FROM projects WHERE id = ?", (pid,))
    assert rows == []


def test_delete_project_cascades_to_datasets():
    pid = register.create_project("Parent")
    ds_id = _insert_dataset(pid)
    register.delete_project(pid)
    rows = _query("SELECT id FROM datasets WHERE id = ?", (ds_id,))
    assert rows == []


def test_delete_project_unknown_id_exits():
    with pytest.raises(SystemExit):
        register.delete_project("nonexistent-id")


# ---------------------------------------------------------------------------
# register_dataset validation
# ---------------------------------------------------------------------------

def test_register_dataset_rejects_unknown_project():
    with pytest.raises(SystemExit):
        register.register_dataset("Name", "file.nc", "nonexistent-uuid")
