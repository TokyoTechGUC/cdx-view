"""
Preprocess the input file for cloud optimization.
Supported file types:
- NetCDF (including WRF output) --> Zarr
- Zarr
- Cloud-optimized GeoTIFF
"""

import os
import warnings
from pathlib import Path
from typing import TypedDict

import dask
import rioxarray
import xarray as xr
import xwrf
from dask.delayed import Delayed
from rio_cogeo.cogeo import cog_validate

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "./storage"))


class VariableStats(TypedDict):
    vmin: float
    vmax: float
    units: str | None
    long_name: str | None


accepted_input_formats = {".nc", ".zarr", ".tif", ".tiff"}


def _apply_model_specific_rules(ds: xr.Dataset, model: str | None) -> xr.Dataset:
    if not model or model.lower() != "wrf":
        return ds
    ds = ds.xwrf.postprocess()
    # xwrf adds wrf_projection as a data variable storing the pyproj object;
    # write it as CRS metadata then drop it so zarr doesn't try to serialize it.
    if "wrf_projection" in ds.data_vars:
        ds = ds.rio.write_crs(
            ds["wrf_projection"].item(), grid_mapping_name="spatial_ref"
        )
        ds = ds.drop_vars("wrf_projection")
    return ds


_LATITUDE_NAMES = ("lat", "latitude", "LAT", "LATITUDE", "Lat", "Latitude")
_LONGITUDE_NAMES = ("lon", "longitude", "LON", "LONGITUDE", "Lon", "Longitude")
_TIME_NAMES = ("Time", "TIME")


def _resolve_dim_renames(ds: xr.Dataset) -> dict[str, str]:
    """Compute the dim renames _normalize_dims would apply, without applying them.

    An empty result means dims are already canonical — x/y (and time, if
    present) need no renaming. Spatial dims are required: raises if neither
    x/y nor a recognized lat/lon pair is present, even after considering the
    renames computed here. Time is optional.
    """
    rename: dict[str, str] = {}

    if "y" not in ds.dims:
        lat_name = next((n for n in _LATITUDE_NAMES if n in ds.dims), None)
        if lat_name:
            rename[lat_name] = "y"
    if "x" not in ds.dims:
        lon_name = next((n for n in _LONGITUDE_NAMES if n in ds.dims), None)
        if lon_name:
            rename[lon_name] = "x"
    if "time" not in ds.dims:
        time_name = next((n for n in _TIME_NAMES if n in ds.dims), None)
        if time_name:
            rename[time_name] = "time"

    resulting_dims = (set(ds.dims) - rename.keys()) | set(rename.values())
    if "x" not in resulting_dims or "y" not in resulting_dims:
        accepted = sorted({"x", "y", *_LATITUDE_NAMES, *_LONGITUDE_NAMES})
        raise ValueError(
            f"Spatial dimensions not found (have: {list(ds.dims)}). "
            f"Expected x/y or a recognized lat/lon pair from {accepted}. "
            "Rename source dims or apply a projection step first."
        )

    return rename


def _normalize_dims(ds: xr.Dataset) -> xr.Dataset:
    """Rename spatial dims to x/y and any time-like dim to time.

    Spatial dims are required: raises if neither x/y nor a recognized
    lat/lon pair is present. Time is optional — datasets without a time
    dimension pass through unchanged.
    """
    rename = _resolve_dim_renames(ds)
    return ds.rename(rename) if rename else ds


def _has_crs(ds: xr.Dataset) -> bool:
    """Whether the dataset already has a CRS — the thing _ensure_crs would
    otherwise write. Shared with the rewrite=False validator: a dataset
    without a CRS can't be registered without something writing one.
    """
    return ds.rio.crs is not None


def _ensure_crs(ds: xr.Dataset, crs: str | None) -> xr.Dataset:
    """Ensure the dataset has a CRS before it reaches the tile server.
    Precedence:
      1. CRS already on the dataset (set by _apply_model_specific_rules or
         picked up from CF grid_mapping via decode_coords="all"): keep it,
         warn if --crs was also provided.
      2. --crs provided, no existing CRS: write it.
      3. Neither: write EPSG:4326 with a loud warning.
    """
    if _has_crs(ds):
        if crs:
            warnings.warn(
                f"Dataset already has CRS ({ds.rio.crs}); ignoring --crs={crs}.",
                stacklevel=2,
            )
        return ds
    if crs:
        return ds.rio.write_crs(crs)
    warnings.warn(
        "No CRS found on dataset and --crs not provided; defaulting to EPSG:4326. "
        "If the source is projected, tiles will render "
        "at the wrong location. Pass --crs to fix.",
        stacklevel=2,
    )
    return ds.rio.write_crs("EPSG:4326")


