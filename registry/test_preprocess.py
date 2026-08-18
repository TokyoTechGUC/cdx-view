"""
Tests preprocess.py
"""

import warnings
from pathlib import Path

import numpy as np
import pytest
import rioxarray  # noqa: F401 (registers the .rio accessor)
import xarray as xr
from preprocess import (
    _build_variable_stats,
    _compute_stats,
    _ensure_crs,
    _filter_variables,
    _normalize_dims,
    preprocess,
)
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles


def _make_ds(*, x_name="x", y_name="y", with_time=False, time_name="time", crs=None):
    dims_2d = (y_name, x_name)
    data = {"T2": (dims_2d, np.arange(9.0).reshape(3, 3))}
    coords = {y_name: [1.0, 2.0, 3.0], x_name: [1.0, 2.0, 3.0]}
    if with_time:
        data["T2"] = ((time_name, *dims_2d), np.arange(9.0).reshape(1, 3, 3))
        coords[time_name] = [0]
    ds = xr.Dataset(data, coords=coords)
    if crs:
        ds = ds.rio.write_crs(crs)
    return ds


def _write_nc(path: Path, ds: xr.Dataset) -> None:
    ds.to_netcdf(path)


def _write_zarr(path: Path, ds: xr.Dataset) -> None:
    ds.to_zarr(path, mode="w", zarr_format=2, consolidated=True)


def _write_tif(
    path: Path,
    *,
    bands: int = 1,
    valid_cog: bool = True,
    size: int = 3,
    with_crs: bool = True,
) -> None:
    if bands == 1:
        arr = np.arange(float(size * size)).reshape(size, size)
        da = xr.DataArray(
            arr,
            dims=("y", "x"),
            coords={"y": np.arange(float(size)), "x": np.arange(float(size))},
        )
    else:
        arr = np.stack([np.arange(9.0).reshape(3, 3) + i * 10 for i in range(bands)])
        da = xr.DataArray(
            arr,
            dims=("band", "y", "x"),
            coords={
                "band": list(range(1, bands + 1)),
                "y": [3.0, 2.0, 1.0],
                "x": [1.0, 2.0, 3.0],
            },
        )
    if with_crs:
        da = da.rio.write_crs("EPSG:4326")
    raw = path.with_suffix(".raw.tif")
    da.rio.to_raster(raw)
    if valid_cog:
        cog_translate(raw, path, cog_profiles.get("deflate"), quiet=True)
    else:
        raw.rename(path)


# ---------------------------------------------------------------------------
# _normalize_dims
# ---------------------------------------------------------------------------


def test_normalize_dims_renames_lat_lon_to_x_y():
    ds = _make_ds(x_name="lon", y_name="lat")
    out = _normalize_dims(ds)
    assert {"x", "y"} <= set(out.dims)
    assert "lat" not in out.dims and "lon" not in out.dims


def test_normalize_dims_renames_time_dim():
    ds = _make_ds(with_time=True, time_name="Time")
    out = _normalize_dims(ds)
    assert "time" in out.dims
    assert "Time" not in out.dims


def test_normalize_dims_noop_when_already_canonical():
    ds = _make_ds(with_time=True, time_name="time")
    out = _normalize_dims(ds)
    assert set(out.dims) == set(ds.dims)


def test_normalize_dims_raises_when_spatial_dims_missing():
    ds = xr.Dataset({"T2": (("a", "b"), np.zeros((2, 2)))})
    with pytest.raises(ValueError, match="Spatial dimensions not found"):
        _normalize_dims(ds)


# ---------------------------------------------------------------------------
# _ensure_crs
# ---------------------------------------------------------------------------


def test_ensure_crs_keeps_existing_and_warns_on_override_conflict():
    ds = _make_ds(crs="EPSG:32654")
    with pytest.warns(UserWarning, match="already has CRS"):
        out = _ensure_crs(ds, "EPSG:4326")
    assert out.rio.crs.to_epsg() == 32654


def test_ensure_crs_keeps_existing_no_warning_without_override():
    ds = _make_ds(crs="EPSG:32654")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        out = _ensure_crs(ds, None)
    assert out.rio.crs.to_epsg() == 32654


def test_ensure_crs_writes_override_when_missing():
    ds = _make_ds()
    out = _ensure_crs(ds, "EPSG:32654")
    assert out.rio.crs.to_epsg() == 32654


def test_ensure_crs_defaults_to_4326_with_warning():
    ds = _make_ds()
    with pytest.warns(UserWarning, match="defaulting to EPSG:4326"):
        out = _ensure_crs(ds, None)
    assert out.rio.crs.to_epsg() == 4326


