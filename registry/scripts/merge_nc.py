"""Concatenate multiple NetCDF files into a single NetCDF file."""

import argparse
import sys
from pathlib import Path

import xarray as xr


def main():
    parser = argparse.ArgumentParser(
        description="Concatenate multiple NetCDF files into one along a shared time dimension."
    )
    parser.add_argument("files", nargs="+", type=Path, metavar="FILE")
    parser.add_argument(
        "--output", "-o", required=True, type=Path, help="Output NetCDF path"
    )
    parser.add_argument(
        "--concat-dim",
        default=None,
        metavar="DIM",
        help=(
            "Dimension name to concatenate along. "
            "Default: auto-detect via combine='by_coords' (requires CF-compliant time coords). "
        ),
    )
    args = parser.parse_args()

    missing = [f for f in args.files if not f.exists()]
    if missing:
        for f in missing:
            print(f"Error: not found: {f}", file=sys.stderr)
        sys.exit(1)

    print(f"Opening {len(args.files)} file(s)...")

    if args.concat_dim:
        ds = xr.open_mfdataset(
            args.files,
            combine="nested",
            concat_dim=args.concat_dim,
            parallel=True,
        )
    else:
        ds = xr.open_mfdataset(
            args.files,
            combine="by_coords",
            parallel=True,
        )

    print(f"Writing → {args.output}")
    ds.to_netcdf(args.output)
    print("Done.")


if __name__ == "__main__":
    main()
