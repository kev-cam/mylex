# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""Minimal rule check for moved geometry: minimum width, same-layer spacing
between different nets, same-net notches, and cut enclosure.  Not a signoff
DRC -- it is the guard that keeps the optimizer's moves legal."""
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Set, Tuple

from . import geom
from .extract import Extraction
from .gds import FlatLayout

Rect = Tuple[int, int, int, int]


@dataclass
class Violation:
    rule: str
    layer: str
    a: int
    b: int
    value_um: float
    limit_um: float
    ra: Optional[Rect] = None          # geometry of a and b: the baseline key survives id shifts
    rb: Optional[Rect] = None

    def __str__(self):
        return "%s %s: rect %d%s %.3f < %.3f um" % (self.rule, self.layer, self.a,
                                                     "" if self.b < 0 else " vs %d" % self.b,
                                                     self.value_um, self.limit_um)


def _gap(a: Rect, b: Rect) -> int:
    dx = max(a[0] - b[2], b[0] - a[2], 0)
    dy = max(a[1] - b[3], b[1] - a[3], 0)
    return max(dx, dy) if (dx == 0 or dy == 0) else int((dx * dx + dy * dy) ** 0.5)


def _shares_edge(a: Rect, b: Rect) -> bool:
    """Closed contact along an edge segment of positive length (not a corner)."""
    x_over = min(a[2], b[2]) - max(a[0], b[0])
    y_over = min(a[3], b[3]) - max(a[1], b[1])
    if x_over > 0 and (a[3] == b[1] or b[3] == a[1]):
        return True
    if y_over > 0 and (a[2] == b[0] or b[2] == a[0]):
        return True
    return False


def _gap_rect(a: Rect, b: Rect) -> Optional[Rect]:
    """The rectangle between two disjoint rectangles: the span they face each
    other across (facing edges), or the corner square when they are diagonal.
    None when the region is degenerate (a point)."""
    x_lo, x_hi = min(a[2], b[2]), max(a[0], b[0])       # x gap: from the left one's right edge to the right one's left edge
    y_lo, y_hi = min(a[3], b[3]), max(a[1], b[1])
    dx = x_hi - x_lo; dy = y_hi - y_lo
    if dx > 0 and dy <= 0:                                # side by side, overlapping in y
        y0, y1 = max(a[1], b[1]), min(a[3], b[3])
        return (x_lo, y0, x_hi, y1) if y1 > y0 else None
    if dy > 0 and dx <= 0:                                # one above the other, overlapping in x
        x0, x1 = max(a[0], b[0]), min(a[2], b[2])
        return (x0, y_lo, x1, y_hi) if x1 > x0 else None
    if dx > 0 and dy > 0:                                 # diagonal: the corner square
        return (x_lo, y_lo, x_hi, y_hi)
    return None


def key(v: "Violation") -> Tuple:
    """Identity of a violation for the delta: rule, layer and the geometry of
    the rects involved (not their ids -- a move that deletes rects shifts ids,
    and a baseline keyed by id would then call every old flag new)."""
    return (v.rule, v.layer, frozenset(x for x in (v.ra, v.rb) if x is not None))


def new_violations(fl: FlatLayout, ex: Extraction, changed: Sequence[int], baseline: Set[Tuple]) -> List[Violation]:
    """Violations among the changed rects that were not already present."""
    return [v for v in check(fl, ex, changed) if key(v) not in baseline]


def check(fl: FlatLayout, ex: Extraction, changed: Optional[Sequence[int]] = None) -> List[Violation]:
    out = _check(fl, ex, changed) + _check_vt(fl, ex, changed)
    for v in out:
        v.ra = fl.rects[v.a].rect if v.a >= 0 else None
        v.rb = fl.rects[v.b].rect if v.b >= 0 else None
    return out


