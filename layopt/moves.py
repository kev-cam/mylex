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
                    grid_um: float = 0.005) -> List[int]:
    """Stretch a transistor along its W axis by editing its footprint: rects
    crossing the cut line at the gate's far W edge grow by dW; rects wholly
    beyond it shift by dW.  Works per finger (all fingers of the device grow
    by dW/fingers)."""
    d = fl.dbu_um
    g = max(1, int(round(grid_um / d)))
    fingers = max(1, dev.fingers)
    dw_total = snap((new_w_um - dev.w) / d, g)
    dw = snap(dw_total / fingers, g)
    if dw == 0:
        return []
    fp, ids = device_footprint(fl, ex, dev)
    own = {i for i in ids if fl.rects[i].prov == dev.prov}
    touched: List[int] = []
    # process fingers from the far end so shifts compose
    gates = sorted((ex.shapes[s].rect for s in dev.gate_ids),
                   key=lambda r: -(r[3] if dev.flow_axis == "x" else r[2]))
    for grect in gates:
        if dev.flow_axis == "x":            # W along y; cut at gate top edge
            cut = grect[3]
            for i in ids:
                x0, y0, x1, y1 = fl.rects[i].rect
                if not (x0 < fp[2] and x1 > fp[0]):
                    continue
                if y0 < cut < y1 or (y1 == cut and y0 < cut and _spans_gate(fl.rects[i].rect, grect, "x")):
                    fl.rects[i].rect = (x0, y0, x1, y1 + dw); touched.append(i)
                elif y0 >= cut and i in own:
                    fl.rects[i].rect = (x0, y0 + dw, x1, y1 + dw); touched.append(i)
        else:                               # W along x; cut at gate right edge
            cut = grect[2]
            for i in ids:
                x0, y0, x1, y1 = fl.rects[i].rect
                if not (y0 < fp[3] and y1 > fp[1]):
                    continue
                if x0 < cut < x1 or (x1 == cut and x0 < cut and _spans_gate(fl.rects[i].rect, grect, "y")):
                    fl.rects[i].rect = (x0, y0, x1 + dw, y1); touched.append(i)
                elif x0 >= cut and i in own:
                    fl.rects[i].rect = (x0 + dw, y0, x1 + dw, y1); touched.append(i)
    return sorted(set(touched))


def _spans_gate(r: Rect, g: Rect, flow: str) -> bool:
    """Rect shares the gate's W extent (diff / poly / li over the channel)."""
    if flow == "x":
        return r[1] <= g[1] and r[3] >= g[3]
    return r[0] <= g[0] and r[2] >= g[2]
