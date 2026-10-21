"""
Usage:
    python visualize.py --input data/chip.tif --mask outputs/mask.tif
                        --route outputs/route.geojson --output outputs/viz.png
"""

import argparse
from pathlib import Path
from typing import Optional

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")   # Non-interactive backend for server/script use
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import rasterio
from rasterio.plot import reshape_as_image
from shapely.geometry import shape
import osmnx as ox


# ── Helpers ───────────────────────────────────────────────────────────────────

def _percentile_stretch(arr: np.ndarray, low: float = 2.0, high: float = 98.0) -> np.ndarray:
    lo, hi = np.percentile(arr[np.isfinite(arr)], [low, high])
    stretched = np.clip((arr - lo) / (hi - lo + 1e-8), 0.0, 1.0)
    return stretched.astype(np.float32)


def _read_sar_vv(tif_path: str) -> tuple:
    with rasterio.open(tif_path) as src:
        vv        = src.read(1).astype(np.float32)
        transform = src.transform
        bounds    = src.bounds
        crs       = src.crs
    return vv, transform, bounds, crs


def _read_flood_mask(mask_path: str) -> np.ndarray:
    with rasterio.open(mask_path) as src:
        mask = src.read(1).astype(np.float32)
    return (mask > 0).astype(np.float32)


# ── Main visualization function ───────────────────────────────────────────────

def visualize(
    tif_path: str,
    mask_path: str,
    road_graph=None,               # NetworkX MultiDiGraph (projected, optional)
    route_gdf: Optional[gpd.GeoDataFrame] = None,
    output_path: str = "outputs/visualization.png",
    figsize: tuple = (14, 12),
    dpi: int = 150,
    alpha_flood: float = 0.45,
):

    # ── Load data ─────────────────────────────────────────────────────────────
    vv, transform, bounds, crs = _read_sar_vv(tif_path)
    flood_mask = _read_flood_mask(mask_path)

    # Percentile-stretch VV for display (convert to dB first)
    vv_db = 10.0 * np.log10(np.where(vv > 0, vv, 1e-10))
    vv_display = _percentile_stretch(vv_db)

    H, W = vv_display.shape
    extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]

    # ── Figure setup ─────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.set_facecolor("#1a1a2e")
    fig.patch.set_facecolor("#1a1a2e")

    # ── 1. SAR VV background (grayscale) ─────────────────────────────────────
    ax.imshow(
        vv_display,
        cmap="gray",
        extent=extent,
        origin="upper",
        interpolation="bilinear",
        vmin=0, vmax=1,
    )

    # ── 2. Flood mask overlay (blue, semi-transparent) ────────────────────────
    flood_rgba = np.zeros((*flood_mask.shape, 4), dtype=np.float32)
    flood_rgba[flood_mask == 1] = [0.10, 0.45, 0.85, alpha_flood]  # blue

    ax.imshow(
        flood_rgba,
        extent=extent,
        origin="upper",
        interpolation="nearest",
    )

    # ── 3. Road network ───────────────────────────────────────────────────────
    if road_graph is not None:
        for u, v, k, data in road_graph.edges(keys=True, data=True):
            geom = data.get("geometry")
            if geom is None:
                continue
            is_flooded = data.get("flooded", False)
            color      = "#FF4444" if is_flooded else "#44FF88"
            linewidth  = 0.8

            xs, ys = geom.xy
            ax.plot(xs, ys, color=color, linewidth=linewidth, alpha=0.85, zorder=3)

    # ── 4. Safe route ─────────────────────────────────────────────────────────
    if route_gdf is not None and len(route_gdf) > 0:
        # Reproject route to chip CRS for display
        route_proj = route_gdf.to_crs(crs)
        for _, row in route_proj.iterrows():
            geom = row.geometry
            if geom is not None and not geom.is_empty:
                xs, ys = geom.xy
                ax.plot(
                    xs, ys,
                    color="#FFD700",   # gold
                    linewidth=3.5,
                    zorder=5,
                    solid_capstyle="round",
                    label="Safe Route",
                )

                # Mark origin and destination
                ax.scatter(xs[0],  ys[0],  s=120, c="#00FF7F", zorder=6, marker="o",
                           edgecolors="white", linewidths=1.5, label="Origin")
                ax.scatter(xs[-1], ys[-1], s=120, c="#FF6347", zorder=6, marker="*",
                           edgecolors="white", linewidths=1.5, label="Destination")

                # Annotate route length
                route_len = row.get("route_length_m", None)
                if route_len:
                    mid_idx = len(xs) // 2
                    ax.annotate(
                        f"{route_len/1000:.2f} km",
                        xy=(xs[mid_idx], ys[mid_idx]),
                        color="white",
                        fontsize=9,
                        fontweight="bold",
                        ha="center",
                        bbox=dict(boxstyle="round,pad=0.3", fc="#1a1a2e", alpha=0.7),
                        zorder=7,
                    )

    # ── 5. Legend and labels ──────────────────────────────────────────────────
    legend_elements = [
        mpatches.Patch(facecolor="#1A72D9", alpha=0.6, label="Flood (predicted)"),
        plt.Line2D([0], [0], color="#44FF88", linewidth=1.5, label="Passable road"),
        plt.Line2D([0], [0], color="#FF4444", linewidth=1.5, label="Flooded road"),
        plt.Line2D([0], [0], color="#FFD700", linewidth=3.0, label="Safe route"),
    ]
    ax.legend(
        handles=legend_elements,
        loc="lower right",
        fontsize=9,
        facecolor="#2d2d44",
        edgecolor="gray",
        labelcolor="white",
        framealpha=0.9,
    )

    ax.set_title(
        "Flood Detection & Safe Route Generation",
        color="white", fontsize=14, fontweight="bold", pad=12,
    )
    ax.set_xlabel("Easting (m)", color="lightgray", fontsize=9)
    ax.set_ylabel("Northing (m)", color="lightgray", fontsize=9)
    ax.tick_params(colors="lightgray", labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor("#555577")

    plt.tight_layout()

    # ── Save ──────────────────────────────────────────────────────────────────
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Visualization saved to: {out}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize flood mask and route overlay.")
    parser.add_argument("--input",  required=True, help="Path to Sentinel-1 GeoTIFF chip.")
    parser.add_argument("--mask",   required=True, help="Path to binary flood mask GeoTIFF.")
    parser.add_argument("--route",  default=None,  help="Path to safe route GeoJSON (optional).")
    parser.add_argument("--output", default="outputs/visualization.png")
    args = parser.parse_args()

    route_gdf = None
    if args.route:
        route_gdf = gpd.read_file(args.route)

    visualize(
        tif_path=args.input,
        mask_path=args.mask,
        route_gdf=route_gdf,
        output_path=args.output,
    )
