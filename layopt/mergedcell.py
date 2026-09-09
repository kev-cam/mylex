# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""A dissolved group of standard cells as one cell the router can use.

After `moves.merge_boundary` two abutting cells share a source/drain region
and the second has slid into the first; the pair is no longer two library
cells on legal sites, and a router working from LEF knows nothing about it.
`MergedCell.build` turns the group's flat geometry into a LEF MACRO -- the
two cells' pins in group coordinates (each renamed <inst>_<pin>; the supplies
merged into one pin each), every other li1/met1 shape an obstruction -- and
a GDS cell of the same name with the geometry itself; `rewrite_def` replaces
the two components by the macro, renames their pin references in NETS and
SPECIALNETS, and moves every other instance to where the dissolve left it.
Then: read_lef (tech, cells, merged) ; read_def ; route.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from . import gds as gdsmod, geom, lefdef
from .gds import FlatLayout, FlatRect
from .tech import Tech

LEF_LAYER = {"li": "li1", "met1": "met1", "met2": "met2", "met3": "met3", "met4": "met4", "met5": "met5"}
SUPPLY_PINS = ("VPWR", "VGND", "VPB", "VNB", "VDD", "VSS")


@dataclass
class MergedCell:
    name: str
    insts: List[str]                               # DEF instance names, left to right
    box: Tuple[int, int, int, int]                 # flat dbu
    pins: Dict[str, List[Tuple[str, Tuple[int, int, int, int]]]] = field(default_factory=dict)   # pin -> [(lef layer, rect dbu, macro-local)]
    pin_use: Dict[str, str] = field(default_factory=dict)
    obs: List[Tuple[str, Tuple[int, int, int, int]]] = field(default_factory=list)
    rects: List[FlatRect] = field(default_factory=list)          # macro-local geometry, all layers
    pin_map: Dict[Tuple[str, str], str] = field(default_factory=dict)   # (inst, pin) -> merged pin

    @staticmethod
    def build(fl: FlatLayout, lef: lefdef.Lef, tech: Tech, d: lefdef.Def, provs: Sequence[str], name: str) -> "MergedCell":
        """`provs`: the group's instance provenances in `fl` (design/inst/macro), whose
        geometry in `fl` is the dissolved one and whose `fl.boxes` are where they sit."""
        L = tech.layers
        inv = {v: k for k, v in L.items()}
        comps = {c.inst: c for c in d.components}
        insts = [p.split("/")[1] for p in provs]
        boxes = [fl.boxes[p] for p in provs]
        box = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
        ox, oy = box[0], box[1]
        mc = MergedCell(name, insts, box)
        pin_rects: Dict[Tuple[int, int], List[Tuple[int, int, int, int]]] = {}
        for prov, bx in zip(provs, boxes):
            inst = prov.split("/")[1]
            c = comps[inst]
            ref, off = lefdef.place_transform(lef, c.macro, c.orient, bx[0], bx[1])
            for pname, pin in lef.macros[c.macro].pins.items():
                merged_name = pname if pname in SUPPLY_PINS else "%s_%s" % (inst, pname)
                mc.pin_map[(inst, pname)] = merged_name
                mc.pin_use[merged_name] = pin.use
                mc.pins.setdefault(merged_name, [])
                for lname, (a, b, c2, e) in pin.ports:
                    # every port is kept (the well pins VPB/VNB sit on nwell/pwell); only
                    # routing-layer ports also carve holes in the obstructions
                    r = gdsmod._xrect((int(round(a * 1000)), int(round(b * 1000)), int(round(c2 * 1000)), int(round(e * 1000))), ref, off)
                    tl = {v: k for k, v in LEF_LAYER.items()}.get(lname)
                    if tl in L:
                        pin_rects.setdefault(L[tl], []).append(r)
                    mc.pins[merged_name].append((lname, (r[0] - ox, r[1] - oy, r[2] - ox, r[3] - oy)))
        # geometry: everything of the group, macro-local; obstructions: routing-layer shapes minus pin shapes
        provset = set(provs)
        for r in fl.rects:
            if r.prov not in provset or r.x1 <= r.x0 or r.y1 <= r.y0:
                continue
            mc.rects.append(FlatRect(r.layer, (r.x0 - ox, r.y0 - oy, r.x1 - ox, r.y1 - oy), name))
            ln = inv.get(r.layer)
            if ln in LEF_LAYER:
                holes = [h for h in pin_rects.get(r.layer, []) if geom.overlaps(h, r.rect)]
                for pc in (geom.subtract(r.rect, holes) if holes else [r.rect]):
                    if pc[2] > pc[0] and pc[3] > pc[1]:
                        mc.obs.append((LEF_LAYER[ln], (pc[0] - ox, pc[1] - oy, pc[2] - ox, pc[3] - oy)))
        return mc

    def lef_text(self, dbu_um: float = 0.001) -> str:
        f = lambda v: "%.3f" % (v * dbu_um)
        w, h = self.box[2] - self.box[0], self.box[3] - self.box[1]
        out = ["MACRO %s" % self.name, "  CLASS BLOCK ;", "  FOREIGN %s 0 0 ;" % self.name, "  ORIGIN 0 0 ;",
               "  SIZE %s BY %s ;" % (f(w), f(h)), "  SYMMETRY X Y ;"]
        for pname in sorted(self.pins):
            use = self.pin_use.get(pname, "SIGNAL")
            out.append("  PIN %s" % pname)
            out.append("    DIRECTION %s ;" % ("INOUT" if use in ("POWER", "GROUND") else "INPUT" if not pname.endswith(("_X", "_Y", "_Q", "_Q_N")) else "OUTPUT"))
            out.append("    USE %s ;" % use)
            if use in ("POWER", "GROUND"):
                out.append("    SHAPE ABUTMENT ;")
            out.append("    PORT")
            for lname, r in self.pins[pname]:
                out.append("      LAYER %s ;" % lname); out.append("        RECT %s %s %s %s ;" % tuple(f(v) for v in r))
            out.append("    END"); out.append("  END %s" % pname)
        if self.obs:
            out.append("  OBS")
            for lname in sorted({l for l, _ in self.obs}):
                out.append("    LAYER %s ;" % lname)
                for l2, r in self.obs:
                    if l2 == lname:
                        out.append("      RECT %s %s %s %s ;" % tuple(f(v) for v in r))
            out.append("  END")
        out.append("END %s" % self.name); out.append("")
        return "\n".join(out)

    def flat(self, dbu_um: float = 0.001) -> FlatLayout:
        fl = FlatLayout(dbu_um=dbu_um, top=self.name)
        fl.rects = list(self.rects)
        return fl


