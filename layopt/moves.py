# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""Topology-preserving geometry moves on a FlatLayout.

Every move edits rectangles in place (or adds some) and returns the list of
touched FlatRect indices, so the caller can re-extract, confirm the netlist
signature is unchanged, and rule-check only what moved.  Coordinates are dbu.
"""
import os
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from . import geom
from .extract import Device, Extraction
from .gds import FlatLayout, FlatRect

Rect = Tuple[int, int, int, int]


def snap(v: float, grid: int) -> int:
    return int(round(v / grid)) * grid


def set_wire_width(fl: FlatLayout, idx: int, width_um: float, grid_um: float = 0.005) -> List[int]:
    """Resize a wire rectangle about its centre-line in its short dimension."""
    r = fl.rects[idx]
    g = max(1, int(round(grid_um / fl.dbu_um)))
    w = snap(width_um / fl.dbu_um, g)
    x0, y0, x1, y1 = r.rect
    if (x1 - x0) <= (y1 - y0):                          # vertical wire: width is x
        cx = (x0 + x1) // 2
        r.rect = (snap(cx - w / 2, 1), y0, snap(cx - w / 2, 1) + w, y1)
    else:
        cy = (y0 + y1) // 2
        r.rect = (x0, snap(cy - w / 2, 1), x1, snap(cy - w / 2, 1) + w)
    return [idx]


def wire_width_um(fl: FlatLayout, idx: int) -> float:
    r = fl.rects[idx]
    return min(r.w, r.h) * fl.dbu_um


def translate(fl: FlatLayout, ids: Iterable[int], dx_um: float, dy_um: float) -> List[int]:
    dx, dy = int(round(dx_um / fl.dbu_um)), int(round(dy_um / fl.dbu_um))
    out = []
    for i in ids:
        x0, y0, x1, y1 = fl.rects[i].rect
        fl.rects[i].rect = (x0 + dx, y0 + dy, x1 + dx, y1 + dy)
        out.append(i)
    return out


def add_rect(fl: FlatLayout, layer: Tuple[int, int], rect_um: Tuple[float, float, float, float], prov: str) -> int:
    d = fl.dbu_um
    r = tuple(int(round(v / d)) for v in rect_um)
    fl.rects.append(FlatRect(layer, (min(r[0], r[2]), min(r[1], r[3]), max(r[0], r[2]), max(r[1], r[3])), prov))
    return len(fl.rects) - 1


def device_footprint(fl: FlatLayout, ex: Extraction, dev: Device, margin_um: float = 0.3) -> Tuple[Rect, List[int]]:
    """Rectangles belonging to a device.

    Primary: everything sharing the device's provenance (kestrel emits one
    cell per transistor).  The gate poly and S/D straps may live one level up
    (the enclosing cell), so rects of the parent that overlap the footprint
    are included too; the caller decides what to do with them by position
    (crossing the cut line -> grow; beyond it -> only if same provenance).
    When the provenance is shared by several devices (a standard cell), the
    footprint is the device's diffusion column expanded by `margin`."""
    prov = dev.prov
    parent = prov.rsplit("/", 1)[0] if "/" in prov else prov
    own = [i for i, r in enumerate(fl.rects) if r.prov == prov]
    same_prov_devices = [d for d in ex.devices if d.prov == prov]
    if len(same_prov_devices) == 1 and own:
        fp = geom.bbox([fl.rects[i].rect for i in own])
    else:
        g = geom.bbox([ex.shapes[s].rect for s in dev.gate_ids])
        m = int(round(margin_um / fl.dbu_um))
        diff_layer = ex.tech.layers[ex.tech.diff]
        diffs = [r.rect for r in fl.rects if r.layer == diff_layer and geom.overlaps(r.rect, g)]
        fp = geom.bbox(diffs + [g])
        fp = (fp[0] - m, fp[1] - m, fp[2] + m, fp[3] + m)
        own = [i for i, r in enumerate(fl.rects) if r.prov == prov and geom.overlaps(r.rect, fp)]
    extra = [i for i, r in enumerate(fl.rects)
             if i not in own and r.prov == parent and geom.overlaps(r.rect, fp)]
    return fp, own + extra


def resize_device_w(fl: FlatLayout, ex: Extraction, dev: Device, new_w_um: float,
                    grid_um: float = 0.005, side: str = "high") -> List[int]:
    """Stretch a transistor along its W axis by editing its footprint: rects
    crossing the cut line at the gate's W edge grow by dW; rects wholly beyond
    it shift by dW (unique-provenance devices only).  `side` picks the edge:
    "high" grows toward +W (top / right), "low" toward -W.  Works per finger
    (all fingers of the device grow by dW/fingers)."""
    d = fl.dbu_um
    g = max(1, int(round(grid_um / d)))
    fingers = max(1, dev.fingers)
    dw_total = snap((new_w_um - dev.w) / d, g)
    dw = snap(dw_total / fingers, g)
    if dw == 0:
        return []
    fp, ids = device_footprint(fl, ex, dev)
    shared = sum(1 for d in ex.devices if d.prov == dev.prov) > 1
    # Unique provenance (kestrel: one cell per transistor): the device's own rects
    # beyond the cut shift with it.  Shared provenance (a standard cell): nothing
    # shifts -- taps, rails and neighbouring devices are the cell's contract; the
    # stretched strip must fit the whitespace, and the rule check decides.
    own = set() if shared else {i for i in ids if fl.rects[i].prov == dev.prov}
    # Rects that span the whole footprint in the W-axis-orthogonal direction
    # (power rails, well/implant frames) are the cell's boundary contract:
    # they never shift.  Growth has to fit in the whitespace below them, and
    # the rule check says whether it does.
    cell_rects = [fl.rects[i].rect for i in range(len(fl.rects)) if fl.rects[i].prov == dev.prov]
    cb = geom.bbox(cell_rects) or fp
    cell_w = (cb[2] - cb[0]) if dev.flow_axis == "x" else (cb[3] - cb[1])
    def is_frame(r: Rect) -> bool:
        span = (r[2] - r[0]) if dev.flow_axis == "x" else (r[3] - r[1])
        return span >= cell_w * 0.9
    touched: List[int] = []
    # process fingers from the far end so shifts compose
    hi = side == "high"
    gates = sorted((ex.shapes[s].rect for s in dev.gate_ids),
                   key=lambda r: (-(r[3] if dev.flow_axis == "x" else r[2])) if hi else (r[1] if dev.flow_axis == "x" else r[0]))
    for grect in gates:
        if dev.flow_axis == "x":            # W along y
            cut = grect[3] if hi else grect[1]
            for i in ids:
                x0, y0, x1, y1 = fl.rects[i].rect
                if not (x0 < fp[2] and x1 > fp[0]):
                    continue
                crossing = (y0 < cut < y1) or ((y1 == cut if hi else y0 == cut) and _spans_gate(fl.rects[i].rect, grect, "x"))
                if crossing:
                    fl.rects[i].rect = (x0, y0, x1, y1 + dw) if hi else (x0, y0 - dw, x1, y1); touched.append(i)
                elif ((y0 >= cut) if hi else (y1 <= cut)) and i in own and not is_frame(fl.rects[i].rect):
                    fl.rects[i].rect = (x0, y0 + dw, x1, y1 + dw) if hi else (x0, y0 - dw, x1, y1 - dw); touched.append(i)
        else:                               # W along x
            cut = grect[2] if hi else grect[0]
            for i in ids:
                x0, y0, x1, y1 = fl.rects[i].rect
                if not (y0 < fp[3] and y1 > fp[1]):
                    continue
                crossing = (x0 < cut < x1) or ((x1 == cut if hi else x0 == cut) and _spans_gate(fl.rects[i].rect, grect, "y"))
                if crossing:
                    fl.rects[i].rect = (x0, y0, x1 + dw, y1) if hi else (x0 - dw, y0, x1, y1); touched.append(i)
                elif ((x0 >= cut) if hi else (x1 <= cut)) and i in own and not is_frame(fl.rects[i].rect):
                    fl.rects[i].rect = (x0 + dw, y0, x1 + dw, y1) if hi else (x0 - dw, y0, x1 - dw, y1); touched.append(i)
    return sorted(set(touched))


def _spans_gate(r: Rect, g: Rect, flow: str) -> bool:
    """Rect shares the gate's W extent (diff / poly / li over the channel)."""
    if flow == "x":
        return r[1] <= g[1] and r[3] >= g[3]
    return r[0] <= g[0] and r[2] >= g[2]


