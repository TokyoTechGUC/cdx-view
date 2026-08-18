"""
cdx-view Registry CLI

Manages projects and datasets in the SQLite database.
Run `python register.py --help` for available commands.
"""

import argparse
import os
import shutil
import sqlite3
import sys
from contextlib import closing, contextmanager
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytz
from preprocess import preprocess

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "./storage"))
DB_PATH = Path(os.getenv("DB_PATH", f"{STORAGE_DIR}/datasets.db"))


@contextmanager
def _get_connection(readonly: bool = False):
    """Context manager: open connection, commit on success, rollback+close on exit.

    Pass readonly=True for SELECT-only operations — opens via SQLite URI ?mode=ro
    and skips commit/rollback entirely.

    Exits with an error message if the database file does not exist yet.
    Use init_database() to create it.
    """
    if not DB_PATH.exists():
        print("Error: Database not found. Run 'just db-init' first.", file=sys.stderr)
        sys.exit(1)
    if readonly:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        if not readonly:
            conn.commit()
    except Exception:
        if not readonly:
            conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """Initialize the database schema. Creates the DB file if it does not exist."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id          TEXT PRIMARY KEY,
                title       TEXT NOT NULL,
                description TEXT,
                created_at  TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                id            TEXT PRIMARY KEY,
                name          TEXT NOT NULL,
                file_path     TEXT NOT NULL,
                description   TEXT,
                project_id    TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                is_background INTEGER NOT NULL DEFAULT 0,
                created_at    TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS variable_stats (
                dataset_id TEXT NOT NULL,
                variable   TEXT NOT NULL,
                vmin       REAL NOT NULL,
                vmax       REAL NOT NULL,
                units      TEXT,
                long_name  TEXT,
                colormap   TEXT,
                PRIMARY KEY (dataset_id, variable),
                FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
            )
        """)
        conn.commit()


def create_project(title: str, description: str | None = None) -> str:
    """Create a new project and return its ID."""
    project_id = str(uuid4())
    created_at = datetime.now(pytz.timezone("Asia/Tokyo")).isoformat()

    with _get_connection() as conn:
        conn.execute(
            "INSERT INTO projects (id, title, description, created_at) VALUES (?, ?, ?, ?)",
            (project_id, title, description, created_at),
        )

    print(f"Created project:")
    print(f"  ID:          {project_id}")
    print(f"  Title:       {title}")
    print(f"  Description: {description}")
    return project_id


def list_projects():
    """List all projects with their dataset counts."""
    with _get_connection(readonly=True) as conn:
        rows = conn.execute("""
            SELECT p.id, p.title, p.description, p.created_at, COUNT(d.id) AS dataset_count
            FROM projects p
            LEFT JOIN datasets d ON d.project_id = p.id
            GROUP BY p.id
            ORDER BY p.created_at DESC
        """).fetchall()

    if not rows:
        print("No projects registered.")
        return

    print(f"\nRegistered projects ({len(rows)}):")
    print("-" * 80)
    for project_id, title, description, created_at, dataset_count in rows:
        print(f"ID:       {project_id}")
        print(f"Title:    {title}")
        print(f"Desc:     {description}")
        print(f"Datasets: {dataset_count}")
        print(f"Created:  {created_at}")
        print("-" * 80)


