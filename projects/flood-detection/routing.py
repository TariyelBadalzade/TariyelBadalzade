import argparse
import math
from pathlib import Path
from typing import Optional, Tuple, List

import geopandas as gpd
import networkx as nx
import osmnx as ox
from shapely.geometry import LineString, Point


# ── Heuristic for A* ─────────────────────────────────────────────────────────

def _euclidean_heuristic(G):

    def heuristic(u, v):
        xu, yu = G.nodes[u]["x"], G.nodes[u]["y"]
        xv, yv = G.nodes[v]["x"], G.nodes[v]["y"]
        return math.hypot(xu - xv, yu - yv)
    return heuristic


# ── Path geometry reconstruction ─────────────────────────────────────────────

def _path_to_linestring(G, path: List[int]) -> Tuple[LineString, float]:

    coords = []
    total_length = 0.0

    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edge_data = G.get_edge_data(u, v)

        # Pick the minimum-weight parallel edge (multigraph)
        if edge_data is None:
            edge_data = G.get_edge_data(v, u)   # try reverse direction
        if edge_data is None:
            continue

        best = min(edge_data.values(), key=lambda d: d.get("weight", 0))
        geom   = best.get("geometry")
        length = best.get("length", 0.0)
        total_length += length

        if geom is not None:
            edge_coords = list(geom.coords)
            # Ensure direction matches path order
            node_u = (G.nodes[u]["x"], G.nodes[u]["y"])
            if edge_coords and _dist2(edge_coords[0], node_u) > _dist2(edge_coords[-1], node_u):
                edge_coords = edge_coords[::-1]
            coords.extend(edge_coords)
        else:
            coords.append((G.nodes[u]["x"], G.nodes[u]["y"]))
            coords.append((G.nodes[v]["x"], G.nodes[v]["y"]))

    # Deduplicate consecutive duplicate coordinates
    unique_coords = [coords[0]] if coords else []
    for c in coords[1:]:
        if c != unique_coords[-1]:
            unique_coords.append(c)

    return LineString(unique_coords) if len(unique_coords) >= 2 else None, total_length


