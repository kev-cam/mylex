# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""The placer-side hand-off: which orientation each standard cell should take,
and which neighbours should abut, so that the post-layout boundary dissolve
(`moves.merge_boundary`) has boundaries to close.

A boundary between two abutting cells can be dissolved when the outer S/D
regions facing each other are on the same net; in a standard-cell row that
means a supply on both strips (signals never match across cells).  Mirroring
a cell swaps its faces, so per row a dynamic programme over the two
orientations of every cell maximises the strips matched across boundaries.
The placer that owns the row is the one to apply it: after its own detailed
placement and mirroring pass (`optimize_mirroring` in OpenROAD, which flips
for wire length), before routing.

    hints = plan_hints(def_path, lefs, gds_lib, tech)     # per instance
    write_json(hints, "hints.json"); write_openroad_tcl(hints, "hints.tcl")

The Tcl sets orientations, slides the chosen partner up against its
neighbour when the gap between them holds no other instance, and marks the
cells FIRM so a later legalisation leaves them.  What the router then pays
for the flips and the slides is the placer's cost of the policy; what the
dissolve gives back afterwards is measured by `moves.boundary_candidates`.
"""
from __future__ import annotations

import json
import os
import tempfile
from collections import defaultdict
from dataclasses import dataclass, asdict, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import extract, lefdef, moves as mv
from .tech import Tech

MIRROR = {"N": "FN", "FN": "N", "FS": "S", "S": "FS"}
DEF_TO_ODB = {"N": "R0", "FN": "MY", "FS": "MX", "S": "R180", "W": "R90", "E": "R270", "FW": "MXR90", "FE": "MYR90"}
FILLER_TAGS = ("fill", "tap", "decap")


@dataclass
class Hint:
    inst: str
    macro: str
    y: int                          # DEF units
    orient_now: str
    orient_pref: str
    x_now: int
    x_pref: int                     # after sliding into abutment (== x_now when not moved)
    partner_left: Optional[str] = None      # instance this one abuts on its left after the hints
    partner_right: Optional[str] = None
    strips_left: int = 0            # strips matched across the left boundary (0..2)
    strips_right: int = 0
    slide_left_um: float = 0.0      # what the dissolve of the left boundary would give back (measured; 0 if not)
    note: str = ""

    @property
    def flipped(self) -> bool:
        return self.orient_pref != self.orient_now

    @property
    def moved(self) -> bool:
        return self.x_pref != self.x_now


class Faces:
    """Outer S/D nets of each macro, by orientation, from layopt's extraction of the cell alone."""

    def __init__(self, lefs: Sequence[str], gds_lib: str, tech: Tech, cache_path: Optional[str] = None):
        self.lefs = list(lefs); self.gds_lib = gds_lib; self.tech = tech
        self._outer: Dict[str, Dict[str, Dict[str, Optional[str]]]] = {}
        self._slide: Dict[Tuple[str, str, str, str], Tuple[float, str, list]] = {}
        self.lef = lefdef.Lef()
        for f in self.lefs:
            lefdef.read_lef(f, self.lef)
        self.cache_path = cache_path          # measured pair slides persist here across runs
        if cache_path and os.path.exists(cache_path):
            try:
                for k, v in json.load(open(cache_path)).items():
                    self._slide[tuple(k.split("|"))] = (v[0], v[1], v[2])
            except (ValueError, OSError):
                pass

    def save_cache(self) -> None:
        if self.cache_path:
            with open(self.cache_path, "w") as fh:
                json.dump({"|".join(k): list(v) for k, v in self._slide.items()}, fh, indent=0)

    def layout_of(self, cells: Sequence[Tuple[str, float, str]]):
        w = sum(int(round(self.lef.macros[m].size[0] * 1000)) for m, _, _ in cells) + 4000
        comps = " ".join("- u%d %s + PLACED ( %d 0 ) %s ;" % (i, m, int(round(x * 1000)), o) for i, (m, x, o) in enumerate(cells))
        deftext = """VERSION 5.8 ; DESIGN c ; UNITS DISTANCE MICRONS 1000 ; DIEAREA ( 0 0 ) ( %d 2720 ) ;
COMPONENTS %d ; %s END COMPONENTS
SPECIALNETS 2 ; - VPWR %s + USE POWER ; - VGND %s + USE GROUND ; END SPECIALNETS
END DESIGN""" % (w, len(cells), comps, " ".join("( u%d VPWR )" % i for i in range(len(cells))), " ".join("( u%d VGND )" % i for i in range(len(cells))))
        with tempfile.TemporaryDirectory() as td:
            open(os.path.join(td, "c.def"), "w").write(deftext)
            return lefdef.def2flat(os.path.join(td, "c.def"), self.lefs, "", self.tech, gds_lib=self.gds_lib)

    def outer_nets(self, macro: str):
        """{'left': {kind: net name or None}, 'right': {...}} for the macro placed N."""
        if macro in self._outer:
            return self._outer[macro]
        fl = self.layout_of([(macro, 1.0, "N")])
        ex = extract.extract(fl, self.tech)
        inst = next(r.prov for r in fl.rects if "/u0/" in r.prov)
        _, box = mv._cell_box(fl, ex, inst)
        res = {}
        for side in ("left", "right"):
            regs = mv._outer_regions(fl, ex, inst, box, side)
            res[side] = {k: (ex.nets[v[3]].name if v is not None and v[3] is not None else None) for k, v in regs.items()}
        self._outer[macro] = res
        return res

    def faces(self, macro: str, orient: str):
        """(left nets, right nets) as {kind: name} in this orientation (a mirror swaps sides)."""
        o = self.outer_nets(macro)
        if orient in ("FN", "S"):
            return o["right"], o["left"]
        return o["left"], o["right"]

    def match(self, right_of_a, left_of_b) -> int:
        """strips matched across a boundary: both nets supplies and equal."""
        n = 0
        for k in ("p", "n"):
            a, b = right_of_a.get(k), left_of_b.get(k)
            if a is not None and a == b and a in self.tech.supply_names:
                n += 1
        return n

    def exact_slide(self, ma: str, oa: str, mb: str, ob: str) -> Tuple[float, str, list]:
        """(um the dissolve of a|b gives back, what bounds it, the shared nets), measured on a two-cell layout."""
        key = (ma, oa, mb, ob)
        if key in self._slide:
            return self._slide[key]
        wa = self.lef.macros[ma].size[0]; P = ma[:ma.rfind("__") + 2]
        # the guard fillers take the pair's vertical flip: an N filler's nwell overhangs its
        # box by 0.19 um and, beside a flipped cell, would land on that cell's NMOS strip
        fo = "FS" if oa in ("FS", "S") else "N"
        fl = self.layout_of([(P + "fill_4", 0.0, fo), (ma, 1.84, oa), (mb, 1.84 + wa, ob), (P + "fill_8", 1.84 + wa + self.lef.macros[mb].size[0], fo)])
        ex = extract.extract(fl, self.tech)
        a = next(r.prov for r in fl.rects if "/u1/" in r.prov); b = next(r.prov for r in fl.rects if "/u2/" in r.prov)
        try:
            d, lim, nets = mv._merge_plan(fl, ex, a, b)[:3]
        except mv.MoveError as e:
            d, lim, nets = 0, str(e)[:60], []
        self._slide[key] = (max(d, 0) / 1000.0, lim, list(nets))
        if self.cache_path and len(self._slide) % 10 == 0:
            self.save_cache()
        return self._slide[key]


