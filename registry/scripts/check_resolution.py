"""
Open a Zarr (or NetCDF) dataset and report its native resolution, plus the
min/maxzoom titiler/rio-tiler would compute for it.

Usage:
    python scripts/check_resolution.py path/to/dataset.zarr --variable T2
    python scripts/check_resolution.py path/to/dataset.nc --variable T2 --tms WebMercatorQuad
"""

import argparse
import sys
from pathlib import Path

import morecantile
import rioxarray  # noqa: registers the .rio accessor
import xarray as xr
from rasterio.rio.overview import get_maximum_overview_level
from rasterio.warp import calculate_default_transform


def check_resolution(path: Path, variable: str, tms: morecantile.TileMatrixSet):
    opener = xr.open_dataset if path.suffix in (".nc", ".nc4") else xr.open_zarr
    with opener(path, decode_coords="all") as ds:
        if variable not in ds.data_vars:
            print(
                f"Error: variable {variable!r} not found. Available: {sorted(ds.data_vars)}",
                file=sys.stderr,
            )
            sys.exit(1)
        da = ds[variable]

        if da.rio.crs is None:
            print("Error: dataset has no CRS set (rio.crs is None).", file=sys.stderr)
            sys.exit(1)

        width, height = da.rio.width, da.rio.height
        native_res = da.rio.resolution()
        crs = da.rio.crs

        dst_affine, dst_w, dst_h = calculate_default_transform(
            crs, tms.rasterio_crs, width, height, *da.rio.bounds()
        )
        dst_resolution = max(abs(dst_affine[0]), abs(dst_affine[4]))

        tilesize = tms.tileMatrices[0].tileWidth
        overview_level = get_maximum_overview_level(dst_w, dst_h, minsize=tilesize)
        ovr_resolution = dst_resolution * (2**overview_level)

        maxzoom = tms.zoom_for_res(dst_resolution)
        minzoom = tms.zoom_for_res(ovr_resolution)

    print(f"file:              {path}")
    print(f"variable:          {variable}")
    print(f"width x height:    {width} x {height}")
    print(f"native CRS:        {crs}")
    print(f"native resolution: {native_res}")
    print(f"{tms.id} width/height (reprojected): {dst_w} x {dst_h}")
    print(f"{tms.id} resolution: {dst_resolution:.2f} m/px")
    print(f"theoretical overview levels (minsize={tilesize}): {overview_level}")
    print(f"minzoom: {minzoom}")
    print(f"maxzoom: {maxzoom}")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("path", type=Path, help="Path to a .zarr or .nc dataset")
    parser.add_argument("--variable", required=True, help="Data variable to inspect")
    parser.add_argument(
        "--tms", default="WebMercatorQuad", help="TileMatrixSet id (default: WebMercatorQuad)"
    )
    args = parser.parse_args()

    if not args.path.exists():
        print(f"Error: path not found: {args.path}", file=sys.stderr)
        sys.exit(1)

    tms = morecantile.tms.get(args.tms)
    check_resolution(args.path, args.variable, tms)


if __name__ == "__main__":
    main()
