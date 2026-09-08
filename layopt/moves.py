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


def set_vt(fl: FlatLayout, ex: Extraction, dev: Device, flavour: str) -> List[int]:
    """Change a device's Vt flavour by implant: `flavour` is a name in
    tech.vt ("hvt" for a sky130 PMOS) or "std".  A rectangle on the implant
    layer covers all the device's gates with the flavour's gate enclosure; any
    other gate of that polarity closer than the enclosure to the rectangle's
    edge is taken in too (a partly covered gate is illegal, and the stock
    cells' 0.42 um gate pitch leaves 0.27 um between gates, less than twice
    0.18), so the move tells you which devices changed with it.  "std" removes
    the implant rects that cover the device's gates.  Zero area, zero wire; the
    extractor reports the new model, the drive model applies the measured
    multiplier, the topology signature is unmoved (a flavour is a size).
    Returns the changed rect ids."""
    tech = ex.tech
    L = tech.layers
    d = fl.dbu_um
    nm = lambda um: int(round(um / d))
    grects = [ex.shapes[q].rect for q in dev.gate_ids]
    touched: List[int] = []
    if flavour == "std":
        # remove the implant over this device's gates: cut a window (gates + enclosure) out
        # of every implant rect of this polarity's flavours.  A neighbouring gate that the
        # remaining implant would then enclose by less than gate_enc is taken into the
        # window too (0.42 um gate pitch: 0.27 between gates, less than 2 x 0.18), and so
        # is any leftover piece narrower than the implant's min width.
        cut_any = False
        for name, f in tech.vt.items():
            if f.kind != dev.kind:
                continue
            lay = L[f.layer]
            e = nm(f.gate_enc); mw = nm(tech.min_width.get(f.layer, 0.38))
            covering = [i for i, r in enumerate(fl.rects) if r.layer == lay and r.x1 > r.x0 and any(geom.overlaps(r.rect, g) for g in grects)]
            if not covering:
                continue
            win = [min(g[0] for g in grects) - e, min(g[1] for g in grects) - e, max(g[2] for g in grects) + e, max(g[3] for g in grects) + e]
            others = [(dv, ex.shapes[q].rect) for dv in ex.devices if dv.kind == dev.kind and dv is not dev for q in dv.gate_ids]
            swept: List[Device] = []
            grew = True
            while grew:
                grew = False
                for dv, g in others:
                    if dv in swept:
                        continue
                    # a gate the window edge would come closer than e to (it stays covered, so
                    # its enclosure by what remains would be too small)
                    if geom.overlaps(g, (win[0] - e, win[1] - e, win[2] + e, win[3] + e)):
                        win = [min(win[0], g[0] - e), min(win[1], g[1] - e), max(win[2], g[2] + e), max(win[3], g[3] + e)]
                        swept.append(dv); grew = True
            for i in covering:
                r = fl.rects[i]
                pieces = geom.subtract(r.rect, [tuple(win)])
                # a leftover sliver below min width: widen the window over it (it has no gate
                # of ours, or the sweep would have taken it)
                for pc in list(pieces):
                    if min(pc[2] - pc[0], pc[3] - pc[1]) < mw:
                        pieces.remove(pc)
                fl.rects[i].rect = pieces[0] if pieces else (r.x0, r.y0, r.x0, r.y0)
                touched.append(i)
                for pc in pieces[1:]:
                    touched.append(add_rect_dbu(fl, lay, pc, r.prov))
            cut_any = True
            LAST_VT_SWEPT[:] = [dv.name for dv in swept]
        if not cut_any:
            raise MoveError("set_vt: %s has no implant to remove" % dev.name)
        return touched
    if flavour not in tech.vt:
        raise MoveError("set_vt: unknown flavour %r (have %s)" % (flavour, sorted(tech.vt)))
    f = tech.vt[flavour]
    if f.kind != dev.kind:
        raise MoveError("set_vt: %s applies to %s devices, %s is %s" % (flavour, f.kind, dev.name, dev.kind))
    if dev.l < f.min_l - 1e-9:
        raise MoveError("set_vt: %s needs a gate at least %.2f um long; %s has L=%.2f (sky130 poly.1b)" % (flavour, f.min_l, dev.name, dev.l))
    e = nm(f.gate_enc)
    lay = L[f.layer]
    box = [min(g[0] for g in grects) - e, min(g[1] for g in grects) - e, max(g[2] for g in grects) + e, max(g[3] for g in grects) + e]
    # take in other gates of this polarity that the box would come too close to
    # (and repeat: taking one in may bring the box near the next)
    others = [(dv, ex.shapes[q].rect) for dv in ex.devices if dv.kind == dev.kind and dv is not dev for q in dv.gate_ids]
    swept: List[Device] = []
    grew = True
    while grew:
        grew = False
        for dv, g in others:
            if dv in swept:
                continue
            near = (box[0] - e, box[1] - e, box[2] + e, box[3] + e)
            if geom.overlaps(g, near) and not (g[0] - box[0] >= e and g[1] - box[1] >= e and box[2] - g[2] >= e and box[3] - g[3] >= e):
                box = [min(box[0], g[0] - e), min(box[1], g[1] - e), max(box[2], g[2] + e), max(box[3], g[3] + e)]
                if dv not in swept:
                    swept.append(dv)
                grew = True
    mw = nm(tech.min_width.get(f.layer, 0.38))
    if box[2] - box[0] < mw:
        pad = (mw - (box[2] - box[0]) + 1) // 2; box[0] -= pad; box[2] += pad
    if box[3] - box[1] < mw:
        pad = (mw - (box[3] - box[1]) + 1) // 2; box[1] -= pad; box[3] += pad
    # existing implant rects of this flavour: merge with any the box overlaps or comes within spacing of
    sp = nm(tech.min_space.get(f.layer, 0.38))
    for i, r in enumerate(fl.rects):
        if r.layer == lay and r.x1 > r.x0 and geom.overlaps(r.rect, (box[0] - sp, box[1] - sp, box[2] + sp, box[3] + sp)):
            box = [min(box[0], r.x0), min(box[1], r.y0), max(box[2], r.x1), max(box[3], r.y1)]
            fl.rects[i].rect = (r.x0, r.y0, r.x0, r.y0); touched.append(i)
    # (no well check: sky130's "hvtp inside nwell" rule is commented out of the PDK's own
    # deck, and the hd cells' hvtp rects extend 0.055 um below their nwell)
    j = add_rect_dbu(fl, lay, tuple(box), dev.prov)
    touched.append(j)
    LAST_VT_SWEPT[:] = [dv.name for dv in swept]
    return touched