def boundary_weight(faces: Faces, ma: str, oa: str, mb: str, ob: str, measure: bool, min_gain_um: float = 0.0) -> float:
    """What the boundary a|b in these orientations is worth: the strips matched
    (cheap), or with `measure` the um the dissolve gives back (a two-cell
    layout, cached) -- a matched boundary whose slide is bounded at zero by
    some other layer is then worth nothing, and not worth a flip or a move."""
    m = faces.match(faces.faces(ma, oa)[1], faces.faces(mb, ob)[0])
    if not m:
        return 0.0
    if not measure:
        return float(m)
    g = faces.exact_slide(ma, oa, mb, ob)[0]
    return g if g >= min_gain_um else 0.0


def row_policy(cells: Sequence[lefdef.DefComponent], faces: Faces, measure: bool = False, min_gain_um: float = 0.0) -> Tuple[List[str], float]:
    """Orientations (one per cell, in order) maximising the summed boundary
    weight of this run of cells, each cell N or its mirror; and the score.
    Ties keep the placer's orientation (a flip for nothing is a wire-length
    cost for nothing)."""
    if not cells:
        return [], 0.0
    opts = [(c.orient, MIRROR.get(c.orient, c.orient)) for c in cells]
    best: List[Dict[str, Tuple[float, Optional[str]]]] = [{o: (0.0, None) for o in opts[0]}]
    for i in range(1, len(cells)):
        cur = {}
        for o in opts[i]:
            cands = []
            for po, (score, _) in best[-1].items():
                w = boundary_weight(faces, cells[i - 1].macro, po, cells[i].macro, o, measure, min_gain_um)
                cands.append((score + w, po == cells[i - 1].orient, po))
            sc, _, po = max(cands)
            cur[o] = (sc, po)
        best.append(cur)
    o = max(best[-1], key=lambda k: (best[-1][k][0], k == cells[-1].orient))
    seq = [o]
    for i in range(len(cells) - 1, 0, -1):
        seq.append(best[i][seq[-1]][1])
    seq.reverse()
    return seq, best[-1][o][0]


