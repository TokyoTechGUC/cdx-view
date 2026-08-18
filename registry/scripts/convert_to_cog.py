"""
Convert a GeoTIFF to a Cloud-Optimized GeoTIFF (COG).

Output is always written as <input_stem>.cog.tif in the same directory as the input.

Usage:
    python scripts/convert_to_cog.py input.tif
    python scripts/convert_to_cog.py input.tif --resampling average
    python scripts/convert_to_cog.py input.tif --profile lzw --tms WorldCRS84Quad
    python scripts/convert_to_cog.py input.tif --bounds 139.6 35.5 139.9 35.8
"""

import argparse
import sys
from pathlib import Path

import morecantile
import rioxarray
from rio_cogeo.cogeo import cog_translate, cog_validate
from rio_cogeo.profiles import cog_profiles

_PROFILES = ["deflate", "lzw", "jpeg", "webp", "zstd", "raw"]
_RESAMPLINGS = ["nearest", "average", "bilinear", "cubic", "lanczos"]
_TMS = list(morecantile.tms.list())


def _clip(input_path: Path, bounds: tuple[float, float, float, float]) -> Path:
    """Clip input_path to bounds (west, south, east, north in EPSG:4326)
    and write the result next to the input as <stem>.clip.tif.
    """
    west, south, east, north = bounds
    clip_path = input_path.with_name(input_path.stem + ".clip.tif")
    with rioxarray.open_rasterio(input_path, masked=True) as da:
        clipped = da.rio.clip_box(
            minx=west, miny=south, maxx=east, maxy=north, crs="EPSG:4326"
        )
        clipped.rio.to_raster(clip_path)
    return clip_path


def convert(
    input_path: Path,
    profile: str,
    resampling: str,
    tms: str,
    bounds: tuple[float, float, float, float] | None = None,
) -> None:
    output_path = input_path.with_name(input_path.stem + ".cog.tif")
    if output_path.exists():
        print(
            f"Error: output file already exists: {output_path}. "
            "Move or remove it before converting.",
            file=sys.stderr,
        )
        sys.exit(1)

    if bounds is None:
        is_valid, _, _ = cog_validate(input_path)
        if is_valid:
            print(f"{input_path.name} is already a valid COG. No conversion needed.")
            return
        tmp_path = input_path
    else:
        print(f"Clipping {input_path.name} to bounds {bounds} ...")
        tmp_path = _clip(input_path, bounds)

    try:
        print(f"Converting {input_path.name} -> {output_path.name} ...")
        cog_translate(
            tmp_path,
            output_path,
            cog_profiles.get(profile),
            overview_resampling=resampling,
            tms=morecantile.tms.get(tms),
        )
    finally:
        if tmp_path != input_path:
            tmp_path.unlink(missing_ok=True)
    print(f"Done: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a GeoTIFF to Cloud-Optimized GeoTIFF"
    )
    parser.add_argument("input", type=Path, help="Input GeoTIFF path")
    parser.add_argument(
        "--profile",
        "-p",
        default="deflate",
        choices=_PROFILES,
        help="Compression profile (default: deflate)",
    )
    parser.add_argument(
        "--resampling",
        "-r",
        default="nearest",
        choices=_RESAMPLINGS,
        help="Overview resampling method (default: nearest)",
    )
    parser.add_argument(
        "--tms",
        default="WebMercatorQuad",
        choices=_TMS,
        help="Tile Matrix Set for web optimization (default: WebMercatorQuad)",
    )
    parser.add_argument(
        "--bounds",
        type=float,
        nargs=4,
        metavar=("WEST", "SOUTH", "EAST", "NORTH"),
        help="Clip to this bounding box (EPSG:4326 lon/lat) before COG conversion. "
        "If omitted, the whole input is converted.",
    )
    args = parser.parse_args()

    input_path: Path = args.input.resolve()
    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    if input_path.suffix.lower() not in (".tif", ".tiff"):
        print(
            f"Error: input must be a GeoTIFF (.tif/.tiff), got: {input_path.suffix}",
            file=sys.stderr,
        )
        sys.exit(1)

    bounds = tuple(args.bounds) if args.bounds else None
    convert(input_path, args.profile, args.resampling, args.tms, bounds)


if __name__ == "__main__":
    main()
