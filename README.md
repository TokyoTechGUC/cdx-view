# cdx-view

[![CI](https://github.com/TokyoTechGUC/cdx-view/actions/workflows/ci.yml/badge.svg)](https://github.com/TokyoTechGUC/cdx-view/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/github/license/TokyoTechGUC/cdx-view)](LICENSE)

cdx-view is a web application for sharing geospatial climate data (such as Weather Research and Forecast (WRF) output) with non-expert users.

## Architecture

Three services, run via Docker Compose:

- **registry** (Python CLI) — preprocesses NetCDF/Zarr/COG files and records metadata in a shared SQLite database
- **server** (FastAPI + titiler-xarray) — reads the database and slices datasets into map tiles on demand
- **client** (SvelteKit + MapLibre GL JS) — renders the tiles on an interactive map

## Quick start

```bash
git clone https://github.com/TokyoTechGUC/cdx-view.git
cd cdx-view
cp .env.example .env
just up -d --build
just db-init
```

For local development instead (hot-reload, separate compose file):

```bash
cp .env.example .env.dev
just dev up -d --build
```

See the [wiki](https://github.com/TokyoTechGUC/cdx-view/wiki) for details:

- **[Home](https://github.com/TokyoTechGUC/cdx-view/wiki/Home)** — architecture overview and components
- **[Deployment](https://github.com/TokyoTechGUC/cdx-view/wiki/Deployment)** — how to stand up a production instance behind Apache
- **[Data Registration](https://github.com/TokyoTechGUC/cdx-view/wiki/Data-Registration)** — how to get a dataset into the catalog and viewable in the app

## License

[MIT](LICENSE)
