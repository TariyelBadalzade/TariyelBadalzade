"""
Usage:
    python split_into_chips.py --input Valencia_2024_S1.tif --output data/valencia_chips
"""

import argparse
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.windows import Window


CHIP_SIZE    = 512       # pixels
MIN_COVERAGE = 0.30      # skip chips where less than 30% of pixels have valid data


def split_into_chips(input_path: str, output_dir: str):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with rasterio.open(input_path) as src:
        width    = src.width
        height   = src.height
        profile  = src.profile.copy()
        n_bands  = src.count

        print(f"Input: {input_path}")
        print(f"  Size: {width} x {height} pixels")
        print(f"  Bands: {n_bands}")
        print(f"  CRS: {src.crs}")
        print(f"  Dtype: {src.dtypes[0]}")

        # Calculate number of chips in each direction
        n_cols = width  // CHIP_SIZE
        n_rows = height // CHIP_SIZE
        total  = n_cols * n_rows
        print(f"\nChip grid: {n_cols} cols x {n_rows} rows = {total} potential chips")
        print(f"Skipping chips with <{MIN_COVERAGE*100:.0f}% valid pixels\n")

        profile.update(
            width=CHIP_SIZE,
            height=CHIP_SIZE,
            count=n_bands,
        )

        saved   = 0
        skipped = 0

        for row in range(n_rows):
            for col in range(n_cols):
                x_off = col * CHIP_SIZE
                y_off = row * CHIP_SIZE

                window = Window(x_off, y_off, CHIP_SIZE, CHIP_SIZE)

                # Read all bands for this window
                data = src.read(window=window).astype(np.float32)

                # Check coverage — valid pixels are finite and non-zero
                vv = data[0]
                valid = np.isfinite(vv) & (vv != 0)
                coverage = valid.mean()

                if coverage < MIN_COVERAGE:
                    skipped += 1
                    continue

                # Get the affine transform for this chip
                chip_transform = src.window_transform(window)

                # Update profile with this chip's transform
                chip_profile = profile.copy()
                chip_profile["transform"] = chip_transform

                # Save chip
                chip_num  = saved + 1
                stem      = Path(input_path).stem
                out_path  = output_dir / f"{stem}_chip_{chip_num:03d}.tif"

                with rasterio.open(out_path, "w", **chip_profile) as dst:
                    dst.write(data.astype(chip_profile["dtype"]))

                saved += 1

                if saved % 10 == 0:
                    print(f"  Saved {saved} chips so far... (skipped {skipped} empty chips)")

        print(f"\nDone!")
        print(f"  Saved:   {saved} chips → {output_dir}/")
        print(f"  Skipped: {skipped} chips (too much nodata)")
        print(f"\nTo run your model on all chips:")
        print(f"  python batch_show_results.py")
        print(f"  (update S1_DIR in batch_show_results.py to '{output_dir}')")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",    required=True, help="Path to large GeoTIFF")
    parser.add_argument("--output",   default="data/valencia_chips", help="Output directory")
    parser.add_argument("--min-coverage", type=float, default=0.30,
                        help="Minimum fraction of valid pixels to keep a chip (default 0.30)")
    args = parser.parse_args()

    MIN_COVERAGE = args.min_coverage
    split_into_chips(args.input, args.output)
