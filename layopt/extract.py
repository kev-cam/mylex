# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""Connectivity and MOS device extraction from a flat rectangle layout.

Mirrors what kestrel/stat-sim do with KLayout's LayoutToNetlist (MOS3
recognition: gate = poly & diff, S/D = diff - poly, well decides N/P) but in
pure Python over rectangles, so the optimizer's inner loop does not need
KLayout and can re-extract after every geometry move.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from . import geom
from .gds import FlatLayout, FlatRect
from .tech import Tech

Rect = Tuple[int, int, int, int]


@dataclass
class Device:
    name: str
    kind: str                       # 'n' | 'p'
    model: str
    g: int                          # net ids
    s: int
    d: int
    w: float                        # um
    l: float                        # um
    as_: float = 0.0                # um^2
    ad: float = 0.0
    ps: float = 0.0                 # um
    pd: float = 0.0
    prov: str = ""
    gate_rect: Optional[Rect] = None
    flow_axis: str = "x"            # current flows along this axis; W is the other
    fingers: int = 1
    gate_ids: List[int] = field(default_factory=list)   # shape ids of gate rects


@dataclass
class Net:
    id: int
    name: str
    shapes: List[int] = field(default_factory=list)     # shape ids (index into Extraction.shapes)
    devices: List[Tuple[str, str]] = field(default_factory=list)   # (device name, terminal)


@dataclass
class Shape:
    """One conducting rectangle in the connectivity graph."""
    layer: str                      # logical layer name ('met1', 'licon', 'gate', 'sd', ...)
    rect: Rect
    prov: str
    src: int = -1                   # index of the originating FlatRect (or -1 for derived)


@dataclass
class Extraction:
    tech: Tech
    dbu_um: float
    shapes: List[Shape]
    net_of_shape: List[int]
    nets: Dict[int, Net]
    devices: List[Device]
    top: str = ""

    def net_by_name(self, name: str) -> Optional[Net]:
        for n in self.nets.values():
            if n.name == name:
                return n
        return None

    def signature(self) -> str:
        """Topology hash (WL colour refinement) for LVS-preservation checks."""
        from .compare import graph_signature
        return graph_signature(self)


def _flow_axis(g: Rect, d: Rect, p: Optional[Rect] = None) -> str:
    """Axis along which current flows.  Primary evidence: the poly overhang --
    poly extends beyond the gate along W, so if poly sticks out top and
    bottom, W is along y and current flows along x.  Fallback: the axis where
    the diffusion extends beyond the gate on both sides; then gate aspect."""
    if p is not None:
        over_y = p[1] < g[1] and p[3] > g[3]
        over_x = p[0] < g[0] and p[2] > g[2]
        if over_y and not over_x:
            return "x"
        if over_x and not over_y:
            return "y"
    ext_x = d[0] < g[0] and d[2] > g[2]
    ext_y = d[1] < g[1] and d[3] > g[3]
    if ext_x and not ext_y:
        return "x"
    if ext_y and not ext_x:
        return "y"
    return "x" if (g[3] - g[1]) >= (g[2] - g[0]) else "y"


def _merge_gate_pieces(gates, shapes):
    """Gate pieces that abut along either axis with identical extent in the
    other (same kind) are one gate: merge them so every gate has a terminal on
    both sides.  Returns (merged gates, set of absorbed gate shape ids)."""
    rects = [shapes[g[0]].rect for g in gates]
    merged = []
    dropped = set()
    for grp in geom.clusters(rects):
        grp = sorted(grp, key=lambda k: (rects[k][0], rects[k][1]))
        while grp:
            k = grp.pop(0); gsid, mpi, drect, kind = gates[k]
            r = rects[k]; dr = list(drect)
            changed = True
            while changed:
                changed = False
                for k2 in list(grp):
                    r2 = rects[k2]
                    same_x = r2[0] == r[0] and r2[2] == r[2] and (r2[1] == r[3] or r2[3] == r[1])
                    same_y = r2[1] == r[1] and r2[3] == r[3] and (r2[0] == r[2] or r2[2] == r[0])
                    if (same_x or same_y) and gates[k2][3] == kind:
                        r = (min(r[0], r2[0]), min(r[1], r2[1]), max(r[2], r2[2]), max(r[3], r2[3]))
                        d2 = gates[k2][2]
                        dr = [min(dr[0], d2[0]), min(dr[1], d2[1]), max(dr[2], d2[2]), max(dr[3], d2[3])]
                        dropped.add(gates[k2][0]); grp.remove(k2); changed = True
            shapes[gsid].rect = r
            merged.append((gsid, mpi, tuple(dr), kind))
    return merged, dropped


