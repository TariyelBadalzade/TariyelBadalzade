import argparse
import warnings
from pathlib import Path
from typing import Optional

import geopandas as gpd
import osmnx as ox
import rasterio
from pyproj import Transformer

# Suppress noisy OSMnx HTTP warnings in non-interactive use
warnings.filterwarnings("ignore", category=UserWarning, module="osmnx")

# ── Road type filter ──────────────────────────────────────────────────────────

# OSM highway tag values included in the driveable routing graph.
# Pedestrian paths, tracks, and cycleways are excluded.
DRIVEABLE_ROAD_TYPES = [
    "motorway",
    "trunk",
    "primary",
    "secondary",
    "tertiary",
    "residential",
    "unclassified",
    "motorway_link",
    "trunk_link",
    "primary_link",
    "secondary_link",
    "tertiary_link",
]

# Approximate road half-widths in metres by OSM highway type.
# Used for buffer-based flood overlay in overlay.py.
ROAD_HALF_WIDTHS = {
    "motorway":       10.0,
    "motorway_link":   5.0,
    "trunk":           8.0,
    "trunk_link":      4.0,
    "primary":         6.0,
    "primary_link":    3.0,
    "secondary":       5.0,
    "secondary_link":  2.5,
    "tertiary":        4.0,
    "tertiary_link":   2.0,
    "residential":     3.0,
    "unclassified":    3.0,
}
DEFAULT_HALF_WIDTH = 3.0


# ── Core function ─────────────────────────────────────────────────────────────

def get_road_graph(
    tif_path: str,
    road_types: Optional[list] = None,
    min_edges: int = 5,
    simplify: bool = True,
):
    """
    Retrieve an OSM road network graph for the geographic extent of a GeoTIFF.

    Args:
        tif_path:   Path to a georeferenced GeoTIFF (Sentinel-1 chip).
        road_types: List of OSM highway tag values to include.
                    Defaults to DRIVEABLE_ROAD_TYPES.
        min_edges:  Minimum number of edges required; returns None if fewer found.
        simplify:   Whether to simplify the graph (remove redundant nodes).

    Returns:
        A projected NetworkX MultiDiGraph in the native UTM CRS of the chip,
        or None if OSM coverage is insufficient.
    """
    if road_types is None:
        road_types = DRIVEABLE_ROAD_TYPES

    # ── 1. Extract bounding box from GeoTIFF metadata ─────────────────────────
    with rasterio.open(tif_path) as src:
        bounds    = src.bounds          # (left, bottom, right, top) in native CRS
        crs_epsg  = src.crs.to_epsg()
        chip_crs  = src.crs

    # ── 2. Reproject bounding box to WGS84 for OSM query ─────────────────────
    transformer = Transformer.from_crs(crs_epsg, 4326, always_xy=True)

    # Transform all four corners to handle non-rectangular projected footprints
    corners = [
        (bounds.left,  bounds.bottom),
        (bounds.right, bounds.bottom),
        (bounds.left,  bounds.top),
        (bounds.right, bounds.top),
    ]
    lons, lats = zip(*[transformer.transform(x, y) for x, y in corners])
    north, south = max(lats), min(lats)
    east,  west  = max(lons), min(lons)

    print(f"Querying OSM for bbox: N={north:.4f} S={south:.4f} E={east:.4f} W={west:.4f}")

    # ── 3. Download road graph from OSM ──────────────────────────────────────
    highway_filter = "|".join(road_types)
    custom_filter  = f'["highway"~"{highway_filter}"]'

    try:
        G = ox.graph_from_bbox(
            bbox=(north, south, east, west),
            network_type="drive",
            custom_filter=custom_filter,
            retain_all=False,
            simplify=False,
        )
    except Exception as e:
        print(f"OSMnx query failed: {e}")
        return None

    # ── 4. Check minimum coverage ─────────────────────────────────────────────
    n_edges = G.number_of_edges()
    if n_edges < min_edges:
        print(f"Insufficient OSM coverage: only {n_edges} edges found (min={min_edges}).")
        return None

    print(f"Retrieved {G.number_of_nodes()} nodes and {n_edges} edges from OSM.")

    # ── 5. Simplify (before projection for accuracy) ─────────────────────────
    if simplify:
        G = ox.simplify_graph(G)
        print(f"After simplification: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")

    # ── 6. Always project to UTM for metric buffering (metres, not degrees) ────
    # The chip may be in WGS84 (EPSG:4326) where buffer(3.0) = 3 degrees = ~300km.
    # We find the correct UTM zone from the bounding box centre instead.
    centre_lon = (east + west) / 2
    centre_lat = (north + south) / 2
    utm_zone   = int((centre_lon + 180) / 6) + 1
    utm_epsg   = (32600 + utm_zone) if centre_lat >= 0 else (32700 + utm_zone)

    G = ox.project_graph(G, to_crs=f"EPSG:{utm_epsg}")

    # Store chip CRS so overlay.py can reproject geometries for rasterization
    G.graph["chip_crs"] = f"EPSG:{crs_epsg}"
    G.graph["utm_epsg"] = utm_epsg
    print(f"Graph projected to UTM EPSG:{utm_epsg} for metric buffering.")

    # ── 7. Annotate edges with half-width for overlay ─────────────────────────
    for u, v, k, data in G.edges(keys=True, data=True):
        hw = data.get("highway", "unclassified")
        if isinstance(hw, list):
            hw = hw[0]
        data["half_width"] = ROAD_HALF_WIDTHS.get(hw, DEFAULT_HALF_WIDTH)

    return G


# ── Export helper ─────────────────────────────────────────────────────────────

def save_graph(G, output_path: str):
    """Save road graph edges as a GeoPackage for inspection in GIS tools."""
    edges_gdf = ox.graph_to_gdfs(G, nodes=False, edges=True)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    edges_gdf.to_file(output_path, driver="GPKG")
    print(f"Road graph saved to: {output_path}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract OSM road network for a GeoTIFF chip.")
    parser.add_argument("--input",  required=True, help="Path to input Sentinel-1 GeoTIFF.")
    parser.add_argument("--output", required=True, help="Path for output GeoPackage (.gpkg).")
    args = parser.parse_args()

    G = get_road_graph(args.input)
    if G is not None:
        save_graph(G, args.output)
    else:
        print("No road graph produced.")