LAST_VT_SWEPT: List[str] = []       # other devices the last set_vt had to take into the implant


def set_gate_length(fl: FlatLayout, ex: Extraction, dev: Device, l_um: float) -> List[int]:
    """Change a device's gate length by stretching its cell at the gate.

    A standard cell has no slack beside a gate: its contacts sit at the
    minimum spacing from it and at the minimum enclosure from the diffusion
    end, so a longer gate cannot be cut into the stripe in place.  What can
    move is everything beyond the gate: the cell is cut just inside the
    outer edge of the device's outermost finger, every rect of the cell
    right of the cut shifts outward by the length change and every rect that
    crosses the cut (the poly stripe, the diffusion, well and implant, a li
    strap over the gate) is stretched by it; the filler abutting the cell on
    that side gives the space (its rects shrink from the near edge).  A poly
    stripe usually gates both a P and an N device, so both lengthen -- the
    move records the companions in LAST_L_COMPANIONS.  DEF wiring inside the
    stretched span is shifted or stretched with the cell; anything that
    could not follow (a vertical wire continuing into other rows) is for the
    guards to judge.  Negative changes shorten the same way.  Refuses when the
    length leaves the characterised range or the flavour's minimum, when the
    device is not the outermost on its side with a filler beyond, or when the
    filler is too narrow.  Returns the changed rect ids."""
    if dev.flow_axis != "x":
        raise MoveError("set_gate_length: only vertical gates (flow along x) are implemented")
    tech = ex.tech
    L = tech.layers
    d = fl.dbu_um
    nm = lambda um: int(round(um / d))
    lo, hi = tech.l_range
    if not (lo - 1e-9 <= l_um <= hi + 1e-9):
        raise MoveError("set_gate_length: L=%.3f outside the characterised range %s" % (l_um, tech.l_range))
    flav = tech.flavour_of_model(dev.model)
    if flav in tech.vt and l_um < tech.vt[flav].min_l - 1e-9:
        raise MoveError("set_gate_length: %s gates must be at least %.2f um long" % (flav, tech.vt[flav].min_l))
    delta = nm(l_um) - nm(dev.l)
    if delta == 0:
        return []
    inst = dev.prov
    cell_rects = [i for i, r in enumerate(fl.rects) if r.prov == inst]
    if not cell_rects:
        raise MoveError("set_gate_length: no rects carry the device's provenance %s" % inst)
    cx0 = min(fl.rects[i].x0 for i in cell_rects); cx1 = max(fl.rects[i].x1 for i in cell_rects)
    cy0 = min(fl.rects[i].y0 for i in cell_rects); cy1 = max(fl.rects[i].y1 for i in cell_rects)
    # every finger of the device is cut just inside its outer edge, outermost first, so
    # each cut shifts what lies beyond it (including the fingers already lengthened)
    fingers = sorted((ex.shapes[q].rect for q in dev.gate_ids), key=lambda r: -r[2])
    g = fingers[0]
    # the cell beyond ours on that side: the instance whose rects start nearest past the
    # gate within our row (a cell's well pokes past its placement box, so the boundary
    # is found from the neighbour, not from our own extent)
    starts: Dict[str, int] = {}
    members: Dict[str, List[int]] = {}
    for i, r in enumerate(fl.rects):
        if r.prov == inst or "/net:" in r.prov or "/pin:" in r.prov or r.y1 <= cy0 or r.y0 >= cy1:
            continue
        members.setdefault(r.prov, []).append(i)
        starts[r.prov] = min(starts.get(r.prov, 10**12), r.x0)
    right = {p: x for p, x in starts.items() if g[2] < x <= cx1 + nm(0.3)}
    if not right:
        raise MoveError("set_gate_length: nothing abuts %s on the right" % inst.split("/", 1)[1][:40])
    fprov = min(right, key=right.get)
    if not ("fill" in fprov.split("/")[-1].lower() or "decap" in fprov.split("/")[-1].lower()):
        raise MoveError("set_gate_length: %s abuts on the right, not a filler" % fprov.split("/")[-1][:40])
    fids = members[fprov]
    # the filler's placement boundary is where its rails start; wells and implants poke past it
    soft_layers = {L[n] for n in (tech.nwell, tech.nsdm, tech.psdm) if n} | {L[f.layer] for f in tech.vt.values()}
    fx0 = min([fl.rects[i].x0 for i in fids if fl.rects[i].layer not in soft_layers] or [right[fprov]])
    fx1 = max(fl.rects[i].x1 for i in fids)
    total = delta * len(fingers)
    if fx1 - fx0 - total < nm(0.2):
        raise MoveError("set_gate_length: the filler %s is too narrow to give %.3f um" % (fprov.split("/")[-1][:30], total * d))
    touched: List[int] = []
    cell_x1 = cx1
    # rail contacts and well taps sit on the continuous supply rail, duplicated by the
    # neighbouring row's cells: they stay where they are (the rail itself stretches)
    s2n = {sh.src: ex.net_of_shape[k] for k, sh in enumerate(ex.shapes) if sh.src >= 0}
    supply_ids = {i for i, n in ex.nets.items() if n.name in tech.supply_names}
    cut_or_tap = {L[c] for _, c, _ in tech.vias} | {L[tech.diff_contact]} | ({L["tap"]} if "tap" in L else set())
    # a supply-net cut or tap outside every diffusion strip of the cell is on the rail
    # (a source contact inside a strip is not, and moves with its region)
    strips = [(fl.rects[i].y0, fl.rects[i].y1) for i in cell_rects if fl.rects[i].layer == L[tech.diff]]
    def on_rail(r):
        return not any(r.y1 > y0 and r.y0 < y1 for y0, y1 in strips)
    fixed = {i for i in cell_rects if fl.rects[i].layer in cut_or_tap and (s2n.get(i) in supply_ids or fl.rects[i].layer == L.get("tap"))
             and on_rail(fl.rects[i])}
    for gk in fingers:
        x_cut = gk[2] - 1
        # 1. the cell: shift what lies beyond the cut, stretch what crosses it
        for i in cell_rects:
            r = fl.rects[i]
            if i in fixed:
                continue
            if r.x0 >= x_cut:
                fl.rects[i].rect = (r.x0 + delta, r.y0, r.x1 + delta, r.y1); touched.append(i)
            elif r.x1 > x_cut:
                fl.rects[i].rect = (r.x0, r.y0, r.x1 + delta, r.y1); touched.append(i)
        # 2. DEF wiring over the cell follows it: shifted beyond the cut, stretched across it
        #    (over the filler it stays -- its cuts sit on the filler's own rail cuts)
        for i, r in enumerate(fl.rects):
            if "/net:" not in r.prov and "/pin:" not in r.prov:
                continue
            if r.y1 <= cy0 or r.y0 >= cy1:
                continue
            if r.prov.rsplit(":", 1)[-1] in tech.supply_names:
                continue                       # rail wiring is continuous and its cuts duplicate the cells' own: it stays
            if r.x0 >= x_cut and r.x1 <= cell_x1 + 1:
                fl.rects[i].rect = (r.x0 + delta, r.y0, r.x1 + delta, r.y1); touched.append(i)
            elif r.x0 < x_cut < r.x1:
                fl.rects[i].rect = (r.x0, r.y0, r.x1 + delta, r.y1); touched.append(i)
        for tx in getattr(fl, "texts", []):
            if tx.xy[0] >= x_cut and cy0 <= tx.xy[1] <= cy1 and cx0 <= tx.xy[0] <= cell_x1:
                tx.xy = (tx.xy[0] + delta, tx.xy[1])
        cell_x1 += delta
    # 3. the filler gives the space from its near edge: rects that start at (or before,
    #    a well's enclosure) its boundary lose the total there
    for i in fids:
        r = fl.rects[i]
        if (r.x0 <= fx0 + 1 or r.layer in soft_layers) and r.x1 - (r.x0 + total) > 0:
            fl.rects[i].rect = (r.x0 + total, r.y0, r.x1, r.y1); touched.append(i)
    LAST_L_COMPANIONS[:] = sorted({dv.name for dv in ex.devices if dv is not dev
                                   for gk in fingers if any(geom.overlaps(ex.shapes[q].rect, (gk[0], cy0, gk[2], cy1)) for q in dv.gate_ids)})
    return sorted(set(touched))