# ---------------------------------------------------------------------------
# _filter_variables
# ---------------------------------------------------------------------------


def test_filter_variables_keeps_only_named():
    ds = xr.Dataset(
        {
            "T2": (("y", "x"), np.zeros((2, 2))),
            "RH": (("y", "x"), np.zeros((2, 2))),
        }
    )
    out = _filter_variables(ds, ["T2"])
    assert set(out.data_vars) == {"T2"}


def test_filter_variables_raises_on_missing_variable():
    ds = xr.Dataset({"T2": (("y", "x"), np.zeros((2, 2)))})
    with pytest.raises(ValueError, match="not in dataset"):
        _filter_variables(ds, ["T2", "MISSING"])


def test_filter_variables_raises_on_empty_variables():
    ds = xr.Dataset({"T2": (("y", "x"), np.zeros((2, 2)))})
    with pytest.raises(ValueError, match="No variables specified"):
        _filter_variables(ds, None)


# ---------------------------------------------------------------------------
# _compute_stats
# ---------------------------------------------------------------------------


def test_compute_stats_correct_min_max():
    ds = xr.Dataset({"T2": (("y", "x"), np.arange(9.0).reshape(3, 3))})
    stats = _compute_stats(ds)
    assert float(stats["T2"]["vmin"].values) == 0.0
    assert float(stats["T2"]["vmax"].values) == 8.0


def test_compute_stats_skips_low_dim_variables():
    ds = xr.Dataset(
        {
            "T2": (("y", "x"), np.arange(9.0).reshape(3, 3)),
            "scalar": ((), np.array(1.0)),
            "oneD": (("x",), np.array([1.0, 2.0, 3.0])),
        }
    )
    stats = _compute_stats(ds)
    assert set(stats) == {"T2"}


# ---------------------------------------------------------------------------
# _build_variable_stats
# ---------------------------------------------------------------------------


def test_build_variable_stats_unwraps_and_applies_overrides():
    ds = xr.Dataset({"T2": (("y", "x"), np.zeros((2, 2)))})
    ds["T2"].attrs["units"] = "K"
    ds["T2"].attrs["long_name"] = "Temperature"
    computed = {"T2": {"vmin": xr.DataArray(0.0), "vmax": xr.DataArray(10.0)}}

    stats = _build_variable_stats(ds, computed)
    assert stats["T2"] == {
        "vmin": 0.0,
        "vmax": 10.0,
        "units": "K",
        "long_name": "Temperature",
    }

    overridden = _build_variable_stats(ds, computed, {"T2": "Custom name"})
    assert overridden["T2"]["long_name"] == "Custom name"


# ---------------------------------------------------------------------------
# preprocess() end-to-end: .nc
# rewrite=True (default), rewrite=False is not accepted
# ---------------------------------------------------------------------------


def test_preprocess_nc_writes_new_zarr_with_correct_stats(tmp_path):
    src = tmp_path / "source.nc"
    _write_nc(src, _make_ds(x_name="lon", y_name="lat"))

    out_path, stats = preprocess(src, model=None, variables=["T2"], crs="EPSG:4326")

    assert out_path == tmp_path / "source.zarr"
    assert out_path.exists()
    with xr.open_zarr(out_path) as ds:
        assert {"x", "y"} <= set(ds.dims)
    assert stats["T2"]["vmin"] == 0.0
    assert stats["T2"]["vmax"] == 8.0


# ---------------------------------------------------------------------------
# preprocess() end-to-end: .zarr
# rewrite=True (default)
# ---------------------------------------------------------------------------


def test_preprocess_zarr_default_returns_new_path(tmp_path):
    src = tmp_path / "source.zarr"
    _write_zarr(src, _make_ds(x_name="lon", y_name="lat"))

    out_path, stats = preprocess(src, model=None, variables=["T2"], crs="EPSG:4326")

    assert out_path != src
    assert out_path.exists()
    assert stats["T2"]["vmin"] == 0.0
    assert stats["T2"]["vmax"] == 8.0


def test_preprocess_zarr_default_writes_normalized_dims_to_new_path(tmp_path):
    src = tmp_path / "source.zarr"
    _write_zarr(src, _make_ds(x_name="lon", y_name="lat"))

    out_path, _ = preprocess(src, model=None, variables=["T2"], crs="EPSG:4326")

    with xr.open_zarr(out_path) as ds:
        assert {"x", "y"} <= set(ds.dims)
        assert "lat" not in ds.dims and "lon" not in ds.dims