def delete_project(project_id: str, purge: bool = False):
    """Delete a project and all its datasets. If purge=True, also removes dataset files."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT title FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if not row:
            print(f"Error: Project not found: {project_id}", file=sys.stderr)
            sys.exit(1)

        project_title = row[0]
        dataset_paths = []
        if purge:
            dataset_paths = [
                STORAGE_DIR / r[0]
                for r in conn.execute(
                    "SELECT file_path FROM datasets WHERE project_id = ?", (project_id,)
                ).fetchall()
            ]

        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))

    print(f"Deleted project: {project_title} ({project_id})")
    for path in dataset_paths:
        if path.is_dir():
            shutil.rmtree(path)
            print(f"  Removed: {path}")
        elif path.is_file():
            path.unlink()
            print(f"  Removed: {path}")
        else:
            print(f"  Warning: not found: {path}")


def register_dataset(
    name: str,
    file_path: str,
    project_id: str,
    description: str | None = None,
    model: str | None = None,
    variables: list[str] | None = None,
    time_slice: tuple[int | None, ...] | None = None,
    crs: str | None = None,
    long_name_overrides: dict[str, str] | None = None,
    is_background: bool = False,
    colormap_overrides: dict[str, str] | None = None,
    rewrite: bool | None = None,
):
    """
    Register a new dataset in the database.

    Args:
        name: Display name for the dataset
        file_path: Path to the dataset file
        project_id: ID of the project this dataset belongs to
        description: Optional description
        model: Optional model name
        variables: Data variables to register (required for all formats)
        time_slice: Slice the time dimension. Single value = stop (keep first N steps).
            Two or three values = (start, end[, step]).
        crs: Optional CRS override (EPSG/WKT/PROJ string). Ignored when the
            source already declares a CRS.
        rewrite: Zarr input only. True (or unset): write a normalized copy.
            False: skip the rewrite, validate the source is already
            canonical, and register it directly. Incompatible with .nc
            (always rewritten) and COG (never rewritten).
    """
    # Validate project exists before the expensive preprocessing pipeline.
    # Without this check, an invalid project_id would only surface after minutes of preprocessing.
    with _get_connection(readonly=True) as conn:
        if not conn.execute(
            "SELECT id FROM projects WHERE id = ?", (project_id,)
        ).fetchone():
            print(f"Error: Project not found: {project_id}", file=sys.stderr)
            sys.exit(1)

    # Validate file exists
    file: Path = Path(STORAGE_DIR / file_path)
    if not file.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    try:
        preprocessed_file_path, stats = preprocess(
            file,
            model,
            variables=variables,
            time_slice=time_slice,
            crs=crs,
            long_name_overrides=long_name_overrides,
            rewrite=rewrite,
        )
    except ValueError as e:
        print(f"Error during preprocessing: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error during preprocessing: {e}", file=sys.stderr)
        sys.exit(1)

    dataset_id = str(uuid4())
    created_at = datetime.now(pytz.timezone("Asia/Tokyo")).isoformat()
    relative_path = str(preprocessed_file_path.relative_to(STORAGE_DIR))

    cm = colormap_overrides or {}
    with _get_connection() as conn:
        conn.execute(
            "INSERT INTO datasets (id, name, file_path, description, project_id, is_background, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                dataset_id,
                name,
                relative_path,
                description,
                project_id,
                int(is_background),
                created_at,
            ),
        )
        conn.executemany(
            "INSERT INTO variable_stats (dataset_id, variable, vmin, vmax, units, long_name, colormap) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    dataset_id,
                    var,
                    s["vmin"],
                    s["vmax"],
                    s["units"],
                    s["long_name"],
                    cm.get(var),
                )
                for var, s in stats.items()
            ],
        )

    print(f"\nSuccessfully registered dataset:")
    print(f"  ID:          {dataset_id}")
    print(f"  Name:        {name}")
    print(f"  File:        {relative_path}")
    print(f"  Description: {description}")
    print(f"  Project:     {project_id}")
    print(f"  Created:     {created_at}")
    for var, s in stats.items():
        unit = f" {s['units']}" if s["units"] else ""
        long = f" ({s['long_name']})" if s["long_name"] else ""
        print(f"  {var}{long}: vmin={s['vmin']:.4g}{unit}, vmax={s['vmax']:.4g}{unit}")


def delete_dataset(dataset_id: str, purge: bool = False):
    """Delete a dataset. If purge=True, also removes its file from storage."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT name, file_path FROM datasets WHERE id = ?", (dataset_id,)
        ).fetchone()
        if not row:
            print(f"Error: Dataset not found: {dataset_id}", file=sys.stderr)
            sys.exit(1)

        dataset_name, file_path = row
        dataset_path = STORAGE_DIR / file_path
        conn.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))

    print(f"Deleted dataset: {dataset_name} ({dataset_id})")
    if purge:
        if dataset_path.is_dir():
            shutil.rmtree(dataset_path)
            print(f"  Removed: {dataset_path}")
        elif dataset_path.is_file():
            dataset_path.unlink()
            print(f"  Removed: {dataset_path}")
        else:
            print(f"  Warning: file not found: {dataset_path}")