def is_filler(macro: str) -> bool:
    return any(t in macro for t in FILLER_TAGS)


def plan_hints(def_path: str, lefs: Sequence[str], gds_lib: str, tech: Tech, abut: bool = True,
               measure: bool = False, faces: Optional[Faces] = None, max_move_um: float = 5.0,
               min_gain_um: float = 0.1) -> List[Hint]:
    """Hints for every logic cell of a placed DEF.  Rows are split into runs of
    logic cells with nothing else (a tap, a filler, a macro) between them; each
    run gets the flip policy; with `abut`, a cell whose left boundary matches
    slides left against its neighbour (cumulatively along the run) and both
    are marked as partners.  `measure` prices each matched boundary with the
    exact dissolve slide (a two-cell layout per macro pair and orientations;
    cached, minutes for a design's worth of pairs) and the policy then maximises
    micrometres given back rather than strips matched, so a boundary worth
    nothing costs no flip and no move.  A slide longer than `max_move_um` is not
    asked of the placer (wire length is its currency; the boundary stays
    unmatched in the hints and is reported in the note), nor is a boundary
    worth less than `min_gain_um` (with `measure`)."""
    F = faces or Faces(lefs, gds_lib, tech)
    d = lefdef.read_def(def_path)
    comps = [c for c in d.components if c.placed]
    width = {m: int(round(F.lef.macros[m].size[0] * d.dbu_per_um)) for m in {c.macro for c in comps} if m in F.lef.macros}
    height = {m: int(round(F.lef.macros[m].size[1] * d.dbu_per_um)) for m in width}
    rows: Dict[int, List[lefdef.DefComponent]] = defaultdict(list)
    for c in comps:
        rows[c.y].append(c)
    row_h = min(height.values()) if height else 0
    # instances placed at another y whose box still spans this row (multi-height cells, hard
    # macros, anything whose LEF is missing) break runs where they stand
    def spanning(y):
        out = []
        for c in comps:
            h = height.get(c.macro, 0)
            if c.y != y and h > row_h and c.y < y + row_h and c.y + h > y:
                out.append(c)
        return out
    hints: List[Hint] = []
    for y, cs in sorted(rows.items()):
        cs = sorted(cs + spanning(y), key=lambda c: c.x)
        runs: List[List[lefdef.DefComponent]] = [[]]
        for c in cs:
            if is_filler(c.macro) or c.macro not in width or c.y != y:
                if runs[-1]:
                    runs.append([])
                continue
            runs[-1].append(c)
        for run in runs:
            if not run:
                continue
            seq, _ = row_policy(run, F, measure, min_gain_um if measure else 0.0)
            hs = [Hint(c.inst, c.macro, y, c.orient, o, c.x, c.x) for c, o in zip(run, seq)]
            for i in range(1, len(run)):
                m = F.match(F.faces(run[i - 1].macro, seq[i - 1])[1], F.faces(run[i].macro, seq[i])[0])
                if not m:
                    continue
                a, b = hs[i - 1], hs[i]
                slide = F.exact_slide(run[i - 1].macro, seq[i - 1], run[i].macro, seq[i])[0] if measure else 0.0
                if measure and slide < min_gain_um:
                    continue                    # matched but worth (nearly) nothing: leave the placer alone
                a.strips_right = b.strips_left = m
                b.slide_left_um = slide
                if abut:
                    # the gap between them holds no instance (runs have none), so b slides left
                    x_abut = a.x_pref + width[a.macro]
                    if x_abut > b.x_now:
                        x_abut = b.x_now            # never move right: that could reach the next cell
                    if (b.x_now - x_abut) / d.dbu_per_um > max_move_um:
                        b.note = "abutment with %s would move it %.2f um for %.3f um; not asked" % (a.inst, (b.x_now - x_abut) / d.dbu_per_um, slide)
                        b.strips_left = a.strips_right = 0; b.slide_left_um = 0.0
                        continue
                    b.x_pref = x_abut
                    a.partner_right = b.inst; b.partner_left = a.inst
            # a flip that serves no kept boundary is undone (a flip is free to us, not to the wires)
            for i, h in enumerate(hs):
                if h.flipped and not (h.strips_left or h.strips_right):
                    h.orient_pref = h.orient_now
            hints += hs
    F.save_cache()
    return hints