LAST_L_COMPANIONS: List[str] = []   # devices on the same poly stripe whose length changed along


def _cell_box(fl: FlatLayout, ex: Extraction, inst: str):
    """Placement box of an instance from its rails (the widest supply-net li
    rects span exactly the placement width) and its rects' y extent."""
    L = ex.tech.layers
    s2n = {sh.src: ex.net_of_shape[k] for k, sh in enumerate(ex.shapes) if sh.src >= 0}
    supply = {i for i, n in ex.nets.items() if n.name in ex.tech.supply_names}
    ids = [i for i, r in enumerate(fl.rects) if r.prov == inst]
    if not ids:
        raise MoveError("no rects carry provenance %s" % inst)
    lis = [fl.rects[i] for i in ids if fl.rects[i].layer == L[ex.tech.routing[0]]]
    rails = lis                                     # the rails are the widest li a cell has
    if rails:
        w = max(r.x1 - r.x0 for r in rails)
        wide = [r for r in rails if r.x1 - r.x0 >= 0.8 * w]
        x0 = min(r.x0 for r in wide); x1 = max(r.x1 for r in wide)
    else:
        x0 = min(fl.rects[i].x0 for i in ids); x1 = max(fl.rects[i].x1 for i in ids)
    y0 = min(fl.rects[i].y0 for i in ids); y1 = max(fl.rects[i].y1 for i in ids)
    return ids, (x0, y0, x1, y1)


