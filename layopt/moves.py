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


def add_finger(fl: FlatLayout, ex: Extraction, dev: Device, side: str = "high", bridge: str = "auto") -> List[int]:
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
    if prev is None:
        inner = (D[0], g[0]) if hi else (g[2], D[2])
    else:
        inner = (prev[2], g[0]) if hi else (g[2], prev[0])
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
    new_straps = []
    for k in inner_straps:
        new_straps.append((k, add_rect_dbu(fl, li_l, mrect(fl.rects[k].rect), dev.prov)))
        touched.append(new_straps[-1][1])
    # 3b. the new outer S/D must join the inner S/D's net.  A supply source
    # reaches it through the rail (the strap runs to the rail li, which continues
    # into the neighbour).  A signal net needs a jumper: mcon on both straps and a
    # met1 bar between them, at a height inside the gate's W range.
    inner_sid = next((q for q, sh in enumerate(ex.shapes) if sh.src == inner_licons[0]), None)
    inner_net = ex.net_of_shape[inner_sid] if inner_sid is not None else None
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
        # the jumper may sit anywhere along the strap (the mirrored strap has the same extent)
        y0, y1 = wide[1], wide[3]
        if y1 - y0 < cs:
            raise MoveError("add_finger: no room for the signal jumper on the strap")
        xa = (wide[0] + wide[2]) // 2
        xb = mx(xa)
        plan = _plan_sd_jumper(fl, ex, dev, inner_net, xa, xb, y0, y1, src2net, nm, L, tech)
        if plan is None:
            raise MoveError("add_finger: no legal S/D jumper (met1 bar, or met1 pads + via1 + met2 bar); heights rejected by: %s" % dict(LAST_JUMPER_TALLY))
        for layer, rect in plan:
            touched.append(add_rect_dbu(fl, layer, rect, dev.prov))
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
    return sorted(set(touched))


LAST_PLAN_TALLY: Dict[str, int] = {}
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
                continue
            return False
        return True
    gate_li = [(k, r.rect) for k, r in enumerate(fl.rects) if r.layer == li_l and own(k) and (r.x1 - r.x0) >= ms and geom.overlaps(r.rect, win)]
    if not gate_li:
        tally["no gate li pin in window"] = 1
        return None
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
                if not clear(diff_l, head, sp_diff, exclude_own=False):
                    tally["head vs diffusion"] = tally.get("head vs diffusion", 0) + 1; continue
                if not clear(poly_l, head, sp_poly):
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
                fx = (licon[0] + licon[2]) // 2
                for k, tr in sorted(gate_li, key=lambda kr: abs((kr[1][0] + kr[1][2]) // 2 - fx)):
                    y0 = max(pad[1] + ms // 2, tr[1] + ms // 2); y1 = min(pad[3] - ms // 2, tr[3] - ms // 2)
                    if y1 < y0:
                        tally["pad and gate pin do not share a height"] = tally.get("pad and gate pin do not share a height", 0) + 1; continue
                    tx = (tr[0] + tr[2]) // 2
                    bar_x = (min(fx, tx) - ms // 2 - enc_m1, max(fx, tx) + ms // 2 + enc_m1)
                    for jj in range(0, (y1 - y0) // step + 1):
                        yj = ((y0 + y1) // 2 + ((jj + 1) // 2) * step * (1 if jj % 2 else -1))
                        if yj < y0 or yj > y1:
                            continue
                        # met1 encloses the mcons by enc on two opposite sides: along the bar (x) is free
                        bar = (bar_x[0], yj - ms // 2, bar_x[1], yj + ms // 2)
                        m_new = [(fx - ms // 2, yj - ms // 2, fx + ms // 2, yj + ms // 2), (tx - ms // 2, yj - ms // 2, tx + ms // 2, yj + ms // 2)]
                        if not clear(m1, bar, sp_m1):
                            tally["met1 bar vs other met1"] = tally.get("met1 bar vs other met1", 0) + 1; continue
                        if not all(clear(mcon_l, m, sp_cut, exclude_own=False) for m in m_new):
                            tally["mcon vs cuts"] = tally.get("mcon vs cuts", 0) + 1; continue
                        return [(poly_l, head), (licon_l, licon), (li_l, pad), (mcon_l, m_new[0]), (mcon_l, m_new[1]), (m1, bar)]
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
    def heights():
        lo, hi_y = y0 + half, y1 - half
        for k in range(0, (hi_y - lo) // step + 1):
            y = ((lo + hi_y) // 2 + ((k + 1) // 2) * step * (1 if k % 2 else -1))
            if lo <= y <= hi_y:
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


def add_rect_dbu(fl: FlatLayout, layer: Tuple[int, int], rect: Rect, prov: str) -> int:
    fl.rects.append(FlatRect(layer, (min(rect[0], rect[2]), min(rect[1], rect[3]), max(rect[0], rect[2]), max(rect[1], rect[3])), prov))
    return len(fl.rects) - 1