def _filter_variables(ds: xr.Dataset, variables: list[str] | None) -> xr.Dataset:
    """Keep only the named data variables. Coordinates are preserved automatically."""
    if not variables:
        raise ValueError("No variables specified for selection.")
    missing = [v for v in variables if v not in ds.data_vars]
    if missing:
        available = sorted(ds.data_vars)
        raise ValueError(
            f"Requested variables not in dataset: {missing}. Available: {available}"
        )
    return ds[variables]


def _slice_time(
    ds: xr.Dataset, time_slice: tuple[int | None, ...] | None
) -> xr.Dataset:
    """Slice the time dimension. No-op if time_slice is None or no time dim.

    A single value is treated as stop (e.g. (24,) keeps the first 24 steps).
    Two or three values map to slice(start, end[, step]).
    """
    if not time_slice or "time" not in ds.dims or len(time_slice) > 3:
        return ds
    return ds.isel(time=slice(*time_slice))


def _compute_stats(ds: xr.Dataset) -> dict[str, dict[str, xr.DataArray]]:
    """Lazily build (vmin, vmax) per data variable, reduced across all dims (incl. time)."""
    stats: dict[str, dict] = {}
    for name, arr in ds.data_vars.items():
        if arr.ndim < 2:
            continue
        stats[name] = {
            "vmin": arr.min(skipna=True),
            "vmax": arr.max(skipna=True),
        }
    return stats


def _validate_cog(file_path: Path) -> None:
    is_valid, errors, _ = cog_validate(file_path)
    if not is_valid:
        raise ValueError(
            f"{file_path.name} is not a valid Cloud-Optimized GeoTIFF: {errors}. "
            "Convert it first to Cloud-Optimized GeoTIFF."
        )


def _to_zarr(ds: xr.Dataset, output_path: Path) -> Delayed:
    chunks = {d: s for d, s in (("time", 1), ("x", 256), ("y", 256)) if d in ds.dims}
    return ds.chunk(chunks).to_zarr(
        output_path, mode="w", zarr_format=2, consolidated=True, compute=False
    )


def _build_variable_stats(
    ds_processed: xr.Dataset,
    computed_stats: dict[str, dict[str, xr.DataArray]],
    long_name_overrides: dict[str, str] | None = None,
) -> dict[str, VariableStats]:
    """Unwrap 0-d DataArrays to floats and attach units/long_name from xarray attrs."""
    overrides = long_name_overrides or {}
    return {
        name: VariableStats(
            vmin=float(s["vmin"]),
            vmax=float(s["vmax"]),
            units=ds_processed[name].attrs.get("units"),
            long_name=overrides.get(name) or ds_processed[name].attrs.get("long_name"),
        )
        for name, s in computed_stats.items()
    }