# ---------------------------------------------------------------------------
# Dissolve move: add a finger to a transistor, growing across the cell edge
# ---------------------------------------------------------------------------

class MoveError(Exception):
    pass


def add_finger(fl: FlatLayout, ex: Extraction, dev: Device, side: str = "high", bridge: str = "auto") -> List[int]:
    """See `_add_finger`; afterwards same-net notches the new geometry makes
    against its own net are filled (`fill_notches`)."""
    touched = _add_finger(fl, ex, dev, side, bridge)
    for _ in range(8):                       # a fill can itself sit within spacing of another fill
        new = fill_notches(fl, ex, touched)  # all new geometry: labels propagate through it
        if not new:
            break
        touched += new
    return sorted(set(touched))


def remove_finger(fl: FlatLayout, ex: Extraction, dev: Device, side: str = "high") -> List[int]:
    """The inverse of `add_finger`: take away `dev`'s outermost finger on the
    `side` of its flow axis.

        [S][G][D][G'][S']  ->  [S][G][D]        (side="high", flow along x)

    The gate poly of that finger is cut out of its stripe and any poly that
    then leads nowhere (a bridge that only served it, a stub to a bar) is
    pruned; the outer S/D region's contacts go and the diffusion is cut back
    to the finger's inner edge, so the region between the remaining fingers
    keeps its width; implant and well that were fitted to the diffusion are
    trimmed with it; li/metal that only served the removed contacts (a strap,
    a jumper) is removed once re-extraction shows it floating.  The device
    must keep at least one finger and the finger must be the outermost on its
    strip.  Works on stock cells as well as on fingers `add_finger` made.
    Returns the changed rect ids (after deletion; ids shift); raises MoveError."""
    if dev.flow_axis != "x":
        raise MoveError("remove_finger: only vertical gates (flow along x) are implemented")
    if len(dev.gate_ids) < 2:
        raise MoveError("remove_finger: %s has a single finger; removing it removes the device" % dev.name)
    tech = ex.tech
    L = tech.layers
    d = fl.dbu_um
    nm = lambda um: int(round(um / d))
    hi = side == "high"
    grects = sorted((ex.shapes[s].rect for s in dev.gate_ids), key=lambda r: r[0])
    g = grects[-1] if hi else grects[0]
    diff_ids = [i for i, r in enumerate(fl.rects) if r.layer == L[tech.diff] and geom.overlaps(r.rect, g)]
    if len(diff_ids) != 1:
        raise MoveError("remove_finger: gate not on exactly one diffusion rect (%d)" % len(diff_ids))
    di = diff_ids[0]; D = fl.rects[di].rect
    strip_gates = sorted({ex.shapes[gs].rect for d_ in ex.devices for gs in d_.gate_ids
                          if geom.overlaps(ex.shapes[gs].rect, D)}, key=lambda r: r[0])
    gi = strip_gates.index(g)
    if (hi and gi != len(strip_gates) - 1) or (not hi and gi != 0):
        raise MoveError("remove_finger: the finger is not the outermost gate on its strip")
    outer = (g[2], D[2]) if hi else (D[0], g[0])
    ext = nm(tech.poly_ext_diff)
    licon_l = L[tech.diff_contact]
    poly_l = L[tech.poly]
    dead: Set[int] = set()
    changed: Set[int] = set()
    # 1. the outer S/D contacts
    for i, r in enumerate(fl.rects):
        if r.layer == licon_l and r.x0 >= outer[0] - 1 and r.x1 <= outer[1] + 1 and r.y1 > D[1] and r.y0 < D[3]:
            dead.add(i)
    # 2. the diffusion, cut back to the inner region's contacts plus enclosure
    #    (the way the stock cells end a strip), or to the finger's inner edge
    #    when that region has no contacts
    prev = strip_gates[gi - 1] if hi else strip_gates[gi + 1] if gi + 1 < len(strip_gates) else None
    inner = ((prev[2] if prev else D[0]), g[0]) if hi else (g[2], (prev[0] if prev else D[2]))
    enc_d = nm(tech.enclosure.get((tech.diff, tech.diff_contact), 0.04))
    inner_licons = [r.rect for r in fl.rects if r.layer == licon_l and r.x0 >= inner[0] - 1 and r.x1 <= inner[1] + 1 and r.y1 > D[1] and r.y0 < D[3]]
    if hi:
        cut = min(g[0], max(c[2] for c in inner_licons) + enc_d) if inner_licons else g[0]
        D2 = (D[0], D[1], cut, D[3])
    else:
        cut = max(g[2], min(c[0] for c in inner_licons) - enc_d) if inner_licons else g[2]
        D2 = (cut, D[1], D[2], D[3])
    fl.rects[di].rect = D2; changed.add(di)
    # 3. the gate poly: cut the finger's span (diffusion plus overhang) out of every
    #    poly rect covering the gate, keep what lies beyond it
    span = (D[1] - ext, D[3] + ext)
    new_pieces: List[int] = []
    for i, r in enumerate(fl.rects):
        if r.layer != poly_l or not geom.overlaps(r.rect, g):
            continue
        if r.x0 < g[0] - 1 or r.x1 > g[2] + 1:
            # a poly rect wider than the gate (a bar over it): only cut the gate's width out
            pieces = geom.subtract(r.rect, [(g[0], span[0], g[2], span[1])])
        else:
            pieces = geom.subtract(r.rect, [(r.x0, span[0], r.x1, span[1])])
        dead.add(i)
        for pc in pieces:
            new_pieces.append(add_rect_dbu(fl, poly_l, pc, r.prov))
    # 3b. prune poly that leads nowhere: no gate (no diffusion under it), no contact,
    #     and at most one other poly rect touching it -- a stub, or a bridge that only
    #     served the removed finger.  Repeat until stable.
    diff_l = L[tech.diff]
    while True:
        alive = [i for i, r in enumerate(fl.rects) if r.layer == poly_l and i not in dead]
        idx = geom.BinIndex()
        for i in alive:
            idx.add(i, fl.rects[i].rect)
        licons = [r.rect for r in fl.rects if r.layer == licon_l]
        li_idx = geom.BinIndex()
        for k, r in enumerate(fl.rects):
            if r.layer == licon_l and k not in dead:
                li_idx.add(k, r.rect)
        di_idx = geom.BinIndex()
        for k, r in enumerate(fl.rects):
            if r.layer == diff_l:
                di_idx.add(k, r.rect)
        removed_any = False
        near = (min(g[0], D[0]) - nm(2.0), D[1] - nm(3.0), max(g[2], D[2]) + nm(2.0), D[3] + nm(3.0))
        for i in alive:
            r = fl.rects[i].rect
            if not geom.overlaps(r, near):
                continue
            if di_idx.query_overlap(r) or li_idx.query_overlap(r):
                continue
            nbrs = [k for k in idx.query_touch(r) if k != i]
            if len(nbrs) <= 1:
                dead.add(i); idx = None; removed_any = True
                break
        if not removed_any:
            break
    # 4. implant and well fitted to the old diffusion shrink with it
    imp = L[tech.psdm if dev.kind == "p" else tech.nsdm] if (tech.psdm and tech.nsdm) else None
    e = nm(tech.implant_enc); ew = nm(tech.nwell_enc); tol = nm(0.02)
    for i, r in enumerate(fl.rects):
        for lay, enc in ((imp, e), (L[tech.nwell] if dev.kind == "p" else None, ew)):
            if lay is None or r.layer != lay or not geom.overlaps(r.rect, D):
                continue
            if hi and abs(r.x1 - (D[2] + enc)) <= tol:
                fl.rects[i].rect = (r.x0, r.y0, D2[2] + enc, r.y1); changed.add(i)
            elif not hi and abs(r.x0 - (D[0] - enc)) <= tol:
                fl.rects[i].rect = (D2[0] - enc, r.y0, r.x1, r.y1); changed.add(i)
    # 5. li/metal that only served the removed contacts -- the mirrored strap, the
    #    jumper's mcons and bar -- now dangles.  Prune dead ends: a conductor in the
    #    vacated region with at most one neighbour (same-layer contact, or the cut /
    #    metal it stacks with) that has no remaining contact under it and no label,
    #    repeatedly; a deleted rect's neighbours become candidates wherever they are,
    #    so the chain back to the net's surviving geometry is followed to its end.
    metal_ids = {L[n] for n in tech.routing}
    cut_up = {L[c]: (L[lo], L[up]) for lo, c, up in tech.vias}
    region = (outer[0] - nm(0.3), D[1] - nm(3.0), outer[1] + nm(0.3), D[3] + nm(3.0))
    idx_by_layer: Dict[Tuple[int, int], geom.BinIndex] = {}
    for i, r in enumerate(fl.rects):
        if i not in dead and (r.layer in metal_ids or r.layer in cut_up or r.layer == licon_l):
            idx_by_layer.setdefault(r.layer, geom.BinIndex()).add(i, r.rect)
    labels = [(tx.layer, tx.xy[0], tx.xy[1]) for tx in getattr(fl, "texts", [])]
    def alive(k):
        return k not in dead
    def neighbours(i):
        r = fl.rects[i]
        out: List[int] = []
        if r.layer in cut_up:
            for lay in cut_up[r.layer]:
                out += [k for k in idx_by_layer.get(lay, geom.BinIndex()).query_overlap(r.rect) if alive(k)]
        else:
            out += [k for k in idx_by_layer.get(r.layer, geom.BinIndex()).query_touch(r.rect) if alive(k) and k != i]
            for c, (lo, up) in cut_up.items():
                if r.layer in (lo, up):
                    out += [k for k in idx_by_layer.get(c, geom.BinIndex()).query_overlap(r.rect) if alive(k)]
        return out
    def anchored(i):
        r = fl.rects[i]
        if r.layer == L[tech.routing[0]] and any(alive(k) for k in idx_by_layer.get(licon_l, geom.BinIndex()).query_overlap(r.rect)):
            return True
        return any(lay == r.layer and r.x0 <= x <= r.x1 and r.y0 <= y <= r.y1 for lay, x, y in labels)
    cands = [i for i, r in enumerate(fl.rects) if alive(i) and (r.layer in metal_ids or r.layer in cut_up) and geom.overlaps(r.rect, region)]
    seen = set(cands)
    while cands:
        i = cands.pop()
        if not alive(i) or anchored(i):
            continue
        nb = neighbours(i)
        if len(nb) <= 1:
            dead.add(i)
            for k in nb:
                if k not in seen or True:
                    cands.append(k); seen.add(k)
    keep = [i for i in range(len(fl.rects)) if i not in dead]
    remap = {old: new for new, old in enumerate(keep)}
    fl.rects = [fl.rects[i] for i in keep]
    changed = {remap[i] for i in changed if i in remap} | {remap[i] for i in new_pieces if i in remap}
    return sorted(changed)