def _check(fl: FlatLayout, ex: Extraction, changed: Optional[Sequence[int]] = None) -> List[Violation]:
    tech = ex.tech
    inv = {v: k for k, v in tech.layers.items()}
    d = fl.dbu_um
    out: List[Violation] = []
    # nets carried by each FlatRect (a diffusion rect carries several: S, D, gate regions)
    net_of_src: Dict[int, frozenset] = {}
    tmp: Dict[int, Set[int]] = {}
    for sid, sh in enumerate(ex.shapes):
        if sh.src >= 0:
            tmp.setdefault(sh.src, set()).add(ex.net_of_shape[sid])
    net_of_src = {k: frozenset(v) for k, v in tmp.items()}
    ids = list(range(len(fl.rects))) if changed is None else list(changed)
    cut_layers = {cut for _, cut, _ in tech.vias} | {tech.diff_contact}      # spacing applies regardless of net
    by_layer: Dict[str, geom.BinIndex] = {}
    for i, r in enumerate(fl.rects):
        ln = inv.get(r.layer)
        if ln is None:
            continue
        by_layer.setdefault(ln, geom.BinIndex()).add(i, r.rect)
    for i in ids:
        r = fl.rects[i]
        ln = inv.get(r.layer)
        if ln is None or r.w <= 0 or r.h <= 0:          # (a degenerate rect is a removed one)
            continue
        mw = tech.min_width.get(ln)
        if mw is not None and min(r.w, r.h) * d < mw - 1e-9:
            # a thin rectangle is legal if it is part of wider merged geometry:
            # widen it to min width toward either edge and see if same-layer
            # rectangles cover that (the stock cells store T-shapes as slabs)
            m = int(round(mw / d))
            if r.w < r.h:
                cands = [(r.x0, r.y0, r.x0 + m, r.y1), (r.x1 - m, r.y0, r.x1, r.y1)]
            else:
                cands = [(r.x0, r.y0, r.x1, r.y0 + m), (r.x0, r.y1 - m, r.x1, r.y1)]
            covered = False
            for c in cands:
                cover = [fl.rects[k].rect for k in by_layer[ln].query_overlap(c)]
                if not geom.subtract(c, cover):
                    covered = True; break
            if not covered:
                out.append(Violation("min_width", ln, i, -1, min(r.w, r.h) * d, mw))
        ms = tech.min_space.get(ln)
        if ms is not None:
            s = int(round(ms / d))
            probe = (r.x0 - s, r.y0 - s, r.x1 + s, r.y1 + s)
            for j in by_layer[ln].query_overlap(probe):
                if j == i:
                    continue
                o = fl.rects[j]
                ni, nj = net_of_src.get(i, frozenset()), net_of_src.get(j, frozenset())
                is_cut = ln in cut_layers
                if ni == nj and not is_cut:
                    if not ni:
                        continue                   # no nets (wells, implants): merging is allowed
                    # Same net.  Overlapping or edge-sharing rectangles merge into
                    # one polygon and cannot violate spacing between themselves.
                    # Two parts of the same net that do not touch and lie closer
                    # than spacing form a notch -- unless the gap between them is
                    # filled by other same-layer geometry (a slab decomposition of
                    # one polygon, a wire landing on a pad beside its route).
                    if geom.overlaps(r.rect, o.rect) or _shares_edge(r.rect, o.rect):
                        continue
                    gap = _gap(r.rect, o.rect)
                    if gap >= s:
                        continue
                    hole = _gap_rect(r.rect, o.rect)
                    if hole is None:
                        continue                   # corner-to-corner touch: no facing edges
                    cover = [fl.rects[k].rect for k in by_layer[ln].query_overlap(hole)]
                    if geom.subtract(hole, cover):
                        out.append(Violation("min_space", ln, i, j, gap * d, ms))
                    continue
                if is_cut and r.rect == o.rect:
                    continue                       # an identical duplicate cut is the same cut
                if not is_cut and (geom.overlaps(r.rect, o.rect) or _shares_edge(r.rect, o.rect)):
                    continue                       # one merged shape (a diffusion drawn as two slabs carries
                                                   # several nets; the extractor merged them, so does DRC)
                if geom.touches(r.rect, o.rect):
                    out.append(Violation("min_space", ln, i, j, 0.0, ms)); continue
                gap = _gap(r.rect, o.rect)
                if gap < s:
                    out.append(Violation("min_space", ln, i, j, gap * d, ms))
        # enclosure of cuts by the union of same-layer metal around each cut
        for (metal, cut), enc in tech.enclosure.items():
            if metal != ln or cut not in by_layer:
                continue
            e = int(round(enc / d))
            for j in by_layer[cut].query_overlap(r.rect):
                c = fl.rects[j].rect
                cover = [fl.rects[k].rect for k in by_layer[ln].query_overlap((c[0] - e, c[1] - e, c[2] + e, c[3] + e))]
                # sky130-style enclosure: the cut must be covered, and enclosed by `enc`
                # on at least two sides (the stock cells use adjacent sides: e.g. a
                # licon 0.085 left / 0.09 below, 0.075 right / 0.04 above).
                covered = not geom.subtract(c, cover)
                if e > 0:
                    sides = [not geom.subtract(r_, cover) for r_ in ((c[0] - e, c[1], c[0], c[3]), (c[2], c[1], c[2] + e, c[3]),
                                                                     (c[0], c[1] - e, c[2], c[1]), (c[0], c[3], c[2], c[3] + e))]
                else:
                    sides = [True, True]                    # zero enclosure: coverage is the whole rule
                if not (covered and sum(sides) >= 2):
                    out.append(Violation("enclosure", "%s/%s" % (metal, cut), i, j, 0.0, enc))
    return out