def write_json(hints: Sequence[Hint], path: str) -> None:
    with open(path, "w") as fh:
        json.dump([asdict(h) for h in hints], fh, indent=1)


def read_json(path: str) -> List[Hint]:
    return [Hint(**h) for h in json.load(open(path))]


def write_openroad_tcl(hints: Sequence[Hint], path: str, firm: bool = True) -> int:
    """An OpenROAD script applying the hints through odb: setOrient for a flip,
    setLocation for a slide, placement status FIRM on both so a later
    legalisation leaves them.  Source it after detailed placement and
    `optimize_mirroring`, before routing.  Returns the number of cells touched."""
    n = 0
    lines = ["# layopt placer hints: flips and abutments for the boundary dissolve (layopt/placer.py)",
             "set __blk [ord::get_db_block]"]
    for h in hints:
        if not (h.flipped or h.moved or h.partner_right):
            continue
        n += 1
        lines.append("set __i [$__blk findInst {%s}]" % h.inst)
        lines.append('if {$__i == "NULL"} { puts "layopt hints: no instance %s" } else {' % h.inst)     # a stale name skips its own block only
        if h.flipped:
            lines.append("  $__i setOrient %s" % DEF_TO_ODB.get(h.orient_pref, h.orient_pref))
        # odb keeps the cell ORIGIN on setOrient, so a mirrored cell's box moves by its
        # width; setLocation places the box's lower-left, so it follows every flip too
        if h.flipped or h.moved:
            lines.append("  $__i setLocation %d %d" % (h.x_pref, h.y))
        if firm:
            lines.append("  $__i setPlacementStatus FIRM")
        lines.append("}")
        tags = []
        if h.flipped:
            tags.append("flip %s->%s" % (h.orient_now, h.orient_pref))
        if h.moved:
            tags.append("slide %.3f um left to abut %s" % ((h.x_now - h.x_pref) / 1000.0, h.partner_left))
        if h.partner_right and not h.moved:
            tags.append("%s abuts on its right" % h.partner_right)
        lines.append("# " + ", ".join(tags))
    lines.append('puts "layopt hints: %d cells flipped, moved or held"' % n)
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return n


def summary(hints: Sequence[Hint]) -> Dict[str, float]:
    return {"cells": len(hints), "flipped": sum(1 for h in hints if h.flipped), "moved": sum(1 for h in hints if h.moved),
            "boundaries": sum(1 for h in hints if h.strips_left), "strips_2": sum(1 for h in hints if h.strips_left == 2),
            "strips_1": sum(1 for h in hints if h.strips_left == 1), "slide_um": round(sum(h.slide_left_um for h in hints), 3),
            "moved_um": round(sum(h.x_now - h.x_pref for h in hints) / 1000.0, 3)}