def lef_library(cells: Sequence[MergedCell], path: str, dbu_um: float = 0.001) -> None:
    with open(path, "w") as fh:
        fh.write("VERSION 5.7 ;\nBUSBITCHARS \"[]\" ;\nDIVIDERCHAR \"/\" ;\n\n")
        for mc in cells:
            fh.write(mc.lef_text(dbu_um) + "\n")
        fh.write("END LIBRARY\n")


def gds_library(cells: Sequence[MergedCell], path: str, dbu_um: float = 0.001) -> None:
    """One GDS with a structure per merged cell (write_flat writes one; several are concatenated by records)."""
    if len(cells) == 1:
        gdsmod.write_flat(cells[0].flat(dbu_um), path, name=cells[0].name); return
    import struct, time
    t = time.localtime()
    ts = struct.pack(">12h", t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec, t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
    R = gdsmod._rec
    out = [R(gdsmod.HEADER, 2, struct.pack(">h", 600)), R(gdsmod.BGNLIB, 2, ts), R(gdsmod.LIBNAME, 6, gdsmod._str("layopt")),
           R(gdsmod.UNITS, 5, gdsmod._to_real8(dbu_um) + gdsmod._to_real8(1e-9))]
    for mc in cells:
        out += [R(gdsmod.BGNSTR, 2, ts), R(gdsmod.STRNAME, 6, gdsmod._str(mc.name))]
        for r in mc.rects:
            x0, y0, x1, y1 = r.rect
            out += [R(gdsmod.BOUNDARY, 0), R(gdsmod.LAYER, 2, struct.pack(">h", r.layer[0])), R(gdsmod.DATATYPE, 2, struct.pack(">h", r.layer[1])),
                    R(gdsmod.XY, 3, struct.pack(">10i", x0, y0, x0, y1, x1, y1, x1, y0, x0, y0)), R(gdsmod.ENDEL, 0)]
        out.append(R(gdsmod.ENDSTR, 0))
    out.append(R(gdsmod.ENDLIB, 0))
    with open(path, "wb") as fh:
        fh.write(b"".join(out))


def rewrite_def(def_text: str, d: lefdef.Def, fl: FlatLayout, cells: Sequence[MergedCell], scale: float = 1.0) -> str:
    """The DEF with each merged group's components replaced by one FIXED
    instance of its macro, their pin references renamed, and every other
    placed instance at the x its `fl.boxes` entry now has (the dissolve slid
    the row).  `scale`: flat dbu per DEF unit (1 for 1 nm / 1000 per um).
    Works line by line: one statement per line, as OpenROAD writes DEF."""
    absorbed: Dict[str, MergedCell] = {inst: mc for mc in cells for inst in mc.insts}
    lines = def_text.split("\n")
    out = []
    in_comp = in_nets = False
    n_comp = sum(1 for c in d.components) - len(absorbed) + len(cells)
    boxes = {p.split("/")[1]: b for p, b in fl.boxes.items()}
    comp_re = re.compile(r"^(\s*-\s+)(\S+)(\s+\S+.*?\+\s+(?:PLACED|FIXED)\s+\(\s*)(-?\d+)(\s+)(-?\d+)(\s*\)\s*)(\S+)(\s*;)")
    pin_re = re.compile(r"\(\s*(\S+)\s+(\S+)\s*\)")
    for ln in lines:
        st = ln.strip()
        if st.startswith("COMPONENTS "):
            in_comp = True; out.append("COMPONENTS %d ;" % n_comp); continue
        if in_comp and st == "END COMPONENTS":
            for mc in cells:
                out.append("    - %s_i %s + FIXED ( %d %d ) N ;" % (mc.name, mc.name, int(round(mc.box[0] / scale)), int(round(mc.box[1] / scale))))
            in_comp = False; out.append(ln); continue
        if in_comp:
            m = comp_re.match(ln)
            if m:
                inst = m.group(2)
                if inst in absorbed:
                    continue
                if inst in boxes:
                    ln = "%s%s%s%d%s%d%s%s%s" % (m.group(1), inst, m.group(3), int(round(boxes[inst][0] / scale)), m.group(5), int(round(boxes[inst][1] / scale)), m.group(7), m.group(8), m.group(9))
            out.append(ln); continue
        if st.startswith("NETS ") or st.startswith("SPECIALNETS "):
            in_nets = True
        elif st.startswith("END NETS") or st.startswith("END SPECIALNETS"):
            in_nets = False
        if in_nets:
            def sub(mm):
                inst, pin = mm.group(1), mm.group(2)
                if inst in absorbed:
                    mc = absorbed[inst]
                    return "( %s_i %s )" % (mc.name, mc.pin_map.get((inst, pin), "%s_%s" % (inst, pin)))
                return mm.group(0)
            ln = pin_re.sub(sub, ln)
            # a supply pin now listed twice for one merged instance: keep one
            seen = set()
            def dedupe(mm):
                k = mm.group(0)
                if k in seen and any(k.endswith(" %s )" % s) for s in SUPPLY_PINS):
                    return ""
                seen.add(k); return k
            ln = pin_re.sub(dedupe, ln)
        out.append(ln)
    return "\n".join(out)