def _check_vt(fl: FlatLayout, ex: Extraction, changed: Optional[Sequence[int]] = None) -> List[Violation]:
    """Vt implants: a gate of the flavour's polarity that an implant rect
    touches must be enclosed by it by gate_enc on every side (a partly covered
    gate is a different device on each side of the edge); a gate it does not
    touch must keep gate_enc clear of it.  Checked for implant rects among
    `changed` (or all), against every gate in the extraction."""
    tech = ex.tech
    if not tech.vt:
        return []
    inv = {v: k for k, v in tech.layers.items()}
    d = fl.dbu_um
    out: List[Violation] = []
    gates = [(i, sh) for i, sh in enumerate(ex.shapes) if sh.layer == "gate"]
    gate_kind = {}
    for dv in ex.devices:
        for gs in dv.gate_ids:
            gate_kind[gs] = dv.kind
    gidx = geom.BinIndex()
    for i, sh in gates:
        gidx.add(i, sh.rect)
    ids = range(len(fl.rects)) if changed is None else changed
    for i in ids:
        r = fl.rects[i]
        ln = inv.get(r.layer)
        fl_ = next((f for f in tech.vt.values() if f.layer == ln), None)
        if fl_ is None or r.w <= 0 or r.h <= 0:
            continue
        e = int(round(fl_.gate_enc / d))
        probe = (r.x0 - e, r.y0 - e, r.x1 + e, r.y1 + e)
        for gi in gidx.query_overlap(probe):
            if gate_kind.get(gi) != fl_.kind:
                continue
            g = ex.shapes[gi].rect
            if geom.overlaps(g, r.rect):
                inside = g[0] - r.x0 >= e and g[1] - r.y0 >= e and r.x1 - g[2] >= e and r.y1 - g[3] >= e
                if not inside:
                    out.append(Violation("enclosure", "%s/gate" % ln, i, -1, min(g[0] - r.x0, g[1] - r.y0, r.x1 - g[2], r.y1 - g[3]) * d, fl_.gate_enc))
            else:
                out.append(Violation("min_space", "%s/gate" % ln, i, -1, _gap(g, r.rect) * d, fl_.gate_enc))
    return out