def extract(fl: FlatLayout, tech: Tech, labels: Optional[Dict[str, Tuple[str, float, float]]] = None,
            combine: bool = True) -> Extraction:
    """Extract nets and MOS devices.

    labels: optional {net_name: (layer_name, x_um, y_um)} probes naming the net
    whose shape on that layer contains the point.  Text labels in the layout on
    a conducting layer are honoured too.
    """
    L = tech.layers
    inv = {v: k for k, v in L.items()}
    dbu = fl.dbu_um
    shapes: List[Shape] = []
    by_layer: Dict[str, List[int]] = {}

    def add(layer: str, rect: Rect, prov: str, src: int = -1) -> int:
        shapes.append(Shape(layer, rect, prov, src))
        i = len(shapes) - 1
        by_layer.setdefault(layer, []).append(i)
        return i

    # conducting routing/cut shapes straight from the layout
    conducting = set(tech.conducting())
    diffs: List[Tuple[Rect, str, int]] = []
    polys: List[int] = []
    wells: List[Rect] = []
    nsdm: List[Rect] = []
    psdm: List[Rect] = []
    for idx, fr in enumerate(fl.rects):
        lname = inv.get(fr.layer)
        if lname is None:
            continue
        if lname == tech.diff:
            diffs.append((fr.rect, fr.prov, idx))
        elif lname == tech.nwell:
            wells.append(fr.rect)
        elif tech.nsdm and lname == tech.nsdm:
            nsdm.append(fr.rect)
        elif tech.psdm and lname == tech.psdm:
            psdm.append(fr.rect)
        elif lname in conducting:
            sid = add(lname, fr.rect, fr.prov, idx)
            if lname == tech.poly:
                polys.append(sid)

    # gates = poly & diff ; S/D = diff - poly.  Both layers are first merged into
    # maximal rectangles per touching cluster: layouts store L-shaped poly and
    # notched diffusion as several rectangles (or as polygons this reader slabs),
    # and a gate must be computed on the union or it arrives in pieces.
    poly_index = geom.BinIndex()
    for sid in polys:
        poly_index.add(sid, shapes[sid].rect)
    well_index = geom.BinIndex()
    for i, w in enumerate(wells):
        well_index.add(i, w)

    diff_rects = [d[0] for d in diffs]
    diff_prov = geom.BinIndex()
    for i, (drect, dprov, didx) in enumerate(diffs):
        diff_prov.add(i, drect)
    merged_diffs = geom.merge_rects(diff_rects)
    merged_polys = geom.merge_rects([shapes[sid].rect for sid in polys])
    mpoly_index = geom.BinIndex()
    for i, r in enumerate(merged_polys):
        mpoly_index.add(i, r)

    def prov_of(rect: Rect):
        cands = diff_prov.query_overlap(rect)
        return (diffs[cands[0]][1], diffs[cands[0]][2]) if cands else ("", -1)

    gates: List[Tuple[int, int, Rect, str]] = []        # (gate sid, merged-poly idx, diff rect, kind)
    sd_shapes: List[int] = []
    for drect in merged_diffs:
        dprov, didx = prov_of(drect)
        in_well = any(geom.overlaps(wells[w], drect) for w in well_index.query_overlap(drect))
        kind = "p" if in_well else "n"
        holes: List[Rect] = []
        for mpi in mpoly_index.query_overlap(drect):
            g = geom.inter(merged_polys[mpi], drect)
            if g is None:
                continue
            gsid = add("gate", g, dprov, didx)
            gates.append((gsid, mpi, drect, kind))
            holes.append(g)
        for sd in geom.subtract(drect, holes):
            sd_shapes.append(add("sd_" + kind, sd, dprov, didx))

    gates, dropped_gates = _merge_gate_pieces(gates, shapes)
    for gsid in dropped_gates:                          # pieces absorbed into a merged gate
        shapes[gsid].rect = (0, 0, 0, 0)
        shapes[gsid].layer = "void"
    by_layer["gate"] = [g for g in by_layer.get("gate", []) if g not in dropped_gates]

    # ---- connectivity ------------------------------------------------------
    uf = geom.UnionFind(len(shapes))
    idx_of: Dict[str, geom.BinIndex] = {}
    for lname, ids in by_layer.items():
        bi = geom.BinIndex()
        for i in ids:
            bi.add(i, shapes[i].rect)
        idx_of[lname] = bi

    def connect_same(lname: str):
        bi = idx_of.get(lname)
        if not bi:
            return
        for i in by_layer[lname]:
            for j in bi.query_touch(shapes[i].rect):
                if j > i:
                    uf.union(i, j)

    def connect_pair(la: str, lb: str, touch: bool = True):
        if la not in idx_of or lb not in idx_of:
            return
        bi = idx_of[lb]
        q = bi.query_touch if touch else bi.query_overlap
        for i in by_layer[la]:
            for j in q(shapes[i].rect):
                uf.union(i, j)

    for lname in [tech.poly] + list(tech.routing):
        connect_same(lname)
    connect_same("sd_n"); connect_same("sd_p")
    for gsid, _, _, _ in gates:                         # gate <-> every poly rect over it
        for psid in poly_index.query_overlap(shapes[gsid].rect):
            uf.union(gsid, psid)
    # diffusion / poly contacts
    connect_pair("sd_n", tech.diff_contact, touch=False)
    connect_pair("sd_p", tech.diff_contact, touch=False)
    connect_pair(tech.poly, tech.diff_contact, touch=False)
    if tech.diff_contact != (tech.vias[0][1] if tech.vias else None):
        connect_pair(tech.diff_contact, tech.routing[0], touch=False)
    for lo, cut, up in tech.vias:
        connect_pair(lo, cut, touch=False)
        connect_pair(cut, up, touch=False)

    # ---- nets --------------------------------------------------------------
    roots: Dict[int, int] = {}
    net_of_shape = [0] * len(shapes)
    nets: Dict[int, Net] = {}
    for i in range(len(shapes)):
        r = uf.find(i)
        nid = roots.get(r)
        if nid is None:
            nid = len(nets) + 1
            roots[r] = nid
            nets[nid] = Net(nid, str(nid))
        net_of_shape[i] = nid
        nets[nid].shapes.append(i)

    # labels: layout text on a conducting layer, then explicit probes
    def name_net_at(layer: str, x: int, y: int, name: str) -> bool:
        bi = idx_of.get(layer)
        if not bi:
            return False
        for sid in bi.candidates((x, y, x, y)):
            r = shapes[sid].rect
            if r[0] <= x <= r[2] and r[1] <= y <= r[3]:
                nets[net_of_shape[sid]].name = name
                return True
        return False

    for tx in fl.texts:
        lname = tech.text_layers.get(tx.layer) or inv.get(tx.layer)
        if lname in idx_of:
            name_net_at(lname, tx.xy[0], tx.xy[1], tx.text)
    for name, (layer, xu, yu) in (labels or {}).items():
        if not name_net_at(layer, int(round(xu / dbu)), int(round(yu / dbu)), name):
            raise ValueError("label %s: no %s shape at (%g, %g)" % (name, layer, xu, yu))

    # ---- devices -----------------------------------------------------------
    sd_index = geom.BinIndex()
    for sid in sd_shapes:
        sd_index.add(sid, shapes[sid].rect)
    # how many gates touch each S/D rect (for area/perimeter sharing)
    gate_index = geom.BinIndex()
    for gsid, _, _, _ in gates:
        gate_index.add(gsid, shapes[gsid].rect)
    sd_share: Dict[int, int] = {}
    for sid in sd_shapes:
        sd_share[sid] = max(1, len(gate_index.query_touch(shapes[sid].rect)))

    devices: List[Device] = []
    for k, (gsid, mpi, drect, kind) in enumerate(gates):
        g = shapes[gsid].rect
        ax = _flow_axis(g, drect, merged_polys[mpi])
        if ax == "x":
            l_dbu, w_dbu = g[2] - g[0], g[3] - g[1]
            side_a = (g[0], g[1], g[0], g[3])          # left edge
            side_b = (g[2], g[1], g[2], g[3])          # right edge
        else:
            l_dbu, w_dbu = g[3] - g[1], g[2] - g[0]
            side_a = (g[0], g[1], g[2], g[1])          # bottom edge
            side_b = (g[0], g[3], g[2], g[3])          # top edge
        ta = [s for s in sd_index.query_touch(side_a) if shapes[s].layer == "sd_" + kind]
        tb = [s for s in sd_index.query_touch(side_b) if shapes[s].layer == "sd_" + kind]

        def term(ids):
            if not ids:
                return None, 0.0, 0.0
            a = sum(geom.area(shapes[s].rect) / sd_share[s] for s in ids) * dbu * dbu
            p = sum(2 * ((shapes[s].rect[2] - shapes[s].rect[0]) + (shapes[s].rect[3] - shapes[s].rect[1]))
                    / sd_share[s] for s in ids) * dbu
            return net_of_shape[ids[0]], a, p

        sn, sa, sp = term(ta)
        dn, da, dp = term(tb)
        if sn is None or dn is None:
            continue                                   # gate over diffusion edge: not a transistor
        dev = Device(name="M%d" % (len(devices) + 1), kind=kind,
                     model=tech.pfet_model if kind == "p" else tech.nfet_model,
                     g=net_of_shape[gsid], s=sn, d=dn, w=w_dbu * dbu, l=l_dbu * dbu,
                     as_=sa, ad=da, ps=sp, pd=dp, prov=shapes[gsid].prov, gate_rect=g,
                     flow_axis=ax, gate_ids=[gsid])
        devices.append(dev)

    if combine:
        devices = combine_parallel(devices)
    for i, dv in enumerate(devices):
        dv.name = "M%d" % (i + 1)
    for dv in devices:
        for t, n in (("G", dv.g), ("S", dv.s), ("D", dv.d)):
            nets[n].devices.append((dv.name, t))

    return Extraction(tech, dbu, shapes, net_of_shape, nets, devices, fl.top)