def fill_notches(fl: FlatLayout, ex: Extraction, new_ids: Sequence[int]) -> List[int]:
    """Two shapes of one net on a spacing layer that neither overlap nor share
    an edge, closer than spacing, form a notch (the delta-DRC flags it).  When
    one of them is new geometry and the gap between them is field that other
    nets keep spacing from, fill the gap: the two merge into one polygon,
    which is what the rule wants.  A poly fill must not cross diffusion (that
    would be a gate).  New rects are labelled with a net by same-layer contact
    with extracted geometry, propagated through touching new rects; unlabelled
    ones are left alone and the DRC has the last word.  Returns added ids."""
    tech = ex.tech
    L = tech.layers
    inv = {v: k for k, v in L.items()}
    nm = lambda v: int(round(v / fl.dbu_um))
    src2net = {sh.src: ex.net_of_shape[k] for k, sh in enumerate(ex.shapes) if sh.src >= 0}
    cut_layers = {L[c] for _, c, _ in tech.vias} | {L[tech.diff_contact]}
    new_set = [i for i in set(new_ids) if 0 <= i < len(fl.rects) and fl.rects[i].layer not in cut_layers]
    if not new_set:
        return []
    # label new rects by contact
    label: Dict[int, int] = {}
    by_layer: Dict[Tuple[int, int], geom.BinIndex] = {}
    for k, r in enumerate(fl.rects):
        by_layer.setdefault(r.layer, geom.BinIndex()).add(k, r.rect)
    pending = list(new_set)
    changed = True
    while changed and pending:
        changed = False
        for i in list(pending):
            r = fl.rects[i]
            for k in by_layer[r.layer].query_touch(r.rect):
                n = src2net.get(k) if k not in new_set else label.get(k)
                if n is not None and k != i:
                    label[i] = n; pending.remove(i); changed = True; break
    added: List[int] = []
    diff_l = L.get(tech.diff)
    for i in new_set:
        n = label.get(i)
        if n is None:
            continue
        r = fl.rects[i]
        ln = inv.get(r.layer)
        ms = tech.min_space.get(ln)
        if ms is None:
            continue
        s_ = nm(ms)
        probe = (r.x0 - s_, r.y0 - s_, r.x1 + s_, r.y1 + s_)
        for k in by_layer[r.layer].query_overlap(probe):
            if k == i:
                continue
            nk = src2net.get(k) if k not in new_set else label.get(k)
            if nk != n:
                continue
            o = fl.rects[k].rect
            if geom.overlaps(r.rect, o) or _shares_edge(r.rect, o):
                continue
            hole = _gap_rect(r.rect, o)
            dbg = os.environ.get("LAYOPT_FILL_DEBUG")
            if dbg:
                print("      fill-debug: %d (net %s) vs %d: hole %s" % (i, n, k, hole and [round(v / 1000.0, 3) for v in hole]))
            if hole is None:
                continue
            cover = [fl.rects[q].rect for q in by_layer[r.layer].query_overlap(hole)]
            if not geom.subtract(hole, cover):
                continue                                   # already filled
            # the fill is at least min width in both directions (a sliver would
            # be a width violation, and a corner square would touch both shapes
            # only at corners, which is no connection): grow it about its centre
            mw = nm(tech.min_width.get(ln, 0.0)); grid = nm(tech.grid_um)
            gx_ = max(0, mw - (hole[2] - hole[0])); gy_ = max(0, mw - (hole[3] - hole[1]))
            snap = lambda v: int(round(v / grid)) * grid
            hole = (snap(hole[0] - (gx_ + 1) // 2), snap(hole[1] - (gy_ + 1) // 2), snap(hole[2] + gx_ // 2), snap(hole[3] + gy_ // 2))
            if hole[2] - hole[0] < mw:
                hole = (hole[0], hole[1], hole[0] + mw, hole[3])
            if hole[3] - hole[1] < mw:
                hole = (hole[0], hole[1], hole[2], hole[1] + mw)
            # align each edge of the fill to a nearby (within min width) edge of the two
            # shapes it joins, outward: a fill edge a few nm off a neighbour's edge
            # would leave a slit, and that slit is the next notch
            def align(v, cands, outward):
                near = [c for c in cands if abs(c - v) <= mw and (c <= v if outward < 0 else c >= v)]
                return (min(near) if outward < 0 else max(near)) if near else v
            hole = (align(hole[0], (r.rect[0], o[0]), -1), align(hole[1], (r.rect[1], o[1]), -1),
                    align(hole[2], (r.rect[2], o[2]), +1), align(hole[3], (r.rect[3], o[3]), +1))
            joins = lambda a, b: geom.overlaps(a, b) or _shares_edge(a, b)
            if not (joins(hole, r.rect) and joins(hole, o)):
                continue                                   # cannot bridge them (too short to reach)
            # the fill must keep spacing from other nets on this layer ...
            grown = (hole[0] - s_, hole[1] - s_, hole[2] + s_, hole[3] + s_)
            ok = True
            for q in by_layer[r.layer].query_overlap(grown):
                nq = src2net.get(q) if q not in new_set else label.get(q)
                if nq != n and not (q in new_set and nq is None):
                    ok = False; break
            # ... and poly must not cross diffusion
            if ok and ln == tech.poly and diff_l in by_layer and by_layer[diff_l].query_overlap(hole):
                ok = False
            if dbg:
                print("      fill-debug:    grown %s ok=%s joins=%s" % ([round(v / 1000.0, 3) for v in hole], ok, joins(hole, r.rect) and joins(hole, o)))
            if not ok:
                continue
            j = add_rect_dbu(fl, r.layer, hole, fl.rects[i].prov)
            by_layer[r.layer].add(j, hole)
            label[j] = n
            added.append(j)
    return added


def _add_finger(fl: FlatLayout, ex: Extraction, dev: Device, side: str = "high", bridge: str = "auto") -> List[int]:
    """Add one parallel finger to `dev` on the `side` of its flow axis, by
    mirroring the existing gate + inner S/D column about the outer S/D region:

        [S][G][D]  ->  [S][G][D][G'][S']        (side="high", flow along x)

    The new outer S/D copies the inner S/D's contacts and strap (mirrored), so
    it connects the way the original does (a strap to the rail for a supply
    source); G' is tied to G by a poly bridge in the field beyond the
    diffusion, or -- when no bridge position meets spacing (`bridge="auto"`
    falls back, `"contact"` forces it) -- by a poly head with a licon, an li
    pad and a met1 jumper to the gate net's existing li pin.
    Diffusion, implant and well are extended.  New rects take the device's
    provenance -- the cell now extends into whatever was next to it (a
    filler, whitespace, or a neighbour: the rule check decides).  Only the
    standard-cell orientation (vertical gate, current along x) is implemented.
    Returns the added/changed rect ids; raises MoveError when the geometry
    around the device does not fit the pattern."""
    if dev.flow_axis != "x":
        raise MoveError("add_finger: only vertical gates (flow along x) are implemented")
    bridge_mode = bridge
    tech = ex.tech
    L = tech.layers
    inv = {v: k for k, v in L.items()}
    d = fl.dbu_um
    nm = lambda um: int(round(um / d))
    hi = side == "high"
    # the outermost finger on this side is the one we mirror; the region between
    # it and the previous finger (or the diffusion edge) is the "inner" S/D
    grects = sorted((ex.shapes[s].rect for s in dev.gate_ids), key=lambda r: r[0])
    g = grects[-1] if hi else grects[0]
    # the diffusion rect holding this gate
    diff_ids = [i for i, r in enumerate(fl.rects) if r.layer == L[tech.diff] and geom.overlaps(r.rect, g)]
    if len(diff_ids) != 1:
        raise MoveError("add_finger: gate not on exactly one diffusion rect (%d)" % len(diff_ids))
    di = diff_ids[0]; D = fl.rects[di].rect
    # the inner S/D region is bounded by the NEXT gate on the strip inward, whichever
    # transistor owns it (a nand2's two PMOS share one strip)
    strip_gates = sorted({ex.shapes[gs].rect for d_ in ex.devices for gs in d_.gate_ids
                          if geom.overlaps(ex.shapes[gs].rect, D)}, key=lambda r: r[0])
    gi = strip_gates.index(g)
    prev = (strip_gates[gi - 1] if gi > 0 else None) if hi else (strip_gates[gi + 1] if gi + 1 < len(strip_gates) else None)
    outer = (g[2], D[2]) if hi else (D[0], g[0])          # x-range of the outer S/D region
    # the gate must be the outermost one on this side of the WHOLE diffusion strip
    # (a nand2's two PMOS share one strip): otherwise the mirror lands on a neighbour
    for other in ex.devices:
        if other is dev:
            continue
        for gs in other.gate_ids:
            og = ex.shapes[gs].rect
            if og[3] > D[1] and og[1] < D[3] and ((hi and outer[0] <= og[0] < D[2]) or ((not hi) and D[0] < og[2] <= outer[1])):
                raise MoveError("add_finger: %s is not the outermost transistor on the %s side of its diffusion (%s is); add the finger there"
                                % (dev.name, side, other.name))
    if outer[1] - outer[0] <= 0:
        raise MoveError("add_finger: gate at the diffusion edge")
    # walk inward over uncontacted S/D nodes (a series stack): the mirrored image
    # must include every gate up to the first contacted region
    licon_l = L[tech.diff_contact]
    def region_has_contacts(xr):
        return any(r.layer == licon_l and r.x0 >= xr[0] - 1 and r.x1 <= xr[1] + 1 and r.y1 > D[1] and r.y0 < D[3] for r in fl.rects)
    stack = [g]                       # gates to mirror, outermost first
    cur = g
    while True:
        if prev is None:
            inner = (D[0], cur[0]) if hi else (cur[2], D[2])
        else:
            inner = (prev[2], cur[0]) if hi else (cur[2], prev[0])
        if inner[1] - inner[0] <= 0:
            raise MoveError("add_finger: no S/D region inside the gate stack")
        if region_has_contacts(inner) or prev is None:
            break
        stack.append(prev); cur = prev
        gi2 = strip_gates.index(prev)
        prev = (strip_gates[gi2 - 1] if gi2 > 0 else None) if hi else (strip_gates[gi2 + 1] if gi2 + 1 < len(strip_gates) else None)
    if not region_has_contacts(inner):
        raise MoveError("add_finger: the series stack reaches the diffusion edge without a contacted node")
    xc = (outer[0] + outer[1]) / 2.0
    touched: List[int] = []
    ystrip = (g[1], g[3])
    def in_inner(r: Rect) -> bool:
        return r[0] >= inner[0] - 1 and r[2] <= inner[1] + 1 and r[3] > ystrip[0] and r[1] < ystrip[1]
    # inner S/D contacts and the strap(s) over them
    inner_licons = [i for i, r in enumerate(fl.rects) if r.layer == licon_l and in_inner(r.rect)]
    if not inner_licons:
        raise MoveError("add_finger: inner S/D has no contacts to mirror")
    li_l = L[tech.routing[0]]
    inner_straps = [i for i, r in enumerate(fl.rects) if r.layer == li_l
                    and any(geom.overlaps(r.rect, fl.rects[k].rect) for k in inner_licons)
                    and (r.x1 - r.x0) < nm(0.6)]                      # the vertical strap, not a rail
    # mirroring about the outer region's centre may land the new strap too close to
    # an asymmetric drain strap or poly of another net: shift the whole new column
    # outward by the largest spacing deficit found (li and poly, other nets only)
    shift = 0
    li_l0 = L[tech.routing[0]]
    def deficit(candidates):
        worst = 0
        for lname, rects in candidates:
            sp = nm(tech.min_space.get(lname, 0.0))
            for nr in rects:
                for k, orr in enumerate(fl.rects):
                    if orr.layer != L[lname] or not (orr.y1 > nr[1] and orr.y0 < nr[3]):
                        continue
                    sid = next((q for q, sh in enumerate(ex.shapes) if sh.src == k), None)
                    if sid is not None and ex.net_of_shape[sid] in (dev.s, dev.d, dev.g):
                        # same conductor as ours only if it is the net this new rect will join
                        pass
                    gap = (nr[0] - orr.x1) if hi else (orr.x0 - nr[2])
                    if 0 <= gap < sp:
                        worst = max(worst, sp - gap)
        return worst
    def mx_base(x):
        return int(round(2 * xc - x))
    probe_li = [(min(mx_base(fl.rects[k].x0), mx_base(fl.rects[k].x1)), fl.rects[k].y0, max(mx_base(fl.rects[k].x0), mx_base(fl.rects[k].x1)), fl.rects[k].y1)
                for k in inner_straps]
    shift = deficit([(tech.routing[0], probe_li)])
    shift = int(round(shift / nm(tech.grid_um))) * nm(tech.grid_um) if shift else 0
    mx = (lambda x: int(round(2 * xc - x)) + shift) if hi else (lambda x: int(round(2 * xc - x)) - shift)
    def mrect(r: Rect) -> Rect:
        return (min(mx(r[0]), mx(r[2])), r[1], max(mx(r[0]), mx(r[2])), r[3])
    # 1. diffusion: extend to the mirror of the inner edge
    x_new = mx(inner[0] if hi else inner[1])
    fl.rects[di].rect = (D[0], D[1], x_new, D[3]) if hi else (x_new, D[1], D[2], D[3])
    touched.append(di)
    # 2. new gate finger(s): every gate of the stack mirrored; spans overhang to overhang
    ext = nm(tech.poly_ext_diff)
    gx0, gx1 = (mx(g[2]), mx(g[0]))
    for extra in stack[1:]:
        touched.append(add_rect_dbu(fl, L[tech.poly], (min(mx(extra[0]), mx(extra[2])), extra[1] - ext, max(mx(extra[0]), mx(extra[2])), extra[3] + ext), dev.prov))
    # poly bridge location: just beyond the overhang on the side with field (no other diffusion/gate)
    bw = nm(max(tech.min_width.get(tech.poly, 0.15), 0.15))
    cand = [((g[1] - ext - bw), (g[1] - ext)), ((g[3] + ext), (g[3] + ext + bw))]
    # rail side first: the mid-row gap between the strips is where gate contact
    # bridges (the far gate of a mirrored series stack, say) have to go, so a
    # poly bridge should use the rail side when it can
    if dev.kind == "p":
        cand.reverse()
    bridge = None
    span_x = (min(g[0], gx0), max(g[2], gx1))
    src2net = {sh.src: ex.net_of_shape[k] for k, sh in enumerate(ex.shapes) if sh.src >= 0}
    sp_poly = nm(tech.min_space.get(tech.poly, 0.21)); sp_diff = nm(tech.min_space.get(tech.diff, 0.27))
    for by0, by1 in cand:
        br = (span_x[0], by0, span_x[1], by1)
        grown_p = (br[0] - sp_poly, br[1] - sp_poly, br[2] + sp_poly, br[3] + sp_poly)
        grown_d = (br[0] - sp_diff, br[1] - sp_diff, br[2] + sp_diff, br[3] + sp_diff)
        blocked = False
        for k, r in enumerate(fl.rects):
            if r.layer == licon_l and geom.overlaps(r.rect, br) and src2net.get(k) != dev.g:
                blocked = True; break                                  # a poly bridge may cross its own net's contacts
            if r.layer == L[tech.diff] and geom.overlaps(r.rect, grown_d) and r.rect != D and not geom.overlaps(r.rect, D):
                blocked = True; break                                  # another diffusion within spacing
            if r.layer == L[tech.poly] and geom.overlaps(r.rect, grown_p) and src2net.get(k) != dev.g:
                blocked = True; break                                  # poly of another net within spacing
        if not blocked:
            bridge = br; break
    if bridge_mode == "contact":
        bridge = None
    if bridge is None and bridge_mode == "poly":
        raise MoveError("add_finger: no field for the poly bridge on either side")
    if bridge is not None:
        fy0 = min(g[1] - ext, bridge[1]); fy1 = max(g[3] + ext, bridge[3])
        touched.append(add_rect_dbu(fl, L[tech.poly], (gx0, fy0, gx1, fy1), dev.prov))
        touched.append(add_rect_dbu(fl, L[tech.poly], bridge, dev.prov))
    else:
        touched.append(add_rect_dbu(fl, L[tech.poly], (gx0, g[1] - ext, gx1, g[3] + ext), dev.prov))
    # 3. mirrored contacts and strap(s)
    for k in inner_licons:
        touched.append(add_rect_dbu(fl, licon_l, mrect(fl.rects[k].rect), dev.prov))
    # The original strap may run across the row to the other device type (a
    # nand's Y strap ties the P drain to the N drain).  The mirrored copy must
    # not run into whatever sits in the other strip -- that strip is not
    # mirrored with us (a mirrored series stack's gate bridge sat there once
    # and a full-height strap shorted Y to B).  Trim the strap on the side away
    # from our rail back to clear of foreign li and cuts; it must still cover
    # our contacts.  The jumper below carries the signal across if needed.
    enc_li = nm(tech.enclosure.get((tech.routing[0], tech.diff_contact), 0.08))
    sp_li = nm(tech.min_space.get(tech.routing[0], 0.17))
    lic_lo = min(fl.rects[k].y0 for k in inner_licons) - enc_li
    lic_hi = max(fl.rects[k].y1 for k in inner_licons) + enc_li
    inner_sid = next((q for q, sh in enumerate(ex.shapes) if sh.src == inner_licons[0]), None)
    inner_net = ex.net_of_shape[inner_sid] if inner_sid is not None else None
    foreign_layers = {li_l, licon_l}
    if tech.vias:
        foreign_layers.add(L[tech.vias[0][1]])
    def foreign(k):
        n = src2net.get(k)
        return n is not None and n != inner_net
    trim_lo, trim_hi = None, None          # strap y bounds forced by conflicts (P: bottom, N: top)
    for k in inner_straps:
        nr = mrect(fl.rects[k].rect)
        grown = (nr[0] - sp_li, nr[1] - sp_li, nr[2] + sp_li, nr[3] + sp_li)
        for k2, r2 in enumerate(fl.rects):
            if r2.layer not in foreign_layers or not foreign(k2) or not geom.overlaps(r2.rect, grown):
                continue
            if dev.kind == "p":
                if r2.y0 >= lic_lo:
                    raise MoveError("add_finger: foreign %s at %s conflicts with the mirrored strap over our contacts" % (inv_layers(tech).get(r2.layer, r2.layer), [round(v / 1000.0, 3) for v in r2.rect]))
                trim_lo = max(trim_lo or -10**9, r2.y1 + sp_li)
            else:
                if r2.y1 <= lic_hi:
                    raise MoveError("add_finger: foreign %s at %s conflicts with the mirrored strap over our contacts" % (inv_layers(tech).get(r2.layer, r2.layer), [round(v / 1000.0, 3) for v in r2.rect]))
                trim_hi = min(trim_hi or 10**9, r2.y0 - sp_li)
    if (dev.kind == "p" and trim_lo is not None and trim_lo > lic_lo) or (dev.kind == "n" and trim_hi is not None and trim_hi < lic_hi):
        raise MoveError("add_finger: foreign li/cuts within spacing of the mirrored strap over our contacts (trimming cannot clear them)")
    def clip_strap(r: Rect) -> Rect:
        if dev.kind == "p" and trim_lo is not None:
            return (r[0], max(r[1], min(trim_lo, lic_lo)), r[2], r[3])
        if dev.kind == "n" and trim_hi is not None:
            return (r[0], r[1], r[2], min(r[3], max(trim_hi, lic_hi)))
        return r
    new_straps = []
    for k in inner_straps:
        nr = clip_strap(mrect(fl.rects[k].rect))
        if nr[3] <= nr[1]:
            continue
        new_straps.append((k, add_rect_dbu(fl, li_l, nr, dev.prov)))
        touched.append(new_straps[-1][1])
    if not new_straps:
        raise MoveError("add_finger: no strap left over the mirrored contacts after trimming")
    # 3b. the new outer S/D must join the inner S/D's net.  A supply source
    # reaches it through the rail (the strap runs to the rail li, which continues
    # into the neighbour).  A signal net needs a jumper: mcon on both straps and a
    # met1 bar between them, at a height inside the gate's W range.
    if inner_net is not None and ex.nets[inner_net].name not in tech.supply_names and len(tech.vias) >= 1:
        cut = tech.vias[0][1]                                  # li -> met1 cut (mcon)
        cs = nm(tech.min_width.get(cut, 0.17)); half = cs // 2
        m1 = L[tech.routing[1]]
        enc = nm(tech.enclosure.get((tech.routing[1], cut), 0.03))
        # one jumper per strap group: the widest slab of the merged inner strap
        # (the stock cells store T-shaped straps as a thin stub + a wide bar)
        old_union = geom.merge_rects([fl.rects[k].rect for k, _ in new_straps])
        wide = max(old_union, key=lambda rr: rr[2] - rr[0])
        if wide[2] - wide[0] < cs:
            raise MoveError("add_finger: inner strap too narrow for a contact")
        # the jumper may sit anywhere along the part of the strap the clipped mirror keeps
        y0, y1 = wide[1], wide[3]
        if dev.kind == "p" and trim_lo is not None:
            y0 = max(y0, min(trim_lo, lic_lo))
        elif dev.kind == "n" and trim_hi is not None:
            y1 = min(y1, max(trim_hi, lic_hi))
        if y1 - y0 < cs:
            raise MoveError("add_finger: no room for the signal jumper on the strap")
        xa = (wide[0] + wide[2]) // 2
        xb = mx(xa)
        plan = _plan_sd_jumper(fl, ex, dev, inner_net, xa, xb, y0, y1, src2net, nm, L, tech)
        if plan is None:
            # no straight bar on met1 or met2: route around the P&R wiring from the
            # new strap to any shape of the net (the inner strap, its mcons, its routes)
            from . import route
            new_span = [fl.rects[j].rect for _, j in new_straps]
            sources = []
            for nr in new_span:
                xs_ = (nr[0] + nr[2]) // 2
                for yy in range(nr[1] + cs, nr[3] - cs + 1, max(cs, nm(0.1))):
                    sources.append((0, xs_, yy))
            xs = [r[0] for r in new_span] + [xa]; ys = [r[1] for r in new_span] + [y0]
            rwin = (min(xs) - nm(1.5), min(ys) - nm(1.0), max(r[2] for r in new_span) + nm(1.5), max(r[3] for r in new_span) + nm(1.0))
            res = route.maze_route(fl, tech, inner_net, src2net, sources, rwin, own_ids=[j for _, j in new_straps])
            LAST_JUMPER_TALLY["maze route"] = dict(route.LAST_ROUTE_STATS)
            if res is None:
                moved = route.reroute_around(fl, tech, inner_net, src2net, sources, rwin, [], own_ids=[j for _, j in new_straps], prov=dev.prov)
                LAST_JUMPER_TALLY["reroute"] = route.LAST_ROUTE_STATS.get("reroute")
                if moved is None:
                    raise MoveError("add_finger: no legal S/D jumper (met1 bar, met1 pads + via1 + met2 bar, routed path, or moving a P&R wire); rejected by: %s" % dict(LAST_JUMPER_TALLY))
                touched.extend(moved)
                plan = []
            else:
                plan = res[1]
        for layer, rect in plan:
            touched.append(add_rect_dbu(fl, layer, rect, dev.prov))
    # 4. implant and well cover the new diffusion
    D2 = fl.rects[di].rect
    imp = L[tech.psdm if dev.kind == "p" else tech.nsdm] if (tech.psdm and tech.nsdm) else None
    e = nm(tech.implant_enc)
    # only the cell's own implant/well rects, and only on the side that grew: a
    # neighbour's well already covers what it covers (and remove_finger can trim
    # back what was fitted to this diffusion, not what belonged to someone else)
    for i, r in enumerate(fl.rects):
        if r.prov != dev.prov or not geom.overlaps(r.rect, D):
            continue
        if imp is not None and r.layer == imp:
            fl.rects[i].rect = (r.x0, r.y0, max(r.x1, D2[2] + e), r.y1) if hi else (min(r.x0, D2[0] - e), r.y0, r.x1, r.y1); touched.append(i)
        if dev.kind == "p" and r.layer == L[tech.nwell]:
            ew = nm(tech.nwell_enc)
            fl.rects[i].rect = (r.x0, r.y0, max(r.x1, D2[2] + ew), r.y1) if hi else (min(r.x0, D2[0] - ew), r.y0, r.x1, r.y1); touched.append(i)
    # 4b. the other gates of a mirrored series stack: each ties to its own original.
    # A poly bridge cannot cross the gates in between, so use the column bridge
    # (aligned same-net poly) or the contact bridge (poly tab + met1 jumper to the pin)
    for extra in stack[1:]:
        owner = next(d_ for d_ in ex.devices for gs in d_.gate_ids if ex.shapes[gs].rect == extra)
        ex0_, ex1_ = min(mx(extra[0]), mx(extra[2])), max(mx(extra[0]), mx(extra[2]))
        new_poly_ids = {i for i in touched if fl.rects[i].layer == L[tech.poly] and i not in src2net}
        s2n = dict(src2net)
        for i in new_poly_ids:
            if fl.rects[i].x0 == ex0_ and fl.rects[i].x1 == ex1_:
                s2n[i] = owner.g
        col = _plan_column_bridge(fl, ex, owner, extra, ex0_, ex1_, ext, s2n, nm, L, tech, [i for i in touched if s2n.get(i) == owner.g])
        if col is not None:
            touched.append(add_rect_dbu(fl, L[tech.poly], col, dev.prov)); continue
        new_ids_x = {i for i in touched if i not in src2net and fl.rects[i].layer != L[tech.poly]}
        plan = _plan_contact_bridge(fl, ex, owner, extra, ex0_, ex1_, ext, s2n, nm, L, tech, new_ids_x)
        if plan is None:
            raise MoveError("add_finger: series stack: no bridge for the mirrored gate of %s (%s); candidates rejected by: %s"
                            % (owner.name, ex.nets[owner.g].name, dict(LAST_PLAN_TALLY)))
        for layer, rect in plan:
            touched.append(add_rect_dbu(fl, layer, rect, dev.prov))
        touched.extend(LAST_PLAN_TOUCHED); LAST_PLAN_TOUCHED.clear()
    if bridge is None:
        # 5a. column bridge: same-net poly already aligned with the new finger beyond the
        # overhang (the other transistor's added finger, or the cell's own gate poly):
        # extend the finger poly to meet it, provided nothing but field lies between
        col = _plan_column_bridge(fl, ex, dev, g, gx0, gx1, ext, src2net, nm, L, tech, touched)
        if col is not None:
            touched.append(add_rect_dbu(fl, L[tech.poly], col, dev.prov))
            return sorted(set(touched))
        # 5b. contact bridge: planned now, with the new S/D geometry in place
        # new S/D geometry (contacts, straps, jumper) is foreign to the gate net; the
        # new poly finger is the gate net itself and must not block its own head
        new_ids = {i for i in touched if i not in src2net and fl.rects[i].layer != L[tech.poly]}
        src2net_now = dict(src2net)
        for i in touched:
            if i not in src2net and fl.rects[i].layer == L[tech.poly]:
                src2net_now[i] = dev.g
        plan = _plan_contact_bridge(fl, ex, dev, g, gx0, gx1, ext, src2net_now, nm, L, tech, new_ids)
        if plan is None:
            raise MoveError("add_finger: no field for a poly bridge and no place for a contact bridge (poly head + met1 jumper to the gate pin); candidates rejected by: %s"
                            % dict(LAST_PLAN_TALLY))
        for layer, rect in plan:
            touched.append(add_rect_dbu(fl, layer, rect, dev.prov))
        touched.extend(LAST_PLAN_TOUCHED); LAST_PLAN_TOUCHED.clear()
    return sorted(set(touched))


LAST_PLAN_TALLY: Dict[str, int] = {}
LAST_PLAN_TOUCHED: List[int] = []      # rect ids a planner changed/added itself (moved P&R wires)
LAST_JUMPER_TALLY: Dict[str, int] = {}


def _plan_column_bridge(fl, ex, dev, g, gx0, gx1, ext, src2net, nm, L, tech, touched):
    """Vertical poly from the new finger's end to same-net poly aligned in its
    column (within 1.6 um), on either side; None if anything but field lies
    between (diffusion, contacts, other nets' poly within spacing)."""
    poly_l, diff_l, licon_l = L[tech.poly], L[tech.diff], L[tech.diff_contact]
    sp_poly = nm(tech.min_space.get(tech.poly, 0.21)); sp_diff = nm(0.075)
    new_poly = {i for i in touched if fl.rects[i].layer == poly_l and i not in src2net}
    def is_gate_net_poly(k):
        return (src2net.get(k) == dev.g) or (k in new_poly)
    best = None
    for k, r in enumerate(fl.rects):
        if r.layer != poly_l or not is_gate_net_poly(k) or r.x1 <= gx0 or r.x0 >= gx1:
            continue
        if r.y0 >= g[3] + ext and r.y0 - (g[3] + ext) <= nm(1.6):          # above
            strip = (gx0, g[3] + ext, gx1, r.y0)
        elif r.y1 <= g[1] - ext and (g[1] - ext) - r.y1 <= nm(1.6):        # below
            strip = (gx0, r.y1, gx1, g[1] - ext)
        else:
            continue
        if strip[3] - strip[1] <= 0:
            continue
        ok = True
        for kk, o in enumerate(fl.rects):
            if o.layer == diff_l and geom.overlaps((strip[0] - sp_diff, strip[1], strip[2] + sp_diff, strip[3]), o.rect):
                ok = False; break
            if o.layer == licon_l and geom.overlaps(strip, o.rect) and src2net.get(kk) != dev.g:
                ok = False; break
            if o.layer == poly_l and not is_gate_net_poly(kk) and geom.overlaps((strip[0] - sp_poly, strip[1] - sp_poly, strip[2] + sp_poly, strip[3] + sp_poly), o.rect):
                ok = False; break
        if ok and (best is None or (strip[3] - strip[1]) < (best[3] - best[1])):
            best = strip
    return best


def _plan_contact_bridge(fl, ex, dev, g, gx0, gx1, ext, src2net, nm, L, tech, new_ids=()):
    """Geometry (list of (layer, rect)) tying the new poly finger to the gate net
    through a contact: a poly tab from the finger's end into the field to a
    licon, an li pad on it, and a met1 bar (mcon at both ends) to the gate net's
    nearest li shape.  Searches tab length and height within the field gap;
    every candidate must clear other nets' diffusion, poly, cuts, li and met1
    (the just-added S/D geometry counts as this device's own net only where it
    is: `new_ids` are treated as foreign to the gate net).  Returns None when
    nothing fits."""
    LAST_PLAN_TALLY.clear()
    tally = LAST_PLAN_TALLY
    licon_l, li_l, m1 = L[tech.diff_contact], L[tech.routing[0]], L[tech.routing[1]]
    cut = tech.vias[0][1]; mcon_l = L[cut]; diff_l = L[tech.diff]; poly_l = L[tech.poly]
    cs = nm(tech.min_width.get(tech.diff_contact, 0.17)); ms = nm(tech.min_width.get(cut, 0.17))
    enc_poly = nm(0.05); enc_li = nm(tech.enclosure.get((tech.routing[0], tech.diff_contact), 0.08))
    enc_m1 = nm(tech.enclosure.get((tech.routing[1], cut), 0.03))
    sp_poly = nm(tech.min_space.get(tech.poly, 0.21)); sp_diff = nm(0.075); sp_li = nm(tech.min_space.get(tech.routing[0], 0.17))
    sp_m1 = nm(tech.min_space.get(tech.routing[1], 0.14)); sp_cut = nm(tech.min_space.get(tech.diff_contact, 0.17))
    step = nm(tech.grid_um) * 2
    tab_h = cs + 2 * enc_poly
    # neighbourhood index per layer (window: 4 um around the gate)
    win = (g[0] - nm(4.0), g[1] - nm(4.0), g[2] + nm(4.0), g[3] + nm(4.0))
    idx = {}
    for k, r in enumerate(fl.rects):
        if r.layer in (diff_l, poly_l, licon_l, mcon_l, li_l, m1) and geom.overlaps(r.rect, win):
            idx.setdefault(r.layer, geom.BinIndex(500)).add(k, r.rect)
    def own(k):                       # belongs to the gate net (and is not new S/D geometry)
        return src2net.get(k) == dev.g and k not in new_ids
    def clear(layer, rect, space, exclude_own=True):
        bi = idx.get(layer)
        if not bi:
            return True
        grown = (rect[0] - space, rect[1] - space, rect[2] + space, rect[3] + space)
        for k in bi.query_overlap(grown):
            if exclude_own and own(k):
                # own-net geometry is fine when the new shape merges with it;
                # near but apart is a spacing violation like any other
                if geom.overlaps(rect, bi.rects[k]) or _touches(rect, bi.rects[k]):
                    continue
            return False
        return True
    gate_li = [(k, r.rect) for k, r in enumerate(fl.rects) if r.layer == li_l and own(k) and (r.x1 - r.x0) >= ms and geom.overlaps(r.rect, win)]
    if not gate_li:
        tally["no gate li pin in window"] = 1
        return None
    # heads whose pad fits but that no straight met1 bar can serve: the maze router's sources
    fallback: List[Tuple[Rect, Rect, Rect]] = []
    # vertical search range on each side of the gate: from just past the overhang out to 1.2 um
    for lo_side in (True, False):
        ys = []
        for j in range(0, nm(1.2) // step + 1):
            if lo_side:
                y1 = g[1] - ext - j * step; ys.append((y1 - tab_h, y1))
            else:
                y0 = g[3] + ext + j * step; ys.append((y0, y0 + tab_h))
        for hy0, hy1 in ys:
            for tab in range(0, nm(0.8) // step + 1):
                lx0 = gx1 + tab * step if tab else gx0                     # licon x0: on the finger, or on a tab to its right
                if tab and lx0 < gx1:
                    continue
                licon = (lx0, (hy0 + hy1) // 2 - cs // 2, lx0 + cs, (hy0 + hy1) // 2 + cs // 2)
                head = (gx0, hy0, licon[2] + enc_poly, hy1)
                # a head beyond the first position needs a finger-width poly stem
                # from the overhang out to it, or it is not connected to anything
                stem = None
                if lo_side and hy1 < g[1] - ext:
                    stem = (gx0, hy1, gx1, g[1] - ext)
                elif not lo_side and hy0 > g[3] + ext:
                    stem = (gx0, g[3] + ext, gx1, hy0)
                if not clear(diff_l, head, sp_diff, exclude_own=False) or (stem and not clear(diff_l, stem, sp_diff, exclude_own=False)):
                    tally["head vs diffusion"] = tally.get("head vs diffusion", 0) + 1; continue
                if not clear(poly_l, head, sp_poly) or (stem and not clear(poly_l, stem, sp_poly)):
                    tally["head vs other poly"] = tally.get("head vs other poly", 0) + 1; continue
                if not (clear(licon_l, licon, sp_cut, exclude_own=False) and clear(mcon_l, licon, sp_cut, exclude_own=False)):
                    tally["licon vs cuts"] = tally.get("licon vs cuts", 0) + 1; continue
                # li enclosure of the licon: 0.08 on two opposite sides -- tall pad or wide pad
                pads = [(licon[0], licon[1] - enc_li, licon[2], licon[3] + enc_li),
                        (licon[0] - enc_li, licon[1], licon[2] + enc_li, licon[3])]
                pads = [pd for pd in pads if clear(li_l, pd, sp_li)]
                if not pads:
                    tally["li pad vs other li"] = tally.get("li pad vs other li", 0) + 1; continue
                pad = pads[0]
                head_rects = [(poly_l, head)] + ([(poly_l, stem)] if stem else [])
                if len(fallback) < 600:
                    fallback.append((head_rects, licon, pad))
                fx = (licon[0] + licon[2]) // 2
                if os.environ.get("LAYOPT_PLAN_DEBUG") and tally.get("_dbg", 0) < 6:
                    tally["_dbg"] = tally.get("_dbg", 0) + 1
                    print("      plan-debug: head %s pad %s  gate li y-ranges %s" % ([round(v / 1000, 3) for v in head], [round(v / 1000, 3) for v in pad],
                          [(round(tr[1] / 1000, 3), round(tr[3] / 1000, 3), round((tr[0] + tr[2]) / 2000, 3)) for _, tr in gate_li][:3]))
                ext_max = nm(0.6)                                    # the pin's li may be extended this far
                for k, tr in sorted(gate_li, key=lambda kr: abs((kr[1][0] + kr[1][2]) // 2 - fx)):
                    y0 = max(pad[1] + ms // 2, tr[1] - ext_max + ms // 2); y1 = min(pad[3] - ms // 2, tr[3] + ext_max - ms // 2)
                    if y1 < y0:
                        tally["pad and gate pin do not share a height"] = tally.get("pad and gate pin do not share a height", 0) + 1; continue
                    tx = (tr[0] + tr[2]) // 2
                    bar_x = (min(fx, tx) - ms // 2 - enc_m1, max(fx, tx) + ms // 2 + enc_m1)
                    for jj in range(0, (y1 - y0) // step + 1):
                        yj = ((y0 + y1) // 2 + ((jj + 1) // 2) * step * (1 if jj % 2 else -1))
                        if yj < y0 or yj > y1:
                            continue
                        # extend the pin li when the mcon would fall outside it (the pin's width gives the
                        # two-sided enclosure along x; along y the cut only needs to be covered)
                        pin_ext = None
                        if yj + ms // 2 > tr[3] or yj - ms // 2 < tr[1]:
                            pin_ext = (tr[0], min(tr[1], yj - ms // 2), tr[2], max(tr[3], yj + ms // 2))
                            if not clear(li_l, pin_ext, sp_li):
                                tally["pin li extension vs other li"] = tally.get("pin li extension vs other li", 0) + 1; continue
                            if not (clear(licon_l, pin_ext, 0) and clear(mcon_l, pin_ext, 0)):
                                tally["pin li extension over other cuts"] = tally.get("pin li extension over other cuts", 0) + 1; continue
                        # met1 encloses the mcons by enc on two opposite sides: along the bar (x) is free
                        bar = (bar_x[0], yj - ms // 2, bar_x[1], yj + ms // 2)
                        m_new = [(fx - ms // 2, yj - ms // 2, fx + ms // 2, yj + ms // 2), (tx - ms // 2, yj - ms // 2, tx + ms // 2, yj + ms // 2)]
                        if not clear(m1, bar, sp_m1):
                            tally["met1 bar vs other met1"] = tally.get("met1 bar vs other met1", 0) + 1; continue
                        if not all(clear(mcon_l, m, sp_cut, exclude_own=False) for m in m_new):
                            tally["mcon vs cuts"] = tally.get("mcon vs cuts", 0) + 1; continue
                        plan = head_rects + [(licon_l, licon), (li_l, pad), (mcon_l, m_new[0]), (mcon_l, m_new[1]), (m1, bar)]
                        if pin_ext is not None:
                            plan.append((li_l, pin_ext))
                        return plan
    # No straight bar: route around whatever occupies the tracks (P&R met1 in
    # the field gap, typically) on li / met1 / met2, landing on any shape of
    # the gate net -- its pin or its own P&R wire.
    if fallback:
        from . import route
        sources = [(0, (pd[0] + pd[2]) // 2, (pd[1] + pd[3]) // 2) for _, _, pd in fallback]
        xs = [pd[0] for _, _, pd in fallback] + [tr[0] for _, tr in gate_li] + [tr[2] for _, tr in gate_li]
        ys = [pd[1] for _, _, pd in fallback] + [tr[1] for _, tr in gate_li] + [tr[3] for _, tr in gate_li]
        rwin = (min(xs) - nm(1.5), min(ys) - nm(1.5), max(xs) + nm(1.5), max(ys) + nm(1.5))
        res = route.maze_route(fl, tech, dev.g, src2net, sources, rwin, new_ids=new_ids)
        tally["maze route"] = dict(route.LAST_ROUTE_STATS)
        if res is not None:
            si, wires = res
            head_rects, licon, pad = fallback[si]
            return head_rects + [(licon_l, licon), (li_l, pad)] + wires
        # no path at all: move the P&R wire that is in the way (the plan is then
        # applied inside; the ids come back through LAST_PLAN_TOUCHED)
        def heads(si):
            head_rects, licon, pad = fallback[si]
            return head_rects + [(licon_l, licon), (li_l, pad)]
        moved = route.reroute_around(fl, tech, dev.g, src2net, sources, rwin, heads, new_ids=new_ids, prov=dev.prov)
        tally["reroute"] = route.LAST_ROUTE_STATS.get("reroute")
        if moved is not None:
            LAST_PLAN_TOUCHED.extend(moved)
            return []
    return None


def _plan_sd_jumper(fl, ex, dev, inner_net, xa, xb, y0, y1, src2net, nm, L, tech):
    """Tie the new outer S/D strap (centre xb) to the inner strap (centre xa) of
    the same signal net.  First choice: mcon at both straps and a met1 bar at a
    height in [y0, y1] clear of other nets' met1.  Second: met1 pads with via1
    and a met2 bar, when every met1 height is taken by P&R routing.  Returns
    [(layer, rect)] or None."""
    LAST_JUMPER_TALLY.clear(); tally = LAST_JUMPER_TALLY
    cut = tech.vias[0][1]; mcon_l = L[cut]; m1 = L[tech.routing[1]]
    ms = nm(tech.min_width.get(cut, 0.17)); half = ms // 2
    enc_m1 = nm(tech.enclosure.get((tech.routing[1], cut), 0.03))
    sp_m1 = nm(tech.min_space.get(tech.routing[1], 0.14)); sp_cut = nm(tech.min_space.get(cut, 0.19))
    step = nm(tech.grid_um)
    win = (min(xa, xb) - nm(3.0), y0 - nm(3.0), max(xa, xb) + nm(3.0), y1 + nm(3.0))
    if y1 - y0 < ms:
        tally["strap window shorter than a cut"] = 1
        return None
    idx = {}
    for k, r in enumerate(fl.rects):
        if geom.overlaps(r.rect, win):
            idx.setdefault(r.layer, geom.BinIndex(500)).add(k, r.rect)
    def clear(layer, rect, space, same_net_ok=True):
        bi = idx.get(layer)
        if not bi:
            return True
        grown = (rect[0] - space, rect[1] - space, rect[2] + space, rect[3] + space)
        for k in bi.query_overlap(grown):
            if same_net_ok and src2net.get(k) == inner_net:
                continue
            return False
        return True
    # heights inside the device's own strip (its gates' y range) first, middle
    # out, then the rest of the strap middle out: a jumper needs no field gap,
    # gate bridges do, so leave the gap for them
    strip = (min(ex.shapes[q].rect[1] for q in dev.gate_ids), max(ex.shapes[q].rect[3] for q in dev.gate_ids))
    def middle_out(lo, hi_y):
        for k in range(0, (hi_y - lo) // step + 1):
            y = ((lo + hi_y) // 2 + ((k + 1) // 2) * step * (1 if k % 2 else -1))
            if lo <= y <= hi_y:
                yield y
    def heights():
        lo, hi_y = y0 + half, y1 - half
        slo, shi = max(lo, strip[0] + half), min(hi_y, strip[1] - half)
        seen = set()
        if shi >= slo:
            for y in middle_out(slo, shi):
                seen.add(y); yield y
        for y in middle_out(lo, hi_y):
            if y not in seen:
                yield y
    # existing same-net mcons on either strap column can be reused instead of adding one
    existing = [(k, r.rect) for k, r in enumerate(fl.rects) if r.layer == mcon_l and src2net.get(k) == inner_net
                and any(abs((r.rect[0] + r.rect[2]) // 2 - x) <= half for x in (xa, xb)) and y0 <= (r.rect[1] + r.rect[3]) // 2 <= y1]
    def mcons_at(yj):
        out = []
        for x in (xa, xb):
            reuse = [er for k, er in existing if abs((er[0] + er[2]) // 2 - x) <= half and abs((er[1] + er[3]) // 2 - yj) <= half]
            if reuse:
                continue                                   # already contacted here
            m = (x - half, yj - half, x + half, yj + half)
            if not clear(mcon_l, m, sp_cut, same_net_ok=False):
                tally["mcon vs other cuts"] = tally.get("mcon vs other cuts", 0) + 1
                return None
            out.append(m)
        return out
    def heights_with_existing():
        for _, er in existing:
            yield (er[1] + er[3]) // 2
        yield from heights()
    # option 1: met1 bar
    for yj in heights_with_existing():
        bar = (min(xa, xb) - half - enc_m1, yj - half - enc_m1, max(xa, xb) + half + enc_m1, yj + half + enc_m1)
        mc = mcons_at(yj)
        if mc is None:
            continue
        if not clear(m1, bar, sp_m1):
            tally["met1 bar vs other met1"] = tally.get("met1 bar vs other met1", 0) + 1
            continue
        return [(mcon_l, m) for m in mc] + [(m1, bar)]
    # option 2: met1 pads + via1 + met2 bar
    if len(tech.vias) < 2:
        return None
    v1 = tech.vias[1][1]; via_l = L[v1]; m2 = L[tech.routing[2]]
    vs = nm(tech.min_width.get(v1, 0.15)); vh = vs // 2
    e1 = nm(tech.enclosure.get((tech.routing[1], v1), 0.055)); e2 = nm(tech.enclosure.get((tech.routing[2], v1), 0.055))
    sp_via = nm(tech.min_space.get(v1, 0.17)); sp_m2 = nm(tech.min_space.get(tech.routing[2], 0.14))
    w2 = max(nm(tech.min_width.get(tech.routing[2], 0.14)), vs + 2 * e2)
    for yj in heights_with_existing():
        plan = []
        ok = True
        mc = mcons_at(yj)
        if mc is None:
            continue
        plan += [(mcon_l, m) for m in mc]
        for x in (xa, xb):
            pad = (x - max(half + enc_m1, vh + e1), yj - max(half + enc_m1, vh), x + max(half + enc_m1, vh + e1), yj + max(half + enc_m1, vh))
            via = (x - vh, yj - vh, x + vh, yj + vh)
            if not clear(m1, pad, sp_m1):
                tally["met1 pad vs other met1"] = tally.get("met1 pad vs other met1", 0) + 1; ok = False; break
            if not clear(via_l, via, sp_via, same_net_ok=False):
                tally["via1 vs other vias"] = tally.get("via1 vs other vias", 0) + 1; ok = False; break
            plan += [(m1, pad), (via_l, via)]
        if not ok:
            continue
        bar = (min(xa, xb) - vh - e2, yj - w2 // 2, max(xa, xb) + vh + e2, yj + w2 // 2)
        if clear(m2, bar, sp_m2):
            return plan + [(m2, bar)]
        tally["met2 bar vs other met2"] = tally.get("met2 bar vs other met2", 0) + 1
    return None


from .drc import _shares_edge, _gap_rect  # noqa: E402  (pure geometry helpers)


def _touches(a: Rect, b: Rect) -> bool:
    """Closed-rectangle contact (shared edge or overlap)."""
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


def inv_layers(tech) -> Dict[int, str]:
    return {v: k for k, v in tech.layers.items()}


def add_rect_dbu(fl: FlatLayout, layer: Tuple[int, int], rect: Rect, prov: str) -> int:
    fl.rects.append(FlatRect(layer, (min(rect[0], rect[2]), min(rect[1], rect[3]), max(rect[0], rect[2]), max(rect[1], rect[3])), prov))
    return len(fl.rects) - 1
