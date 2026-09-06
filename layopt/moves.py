# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""Topology-preserving geometry moves on a FlatLayout.

Every move edits rectangles in place (or adds some) and returns the list of
touched FlatRect indices, so the caller can re-extract, confirm the netlist
signature is unchanged, and rule-check only what moved.  Coordinates are dbu.
"""
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

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


def add_finger(fl: FlatLayout, ex: Extraction, dev: Device, side: str = "high") -> List[int]:
    """Add one parallel finger to `dev` on the `side` of its flow axis, by
    mirroring the existing gate + inner S/D column about the outer S/D region:

        [S][G][D]  ->  [S][G][D][G'][S']        (side="high", flow along x)

    The new outer S/D copies the inner S/D's contacts and strap (mirrored), so
    it connects the way the original does (a strap to the rail for a supply
    source); a poly bridge in the field beyond the diffusion ties G' to G.
    Diffusion, implant and well are extended.  New rects take the device's
    provenance -- the cell now extends into whatever was next to it (a
    filler, whitespace, or a neighbour: the rule check decides).  Only the
    standard-cell orientation (vertical gate, current along x) is implemented.
    Returns the added/changed rect ids; raises MoveError when the geometry
    around the device does not fit the pattern."""
    if dev.flow_axis != "x":
        raise MoveError("add_finger: only vertical gates (flow along x) are implemented")
    tech = ex.tech
    L = tech.layers
    inv = {v: k for k, v in L.items()}
    d = fl.dbu_um
    nm = lambda um: int(round(um / d))
    g = geom.bbox([ex.shapes[s].rect for s in dev.gate_ids])
    if len(dev.gate_ids) != 1:
        raise MoveError("add_finger: multi-finger device; add fingers to one finger at a time")
    hi = side == "high"
    # the diffusion rect holding this gate
    diff_ids = [i for i, r in enumerate(fl.rects) if r.layer == L[tech.diff] and geom.overlaps(r.rect, g)]
    if len(diff_ids) != 1:
        raise MoveError("add_finger: gate not on exactly one diffusion rect (%d)" % len(diff_ids))
    di = diff_ids[0]; D = fl.rects[di].rect
    outer = (g[2], D[2]) if hi else (D[0], g[0])          # x-range of the outer S/D region
    inner = (D[0], g[0]) if hi else (g[2], D[2])
    if outer[1] - outer[0] <= 0 or inner[1] - inner[0] <= 0:
        raise MoveError("add_finger: gate at the diffusion edge")
    xc = (outer[0] + outer[1]) / 2.0
    touched: List[int] = []
    ystrip = (g[1], g[3])
    def in_inner(r: Rect) -> bool:
        return r[0] >= inner[0] - 1 and r[2] <= inner[1] + 1 and r[3] > ystrip[0] and r[1] < ystrip[1]
    # inner S/D contacts and the strap(s) over them
    licon_l = L[tech.diff_contact]
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
    # 2. new gate finger: same x-width as the gate, mirrored; spans overhang to overhang
    ext = nm(tech.poly_ext_diff)
    gx0, gx1 = (mx(g[2]), mx(g[0]))
    # poly bridge location: just beyond the overhang on the side with field (no other diffusion/gate)
    bw = nm(max(tech.min_width.get(tech.poly, 0.15), 0.15))
    cand = [((g[1] - ext - bw), (g[1] - ext)), ((g[3] + ext), (g[3] + ext + bw))]
    bridge = None
    span_x = (min(g[0], gx0), max(g[2], gx1))
    for by0, by1 in cand:
        br = (span_x[0], by0, span_x[1], by1)
        blocked = False
        for r in fl.rects:
            if r.layer in (L[tech.diff], licon_l) and geom.overlaps(r.rect, br):
                blocked = True; break
            if r.layer == L[tech.poly] and geom.overlaps(r.rect, br):
                # poly of another net?  the device's own poly is fine
                sid = next((k for k, sh in enumerate(ex.shapes) if sh.src == fl.rects.index(r)), None)
                if sid is not None and ex.net_of_shape[sid] != dev.g:
                    blocked = True; break
        if not blocked:
            bridge = br; break
    if bridge is None:
        raise MoveError("add_finger: no field for the poly bridge on either side")
    fy0 = min(g[1] - ext, bridge[1]); fy1 = max(g[3] + ext, bridge[3])
    touched.append(add_rect_dbu(fl, L[tech.poly], (gx0, fy0, gx1, fy1), dev.prov))
    touched.append(add_rect_dbu(fl, L[tech.poly], bridge, dev.prov))
    # 3. mirrored contacts and strap(s)
    for k in inner_licons:
        touched.append(add_rect_dbu(fl, licon_l, mrect(fl.rects[k].rect), dev.prov))
    for k in inner_straps:
        touched.append(add_rect_dbu(fl, li_l, mrect(fl.rects[k].rect), dev.prov))
    # 4. implant and well cover the new diffusion
    D2 = fl.rects[di].rect
    imp = L[tech.psdm if dev.kind == "p" else tech.nsdm] if (tech.psdm and tech.nsdm) else None
    e = nm(tech.implant_enc)
    for i, r in enumerate(fl.rects):
        if imp is not None and r.layer == imp and geom.overlaps(r.rect, D):
            fl.rects[i].rect = (min(r.x0, D2[0] - e), r.y0, max(r.x1, D2[2] + e), r.y1); touched.append(i)
        if dev.kind == "p" and r.layer == L[tech.nwell] and geom.overlaps(r.rect, D):
            ew = nm(tech.nwell_enc)
            fl.rects[i].rect = (min(r.x0, D2[0] - ew), r.y0, max(r.x1, D2[2] + ew), r.y1); touched.append(i)
    return sorted(set(touched))


def add_rect_dbu(fl: FlatLayout, layer: Tuple[int, int], rect: Rect, prov: str) -> int:
    fl.rects.append(FlatRect(layer, (min(rect[0], rect[2]), min(rect[1], rect[3]), max(rect[0], rect[2]), max(rect[1], rect[3])), prov))
    return len(fl.rects) - 1