def preprocess(
    file_path: Path,
    model: str | None,
    variables: list[str] | None = None,
    time_slice: tuple[int | None, ...] | None = None,
    crs: str | None = None,
    long_name_overrides: dict[str, str] | None = None,
    rewrite: bool | None = None,
) -> tuple[Path, dict[str, VariableStats]]:
    """
    Preprocess the input file and return (output_path, per-variable stats).

    - NetCDF  → writes a CF-compliant Zarr, returns its path.
    - Zarr    → reads stats from the existing Zarr, returns its path unchanged.
    - COG     → validates the COG, reads stats, returns the original .tif path unchanged.

    Args:
        file_path: Path to the input file
        model: Model name for model-specific postprocessing (e.g. 'wrf')
        variables: Data variables to keep stats for (required).
        time_slice: Slice the time dimension as slice(*time_slice) before stats/zarr write.
        crs: CRS override (any string rioxarray.write_crs accepts). Only
            applied if the dataset doesn't already declare one.
        rewrite: Whether to create a new file or use the existing file.
    Returns:
        Tuple of (output path, per-variable {vmin, vmax, units} stats).
    """
    if file_path.suffix not in accepted_input_formats:
        raise ValueError(f"Unsupported file format: {file_path}")

    if file_path.suffix in (".tif", ".tiff"):
        # TIFF/COG: only cog is accepted, no conversion
        if rewrite is True:
            raise ValueError(
                "COG input cannot be rewritten; --rewrite is currently not supported."
            )
        if model is not None:
            raise ValueError(
                "model is not supported for COG input: no model-specific "
                "postprocessing applies to COG. Omit model."
            )
        if time_slice is not None:
            raise ValueError(
                "time_slice is not supported for COG input: COG has no time "
                "dimension. Omit time_slice."
            )
        _validate_cog(file_path)
        with rioxarray.open_rasterio(
            file_path, chunks={}, lock=False, masked=True, mask_and_scale=True
        ) as da:
            n_bands = da.sizes.get("band", 1)
            if n_bands > 1:
                raise ValueError(
                    f"Multi-band COGs are not supported (got {n_bands} bands). "
                    "Register each band as a separate single-band COG."
                )
            if not variables:
                raise ValueError("--variables is required for COG files.")
            if len(variables) != 1:
                raise ValueError(
                    f"Expected exactly 1 variable name for a single-band COG, got {len(variables)}."
                )
            var_name = variables[0]
            band_da = da.squeeze("band").drop_vars("band")
            ds = xr.Dataset({var_name: band_da})
            if not _has_crs(ds):
                raise ValueError("COG input requires an existing CRS (none found).")
            if crs is not None:
                warnings.warn(
                    f"Dataset already has CRS ({ds.rio.crs}); ignoring crs={crs}.",
                    stacklevel=2,
                )
            stats_lazy = _compute_stats(ds)
            (computed_stats,) = dask.compute(stats_lazy)
            return file_path, _build_variable_stats(
                ds, computed_stats, long_name_overrides
            )

    if file_path.suffix == ".nc":
        # NetCDF: always convert to Zarr
        if rewrite is False:
            raise ValueError(
                "--rewrite=False only applies to .zarr input: .nc must "
                "always be converted to a new Zarr."
            )
        with xr.open_dataset(
            file_path, chunks="auto", mask_and_scale=True, decode_coords="all"
        ) as ds:
            ds_processed = (
                ds.pipe(_apply_model_specific_rules, model)
                .pipe(_filter_variables, variables)
                .pipe(_normalize_dims)
                .pipe(_ensure_crs, crs)
                .pipe(_slice_time, time_slice)
            )
            output_zarr = file_path.with_suffix(".zarr")

            stats_lazy = _compute_stats(ds_processed)
            delayed_write = _to_zarr(ds_processed, output_zarr)

            _, computed_stats = dask.compute(delayed_write, stats_lazy)
            return output_zarr, _build_variable_stats(
                ds_processed, computed_stats, long_name_overrides
            )

    if file_path.suffix == ".zarr":
        # Zarr: rewrite a normalized copy unless rewrite=False
        if rewrite is False:
            if model is not None:
                raise ValueError(
                    "model is not supported when rewrite=False: model-specific "
                    "postprocessing only runs when writing a new copy. Drop "
                    "rewrite=False or omit model."
                )
            if time_slice is not None:
                raise ValueError(
                    "time_slice is not supported when rewrite=False: nothing "
                    "is written, so a time slice can't be applied. Drop "
                    "rewrite=False or omit time_slice."
                )
        with xr.open_zarr(
            file_path, chunks="auto", mask_and_scale=True, decode_coords="all"
        ) as ds:
            if rewrite is False:
                if _resolve_dim_renames(ds):
                    raise ValueError(
                        f"rewrite=False requires dims already normalized to "
                        f"x/y/time (have: {sorted(ds.dims)})."
                    )
                if not _has_crs(ds):
                    raise ValueError(
                        "rewrite=False requires an existing CRS on the source"
                    )
                if crs is not None:
                    warnings.warn(
                        f"Dataset already has CRS ({ds.rio.crs}); ignoring crs={crs}.",
                        stacklevel=2,
                    )
                ds_processed = _filter_variables(ds, variables)
                stats_lazy = _compute_stats(ds_processed)
                (computed_stats,) = dask.compute(stats_lazy)
                return file_path, _build_variable_stats(
                    ds_processed, computed_stats, long_name_overrides
                )

            ds_processed = (
                ds.pipe(_filter_variables, variables)
                .pipe(_normalize_dims)
                .pipe(_ensure_crs, crs)
                .pipe(_slice_time, time_slice)
            )
            stats_lazy = _compute_stats(ds_processed)
            output_zarr = file_path.with_name(file_path.stem + ".processed.zarr")
            delayed_write: Delayed = _to_zarr(ds_processed, output_zarr)

            _, computed_stats = dask.compute(delayed_write, stats_lazy)
            return output_zarr, _build_variable_stats(
                ds_processed, computed_stats, long_name_overrides
            )

    raise ValueError(f"Unsupported file format: {file_path}")
