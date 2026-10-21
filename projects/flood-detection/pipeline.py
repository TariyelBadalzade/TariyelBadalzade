"""
Usage:
    python pipeline.py --config config.yaml \
                       --input  data/chip.tif \
                       --origin "12.9716,77.5946" \
                       --dest   "12.8406,80.2200"
"""

import argparse
import json
import time
from pathlib import Path

import yaml


def run_pipeline(
    tif_path: str,
    origin_latlon: tuple,
    dest_latlon: tuple,
    cfg: dict,
) -> dict:
    
    out_dir = Path(cfg.get("output_dir", "outputs"))
    out_dir.mkdir(parents=True, exist_ok=True)

    chip_name   = Path(tif_path).stem
    mask_path   = out_dir / f"{chip_name}_flood_mask.tif"
    route_path  = out_dir / f"{chip_name}_safe_route.geojson"
    viz_path    = out_dir / f"{chip_name}_visualization.png"

    results = {
        "chip":       chip_name,
        "mask_path":  str(mask_path),
        "route_path": None,
        "viz_path":   str(viz_path),
        "status":     None,
        "timings":    {},
    }

    t_total = time.time()

    # ── STEP 1: Flood segmentation ────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 1/4 — Flood Segmentation (U-Net inference)")
    print("=" * 60)
    t0 = time.time()

    from predict import predict_flood_mask
    predict_flood_mask(
        tif_path=tif_path,
        checkpoint_path=cfg["checkpoint"],
        output_path=str(mask_path),
        threshold=cfg.get("seg_threshold", 0.5),
    )
    results["timings"]["segmentation_s"] = round(time.time() - t0, 2)

    # ── STEP 2: OSM road extraction ───────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 2/4 — OSM Road Network Extraction")
    print("=" * 60)
    t0 = time.time()

    from road_extraction import get_road_graph
    G = get_road_graph(tif_path)
    results["timings"]["road_extraction_s"] = round(time.time() - t0, 2)

    if G is None:
        msg = "Pipeline aborted: insufficient OSM road coverage for this chip."
        print(msg)
        results["status"] = msg
        return results

    # ── STEP 3: Flood-road overlay ────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 3/4 — Flood-Road Overlay")
    print("=" * 60)
    t0 = time.time()

    from overlay import classify_edges, load_flood_mask
    flood_mask, transform = load_flood_mask(str(mask_path))
    G = classify_edges(
        G,
        flood_mask,
        transform,
        flood_threshold=cfg.get("flood_threshold", 0.30),
        soft_penalty=cfg.get("soft_penalty", False),
    )
    results["timings"]["overlay_s"] = round(time.time() - t0, 2)

    # ── STEP 4: Safe route generation ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 4/4 — Safe Route Generation")
    print("=" * 60)
    t0 = time.time()

    from routing import get_safe_route
    route_gdf, route_status = get_safe_route(
        G,
        origin_latlon=origin_latlon,
        dest_latlon=dest_latlon,
        algorithm=cfg.get("algorithm", "dijkstra"),
        fallback_radius=cfg.get("fallback_radius_m", 200.0),
    )
    results["timings"]["routing_s"] = round(time.time() - t0, 2)
    results["status"] = route_status

    if route_gdf is not None:
        route_gdf.to_file(str(route_path), driver="GeoJSON")
        results["route_path"] = str(route_path)
        print(f"Route GeoJSON saved: {route_path}")
    else:
        print(f"No route: {route_status}")

    # ── Visualization ─────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Generating visualization...")
    print("=" * 60)

    from visualize import visualize
    visualize(
        tif_path=tif_path,
        mask_path=str(mask_path),
        road_graph=G,
        route_gdf=route_gdf,
        output_path=str(viz_path),
    )

    # ── Summary ───────────────────────────────────────────────────────────────
    results["timings"]["total_s"] = round(time.time() - t_total, 2)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  Flood mask:   {mask_path}")
    print(f"  Route:        {results['route_path'] or 'N/A'}")
    print(f"  Visualization:{viz_path}")
    print(f"  Status:       {route_status}")
    print(f"  Timings:      {results['timings']}")

    # Save results summary
    summary_path = out_dir / f"{chip_name}_summary.json"
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Summary:      {summary_path}")

    return results


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="End-to-end flood detection and safe route generation pipeline."
    )
    parser.add_argument("--config",  default="config.yaml",  help="Path to config YAML.")
    parser.add_argument("--input",   required=True,          help="Path to Sentinel-1 GeoTIFF.")
    parser.add_argument("--origin",  required=True,          help="Origin as 'lat,lon' (WGS84).")
    parser.add_argument("--dest",    required=True,          help="Destination as 'lat,lon' (WGS84).")
    args = parser.parse_args()

    with open(args.config) as f:
        cfg = yaml.safe_load(f)

    origin = tuple(map(float, args.origin.split(",")))
    dest   = tuple(map(float, args.dest.split(",")))

    run_pipeline(
        tif_path=args.input,
        origin_latlon=origin,
        dest_latlon=dest,
        cfg=cfg,
    )