def _dist2(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


# ── Main routing function ─────────────────────────────────────────────────────

def get_safe_route(
    G,
    origin_latlon: Tuple[float, float],
    dest_latlon: Tuple[float, float],
    algorithm: str = "dijkstra",
    fallback_radius: float = 200.0,
) -> Tuple[Optional[gpd.GeoDataFrame], str]:

    # ── 1. Match lat/lon to nearest graph nodes ───────────────────────────────
    # ── Convert WGS84 lat/lon to graph CRS before nearest node lookup ────────
    # Graph is in UTM — ox.nearest_nodes uses node x/y which are in metres.
    # Passing lon/lat directly would snap everything to the same wrong node.
    try:
        from pyproj import Transformer as _T
        graph_crs = G.graph.get("crs", "EPSG:4326")
        if "4326" not in str(graph_crs):
            # Graph is in UTM — convert WGS84 coords to UTM before lookup
            _to_utm = _T.from_crs("EPSG:4326", graph_crs, always_xy=True)
            orig_x, orig_y = _to_utm.transform(origin_latlon[1], origin_latlon[0])
            dest_x, dest_y = _to_utm.transform(dest_latlon[1],   dest_latlon[0])
        else:
            orig_x, orig_y = origin_latlon[1], origin_latlon[0]
            dest_x, dest_y = dest_latlon[1],   dest_latlon[0]

        orig_node = ox.nearest_nodes(G, orig_x, orig_y)
        dest_node = ox.nearest_nodes(G, dest_x, dest_y)
    except Exception as e:
        return None, f"Node matching failed: {e}"

    # ── 2. Substitute flooded endpoints with nearest dry nodes ────────────────
    from overlay import find_nearest_dry_node
    orig_node = find_nearest_dry_node(G, orig_node, fallback_radius)
    dest_node = find_nearest_dry_node(G, dest_node, fallback_radius)

    if orig_node == dest_node:
        return None, "Origin and destination resolve to the same node."

    # ── 3. Shortest path search ───────────────────────────────────────────────
    try:
        if algorithm == "astar":
            path = nx.astar_path(
                G,
                source=orig_node,
                target=dest_node,
                heuristic=_euclidean_heuristic(G),
                weight="weight",
            )
        else:  # dijkstra (default)
            path = nx.dijkstra_path(G, source=orig_node, target=dest_node, weight="weight")

    except nx.NetworkXNoPath:
        return None, (
            "No safe route found: flooding completely disconnects the origin "
            "and destination. Consider alternative transport or await flood recession."
        )
    except nx.NodeNotFound as e:
        return None, f"Node not found in graph: {e}"

    # ── 4. Check if the returned path actually avoids flooded edges ───────────
    flooded_edges_in_path = []
    for i in range(len(path) - 1):
        ed = G.get_edge_data(path[i], path[i + 1])
        if ed:
            best = min(ed.values(), key=lambda d: d.get("weight", 0))
            if best.get("flooded", False):
                flooded_edges_in_path.append((path[i], path[i + 1]))

    status = "OK"
    if flooded_edges_in_path:
        status = (
            f"WARNING: Route includes {len(flooded_edges_in_path)} flooded edge(s) "
            f"— no fully dry path exists. Proceed with extreme caution."
        )

    # ── 5. Reconstruct full route geometry ────────────────────────────────────
    route_geom, route_length = _path_to_linestring(G, path)
    if route_geom is None:
        return None, "Could not reconstruct route geometry."

    # ── 6. Collect road names along the route ────────────────────────────────
    road_names = []
    for i in range(len(path) - 1):
        ed = G.get_edge_data(path[i], path[i + 1])
        if ed:
            best = min(ed.values(), key=lambda d: d.get("weight", 0))
            name = best.get("name")
            if name and name not in road_names:
                road_names.append(name if isinstance(name, str) else str(name))

    # ── 7. Build output GeoDataFrame (in WGS84 for GeoJSON export) ───────────
    # Re-project route geometry back to WGS84
    route_gdf = gpd.GeoDataFrame(
        {
            "route_length_m": [round(route_length, 1)],
            "n_segments":     [len(path) - 1],
            "algorithm":      [algorithm],
            "road_names":     ["; ".join(road_names) if road_names else "N/A"],
            "status":         [status],
        },
        geometry=[route_geom],
        crs=G.graph.get("crs", "EPSG:4326"),
    )
    route_gdf = route_gdf.to_crs("EPSG:4326")

    # Ensure string columns use plain str dtype for GeoJSON compatibility
    for col in route_gdf.select_dtypes(include='string').columns:
        route_gdf[col] = route_gdf[col].astype(str)

    print(f"Route found: {route_length:.0f} m, {len(path)-1} segments. Status: {status}")
    return route_gdf, status


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate safe route on a flood-annotated road graph.")
    parser.add_argument("--flood-mask",  required=True, help="Path to binary flood mask GeoTIFF.")
    parser.add_argument("--input-tif",   required=True, help="Path to original Sentinel-1 GeoTIFF (for road extraction).")
    parser.add_argument("--checkpoint",  required=True, help="Path to model checkpoint (used if mask not pre-computed).")
    parser.add_argument("--origin",      required=True, help="Origin as 'lat,lon' (WGS84).")
    parser.add_argument("--destination", required=True, help="Destination as 'lat,lon' (WGS84).")
    parser.add_argument("--algorithm",   default="dijkstra", choices=["dijkstra", "astar"])
    parser.add_argument("--threshold",   type=float, default=0.30, help="Flood edge classification threshold.")
    parser.add_argument("--output",      default="outputs/route.geojson", help="Output GeoJSON path.")
    args = parser.parse_args()

    from road_extraction import get_road_graph
    from overlay import classify_edges, load_flood_mask

    origin = tuple(map(float, args.origin.split(",")))
    dest   = tuple(map(float, args.destination.split(",")))

    flood_mask, transform = load_flood_mask(args.flood_mask)
    G = get_road_graph(args.input_tif)

    if G is None:
        print("ERROR: Could not extract road graph.")
        exit(1)

    G = classify_edges(G, flood_mask, transform, flood_threshold=args.threshold)
    route_gdf, status = get_safe_route(G, origin, dest, algorithm=args.algorithm)

    if route_gdf is not None:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        route_gdf.to_file(out, driver="GeoJSON")
        print(f"Route saved to: {out}")
    else:
        print(f"No route: {status}")