def test_preprocess_zarr_rewrite_true_explicit_same_as_default(tmp_path):
    """Explicit rewrite=True and the unset default must agree."""
    src = tmp_path / "source.zarr"
    _write_zarr(src, _make_ds(x_name="lon", y_name="lat"))

    out_path, stats = preprocess(
        src, model=None, variables=["T2"], crs="EPSG:4326", rewrite=True
    )

    assert out_path != src
    assert stats["T2"]["vmin"] == 0.0
    assert stats["T2"]["vmax"] == 8.0


def test_preprocess_zarr_default_leaves_source_untouched(tmp_path):
    src = tmp_path / "source.zarr"
    _write_zarr(src, _make_ds(x_name="lon", y_name="lat"))

    preprocess(src, model=None, variables=["T2"], crs="EPSG:4326")

    with xr.open_zarr(src) as ds:
        assert {"lat", "lon"} <= set(ds.dims)


# ---------------------------------------------------------------------------
# preprocess() end-to-end: .zarr
# rewrite=False (validate-only)
# ---------------------------------------------------------------------------


def test_preprocess_zarr_norewrite_returns_original_path_and_writes_nothing(tmp_path):
    src = tmp_path / "source.zarr"
    _write_zarr(src, _make_ds(with_time=True, crs="EPSG:32654"))

    out_path, stats = preprocess(src, model=None, variables=["T2"], rewrite=False)

    assert out_path == src
    assert not (tmp_path / "source.processed.zarr").exists()
    assert stats["T2"]["vmin"] == 0.0
    assert stats["T2"]["vmax"] == 8.0


def test_preprocess_zarr_norewrite_rejects_noncanonical_dims(tmp_path):
    src = tmp_path / "source.zarr"
    _write_zarr(src, _make_ds(x_name="lon", y_name="lat", crs="EPSG:4326"))

    with pytest.raises(ValueError, match="normalized to x/y/time"):
        preprocess(src, model=None, variables=["T2"], rewrite=False)


def test_preprocess_zarr_norewrite_rejects_missing_crs(tmp_path):
    src = tmp_path / "source.zarr"
    _write_zarr(src, _make_ds())  # canonical dims, no CRS

    with pytest.raises(ValueError, match="existing CRS"):
        preprocess(src, model=None, variables=["T2"], rewrite=False)


def test_preprocess_zarr_norewrite_rejects_missing_crs_even_with_crs_option(tmp_path):
    src = tmp_path / "source.zarr"
    _write_zarr(src, _make_ds())  # canonical dims, no CRS

    with pytest.raises(ValueError, match="existing CRS"):
        preprocess(src, model=None, variables=["T2"], crs="EPSG:4326", rewrite=False)


def test_preprocess_zarr_norewrite_warns_on_redundant_crs_option(tmp_path):
    src = tmp_path / "source.zarr"
    _write_zarr(src, _make_ds(crs="EPSG:32654"))  # already has a CRS

    with pytest.warns(UserWarning, match="already has CRS"):
        out_path, stats = preprocess(
            src, model=None, variables=["T2"], crs="EPSG:4326", rewrite=False
        )

    assert out_path == src
    assert stats["T2"]["vmin"] == 0.0
    assert stats["T2"]["vmax"] == 8.0


def test_preprocess_zarr_norewrite_rejects_time_slice_option(tmp_path):
    src = tmp_path / "source.zarr"
    _write_zarr(src, _make_ds(with_time=True, crs="EPSG:32654"))

    with pytest.raises(ValueError, match="time_slice is not supported"):
        preprocess(src, model=None, variables=["T2"], time_slice=(1,), rewrite=False)


def test_preprocess_zarr_norewrite_rejects_model_option(tmp_path):
    src = tmp_path / "source.zarr"
    _write_zarr(src, _make_ds(crs="EPSG:32654"))

    with pytest.raises(ValueError, match="model is not supported"):
        preprocess(src, model="wrf", variables=["T2"], rewrite=False)


def test_preprocess_norewrite_rejects_non_zarr_input(tmp_path):
    with pytest.raises(ValueError, match="only applies to .zarr"):
        preprocess(tmp_path / "dummy.nc", model=None, variables=["T2"], rewrite=False)


