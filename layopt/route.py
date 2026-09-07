# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""A small maze router for the connections a move has to make.

When a bridge or jumper cannot be a straight bar because place-and-route
wiring already occupies the track, the connection is routed *around* it: a
Dijkstra search over a rasterized window on the lowest routing layers (li,
met1, met2 in sky130) with vias between them.  Other nets' geometry, grown by
the layer's spacing plus half the wire width, is blocked; the connection's own
net (its pins, its existing P&R wires) is free space and any of it is a
legal landing -- touching a net's own wire connects to it.  The result is
plain rectangles (wires, cuts, landing pads) that the caller adds to the
layout and then verifies the way every move is verified: re-extraction,
topology signature, delta-DRC.  The raster is conservative (growth rounded
up), so a path found here is normally legal; the guards remain the authority.

Coordinates are dbu; `grid_um` is the routing raster (default 10 nm).
"""
import heapq
import os
from typing import Dict, List, Optional, Sequence, Set, Tuple

import numpy as np

from . import geom
from .geom import Rect

LAST_ROUTE_STATS: Dict[str, object] = {}


def maze_route(fl, tech, net: int, src2net: Dict[int, int], sources: Sequence[Tuple[int, int, int]],
               window: Rect, new_ids: Sequence[int] = (), n_layers: int = 3, grid_um: float = 0.01,
               via_cost: int = 25, targets_extra: Sequence[Tuple[int, Rect]] = (),
               own_ids: Sequence[int] = (),
               max_pops: int = 2_000_000) -> Optional[Tuple[int, List[Tuple[Tuple[int, int], Rect]]]]:
    """Route from any of `sources` -- (layer index, x, y) points, layer 0 =
    tech.routing[0] -- to any shape of `net` on the first `n_layers` routing
    layers inside `window` (plus `targets_extra`: (layer index, rect) landings
    the caller is about to add).  Returns (source index used, [(layer, rect)])
    or None.  Rects added by the current move are not extracted yet, so
    src2net does not know them: `own_ids` are the ones that belong to `net`
    (a new strap the route starts from), `new_ids` the ones that do not even
    if src2net says otherwise."""
    LAST_ROUTE_STATS.clear()
    L = tech.layers
    dbu = fl.dbu_um
    nm = lambda v: int(round(v / dbu))
    g = max(1, nm(grid_um))
    layers = list(tech.routing[:n_layers])
    cuts = [c for (lo, c, up) in tech.vias if lo in layers and up in layers][:n_layers - 1]
    lay_ids = [L[n] for n in layers]
    cut_ids = [L[c] for c in cuts]
    width = [nm(tech.min_width.get(n, 0.14)) for n in layers]
    space = [nm(tech.min_space.get(n, 0.14)) for n in layers]
    cw = [nm(tech.min_width.get(c, 0.17)) for c in cuts]
    csp = [nm(tech.min_space.get(c, 0.17)) for c in cuts]
    enc = [(nm(tech.enclosure.get((layers[i], cuts[i]), 0.03)), nm(tech.enclosure.get((layers[i + 1], cuts[i]), 0.03)))
           for i in range(len(cuts))]
    x0, y0, x1, y1 = window
    nx = (x1 - x0) // g + 1
    ny = (y1 - y0) // g + 1
    if nx * ny * len(layers) > 6_000_000:
        LAST_ROUTE_STATS["error"] = "window too large (%d cells)" % (nx * ny * len(layers))
        return None

    own_set = set(own_ids); new_set = set(new_ids)
    def own(k: int) -> bool:
        return (src2net.get(k) == net or k in own_set) and k not in new_set

    def cells(r: Rect, grow: int) -> Optional[Tuple[int, int, int, int]]:
        """Raster cell range whose centres lie inside r grown by `grow`
        (centres strictly inside: a centre exactly on the grown edge is a
        wire edge touching the spacing envelope, which is legal)."""
        ax0, ay0, ax1, ay1 = r[0] - grow, r[1] - grow, r[2] + grow, r[3] + grow
        i0 = max(0, (ax0 - x0) // g + 1)          # first centre strictly right of ax0
        i1 = min(nx - 1, (ax1 - x0 - 1) // g)     # last centre strictly left of ax1
        j0 = max(0, (ay0 - y0) // g + 1)
        j1 = min(ny - 1, (ay1 - y0 - 1) // g)
        if i1 < i0 or j1 < j0:
            return None
        return i0, j0, i1, j1

    def mark(arr, r: Rect, grow: int):
        c = cells(r, grow)
        if c:
            arr[c[0]:c[2] + 1, c[1]:c[3] + 1] = True

    blocked = [np.zeros((nx, ny), dtype=bool) for _ in layers]
    via_ok: List[np.ndarray] = []
    target = [np.zeros((nx, ny), dtype=bool) for _ in layers]
    big = (x0 - nm(1.0), y0 - nm(1.0), x1 + nm(1.0), y1 + nm(1.0))
    by_layer: Dict[Tuple[int, int], List[Tuple[int, Rect]]] = {}
    for k, r in enumerate(fl.rects):
        if (r.layer in lay_ids or r.layer in cut_ids) and geom.overlaps(r.rect, big):
            by_layer.setdefault(r.layer, []).append((k, r.rect))
    n_obst = 0
    own_rects: List[List[Rect]] = [[] for _ in layers]
    for i, lid in enumerate(lay_ids):
        half = width[i] // 2
        for k, r in by_layer.get(lid, []):
            if own(k):
                # a landing: the wire centre inside the shape (overlap of at least half
                # a width, not a corner touch).  The move's own new rects (own_ids)
                # are free space but not landings: the route starts from them.
                if k not in own_set:
                    mark(target[i], r, 0)
                own_rects[i].append(r)
                continue
            n_obst += 1
            mark(blocked[i], r, space[i] + half)
        # other nets' cuts touching this layer short a wire drawn over them
        for vi in (i - 1, i):
            if 0 <= vi < len(cuts):
                for k, r in by_layer.get(cut_ids[vi], []):
                    if not own(k):
                        mark(blocked[i], r, half)
    # a via needs its cut clear of every cut on that layer (cut spacing is
    # net-blind) and its two landing pads clear of other nets on both layers
    for vi, cid in enumerate(cut_ids):
        bad = np.zeros((nx, ny), dtype=bool)
        for i in (vi, vi + 1):
            pad_half = cw[vi] // 2 + enc[vi][i - vi]          # this layer's landing pad
            for k, r in by_layer.get(lay_ids[i], []):
                if not own(k):
                    mark(bad, r, space[i] + pad_half)
            for vj in (i - 1, i):
                if 0 <= vj < len(cuts):
                    for k, r in by_layer.get(cut_ids[vj], []):
                        if not own(k) and vj != vi:
                            mark(bad, r, pad_half)
        # cut spacing applies regardless of net
        for k, r in by_layer.get(cid, []):
            mark(bad, r, csp[vi] + cw[vi] // 2)
        via_ok.append(~bad)
    for li, r in targets_extra:
        if 0 <= li < len(layers):
            mark(target[li], r, 0)
    # wire footprints must stay inside the window
    for i in range(len(layers)):
        m = width[i] // 2 // g + 1
        blocked[i][:m, :] = True; blocked[i][-m:, :] = True
        blocked[i][:, :m] = True; blocked[i][:, -m:] = True
    LAST_ROUTE_STATS.update({"cells": nx * ny, "layers": len(layers), "obstacles": n_obst,
                             "targets": int(sum(int(t.sum()) for t in target))})
    probe = os.environ.get("LAYOPT_ROUTE_PROBE")
    if probe:                                    # "li:3825:1200,mcon:3825:1445,..." (dbu)
        for item in probe.split(","):
            name, px, py = item.split(":"); px, py = int(px), int(py)
            i = int(round((px - x0) / g)); j = int(round((py - y0) / g))
            if not (0 <= i < nx and 0 <= j < ny):
                print("      route-probe %s: outside window" % item); continue
            if name in layers:
                li = layers.index(name)
                print("      route-probe %s: blocked=%s target=%s" % (item, bool(blocked[li][i, j]), bool(target[li][i, j])))
            elif name in cuts:
                print("      route-probe %s: via_ok=%s" % (item, bool(via_ok[cuts.index(name)][i, j])))
    if not any(t.any() for t in target):
        LAST_ROUTE_STATS["error"] = "no landing of the net inside the window"
        return None

    # Same-net geometry is free space (a wire merging into its own net is the
    # point), but a wire passing *beside* an own shape closer than spacing
    # without touching it is a violation the raster cannot express per cell
    # (a straight run's rect is the union of its cells).  So: search, check the
    # resulting rects against own shapes, block the offending cells, repeat.
    for attempt in range(6):
        res = _search(layers, cuts, nx, ny, x0, y0, g, blocked, via_ok, target, sources, via_cost, max_pops)
        if res is None:
            return None
        src_idx, path = res
        tagged = _path_rects(path, x0, y0, g, lay_ids, cut_ids, width, cw, enc)
        rects = [(lid, r) for lid, r, _ in tagged]
        faults = _own_spacing_faults(tagged, own_rects, lay_ids, space)
        if probe:
            print("      route-attempt %d: cost %s, %d cells, %d rects, %d own-spacing faults" % (
                attempt, LAST_ROUTE_STATS.get("cost"), len(path), len(rects), len(faults)))
            for lid, r in rects:
                print("         %s %s" % (layers[lay_ids.index(lid)] if lid in lay_ids else cuts[cut_ids.index(lid)], [round(v * dbu, 3) for v in r]))
        if not faults or os.environ.get("LAYOPT_ROUTE_NO_REPAIR"):
            # (the env switch returns the unrepaired path so the delta-DRC's
            # same-net notch rule can be shown to catch what the repair fixes)
            LAST_ROUTE_STATS["repairs"] = attempt
            LAST_ROUTE_STATS["unrepaired_faults"] = len(faults)
            return src_idx, rects
        # Block the spacing band around each offending own shape, except the
        # corridors from which a straight run enters the shape (its centre line
        # inside the shape's extent on the other axis): a wire may merge into
        # its own net head-on, not skirt it.
        for li, o, via_i in faults:
            inside = np.zeros((nx, ny), dtype=bool); mark(inside, o, 0)
            if via_i is not None:
                # a landing pad beside an own shape: no via there unless the pad
                # centre is inside the shape (then the pad merges with it)
                pad_half = cw[via_i] // 2 + enc[via_i][li - via_i]
                band = np.zeros((nx, ny), dtype=bool); mark(band, o, space[li] + pad_half)
                via_ok[via_i] &= ~(band & ~inside)
                continue
            half = width[li] // 2
            band = np.zeros((nx, ny), dtype=bool); mark(band, o, space[li] + half)
            corridor = np.zeros((nx, ny), dtype=bool)
            cx = cells((o[0] + half, y0, o[2] - half, y1), 0)
            if cx:
                corridor[cx[0]:cx[2] + 1, :] = True
            cy = cells((x0, o[1] + half, x1, o[3] - half), 0)
            if cy:
                corridor[:, cy[1]:cy[3] + 1] = True
            blocked[li] |= band & ~inside & ~corridor
    LAST_ROUTE_STATS["error"] = "own-net spacing could not be repaired"
    return None


def _own_spacing_faults(tagged, own_rects, lay_ids, space):
    """(layer index, own shape, via index or None) where a routed wire or
    landing pad lies within spacing of a same-net shape it does not touch."""
    faults = []
    for lid, r, via_i in tagged:
        if lid not in lay_ids:
            continue
        li = lay_ids.index(lid)
        sp = space[li]
        for o in own_rects[li]:
            if geom.touches(r, o):
                continue
            grown = (o[0] - sp, o[1] - sp, o[2] + sp, o[3] + sp)
            if geom.overlaps(r, grown) and (li, o, via_i) not in faults:
                faults.append((li, o, via_i))
    return faults


def _search(layers, cuts, nx, ny, x0, y0, g, blocked, via_ok, target, sources, via_cost, max_pops):
    # Dijkstra over (layer, i, j)
    INF = 1 << 60
    dist = [np.full((nx, ny), INF, dtype=np.int64) for _ in layers]
    prev: Dict[Tuple[int, int, int], Tuple[int, int, int]] = {}
    src_of: Dict[Tuple[int, int, int], int] = {}
    heap = []
    for si, (li, sx, sy) in enumerate(sources):
        i = int(round((sx - x0) / g)); j = int(round((sy - y0) / g))
        if not (0 <= i < nx and 0 <= j < ny) or not (0 <= li < len(layers)):
            continue
        if dist[li][i, j] == 0:
            continue
        dist[li][i, j] = 0
        src_of[(li, i, j)] = si
        heapq.heappush(heap, (0, li, i, j))
    pops = 0
    found = None
    while heap:
        d, li, i, j = heapq.heappop(heap)
        if d != dist[li][i, j]:
            continue
        pops += 1
        if pops > max_pops:
            LAST_ROUTE_STATS["error"] = "search budget exhausted"
            break
        if target[li][i, j] and not blocked[li][i, j] and d > 0:
            found = (li, i, j)
            break
        # the source cell itself may sit on blocked raster (it is over the caller's new pad);
        # from there we may only step to legal cells
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ni, nj = i + di, j + dj
            if 0 <= ni < nx and 0 <= nj < ny and not blocked[li][ni, nj]:
                nd = d + 1
                if nd < dist[li][ni, nj]:
                    dist[li][ni, nj] = nd
                    prev[(li, ni, nj)] = (li, i, j)
                    heapq.heappush(heap, (nd, li, ni, nj))
        for nl, vi in ((li + 1, li), (li - 1, li - 1)):
            if 0 <= nl < len(layers) and 0 <= vi < len(cuts) and via_ok[vi][i, j] and not blocked[nl][i, j]:
                nd = d + via_cost
                if nd < dist[nl][i, j]:
                    dist[nl][i, j] = nd
                    prev[(nl, i, j)] = (li, i, j)
                    heapq.heappush(heap, (nd, nl, i, j))
    LAST_ROUTE_STATS["pops"] = LAST_ROUTE_STATS.get("pops", 0) + pops
    if found is None:
        LAST_ROUTE_STATS.setdefault("error", "no path")
        return None
    # walk back
    path = [found]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path.reverse()
    src_idx = src_of.get(path[0], 0)
    LAST_ROUTE_STATS.update({"path_cells": len(path), "cost": int(dist[found[0]][found[1], found[2]])})
    return src_idx, path


def _path_rects(path, x0, y0, g, lay_ids, cut_ids, width, cw, enc) -> List[Tuple[Tuple[int, int], Rect, Optional[int]]]:
    """Wires as one rect per straight run (extended by half a width at the
    ends so corners are square), a cut plus two pads per layer change.  Each
    entry is (layer, rect, via index for a landing pad else None)."""
    out: List[Tuple[Tuple[int, int], Rect, Optional[int]]] = []
    xy = lambda i, j: (x0 + i * g, y0 + j * g)
    run = [path[0]]

    def flush(run):
        li = run[0][0]
        half = width[li] // 2
        xs = [xy(i, j)[0] for _, i, j in run]; ys = [xy(i, j)[1] for _, i, j in run]
        out.append((lay_ids[li], (min(xs) - half, min(ys) - half, max(xs) + half, max(ys) + half), None))

    for a, b in zip(path, path[1:]):
        if a[0] != b[0]:                       # via
            flush(run)
            vi = min(a[0], b[0])
            x, y = xy(a[1], a[2])
            h = cw[vi] // 2
            out.append((cut_ids[vi], (x - h, y - h, x + h, y + h), None))
            for side, li in ((0, vi), (1, vi + 1)):
                p = h + enc[vi][side]
                out.append((lay_ids[li], (x - p, y - p, x + p, y + p), vi))
            run = [b]
            continue
        # same layer: extend the run while collinear
        if len(run) >= 2:
            (_, i0, j0), (_, i1, j1) = run[-2], run[-1]
            if (b[1] - i1, b[2] - j1) != (i1 - i0, j1 - j0):
                flush(run)
                run = [run[-1]]
        run.append(b)
    flush(run)
    return out