def delete_all_datasets(purge: bool = False):
    """Delete every dataset. If purge=True, also removes all dataset files from storage."""
    with _get_connection() as conn:
        rows = conn.execute("SELECT id, name, file_path FROM datasets").fetchall()
        if not rows:
            print("No datasets registered. Nothing to delete.")
            return
        conn.execute("DELETE FROM datasets")

    print(f"Deleted {len(rows)} dataset(s):")
    for dataset_id, name, file_path in rows:
        print(f"  - {dataset_id}  {name}")
        if purge:
            path = STORAGE_DIR / file_path
            if path.is_dir():
                shutil.rmtree(path)
                print(f"    removed {path}")
            elif path.is_file():
                path.unlink()
                print(f"    removed {path}")
            else:
                print(f"    warning: file not found: {path}")


def list_datasets(project_id: str | None = None):
    """List all registered datasets, optionally filtered by project."""
    with _get_connection(readonly=True) as conn:
        if project_id:
            rows = conn.execute(
                "SELECT id, name, file_path, description, created_at FROM datasets WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, name, file_path, description, created_at FROM datasets ORDER BY created_at DESC"
            ).fetchall()

    if not rows:
        print("No datasets registered.")
        return

    print(f"\nRegistered datasets ({len(rows)}):")
    print("-" * 80)
    for dataset_id, name, file_path, description, created_at in rows:
        print(f"ID:          {dataset_id}")
        print(f"Name:        {name}")
        print(f"File:        {file_path}")
        print(f"Description: {description}")
        print(f"Created:     {created_at}")
        print("-" * 80)


