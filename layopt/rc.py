# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""Parasitic R/C from rectangle geometry.

Capacitance: exact union area + perimeter per (net, layer) x tech Carea/Cfringe.
Resistance: a distributed model -- every conducting rectangle is a node; two
touching rectangles on one layer, or a cut and the metals it lands on, are an
edge whose resistance is the sheet resistance times the squares from each
rectangle's centre to the junction (plus the per-cut via resistance).  The
lumped per-net R is the sum over segments (what stat-sim's spef.py expects);
effective point-to-point resistance (IR drop, supply gradients) is solved
exactly on the Laplacian with numpy.
"""
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from . import geom
from .extract import Extraction

Rect = Tuple[int, int, int, int]


@dataclass
class Segment:
    a: int                      # shape ids
    b: int
    r: float                    # ohm
    layer: str
    kind: str                   # 'wire' | 'via'


@dataclass
class NetRC:
    net: int
    name: str
    c_fF: float
    r_ohm: float                # lumped series estimate (sum of segments)
    per_layer_c: Dict[str, float] = field(default_factory=dict)
    per_layer_len_um: Dict[str, float] = field(default_factory=dict)
    segments: List[Segment] = field(default_factory=list)

    @property
    def c(self) -> float:       # farads
        return self.c_fF * 1e-15


def _junction_r(ex: Extraction, i: int, j: int, layer: str) -> float:
    """Sheet R from centre of i to centre of j through their overlap/touch region."""
    rsh = ex.tech.rsh.get(layer, 0.0)
    if rsh == 0.0:
        return 0.0
    ri, rj = ex.shapes[i].rect, ex.shapes[j].rect
    ox0, oy0 = max(ri[0], rj[0]), max(ri[1], rj[1])
    ox1, oy1 = min(ri[2], rj[2]), min(ri[3], rj[3])
    jx, jy = (ox0 + ox1) / 2.0, (oy0 + oy1) / 2.0
    r = 0.0
    for rc in (ri, rj):
        cx, cy = (rc[0] + rc[2]) / 2.0, (rc[1] + rc[3]) / 2.0
        w, h = rc[2] - rc[0], rc[3] - rc[1]
        dx, dy = abs(jx - cx), abs(jy - cy)
        # squares along x use height as width and vice versa
        sq = (dx / h if h else 0.0) + (dy / w if w else 0.0)
        r += rsh * sq
    return r


def net_rc(ex: Extraction, net_id: int, with_segments: bool = True) -> NetRC:
    tech = ex.tech
    dbu = ex.dbu_um
    net = ex.nets[net_id]
    by_layer: Dict[str, List[int]] = {}
    for s in net.shapes:
        by_layer.setdefault(ex.shapes[s].layer, []).append(s)
    c_total = 0.0
    per_c: Dict[str, float] = {}
    per_len: Dict[str, float] = {}
    for layer, ids in by_layer.items():
        if layer not in tech.carea and layer not in tech.cfringe:
            continue
        a, p = geom.union_area_perimeter([ex.shapes[s].rect for s in ids])
        a_um2, p_um = a * dbu * dbu, p * dbu
        c = tech.carea.get(layer, 0.0) * a_um2 + tech.cfringe.get(layer, 0.0) * p_um
        per_c[layer] = c
        per_len[layer] = sum(max(ex.shapes[s].rect[2] - ex.shapes[s].rect[0],
                                 ex.shapes[s].rect[3] - ex.shapes[s].rect[1]) for s in ids) * dbu
        c_total += c
    segs: List[Segment] = []
    if with_segments:
        segs = net_segments(ex, net_id)
    r_total = sum(s.r for s in segs)
    return NetRC(net_id, net.name, c_total, r_total, per_c, per_len, segs)


def net_segments(ex: Extraction, net_id: int) -> List[Segment]:
    tech = ex.tech
    net = ex.nets[net_id]
    ids = net.shapes
    by_layer: Dict[str, List[int]] = {}
    for s in ids:
        by_layer.setdefault(ex.shapes[s].layer, []).append(s)
    idx: Dict[str, geom.BinIndex] = {}
    for layer, ls in by_layer.items():
        bi = geom.BinIndex(1000)
        for s in ls:
            bi.add(s, ex.shapes[s].rect)
        idx[layer] = bi
    segs: List[Segment] = []
    seen = set()
    wire_layers = [tech.poly] + list(tech.routing)
    for layer in wire_layers:
        if layer not in idx:
            continue
        for i in by_layer[layer]:
            for j in idx[layer].query_touch(ex.shapes[i].rect):
                if j <= i or (i, j) in seen:
                    continue
                seen.add((i, j))
                segs.append(Segment(i, j, _junction_r(ex, i, j, layer), layer, "wire"))
    # gate regions ride on their poly (negligible R): so receivers may be given as gate shapes
    if "gate" in idx and tech.poly in idx:
        for gsid in by_layer["gate"]:
            for psid in idx[tech.poly].query_overlap(ex.shapes[gsid].rect):
                segs.append(Segment(gsid, psid, 1e-3, tech.poly, "wire"))
    # cuts: diff contact -> first routing layer; via stack
    stacks = list(tech.vias)
    lower_of_contact = ["sd_n", "sd_p", tech.poly]
    for cut_layer, lowers, upper in ([(tech.diff_contact, lower_of_contact, tech.routing[0])] +
                                     [(cut, [lo], up) for lo, cut, up in stacks]):
        if cut_layer not in idx:
            continue
        rvia = tech.rvia.get(cut_layer, 0.0)
        for v in by_layer[cut_layer]:
            vr = ex.shapes[v].rect
            ups = idx[upper].query_overlap(vr) if upper in idx else []
            los = [s for lo in lowers if lo in idx for s in idx[lo].query_overlap(vr)]
            # via resistance sits on the cut node; wire squares to the landing rects
            for u in ups:
                segs.append(Segment(v, u, rvia / 2.0 + _junction_r(ex, v, u, upper) * 0.0, cut_layer, "via"))
            for lo in los:
                lay = ex.shapes[lo].layer
                rl = tech.rsh.get(lay, 0.0)
                segs.append(Segment(v, lo, rvia / 2.0, cut_layer, "via"))
    return segs


class ResistiveNet:
    """Laplacian of one net's segment graph; exact effective resistances."""

    def __init__(self, ex: Extraction, net_id: int, segments: Optional[Sequence[Segment]] = None,
                 r_floor: float = 1e-3):
        import numpy as np
        self.np = np
        segs = list(segments) if segments is not None else net_segments(ex, net_id)
        nodes = sorted({s.a for s in segs} | {s.b for s in segs} | set(ex.nets[net_id].shapes))
        self.index = {n: k for k, n in enumerate(nodes)}
        n = len(nodes)
        Lp = np.zeros((n, n))
        for s in segs:
            g = 1.0 / max(s.r, r_floor)
            a, b = self.index[s.a], self.index[s.b]
            Lp[a, a] += g; Lp[b, b] += g; Lp[a, b] -= g; Lp[b, a] -= g
        self.L = Lp
        self._pinv = None

    def r_eff(self, a: int, b: int) -> float:
        np = self.np
        if self._pinv is None:
            self._pinv = np.linalg.pinv(self.L, rcond=1e-12)
        i, j = self.index[a], self.index[b]
        P = self._pinv
        return float(P[i, i] + P[j, j] - 2 * P[i, j])

    def connected(self, a: int, b: int) -> bool:
        return math.isfinite(self.r_eff(a, b)) and self.r_eff(a, b) < 1e9


def shape_at(ex: Extraction, layer: str, x_um: float, y_um: float) -> Optional[int]:
    dbu = ex.dbu_um
    x, y = int(round(x_um / dbu)), int(round(y_um / dbu))
    for i, s in enumerate(ex.shapes):
        if s.layer == layer and s.rect[0] <= x <= s.rect[2] and s.rect[1] <= y <= s.rect[3]:
            return i
    return None


def all_nets_rc(ex: Extraction, with_segments: bool = False, min_shapes: int = 1) -> List[NetRC]:
    out = []
    for nid, net in ex.nets.items():
        if len(net.shapes) < min_shapes:
            continue
        out.append(net_rc(ex, nid, with_segments=with_segments))
    return out


# --------------------------------------------------------------------------
# SPEF (stat-sim spef.py compatible: one lumped C, one lumped R per net)
# --------------------------------------------------------------------------

def write_spef(nets: Sequence[NetRC], path: str, design: str = "layopt") -> int:
    lines = ['*SPEF "IEEE 1481-1998"', '*DESIGN "%s"' % design, '*DATE "generated by layopt"',
             '*VENDOR "Cameron EDA"', '*PROGRAM "layopt"', '*VERSION "0.1"', '*DESIGN_FLOW "EXTRACTION"',
             '*DIVIDER /', '*DELIMITER :', '*BUS_DELIMITER [ ]',
             '*T_UNIT 1 PS', '*C_UNIT 1 FF', '*R_UNIT 1 OHM', '*L_UNIT 1 HENRY', '', '*NAME_MAP']
    for i, n in enumerate(nets, start=1):
        lines.append('*%d %s' % (i, n.name))
    for i, n in enumerate(nets, start=1):
        lines += ['', '*D_NET *%d %.6g' % (i, n.c_fF)]
        if n.c_fF > 0:
            lines += ['*CAP', '1 *%d %.6g' % (i, n.c_fF)]
        if n.r_ohm > 0:
            lines += ['*RES', '1 *%d *0 %.6g' % (i, n.r_ohm)]
        lines.append('*END')
    with open(path, 'w') as fh:
        fh.write('\n'.join(lines) + '\n')
    return len(nets)


def shapes_c_fF(ex: Extraction, shape_ids: Sequence[int]) -> float:
    """Capacitance of a subset of shapes (e.g. one cell's share of a net):
    exact union area + perimeter per layer, same formula as net_rc."""
    tech, dbu = ex.tech, ex.dbu_um
    by: Dict[str, List[Rect]] = {}
    for s in shape_ids:
        by.setdefault(ex.shapes[s].layer, []).append(ex.shapes[s].rect)
    c = 0.0
    for layer, rects in by.items():
        if layer not in tech.carea and layer not in tech.cfringe:
            continue
        a, p = geom.union_area_perimeter(rects)
        c += tech.carea.get(layer, 0.0) * a * dbu * dbu + tech.cfringe.get(layer, 0.0) * p * dbu
    return c


def shape_c_fF(ex: Extraction, sid: int) -> float:
    """Capacitance of one conducting shape from its own rectangle."""
    sh = ex.shapes[sid]
    tech, dbu = ex.tech, ex.dbu_um
    if sh.layer not in tech.carea and sh.layer not in tech.cfringe:
        return 0.0
    w, h = (sh.rect[2] - sh.rect[0]) * dbu, (sh.rect[3] - sh.rect[1]) * dbu
    return tech.carea.get(sh.layer, 0.0) * w * h + tech.cfringe.get(sh.layer, 0.0) * 2 * (w + h)


def elmore_delays(ex: Extraction, net_id: int, driver_sid: int, receiver_sids: Sequence[int],
                  r_drive: float = 0.0, c_in_fF: Optional[Dict[int, float]] = None,
                  segments: Optional[Sequence[Segment]] = None) -> Dict[int, float]:
    """Elmore delay (ps) from a driver shape to each receiver shape on one net.

    The net's segment graph is reduced to its shortest-resistance-path tree
    from the driver (via stacks make small loops; the tree keeps the
    least-resistive route).  Each shape carries its own C plus any receiver
    input capacitance; Elmore(receiver) = r_drive*C_total + sum over the path
    of R_seg * C_downstream(seg).
    """
    import heapq
    segs = list(segments) if segments is not None else net_segments(ex, net_id)
    adj: Dict[int, List[Tuple[int, float]]] = {}
    for s in segs:
        r = max(s.r, 1e-3)
        adj.setdefault(s.a, []).append((s.b, r)); adj.setdefault(s.b, []).append((s.a, r))
    nodes = set(ex.nets[net_id].shapes) | set(adj)
    dist = {driver_sid: 0.0}; parent: Dict[int, Tuple[int, float]] = {}
    pq = [(0.0, driver_sid)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, float("inf")):
            continue
        for v, r in adj.get(u, []):
            nd = d + r
            if nd < dist.get(v, float("inf")):
                dist[v] = nd; parent[v] = (u, r); heapq.heappush(pq, (nd, v))
    c_in = c_in_fF or {}
    cap = {n: shape_c_fF(ex, n) + c_in.get(n, 0.0) for n in nodes}
    children: Dict[int, List[int]] = {}
    for v, (u, r) in parent.items():
        children.setdefault(u, []).append(v)
    down: Dict[int, float] = {}
    order = sorted(dist, key=lambda n: -dist[n])            # leaves first
    for n in order:
        down[n] = cap.get(n, 0.0) + sum(down[c] for c in children.get(n, []))
    c_total = sum(cap[n] for n in dist)
    out = {}
    for rs in receiver_sids:
        if rs not in dist:
            out[rs] = float("inf"); continue
        t = r_drive * c_total
        n = rs
        while n in parent:
            u, r = parent[n]
            t += r * down[n]
            n = u
        out[rs] = t * 1e-3                                  # ohm*fF -> ps
    return out


def fork_branches(ex: Extraction, net_id: int, driver_sid: int, receiver_sids: Sequence[int],
                  segments: Optional[Sequence[Segment]] = None) -> Dict:
    """Reduce a fork to lumped trunk + per-branch RC for a 2-port wire model
    (stat-sim's statsim_pl_rc): trunk = driver to the receivers' lowest common
    ancestor on the shortest-resistance tree; branch k = LCA to receiver k.
    R = series resistance along the path, C = capacitance of the shapes on it
    (plus, for the trunk, everything else hanging off the trunk).  Returns
    {"trunk": (R, C_fF), "branches": {rsid: (R, C_fF)}, "lca": shape id}."""
    import heapq
    segs = list(segments) if segments is not None else net_segments(ex, net_id)
    adj: Dict[int, List[Tuple[int, float]]] = {}
    for s in segs:
        r = max(s.r, 1e-3)
        adj.setdefault(s.a, []).append((s.b, r)); adj.setdefault(s.b, []).append((s.a, r))
    dist = {driver_sid: 0.0}; parent: Dict[int, Tuple[int, float]] = {}
    pq = [(0.0, driver_sid)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, float("inf")):
            continue
        for v, r in adj.get(u, []):
            if d + r < dist.get(v, float("inf")):
                dist[v] = d + r; parent[v] = (u, r); heapq.heappush(pq, (d + r, v))
    def path(n):
        p = [n]
        while p[-1] in parent:
            p.append(parent[p[-1]][0])
        return p[::-1]                                   # driver ... n
    paths = {r: path(r) for r in receiver_sids}
    common = None
    for p in paths.values():
        common = set(p) if common is None else common & set(p)
    lca = max(common, key=lambda n: dist[n]) if common else driver_sid
    def rc_of(nodes):
        R = sum(parent[n][1] for n in nodes if n in parent)
        C = sum(shape_c_fF(ex, n) for n in nodes)
        return R, C
    trunk_nodes = path(lca)
    branch = {}
    for r, p in paths.items():
        i = p.index(lca)
        branch[r] = rc_of(p[i + 1:])
    Rt, Ct = rc_of(trunk_nodes[1:])                      # driver shape itself is the source
    Ct += shape_c_fF(ex, driver_sid)
    # side loads on the trunk (shapes whose tree path leaves the trunk but reaches no receiver)
    on_paths = set().union(*paths.values())
    for n in dist:
        if n not in on_paths:
            q = n
            while q in parent and q not in on_paths:
                q = parent[q][0]
            if q in trunk_nodes:
                Ct += shape_c_fF(ex, n)
    return {"trunk": (Rt, Ct), "branches": branch, "lca": lca}
