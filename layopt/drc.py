# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""Minimal rule check for moved geometry: minimum width, same-layer spacing
between different nets, and cut enclosure.  Not a signoff DRC -- it is the
guard that keeps the optimizer's moves legal."""
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

    def __str__(self):
        return "%s %s: rect %d%s %.3f < %.3f um" % (self.rule, self.layer, self.a,
                                                     "" if self.b < 0 else " vs %d" % self.b,
                                                     self.value_um, self.limit_um)


def _gap(a: Rect, b: Rect) -> int:
    dx = max(a[0] - b[2], b[0] - a[2], 0)
    dy = max(a[1] - b[3], b[1] - a[3], 0)
    return max(dx, dy) if (dx == 0 or dy == 0) else int((dx * dx + dy * dy) ** 0.5)


def key(v: "Violation") -> Tuple:
    return (v.rule, v.layer, frozenset((v.a, v.b)))


def new_violations(fl: FlatLayout, ex: Extraction, changed: Sequence[int], baseline: Set[Tuple]) -> List[Violation]:
    """Violations among the changed rects that were not already present."""
    return [v for v in check(fl, ex, changed) if key(v) not in baseline]


def check(fl: FlatLayout, ex: Extraction, changed: Optional[Sequence[int]] = None) -> List[Violation]:
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
    by_layer: Dict[str, geom.BinIndex] = {}
    for i, r in enumerate(fl.rects):
        ln = inv.get(r.layer)
        if ln is None:
            continue
        by_layer.setdefault(ln, geom.BinIndex()).add(i, r.rect)
    for i in ids:
        r = fl.rects[i]
        ln = inv.get(r.layer)
        if ln is None:
            continue
        mw = tech.min_width.get(ln)
        if mw is not None and min(r.w, r.h) * d < mw - 1e-9:
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
                if ni == nj:
                    continue                       # same conductor (or no nets, e.g. wells): merge/notch, allowed
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
                grown = (c[0] - e, c[1] - e, c[2] + e, c[3] + e)
                cover = [fl.rects[k].rect for k in by_layer[ln].query_overlap(grown)]
                if geom.subtract(grown, cover):
                    out.append(Violation("enclosure", "%s/%s" % (metal, cut), i, j, 0.0, enc))
    return out
