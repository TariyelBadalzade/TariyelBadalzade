from typing import Tuple

import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.transform import Affine
import networkx as nx

# High routing weight assigned to flooded edges (effectively impassable)
FLOOD_WEIGHT = 1_000_000.0


# ── Core function ─────────────────────────────────────────────────────────────

def classify_edges(
    G,
    flood_mask: np.ndarray,
    transform: Affine,
    flood_threshold: float = 0.30,
    soft_penalty: bool = False,
) -> object:
    mask_shape = flood_mask.shape    # (H, W)

    # ── CRS handling ──────────────────────────────────────────────────────────
    # The graph is in UTM (metres) for correct metric buffering.
    # The flood mask is in the chip CRS (often WGS84 degrees).
    # We must reproject buffered UTM polygons → mask CRS before rasterizing.
    from pyproj import Transformer as _Transformer
    from shapely.ops import transform as _shp_transform

    graph_crs = G.graph.get("crs", "EPSG:4326")
    chip_crs  = G.graph.get("chip_crs", "EPSG:4326")
    need_reproject = (graph_crs != chip_crs)

    if need_reproject:
        _proj = _Transformer.from_crs(graph_crs, chip_crs, always_xy=True)
        def _reproject(geom):
            return _shp_transform(_proj.transform, geom)
    else:
        def _reproject(geom):
            return geom

    flooded_count   = 0
    processed_count = 0

    for u, v, k, data in G.edges(keys=True, data=True):
        geom = data.get("geometry")
        if geom is None:
            from shapely.geometry import LineString
            u_data = G.nodes[u]
            v_data = G.nodes[v]
            geom = LineString([(u_data["x"], u_data["y"]), (v_data["x"], v_data["y"])])

        half_width = data.get("half_width", 3.0)

        # Buffer in UTM (metres), then reproject to mask CRS for rasterization
        road_poly = _reproject(geom.buffer(half_width))

        # Rasterize the road footprint polygon onto the flood mask grid
        road_pixels = rasterize(
            shapes=[(road_poly, 1)],
            out_shape=mask_shape,
            transform=transform,
            fill=0,
            default_value=1,
            dtype=np.uint8,
            all_touched=True,
        )

        total_road_pixels = int(road_pixels.sum())

        if total_road_pixels == 0:
            # Edge falls entirely outside the image extent
            data["flooded"]     = False
            data["flood_ratio"] = 0.0
            data["weight"]      = data.get("length", 1.0)
            continue

        # Count flooded pixels within the road footprint
        flooded_pixels = int((road_pixels & flood_mask).sum())
        flood_ratio    = flooded_pixels / total_road_pixels

        is_flooded = flood_ratio > flood_threshold

        data["flooded"]     = is_flooded
        data["flood_ratio"] = round(flood_ratio, 4)

        if is_flooded:
            if soft_penalty:
                # Weight increases with flood coverage: fully flooded = FLOOD_WEIGHT
                data["weight"] = data.get("length", 1.0) * (1.0 + flood_ratio * FLOOD_WEIGHT)
            else:
                data["weight"] = FLOOD_WEIGHT
            flooded_count += 1
        else:
            data["weight"] = data.get("length", 1.0)

        processed_count += 1

    total_edges = G.number_of_edges()
    print(
        f"Edge classification complete: "
        f"{flooded_count}/{total_edges} edges flooded "
        f"({100 * flooded_count / max(total_edges, 1):.1f}%) "
        f"at threshold={flood_threshold}"
    )

    return G


# ── Passability check ─────────────────────────────────────────────────────────

def find_nearest_dry_node(G, node_id: int, search_radius: float = 200.0) -> int:
    from shapely.geometry import Point

    # Check if the node itself is dry (has at least one passable adjacent edge)
    def is_dry(n):
        for nbr in list(G.successors(n)) + list(G.predecessors(n)):
            edge_data = G.get_edge_data(n, nbr) or G.get_edge_data(nbr, n)
            if edge_data:
                for _, d in edge_data.items():
                    if not d.get("flooded", True):
                        return True
        return False

    if is_dry(node_id):
        return node_id

    # Search within radius
    node_pos = (G.nodes[node_id]["x"], G.nodes[node_id]["y"])
    origin   = Point(node_pos)

    candidates = [
        (n, origin.distance(Point(G.nodes[n]["x"], G.nodes[n]["y"])))
        for n in G.nodes()
        if n != node_id and is_dry(n)
    ]
    if not candidates:
        return node_id   # No dry node found; return original

    candidates.sort(key=lambda t: t[1])
    nearest_node, dist = candidates[0]

    if dist <= search_radius:
        print(f"Rerouted endpoint from node {node_id} to nearest dry node {nearest_node} ({dist:.1f} m away).")
        return nearest_node

    print(f"Warning: No dry node found within {search_radius} m of node {node_id}.")
    return node_id


# ── Flood mask loader helper ──────────────────────────────────────────────────

def load_flood_mask(mask_path: str) -> Tuple[np.ndarray, Affine]:
    """Load a binary flood mask GeoTIFF and return (mask_array, affine_transform)."""
    with rasterio.open(mask_path) as src:
        mask      = src.read(1).astype(np.uint8)
        transform = src.transform
    # Ensure binary: treat any non-zero value as flooded
    mask = (mask > 0).astype(np.uint8)
    return mask, transform
