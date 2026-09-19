"""Tests for app/database/repository.py."""

from uuid import uuid4

from app.database import repository

# ---------------------------------------------------------------------------
# list_projects
# ---------------------------------------------------------------------------


def test_list_projects_empty():
    assert repository.list_projects() == []


def test_list_projects_orders_newest_first(insert_project):
    insert_project(str(uuid4()), "Older", created_at="2024-01-01T00:00:00")
    insert_project(str(uuid4()), "Newer", created_at="2024-06-01T00:00:00")

    result = repository.list_projects()

    assert [p.title for p in result] == ["Newer", "Older"]


def test_list_projects_omits_datasets(insert_project, insert_dataset):
    project_id = str(uuid4())
    insert_project(project_id, "Project")
    insert_dataset(str(uuid4()), project_id, "DS", "ds.zarr")

    (project,) = repository.list_projects()

    assert not hasattr(project, "datasets")


# ---------------------------------------------------------------------------
# get_project
# ---------------------------------------------------------------------------


def test_get_project_missing_returns_none():
    assert repository.get_project(str(uuid4())) is None


def test_get_project_separates_background_layers(insert_project, insert_dataset):
    project_id = str(uuid4())
    insert_project(project_id, "Project")
    insert_dataset(str(uuid4()), project_id, "Foreground", "fg.zarr", is_background=False)
    insert_dataset(str(uuid4()), project_id, "Background", "bg.zarr", is_background=True)

    project = repository.get_project(project_id)

    assert [d.name for d in project.datasets] == ["Foreground"]
    assert [d.name for d in project.background_layers] == ["Background"]


def test_get_project_includes_variable_stats(insert_project, insert_dataset, insert_variable_stats):
    project_id = str(uuid4())
    dataset_id = str(uuid4())
    insert_project(project_id, "Project")
    insert_dataset(dataset_id, project_id, "DS", "ds.zarr")
    insert_variable_stats(dataset_id, "T2", vmin=250.0, vmax=310.0, units="K")

    project = repository.get_project(project_id)

    (variable,) = project.datasets[0].variables
    assert variable.name == "T2"
    assert variable.vmin == 250.0
    assert variable.units == "K"


def test_get_project_detects_cog_format_from_extension(insert_project, insert_dataset):
    project_id = str(uuid4())
    insert_project(project_id, "Project")
    insert_dataset(str(uuid4()), project_id, "DS", "ds.tif")

    project = repository.get_project(project_id)

    assert project.datasets[0].format == "cog"


def test_get_project_defaults_to_zarr_format(insert_project, insert_dataset):
    project_id = str(uuid4())
    insert_project(project_id, "Project")
    insert_dataset(str(uuid4()), project_id, "DS", "ds.zarr")

    project = repository.get_project(project_id)

    assert project.datasets[0].format == "zarr"


# ---------------------------------------------------------------------------
# get_dataset
# ---------------------------------------------------------------------------


def test_get_dataset_missing_returns_none():
    assert repository.get_dataset(str(uuid4())) is None


def test_get_dataset_resolves_path_under_storage_dir(tmp_db, insert_project, insert_dataset):
    project_id = str(uuid4())
    dataset_id = str(uuid4())
    insert_project(project_id, "Project")
    insert_dataset(dataset_id, project_id, "DS", "sub/ds.zarr")

    dataset = repository.get_dataset(dataset_id)

    assert dataset.file_path == f"{tmp_db.parent}/sub/ds.zarr"