def _outer_regions(fl: FlatLayout, ex: Extraction, inst: str, box, side: str):
    """For each polarity, the outer S/D region of `inst` on `side` ("right" or
    "left"): (kind, diffusion rect, gate rect, region net id, region x-range)
    or None when that strip has no gate."""
    L = ex.tech.layers
    out = {}
    for kind in ("p", "n"):
        gates = [(ex.shapes[q].rect, dv) for dv in ex.devices if dv.prov == inst and dv.kind == kind for q in dv.gate_ids]
        if not gates:
            out[kind] = None; continue
        g, dv = max(gates, key=lambda t: t[0][2]) if side == "right" else min(gates, key=lambda t: t[0][0])
        diff = next(r.rect for r in fl.rects if r.layer == L[ex.tech.diff] and r.prov == inst and geom.overlaps(r.rect, g))
        xr = (g[2], diff[2]) if side == "right" else (diff[0], g[0])
        probe = (xr[0] + 1, (g[1] + g[3]) // 2)
        net = None
        for k, sh in enumerate(ex.shapes):
            if sh.layer.startswith("sd_") and sh.rect[0] <= probe[0] <= sh.rect[2] and sh.rect[1] <= probe[1] <= sh.rect[3]:
                net = ex.net_of_shape[k]; break
        out[kind] = (kind, diff, g, net, xr)
    return out


def _merge_plan(fl: FlatLayout, ex: Extraction, inst_a: str, inst_b: str):
    """What a dissolve of the boundary A|B can do: (delta, limiter, nets, ra, rb,
    ids_a, ids_b, box_a, box_b, fixed, s2n).  Raises MoveError when the cells do
    not abut or their outer regions are not the same net on every strip."""
    tech = ex.tech
    L = tech.layers
    ids_a, box_a = _cell_box(fl, ex, inst_a); ids_b, box_b = _cell_box(fl, ex, inst_b)
    if abs(box_a[2] - box_b[0]) > 1:
        raise MoveError("merge_boundary: %s and %s do not abut" % (inst_a.split("/")[1], inst_b.split("/")[1]))
    ra = _outer_regions(fl, ex, inst_a, box_a, "right"); rb = _outer_regions(fl, ex, inst_b, box_b, "left")
    # per strip: same net facing -> the regions may become one (slide over the gap and
    # B's region); different nets -> the diffusions keep their spacing (a plain compaction)
    sp_diff = int(round(tech.min_space.get(tech.diff, 0.27) / fl.dbu_um))
    deltas = []; nets = []
    for kind in ("p", "n"):
        if ra[kind] is None or rb[kind] is None:
            continue
        gap = rb[kind][1][0] - ra[kind][1][2]
        if ra[kind][3] is not None and ra[kind][3] == rb[kind][3]:
            deltas.append(gap + (rb[kind][4][1] - rb[kind][4][0])); nets.append(ex.nets[ra[kind][3]].name)
        else:
            deltas.append(gap - sp_diff); nets.append("spacing")
    if not deltas:
        raise MoveError("merge_boundary: no strip on either side (a filler or tap cell)")
    s2n = {sh.src: ex.net_of_shape[k] for k, sh in enumerate(ex.shapes) if sh.src >= 0}
    supply = {i for i, n in ex.nets.items() if n.name in tech.supply_names}
    cut_or_tap = {L[c] for _, c, _ in tech.vias} | {L[tech.diff_contact]} | ({L["tap"]} if "tap" in L else set())
    strips_b = [(fl.rects[i].y0, fl.rects[i].y1) for i in ids_b if fl.rects[i].layer == L[tech.diff]]
    def on_rail(r):
        return not any(r.y1 > y0 and r.y0 < y1 for y0, y1 in strips_b)
    fixed = {i for i in ids_b if fl.rects[i].layer in cut_or_tap and (s2n.get(i) in supply or fl.rects[i].layer == L.get("tap")) and on_rail(fl.rects[i])}
    delta, limiter = _slide_limit(fl, ex, ids_a, [i for i in ids_b if i not in fixed], box_a, box_b, s2n, min(deltas))
    return delta, limiter, nets, ra, rb, ids_a, ids_b, box_a, box_b, fixed, s2n


def boundary_candidates(fl: FlatLayout, ex: Extraction):
    """Abutting cell pairs (A left of B, same row) whose outer S/D regions face
    each other on the same net for every strip both have: the boundaries a
    dissolve can close.  Returns [(inst_a, inst_b, delta_dbu, nets)] with the
    compaction each would give."""
    insts = sorted({r.prov for r in fl.rects if "/net:" not in r.prov and "/pin:" not in r.prov and r.prov.count("/") >= 2})
    boxes = {}
    for inst in insts:
        try:
            boxes[inst] = _cell_box(fl, ex, inst)[1]
        except MoveError:
            continue
    by_row: Dict[Tuple[int, int], List[str]] = {}
    for inst, b in boxes.items():
        by_row.setdefault((b[1], b[3]), []).append(inst)
    out = []
    for row, members in by_row.items():
        members.sort(key=lambda i: boxes[i][0])
        for a, b in zip(members, members[1:]):
            if abs(boxes[a][2] - boxes[b][0]) > 1:
                continue
            try:
                delta, limiter, nets = _merge_plan(fl, ex, a, b)[:3]
            except (MoveError, StopIteration):
                continue
            if delta > 0:
                out.append((a, b, delta, nets))
    return out


def merge_boundary(fl: FlatLayout, ex: Extraction, inst_a: str, inst_b: str) -> List[int]:
    """Dissolve the boundary between two abutting cells: B slides left as far
    as every rule allows.  On a strip whose outer S/D regions face each other
    on the same net the two regions become one shared region with A's
    contacts (the slide may cover the gap and B's region); on a strip whose
    regions are different nets the diffusions keep their spacing (a plain
    compaction); the least of these, then every other layer's spacing, bounds
    the slide. B's contacts and
    straps that would then sit within contact spacing of A's go (they are
    the same net; the fill pass merges what is left); the filler beyond B
    grows by the same amount, so the saving appears as room beside the pair.
    The cells' rail contacts and taps stay on the shared rail (the
    neighbouring row duplicates them), as does supply-net DEF wiring; other
    DEF wiring over B follows it.  Returns the changed rect ids; the amount
    is in LAST_MERGE_DELTA."""
    tech = ex.tech
    L = tech.layers
    d = fl.dbu_um
    nm = lambda um: int(round(um / d))
    delta, limiter, nets, ra, rb, ids_a, ids_b, box_a, box_b, fixed, s2n = _merge_plan(fl, ex, inst_a, inst_b)
    if delta <= 0:
        raise MoveError("merge_boundary: nothing to gain -- %s" % limiter)
    LAST_MERGE_LIMIT[0] = limiter
    cy0, cy1 = min(box_a[1], box_b[1]), max(box_a[3], box_b[3])
    touched: List[int] = []
    # the filler beyond B grows toward B
    starts: Dict[str, int] = {}; members: Dict[str, List[int]] = {}
    for i, r in enumerate(fl.rects):
        if r.prov in (inst_a, inst_b) or "/net:" in r.prov or "/pin:" in r.prov or r.y1 <= cy0 or r.y0 >= cy1:
            continue
        members.setdefault(r.prov, []).append(i); starts[r.prov] = min(starts.get(r.prov, 10**12), r.x0)
    right = {p: x for p, x in starts.items() if box_b[2] - nm(0.3) <= x <= box_b[2] + nm(0.3)}
    if not right:
        raise MoveError("merge_boundary: nothing abuts %s on the right to take the freed space" % inst_b.split("/")[1])
    fprov = min(right, key=right.get)
    if not ("fill" in fprov.split("/")[-1].lower() or "decap" in fprov.split("/")[-1].lower()):
        raise MoveError("merge_boundary: %s abuts %s on the right, not a filler" % (fprov.split("/")[-1][:30], inst_b.split("/")[1]))
    soft_layers = {L[n] for n in (tech.nwell, tech.nsdm, tech.psdm) if n} | {L[f.layer] for f in tech.vt.values()}
    fx0 = min([fl.rects[i].x0 for i in members[fprov] if fl.rects[i].layer not in soft_layers] or [right[fprov]])
    # 1. B slides left (rail cuts stay)
    for i in ids_b:
        if i in fixed:
            continue
        r = fl.rects[i]
        fl.rects[i].rect = (r.x0 - delta, r.y0, r.x1 - delta, r.y1); touched.append(i)
    for i, r in enumerate(fl.rects):
        if ("/net:" in r.prov or "/pin:" in r.prov) and r.y1 > cy0 and r.y0 < cy1 and r.prov.rsplit(":", 1)[-1] not in tech.supply_names:
            if r.x0 >= box_b[0] - 1 and r.x1 <= box_b[2] + 1:
                fl.rects[i].rect = (r.x0 - delta, r.y0, r.x1 - delta, r.y1); touched.append(i)
    for tx in getattr(fl, "texts", []):
        if box_b[0] <= tx.xy[0] <= box_b[2] and cy0 <= tx.xy[1] <= cy1:
            tx.xy = (tx.xy[0] - delta, tx.xy[1])
    # 2. the filler grows toward B
    for i in members[fprov]:
        r = fl.rects[i]
        if r.x0 <= fx0 + 1 or r.layer in soft_layers:
            fl.rects[i].rect = (r.x0 - delta, r.y0, r.x1, r.y1); touched.append(i)
    # 3. A's rails, wells and implants reach B's (the two abut already; the diffusion
    #    strips are joined by extending A's to B's shifted start), and B's contacts /
    #    straps that landed within contact spacing of A's in the shared region go
    sp_cut = nm(tech.min_space.get(tech.diff_contact, 0.17))
    for kind in ("p", "n"):
        if ra[kind] is None or rb[kind] is None or ra[kind][3] is None or ra[kind][3] != rb[kind][3]:
            continue                                   # not a shared region: the strips merely keep spacing
        da = ra[kind][1]; db_id = next(i for i in ids_b if fl.rects[i].layer == L[tech.diff] and fl.rects[i].rect[1] == rb[kind][1][1] and fl.rects[i].rect[3] == rb[kind][1][3])
        db = fl.rects[db_id].rect
        ia = next(i for i in ids_a if fl.rects[i].layer == L[tech.diff] and fl.rects[i].rect == da)
        if db[0] > da[2]:
            fl.rects[ia].rect = (da[0], da[1], db[0], da[3]); touched.append(ia)
        shared = (ra[kind][2][2], da[1], rb[kind][2][0] - delta, da[3])
        a_cuts = [fl.rects[i].rect for i in ids_a if fl.rects[i].layer == L[tech.diff_contact] and geom.overlaps(fl.rects[i].rect, shared)]
        for i in ids_b:
            r = fl.rects[i]
            if r.layer == L[tech.diff_contact] and geom.overlaps(r.rect, shared):
                if any(r.rect == c for c in a_cuts):
                    continue
                if any(geom.overlaps((r.x0 - sp_cut, r.y0 - sp_cut, r.x1 + sp_cut, r.y1 + sp_cut), c) for c in a_cuts):
                    fl.rects[i].rect = (r.x0, r.y0, r.x0, r.y0); touched.append(i)
    LAST_MERGE_DELTA[0] = delta
    touched = sorted(set(touched))
    for _ in range(4):                                     # same-net straps that met: merge them
        new = fill_notches(fl, ex, touched)
        if not new:
            break
        touched += new
    return sorted(set(touched))


LAST_MERGE_DELTA: List[int] = [0]
LAST_MERGE_LIMIT: List[str] = [""]      # what bounded the last merge_boundary slide


def _slide_limit(fl: FlatLayout, ex: Extraction, ids_a, ids_b, box_a, box_b, s2n, delta: int):
    """Largest slide of B toward A, at most `delta`, that keeps every spacing
    rule between A's and B's shapes on the conducting layers.  Returns
    (delta, description of the limiting pair)."""
    tech = ex.tech
    L = tech.layers
    inv = {v: k for k, v in L.items()}
    nm = lambda um: int(round(um / fl.dbu_um))
    cuts = {L[c] for _, c, _ in tech.vias} | {L[tech.diff_contact]}
    layers = {L[tech.poly]} | {L[n] for n in tech.routing[:3]} | cuts
    reach = nm(1.5) + delta
    a_near = [i for i in ids_a if fl.rects[i].layer in layers and fl.rects[i].x1 > box_a[2] - reach and fl.rects[i].x1 > fl.rects[i].x0]
    b_near = [i for i in ids_b if fl.rects[i].layer in layers and fl.rects[i].x0 < box_b[0] + reach and fl.rects[i].x1 > fl.rects[i].x0]
    best, who = delta, "the diffusion regions"
    for i in a_near:
        ra = fl.rects[i]
        for j in b_near:
            rb = fl.rects[j]
            if rb.layer != ra.layer or rb.y1 <= ra.y0 or rb.y0 >= ra.y1:
                continue
            ln = inv.get(ra.layer)
            is_cut = ra.layer in cuts
            if not is_cut and s2n.get(i) is not None and s2n.get(i) == s2n.get(j):
                continue                                   # same net: they may merge
            sp = nm(tech.min_space.get(ln, 0.17))
            allowed = rb.x0 - ra.x1 - sp                   # slide that leaves exactly the spacing
            if is_cut and (rb.x0 - ra.x1 - delta) == 0 and ra.y0 == rb.y0 and ra.y1 == rb.y1 and (ra.x1 - ra.x0) == (rb.x1 - rb.x0):
                continue                                   # they would coincide exactly: one cut
            if allowed < best:
                best, who = allowed, "%s %s (%s) vs %s (%s), spacing %.2f" % (ln, [round(v * fl.dbu_um, 3) for v in ra.rect], ra.prov.split("/")[1],
                                                                           [round(v * fl.dbu_um, 3) for v in rb.rect], rb.prov.split("/")[1], tech.min_space.get(ln, 0.17))
    return best, who


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
    cut_pairs = {L[c]: (L[lo], L[up]) for lo, c, up in tech.vias}
    def known(k):
        return src2net.get(k) if k not in new_set and k not in label else label.get(k)
    while changed and pending:
        changed = False
        for i in list(pending):
            r = fl.rects[i]
            got = None
            for k in by_layer[r.layer].query_touch(r.rect):           # same-layer contact
                n = known(k)
                if n is not None and k != i:
                    got = n; break
            if got is None:                                            # through a cut to the layer below/above
                for c, (lo, up) in cut_pairs.items():
                    if r.layer not in (lo, up) or c not in by_layer:
                        continue
                    other = up if r.layer == lo else lo
                    for kc in by_layer[c].query_overlap(r.rect):
                        for k in by_layer.get(other, geom.BinIndex()).query_overlap(fl.rects[kc].rect):
                            n = known(k)
                            if n is not None:
                                got = n; break
                        if got is not None:
                            break
                    if got is not None:
                        break
            if got is not None:
                label[i] = got; pending.remove(i); changed = True
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
    # The deficit above is a first estimate from the straps alone.  Search the
    # shift upward (grid steps, up to 0.6 um) until the mirrored straps clear
    # every other net's li by spacing and cover none of its cuts, the mirrored
    # contacts clear other cuts, and the new gate finger clears other poly: a
    # cell's own strap at the strip's end (a supply tab beside the outer
    # region, an internal column) is the usual reason, and a wider outer
    # region is the price.
    li_l_ = L[tech.routing[0]]; licon_l_ = L[tech.diff_contact]; poly_l_ = L[tech.poly]
    cut_ls = {licon_l_} | ({L[tech.vias[0][1]]} if tech.vias else set())
    sp_li_ = nm(tech.min_space.get(tech.routing[0], 0.17)); sp_cut_ = nm(tech.min_space.get(tech.diff_contact, 0.17)); sp_po_ = nm(tech.min_space.get(tech.poly, 0.21))
    s2n_ = {sh.src: ex.net_of_shape[k] for k, sh in enumerate(ex.shapes) if sh.src >= 0}
    inner_licon_rects = [fl.rects[k].rect for k in inner_licons]
    inner_sid0 = next((q for q, sh in enumerate(ex.shapes) if sh.src == inner_licons[0]), None)
    inner_net0 = ex.net_of_shape[inner_sid0] if inner_sid0 is not None else None
    near = geom.BinIndex()
    for k, r in enumerate(fl.rects):
        if r.layer in (li_l_, poly_l_) or r.layer in cut_ls:
            if r.x1 >= D[0] - nm(2.0) and r.x0 <= D[2] + nm(3.0) and r.y1 >= D[1] - nm(3.0) and r.y0 <= D[3] + nm(3.0):
                near.add(k, r.rect)
    def legal_shift(sh):
        m = (lambda x: int(round(2 * xc - x)) + sh) if hi else (lambda x: int(round(2 * xc - x)) - sh)
        mr = lambda r: (min(m(r[0]), m(r[2])), r[1], max(m(r[0]), m(r[2])), r[3])
        straps = [mr(fl.rects[k].rect) for k in inner_straps]
        licons = [mr(r) for r in inner_licon_rects]
        ext_ = nm(tech.poly_ext_diff)
        finger = (min(m(g[0]), m(g[2])), g[1] - ext_, max(m(g[0]), m(g[2])), g[3] + ext_)
        for st in straps:
            for k in near.query_overlap((st[0] - sp_li_, st[1] - sp_li_, st[2] + sp_li_, st[3] + sp_li_)):
                r = fl.rects[k]; n = s2n_.get(k)
                if n is None:
                    continue
                if n == inner_net0:
                    # our own net: fine when merged (overlap / shared edge), a notch when merely near
                    if r.layer == li_l_ and not (geom.overlaps(r.rect, st) or _shares_edge(r.rect, st)):
                        return False
                    continue
                if r.layer == li_l_ or (r.layer in cut_ls and geom.overlaps(r.rect, st)):
                    return False
        for lc in licons:
            for k in near.query_overlap((lc[0] - sp_cut_, lc[1] - sp_cut_, lc[2] + sp_cut_, lc[3] + sp_cut_)):
                if fl.rects[k].layer in cut_ls and fl.rects[k].rect != lc:
                    return False
        for k in near.query_overlap((finger[0] - sp_po_, finger[1] - sp_po_, finger[2] + sp_po_, finger[3] + sp_po_)):
            r = fl.rects[k]
            if r.layer == poly_l_ and s2n_.get(k) != dev.g:
                return False
        return True
    grid_ = nm(tech.grid_um)
    if not legal_shift(shift):
        for sh in range(shift, nm(0.6) + 1, grid_):
            if legal_shift(sh):
                shift = sh; break
    mx = (lambda x: int(round(2 * xc - x)) + shift) if hi else (lambda x: int(round(2 * xc - x)) - shift)
    def mrect(r: Rect) -> Rect:
        return (min(mx(r[0]), mx(r[2])), r[1], max(mx(r[0]), mx(r[2])), r[3])
    # 1. diffusion: extend to the mirror of the inner edge -- unless other diffusion
    #    or a tap lies within spacing of the new strip (a neighbour that abuts, a tap
    #    in the filler): shifting cannot cure that, so refuse and name it
    x_new = mx(inner[0] if hi else inner[1])
    D_new = (D[0], D[1], x_new, D[3]) if hi else (x_new, D[1], D[2], D[3])
    sp_d = nm(tech.min_space.get(tech.diff, 0.27))
    grown_part = (D[2] - 1, D[1] - sp_d, x_new + sp_d, D[3] + sp_d) if hi else (x_new - sp_d, D[1] - sp_d, D[0] + 1, D[3] + sp_d)
    for k, r in enumerate(fl.rects):
        if k == di or r.layer not in (L[tech.diff], L.get("tap")) or not geom.overlaps(r.rect, grown_part):
            continue
        if geom.overlaps(r.rect, D_new) or _shares_edge(r.rect, D_new):
            if r.layer == L[tech.diff] and r.prov == fl.rects[di].prov and (geom.overlaps(r.rect, D) or _shares_edge(r.rect, D)):
                continue                           # a slab of our own strip (the stock cells draw one strip as several rects)
        raise MoveError("add_finger: %s at %s (%s) lies within diffusion spacing of the extended strip"
                        % (inv.get(r.layer, r.layer), [round(v * d, 3) for v in r.rect], r.prov.split("/", 1)[1][:40]))
    # poly of another net crossing the new diffusion would be a transistor that was not there
    ext_region = (D[2], D[1], x_new, D[3]) if hi else (x_new, D[1], D[0], D[3])
    s2n_here = {sh.src: ex.net_of_shape[k] for k, sh in enumerate(ex.shapes) if sh.src >= 0}
    for k, r in enumerate(fl.rects):
        if r.layer == L[tech.poly] and geom.overlaps(r.rect, ext_region) and s2n_here.get(k) != dev.g:
            raise MoveError("add_finger: poly at %s (%s) crosses the extended diffusion (it would gate a new transistor)"
                            % ([round(v * d, 3) for v in r.rect], r.prov.split("/", 1)[1][:40]))
    fl.rects[di].rect = D_new
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
    cut_layers = {licon_l} | ({L[tech.vias[0][1]]} if tech.vias else set())
    def foreign(k):
        n = src2net.get(k)
        return n is not None and n != inner_net
    # The part of the strap that must exist covers our contacts: [lic_lo, lic_hi].
    # A foreign li shape within spacing of that part (or a foreign cut under it)
    # cannot be trimmed away: refuse.  Beyond it, on either side, trim the strap
    # back to clear (li by spacing; a cut of another net only by overlap -- li
    # has no spacing rule against a cut, it must merely not cover it).
    trim_lo, trim_hi = None, None
    for k in inner_straps:
        nr = mrect(fl.rects[k].rect)
        grown = (nr[0] - sp_li, nr[1] - sp_li, nr[2] + sp_li, nr[3] + sp_li)
        must = (nr[0], lic_lo, nr[2], lic_hi)
        for k2, r2 in enumerate(fl.rects):
            if (r2.layer != li_l and r2.layer not in cut_layers) or not foreign(k2):
                continue
            sp = sp_li if r2.layer == li_l else 0
            if not geom.overlaps(r2.rect, grown if sp else nr):
                continue
            if geom.overlaps(r2.rect, (must[0] - sp, must[1] - sp, must[2] + sp, must[3] + sp)):
                raise MoveError("add_finger: foreign %s at %s (%s) conflicts with the mirrored strap %s over our contacts (y %s..%s)"
                                % (inv_layers(tech).get(r2.layer, r2.layer), [round(v / 1000.0, 3) for v in r2.rect], r2.prov.split("/", 1)[1][:40],
                                   [round(v / 1000.0, 3) for v in nr], round(lic_lo / 1000.0, 3), round(lic_hi / 1000.0, 3)))
            if r2.rect[1] >= lic_hi:                       # beyond the contacts, above
                trim_hi = min(trim_hi if trim_hi is not None else 10**9, r2.rect[1] - sp)
            elif r2.rect[3] <= lic_lo:                     # beyond the contacts, below
                trim_lo = max(trim_lo if trim_lo is not None else -10**9, r2.rect[3] + sp)
    def clip_strap(r: Rect) -> Rect:
        y0 = max(r[1], min(trim_lo, lic_lo)) if trim_lo is not None else r[1]
        y1 = min(r[3], max(trim_hi, lic_hi)) if trim_hi is not None else r[3]
        return (r[0], y0, r[2], y1)
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
        if trim_lo is not None:
            y0 = max(y0, min(trim_lo, lic_lo))
        if trim_hi is not None:
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
                if not sources:                              # a strap clipped to its contact span: start at its centre
                    sources.append((0, xs_, (nr[1] + nr[3]) // 2))
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
            for tab in range(-1, nm(0.8) // step + 1):
                if tab < 0:
                    # centred on the finger: the narrowest head there is (cut + 2 enc), the
                    # one that fits between the fingers of a mirrored stack
                    lx0 = (gx0 + gx1) // 2 - cs // 2
                    head = (min(gx0, lx0 - enc_poly), hy0, max(gx1, lx0 + cs + enc_poly), hy1)
                else:
                    lx0 = gx1 + tab * step if tab else gx0                 # licon x0: on the finger, or on a tab to its right
                    if tab and lx0 < gx1:
                        continue
                    head = (gx0, hy0, lx0 + cs + enc_poly, hy1)
                licon = (lx0, (hy0 + hy1) // 2 - cs // 2, lx0 + cs, (hy0 + hy1) // 2 + cs // 2)
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
                    if os.environ.get("LAYOPT_PLAN_DEBUG") == "2" and tally.get("_dbgp", 0) < 8 and tab < 0 and (hy0 > g[3] + ext + sp_poly or hy1 < g[1] - ext - sp_poly):
                        tally["_dbgp"] = tally.get("_dbgp", 0) + 1
                        bi = idx.get(poly_l)
                        who = [(k, [round(v / 1000, 3) for v in bi.rects[k]], ex.nets[src2net[k]].name if k in src2net else "?") for k in bi.query_overlap((head[0] - sp_poly, head[1] - sp_poly, head[2] + sp_poly, head[3] + sp_poly)) if not own(k)]
                        print("      plan-debug: head %s stem %s blocked by poly %s" % ([round(v / 1000, 3) for v in head], stem and [round(v / 1000, 3) for v in stem], who[:3]))
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