def test_preprocess_zarr_norewrite_and_default_agree_on_stats(tmp_path):
    """Consistency check: for a source that's already canonical, rewrite=False
    (validate-only) and the default (rewrite=True) must compute the same
    stats"""
    src = tmp_path / "source.zarr"
    _write_zarr(src, _make_ds(with_time=True, crs="EPSG:32654"))

    norewrite_out, norewrite_stats = preprocess(
        src, model=None, variables=["T2"], rewrite=False
    )
    default_out, default_stats = preprocess(src, model=None, variables=["T2"])

    assert norewrite_out == src
    assert default_out != src
    assert norewrite_stats == default_stats


# ---------------------------------------------------------------------------
# preprocess() end-to-end: .tif, .tiff / COG
# ---------------------------------------------------------------------------


def test_preprocess_cog_returns_original_path_with_correct_stats(tmp_path):
    path = tmp_path / "valid.cog.tif"
    _write_tif(path, valid_cog=True)

    out_path, stats = preprocess(path, model=None, variables=["T2"])

    assert out_path == path
    assert stats["T2"]["vmin"] == 0.0
    assert stats["T2"]["vmax"] == 8.0


def test_preprocess_cog_never_modifies_source_file(tmp_path):
    path = tmp_path / "valid.cog.tif"
    _write_tif(path, valid_cog=True)
    before = path.read_bytes()

    preprocess(path, model=None, variables=["T2"])

    assert path.read_bytes() == before


def test_preprocess_cog_creates_no_new_files(tmp_path):
    path = tmp_path / "valid.cog.tif"
    _write_tif(path, valid_cog=True)
    before = set(tmp_path.iterdir())

    preprocess(path, model=None, variables=["T2"])

    assert set(tmp_path.iterdir()) == before


def test_preprocess_cog_norewrite_is_accepted(tmp_path):
    """COG is always effectively validate-only (no rewrite path exists at
    all), so explicit rewrite=False is redundant but valid — same result as
    the default (rewrite unset).
    """
    path = tmp_path / "valid.cog.tif"
    _write_tif(path, valid_cog=True)

    out_path, stats = preprocess(path, model=None, variables=["T2"], rewrite=False)

    assert out_path == path
    assert stats["T2"]["vmin"] == 0.0
    assert stats["T2"]["vmax"] == 8.0


def test_preprocess_cog_rewrite_true_is_rejected(tmp_path):
    """Explicit rewrite=True asks for a rewrite, which COG can never
    do — reject it rather than silently ignoring the request.
    """
    path = tmp_path / "valid.cog.tif"
    _write_tif(path, valid_cog=True)

    with pytest.raises(ValueError, match="cannot be rewritten"):
        preprocess(path, model=None, variables=["T2"], rewrite=True)


def test_preprocess_cog_rejects_missing_crs(tmp_path):
    path = tmp_path / "no_crs.cog.tif"
    _write_tif(path, valid_cog=True, with_crs=False)

    with pytest.raises(ValueError, match="existing CRS"):
        preprocess(path, model=None, variables=["T2"])


def test_preprocess_cog_rejects_time_slice_option(tmp_path):
    path = tmp_path / "valid.cog.tif"
    _write_tif(path, valid_cog=True)

    with pytest.raises(ValueError, match="time_slice is not supported"):
        preprocess(path, model=None, variables=["T2"], time_slice=(1,))


def test_preprocess_cog_rejects_model_option(tmp_path):
    path = tmp_path / "valid.cog.tif"
    _write_tif(path, valid_cog=True)

    with pytest.raises(ValueError, match="model is not supported"):
        preprocess(path, model="wrf", variables=["T2"])


def test_preprocess_cog_rejects_multiband(tmp_path):
    path = tmp_path / "multiband.cog.tif"
    _write_tif(path, bands=2, valid_cog=True)

    with pytest.raises(ValueError, match="Multi-band COGs are not supported"):
        preprocess(path, model=None, variables=["T2"])


def test_preprocess_cog_requires_variables(tmp_path):
    path = tmp_path / "valid.cog.tif"
    _write_tif(path, valid_cog=True)

    with pytest.raises(ValueError, match="variables is required"):
        preprocess(path, model=None, variables=None)


def test_preprocess_cog_requires_exactly_one_variable(tmp_path):
    path = tmp_path / "valid.cog.tif"
    _write_tif(path, valid_cog=True)

    with pytest.raises(ValueError, match="Expected exactly 1 variable name"):
        preprocess(path, model=None, variables=["A", "B"])


# ---------------------------------------------------------------------------
# format validation
# ---------------------------------------------------------------------------


def test_preprocess_rejects_unsupported_suffix(tmp_path):
    with pytest.raises(ValueError, match="Unsupported file format"):
        preprocess(tmp_path / "dummy.xyz", model=None, variables=["T2"])