def combine_parallel(devices: List[Device]) -> List[Device]:
    """Merge parallel fingers: same kind, L, gate net and {S,D} net pair.
    W, areas and perimeters add (KLayout combine_devices semantics)."""
    groups: Dict[Tuple, Device] = {}
    order: List[Tuple] = []
    for dv in devices:
        key = (dv.kind, round(dv.l, 6), dv.g, frozenset((dv.s, dv.d)))
        if key in groups:
            m = groups[key]
            if (dv.s, dv.d) != (m.s, m.d):             # align S/D orientation
                dv.s, dv.d, dv.as_, dv.ad, dv.ps, dv.pd = dv.d, dv.s, dv.ad, dv.as_, dv.pd, dv.ps
            m.w += dv.w; m.as_ += dv.as_; m.ad += dv.ad; m.ps += dv.ps; m.pd += dv.pd
            m.fingers += 1; m.gate_ids += dv.gate_ids
        else:
            groups[key] = dv; order.append(key)
    return [groups[k] for k in order]


def write_spice(ex: Extraction, path: str, subckt: Optional[str] = None):
    name = subckt or ex.top or "top"
    lines = ["* layopt extraction of %s (%s)" % (name, ex.tech.name), ".SUBCKT %s" % name]
    for dv in ex.devices:
        nn = lambda i: ex.nets[i].name
        lines.append("%s %s %s %s %s %s L=%gU W=%gU AS=%gP AD=%gP PS=%gU PD=%gU"
                     % (dv.name, nn(dv.d), nn(dv.g), nn(dv.s), nn(dv.s), dv.model,
                        round(dv.l, 4), round(dv.w, 4), round(dv.as_, 5), round(dv.ad, 5),
                        round(dv.ps, 4), round(dv.pd, 4)))
    lines.append(".ENDS %s" % name)
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