def edit_dataset(
    dataset_id: str,
    name: str | None = None,
    description: str | None = None,
    remove_variables: list[str] | None = None,
    units_overrides: dict[str, str] | None = None,
    long_name_overrides: dict[str, str] | None = None,
    colormap_overrides: dict[str, str] | None = None,
):
    """Edit dataset metadata or update/remove registered variable stats."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT name FROM datasets WHERE id = ?", (dataset_id,)
        ).fetchone()
        if not row:
            print(f"Error: Dataset not found: {dataset_id}", file=sys.stderr)
            sys.exit(1)

        current_name = row[0]

        if name is not None:
            conn.execute(
                "UPDATE datasets SET name = ? WHERE id = ?", (name, dataset_id)
            )
            print(f"Updated metadata for dataset: {current_name} ({dataset_id})")
            print("  Name: ", name)
        if description is not None:
            conn.execute(
                "UPDATE datasets SET description = ? WHERE id = ?",
                (description, dataset_id),
            )
            print(f"Updated metadata for dataset: {current_name} ({dataset_id})")
            print("  Description: ", description)

        if remove_variables:
            registered = {
                r[0]
                for r in conn.execute(
                    "SELECT variable FROM variable_stats WHERE dataset_id = ?",
                    (dataset_id,),
                ).fetchall()
            }
            not_found = [v for v in remove_variables if v not in registered]
            if not_found:
                print(
                    f"Error: variables not registered for this dataset: {not_found}",
                    file=sys.stderr,
                )
                sys.exit(1)
            conn.executemany(
                "DELETE FROM variable_stats WHERE dataset_id = ? AND variable = ?",
                [(dataset_id, v) for v in remove_variables],
            )
            for var in remove_variables:
                print(f"  Removed variable: {var}")

        var_stat_update_sql = {
            "units": "UPDATE variable_stats SET units     = ? WHERE dataset_id = ? AND variable = ?",
            "long_name": "UPDATE variable_stats SET long_name = ? WHERE dataset_id = ? AND variable = ?",
            "colormap": "UPDATE variable_stats SET colormap  = ? WHERE dataset_id = ? AND variable = ?",
        }
        stat_updates: dict[str, dict[str, str]] = {}
        for field, overrides in (
            ("units", units_overrides),
            ("long_name", long_name_overrides),
            ("colormap", colormap_overrides),
        ):
            if not overrides:
                continue
            registered = {
                r[0]
                for r in conn.execute(
                    "SELECT variable FROM variable_stats WHERE dataset_id = ?",
                    (dataset_id,),
                ).fetchall()
            }
            not_found = [v for v in overrides if v not in registered]
            if not_found:
                print(
                    f"Error: variables not registered for this dataset: {not_found}",
                    file=sys.stderr,
                )
                sys.exit(1)
            for var, value in overrides.items():
                conn.execute(var_stat_update_sql[field], (value, dataset_id, var))
                stat_updates.setdefault(var, {})[field] = value

        for var, changes in stat_updates.items():
            parts = ", ".join(f"{k}={v!r}" for k, v in changes.items())
            print(f"  Updated {var}: {parts}")


def _parse_kv(items: list[str], flag: str) -> dict[str, str]:
    """Parse a list of VAR=VALUE strings into a dict, exiting on malformed input."""
    result: dict[str, str] = {}
    for item in items:
        var, _, value = item.partition("=")
        if not var or not value:
            print(
                f"Error: {flag} values must be VAR=VALUE, got: {item!r}",
                file=sys.stderr,
            )
            sys.exit(1)
        result[var] = value
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Register datasets into the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Init command
    subparsers.add_parser("init", help="Initialize the database")

    # --- Project commands ---

    cpp = subparsers.add_parser("create-project", help="Create a new project")
    cpp.add_argument("--title", required=True, help="Project title")
    cpp.add_argument("--description", help="Project description (optional)")

    subparsers.add_parser("list-projects", help="List all registered projects")

    dpp = subparsers.add_parser(
        "delete-project", help="Delete a project and all its datasets"
    )
    dpp.add_argument("--id", required=True, help="Project ID to delete")
    dpp.add_argument(
        "--purge", action="store_true", help="Also remove dataset files from storage"
    )

    # --- Dataset commands ---

    rdp = subparsers.add_parser(
        "register-dataset", help="Register a new dataset into a project"
    )
    rdp.add_argument("--name", required=True, help="Dataset name")
    rdp.add_argument("--file-path", required=True, help="Path to dataset file")
    rdp.add_argument(
        "--project-id", required=True, help="Project this dataset belongs to"
    )
    rdp.add_argument(
        "--model", help="Model name which requires preprocessing (optional)"
    )
    rdp.add_argument(
        "--variables",
        nargs="+",
        required=True,
        metavar="VAR",
        help="Variables to register. For NC/Zarr: names of data variables to extract. "
        "For COG: exactly one variable name for the single band.",
    )
    rdp.add_argument(
        "--time-slice",
        nargs="+",
        type=int,
        metavar="N",
        help="Slice time dimension: END or START END [STEP]. A single value is the stop index (e.g. --time-slice 24 keeps the first 24 steps). Two or three values map to slice(start, end[, step]).",
    )
    rdp.add_argument("--description", help="Dataset description (optional)")
    rdp.add_argument(
        "--long-name",
        nargs="+",
        metavar="VAR=TEXT",
        help="Override or supply long_name for variables lacking CF attrs "
        '(e.g. --long-name T2="2 meter temperature" U10="10m U-wind").',
    )
    rdp.add_argument(
        "--crs",
        metavar="CRS",
        help="CRS to apply if the source file doesn't declare one. Accepts any "
        "string rioxarray.write_crs understands (e.g. EPSG:4326, a PROJ "
        "string, or a WKT). Ignored if the dataset already has a CRS.",
    )
    rdp.add_argument(
        "--background",
        action="store_true",
        help="Register as a background layer (population, land use, etc.).",
    )
    rdp.add_argument(
        "--colormap",
        nargs="+",
        metavar="VAR=VALUE",
        help="Colormap per variable. VALUE is either a named colormap string "
        "(e.g. plasma) or a JSON dict for categorical data "
        '(e.g. lc=\'{"1":[34,139,34,255],"2":[70,130,180,255]}\').',
    )
    rdp.add_argument(
        "--rewrite",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Zarr input only. Default (omitted) or --rewrite: write a "
        "normalized copy. --no-rewrite: skip the rewrite and validate the "
        "source is already canonical (x/y/time dims, CRS present) instead, "
        "registering it directly. --no-rewrite is rejected for .nc (always "
        "converted) and --rewrite is rejected for COG (never rewritten).",
    )

    ldp = subparsers.add_parser("list-datasets", help="List all registered datasets")
    ldp.add_argument("--project-id", help="Filter by project ID (optional)")

    ddp = subparsers.add_parser("delete-dataset", help="Delete a registered dataset")
    ddp.add_argument("--id", required=True, help="Dataset ID to delete")
    ddp.add_argument(
        "--purge",
        action="store_true",
        help="Also remove the dataset file from storage",
    )

    dadp = subparsers.add_parser(
        "delete-all-datasets", help="Delete every registered dataset"
    )
    dadp.add_argument(
        "--purge",
        action="store_true",
        help="Also remove each dataset file from storage",
    )

    edp = subparsers.add_parser(
        "edit-dataset", help="Edit dataset metadata or update registered variable stats"
    )
    edp.add_argument("--id", required=True, help="Dataset ID to edit")
    edp.add_argument("--name", help="New display name")
    edp.add_argument(
        "--description", help="New description (pass empty string to clear)"
    )
    edp.add_argument(
        "--remove-variables",
        nargs="+",
        metavar="VAR",
        help="Registered variables to remove from the DB (does not modify the Zarr)",
    )
    edp.add_argument(
        "--units",
        nargs="+",
        metavar="VAR=VALUE",
        help="Override units for registered variables (e.g. T2=K RH=%%)",
    )
    edp.add_argument(
        "--long-name",
        nargs="+",
        metavar="VAR=TEXT",
        help='Override long_name for registered variables (e.g. T2="2m temperature")',
    )
    edp.add_argument(
        "--colormap",
        nargs="+",
        metavar="VAR=VALUE",
        help="Override colormap for registered variables (e.g. T2=plasma)",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Ensure storage directory exists
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    if args.command == "init":
        init_database()
        print(f"Database initialized at {DB_PATH}")
    elif args.command == "create-project":
        init_database()
        create_project(args.title, args.description)
    elif args.command == "list-projects":
        list_projects()
    elif args.command == "delete-project":
        delete_project(args.id, purge=args.purge)
    elif args.command == "register-dataset":
        init_database()
        register_dataset(
            args.name,
            args.file_path,
            args.project_id,
            args.description,
            args.model,
            args.variables,
            tuple(args.time_slice) if args.time_slice else None,
            args.crs,
            _parse_kv(args.long_name, "--long-name") if args.long_name else None,
            args.background,
            _parse_kv(args.colormap, "--colormap") if args.colormap else None,
            args.rewrite,
        )
    elif args.command == "list-datasets":
        list_datasets(args.project_id)
    elif args.command == "delete-dataset":
        delete_dataset(args.id, purge=args.purge)
    elif args.command == "delete-all-datasets":
        delete_all_datasets(purge=args.purge)
    elif args.command == "edit-dataset":
        if not any(
            [
                args.name,
                args.description,
                args.remove_variables,
                args.units,
                args.long_name,
                args.colormap,
            ]
        ):
            print(
                "Error: specify at least one of --name, --description, --remove-variables, --units, --long-name, --colormap",
                file=sys.stderr,
            )
            sys.exit(1)

        edit_dataset(
            args.id,
            args.name,
            args.description,
            args.remove_variables,
            _parse_kv(args.units, "--units") if args.units else None,
            _parse_kv(args.long_name, "--long-name") if args.long_name else None,
            _parse_kv(args.colormap, "--colormap") if args.colormap else None,
        )


if __name__ == "__main__":
    main()
