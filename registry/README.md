# registry

CLI for preprocessing datasets and registering them into the cdx-view catalog.
See the `justfile` for shortcuts (`just db-init`, `just db-register-dataset`, …).

## What your input file must satisfy

To be registerable, the source NetCDF or Zarr file must have:

1. **A recognised spatial dim pair** — see table below. Registration
   renames to `x`/`y` automatically.
2. **A 1D rectilinear grid.** Curvilinear 2D coordinates (raw WRF, some
   satellite swaths) need a projection step first.
3. **A CRS.** Either declared in the source file, 
   set by model specific preprocessing, or provided with `--crs`.
   Without one, tiles silently render at the wrong location.
4. **2D or 3D variables.** After `--variables` filtering each kept
   variable must be `(y, x)` or `(time, y, x)`.

Time is **optional**. Datasets without a time dim are accepted and the
time slider is hidden in the viewer.

### Recognised dim names

| Target | Accepted source names                                           |
| ------ | --------------------------------------------------------------- |
| `y`    | `y`, `lat`, `latitude`, `LAT`, `LATITUDE`, `Lat`, `Latitude`    |
| `x`    | `x`, `lon`, `longitude`, `LON`, `LONGITUDE`, `Lon`, `Longitude` |
| `time` | `time`, `Time`, `TIME` (optional)                               |

If your source uses a different name (`XLONG`/`XLAT`,
`west_east`/`south_north`, `valid_time`, …), rename it in the source
file or apply a projection step first.

For WRF, `--model wrf` projects the grid to `x`/`y` and writes the CRS automatically (via the `xwrf` library).

### CRS values

`--crs` accepts any string `rioxarray.write_crs` understands:

- EPSG codes: `EPSG:4326`, `EPSG:3857`
- PROJ strings: `"+proj=lcc +lat_1=30 +lat_2=60 ..."`
- WKT (read from a file for long WKT: `--crs "$(cat my.wkt)"`)

If the source already has a CRS, `--crs` is ignored.

## Reference

See [`DATA_REQUIREMENTS.md`](./DATA_REQUIREMENTS.md) for the contract
this is derived from, with citations into the titiler / rio-tiler /
rioxarray source.
