# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""LEF/DEF -> FlatLayout: the standard-cell entry point ("def2flat").

Reads a tech LEF (layer widths, VIA geometry, SITE), cell LEFs (MACRO size,
pins), and a DEF (components with placement/orientation, routed nets, special
nets, pins).  Every component's GDS is flattened in place with provenance
`top/<inst>/<macro>`; routing becomes rectangles with provenance
`top/net:<name>`; each net gets a label so extraction names it.  The result is
the same FlatLayout the rest of layopt works on -- the cell boundary survives
only as provenance.
"""
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from . import gds
from .gds import FlatLayout, FlatRect, FlatText, Ref
from .tech import Tech

Rect = Tuple[int, int, int, int]


@dataclass
class LefLayer:
    name: str
    kind: str                    # ROUTING | CUT | MASTERSLICE | ...
    width_um: float = 0.0
    direction: str = ""


@dataclass
class LefVia:
    name: str
    rects: List[Tuple[str, Tuple[float, float, float, float]]] = field(default_factory=list)   # (layer, rect um)


@dataclass
class LefPin:
    name: str
    use: str = "SIGNAL"
    ports: List[Tuple[str, Tuple[float, float, float, float]]] = field(default_factory=list)


@dataclass
class LefMacro:
    name: str
    size: Tuple[float, float] = (0.0, 0.0)
    origin: Tuple[float, float] = (0.0, 0.0)
    pins: Dict[str, LefPin] = field(default_factory=dict)


@dataclass
class Lef:
    layers: Dict[str, LefLayer] = field(default_factory=dict)
    vias: Dict[str, LefVia] = field(default_factory=dict)
    macros: Dict[str, LefMacro] = field(default_factory=dict)
    sites: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    dbu_per_um: int = 1000


def _tokens(text: str):
    text = re.sub(r"#.*", "", text)
    return text.replace(";", " ; ").split()


def read_lef(path: str, lef: Optional[Lef] = None) -> Lef:
    lef = lef or Lef()
    t = _tokens(open(path).read())
    i, n = 0, len(t)

    def stmt(j):                     # tokens of statement starting at j up to ';'
        k = j
        while k < n and t[k] != ";":
            k += 1
        return t[j:k], k + 1

    skip_blocks = {"PROPERTYDEFINITIONS", "VIARULE", "NONDEFAULTRULE", "SPACING", "IRDROP", "NOISETABLE"}
    while i < n:
        tok = t[i]
        if tok in skip_blocks:                     # END <keyword> or END <name>
            name = t[i + 1] if tok in ("VIARULE", "NONDEFAULTRULE") else tok
            i += 1
            while i < n and not (t[i] == "END" and t[i + 1] == name):
                i += 1
            i += 2
        elif tok == "UNITS":
            while t[i] != "END" or t[i + 1] != "UNITS":
                if t[i] == "DATABASE" and t[i + 1] == "MICRONS":
                    lef.dbu_per_um = int(float(t[i + 2]))
                i += 1
            i += 2
        elif tok == "LAYER":
            name = t[i + 1]; i += 2
            L = LefLayer(name, "")
            while not (t[i] == "END" and t[i + 1] == name):
                s, i = stmt(i)
                if not s:
                    continue
                if s[0] == "TYPE": L.kind = s[1]
                elif s[0] == "WIDTH": L.width_um = float(s[1])
                elif s[0] == "DIRECTION": L.direction = s[1]
            lef.layers[name] = L; i += 2
        elif tok == "VIA":
            name = t[i + 1]; i += 2
            V = LefVia(name); cur = None
            while not (t[i] == "END" and t[i + 1] == name):
                s, i = stmt(i)
                if s and s[0] == "DEFAULT":          # `VIA name DEFAULT` shares the first statement
                    s = s[1:]
                if not s:
                    continue
                if s[0] == "LAYER": cur = s[1]
                elif s[0] == "RECT" and cur:
                    V.rects.append((cur, tuple(float(v) for v in s[1:5])))
            lef.vias[name] = V; i += 2
        elif tok == "SITE" and i + 2 < n and t[i + 2] != ";":
            name = t[i + 1]; i += 2
            while not (t[i] == "END" and t[i + 1] == name):
                s, i = stmt(i)
                if s and s[0] == "SIZE":
                    lef.sites[name] = (float(s[1]), float(s[3]))
            i += 2
        elif tok == "MACRO":
            name = t[i + 1]; i += 2
            M = LefMacro(name)
            while not (t[i] == "END" and t[i + 1] == name):
                if t[i] == "PIN":
                    pname = t[i + 1]; i += 2
                    P = LefPin(pname); cur = None
                    while not (t[i] == "END" and t[i + 1] == pname):
                        if t[i] in ("PORT", "END"):
                            i += 1; continue
                        s, i = stmt(i)
                        if not s:
                            continue
                        if s[0] == "USE": P.use = s[1]
                        elif s[0] == "LAYER": cur = s[1]
                        elif s[0] == "RECT" and cur:
                            P.ports.append((cur, tuple(float(v) for v in s[1:5])))
                    M.pins[pname] = P; i += 2
                elif t[i] == "OBS":
                    while t[i] != "END":
                        i += 1
                    i += 1
                else:
                    s, i = stmt(i)
                    if not s:
                        continue
                    if s[0] == "SIZE": M.size = (float(s[1]), float(s[3]))
                    elif s[0] == "ORIGIN": M.origin = (float(s[1]), float(s[2]))
            lef.macros[name] = M; i += 2
        else:
            i += 1
    return lef


@dataclass
class DefComponent:
    inst: str
    macro: str
    x: int = 0                    # DEF units
    y: int = 0
    orient: str = "N"
    placed: bool = False


@dataclass
class DefWire:
    layer: str
    width: int                    # 0 -> layer default
    points: List[Tuple[int, int]]
    via: Optional[str] = None     # via placed at the last point


@dataclass
class DefNet:
    name: str
    pins: List[Tuple[str, str]] = field(default_factory=list)   # (inst | 'PIN', pin)
    wires: List[DefWire] = field(default_factory=list)
    special: bool = False


@dataclass
class DefPin:
    name: str
    net: str
    layer: str = ""
    rect: Optional[Tuple[int, int, int, int]] = None      # DEF units, absolute
    use: str = "SIGNAL"


@dataclass
class Def:
    design: str = "top"
    dbu_per_um: int = 1000
    diearea: Optional[Tuple[int, int, int, int]] = None
    components: List[DefComponent] = field(default_factory=list)
    nets: List[DefNet] = field(default_factory=list)
    pins: List[DefPin] = field(default_factory=list)


def read_def(path: str) -> Def:
    d = Def()
    t = _tokens(open(path).read())
    i, n = 0, len(t)
    while i < n:
        tok = t[i]
        if tok == "END":
            i += 2
        elif tok == "DESIGN":
            d.design = t[i + 1]; i += 3
        elif tok == "UNITS":
            d.dbu_per_um = int(float(t[i + 3])); i += 5
        elif tok == "DIEAREA":
            nums = []
            j = i + 1
            while t[j] != ";":
                if t[j] not in "()":
                    nums.append(int(float(t[j])))
                j += 1
            d.diearea = (min(nums[0::2]), min(nums[1::2]), max(nums[0::2]), max(nums[1::2])); i = j + 1
        elif tok == "COMPONENTS":
            i += 3
            while t[i] != "END":
                assert t[i] == "-", t[i]
                c = DefComponent(t[i + 1], t[i + 2]); i += 3
                while t[i] != ";":
                    if t[i] == "+" and t[i + 1] in ("PLACED", "FIXED"):
                        c.x, c.y = int(float(t[i + 3])), int(float(t[i + 4])); c.orient = t[i + 6]
                        c.placed = True; i += 7
                    else:
                        i += 1
                d.components.append(c); i += 1
            i += 2
        elif tok == "PINS":
            i += 3
            while t[i] != "END":
                p = DefPin(t[i + 1], ""); i += 2
                lay = None; rect = None; loc = None
                while t[i] != ";":
                    if t[i] == "+" and t[i + 1] == "NET": p.net = t[i + 2]; i += 3
                    elif t[i] == "+" and t[i + 1] == "USE": p.use = t[i + 2]; i += 3
                    elif t[i] == "+" and t[i + 1] == "LAYER":
                        lay = t[i + 2]
                        nums = [int(float(v)) for v in (t[i + 4], t[i + 5], t[i + 8], t[i + 9])]
                        rect = (nums[0], nums[1], nums[2], nums[3]); i += 11
                    elif t[i] == "+" and t[i + 1] in ("PLACED", "FIXED"):
                        loc = (int(float(t[i + 3])), int(float(t[i + 4]))); i += 7
                    else:
                        i += 1
                if lay and rect and loc:
                    p.layer = lay
                    p.rect = (loc[0] + rect[0], loc[1] + rect[1], loc[0] + rect[2], loc[1] + rect[3])
                d.pins.append(p); i += 1
            i += 2
        elif tok in ("NETS", "SPECIALNETS"):
            special = tok == "SPECIALNETS"
            i += 3
            while t[i] != "END":
                assert t[i] == "-", t[i]
                net = DefNet(t[i + 1], special=special); i += 2
                while t[i] != ";":
                    if t[i] == "(":
                        net.pins.append((t[i + 1], t[i + 2])); i += 4
                    elif t[i] == "+" and t[i + 1] in ("ROUTED", "FIXED", "COVER"):
                        i += 2
                        i = _parse_wires(t, i, net, special)
                    else:
                        i += 1
                d.nets.append(net); i += 1
            i += 2
        else:
            i += 1
    return d


def _parse_wires(t, i, net: DefNet, special: bool) -> int:
    """Parse `layer [width] (x y) (x y|*) ... [via] NEW layer ...` until ';' or '+'."""
    while t[i] not in (";", "+"):
        if t[i] == "NEW":
            i += 1
        layer = t[i]; i += 1
        width = 0
        if special or re.match(r"^\d", t[i]):
            if re.match(r"^\d", t[i]):
                width = int(float(t[i])); i += 1
        while t[i] == "+" and t[i + 1] in ("SHAPE", "STYLE", "MASK"):
            i += 3
        pts: List[Tuple[int, int]] = []
        via = None
        while i < len(t) and t[i] == "(":
            x = t[i + 1]; y = t[i + 2]
            px, py = pts[-1] if pts else (0, 0)
            xv = px if x == "*" else int(float(x)); yv = py if y == "*" else int(float(y))
            j = i + 3
            if t[j] not in ")":           # optional extension value
                j += 1
            i = j + 1
            pts.append((xv, yv))
            if i < len(t) and t[i] not in ("(", "NEW", ";", "+") and not t[i][0].isdigit():
                via = t[i]; i += 1
                net.wires.append(DefWire(layer, width, list(pts), via)); pts = [pts[-1]]; via = None
        if len(pts) >= 1:
            net.wires.append(DefWire(layer, width, pts, None))
    return i


ORIENT = {"N": (False, 0), "W": (False, 90), "S": (False, 180), "E": (False, 270),
          "FS": (True, 0), "FW": (True, 90), "FN": (True, 180), "FE": (True, 270)}


def def2flat(def_path: str, lef_paths: List[str], gds_dir: str, tech: Tech,
             gds_name: Optional[str] = None, gds_lib: Optional[str] = None) -> FlatLayout:
    """Build the flat layout of a placed-and-routed DEF.  Cell geometry comes
    from gds_dir/<macro>.gds (or gds_name(macro) -> path), or, when gds_lib is
    given, from that one merged GDS library holding every macro as a cell."""
    lef = Lef()
    for p in lef_paths:
        read_lef(p, lef)
    d = read_def(def_path)
    dbu = 1.0 / tech.grid_um if False else 0.001                    # FlatLayout in 1 nm
    scale = 1000.0 / d.dbu_per_um                                    # DEF units -> nm
    fl = FlatLayout(dbu_um=0.001, top=d.design)
    L = tech.layers
    lef2tech = {"li1": "li", "met1": "met1", "met2": "met2", "met3": "met3", "met4": "met4", "met5": "met5",
                "mcon": "mcon", "via": "via1", "via2": "via2", "via3": "via3", "via4": "via4",
                "poly": "poly", "nwell": "nwell", "pwell": None}
    libs: Dict[str, gds.Library] = {}
    merged = gds.read(gds_lib) if gds_lib else None
    flat_cache: Dict[str, FlatLayout] = {}

    def cell_lib(macro: str) -> gds.Library:
        if merged is not None:
            return merged
        if macro not in libs:
            path = gds_name(macro) if gds_name else os.path.join(gds_dir, macro + ".gds")
            libs[macro] = gds.read(path)
        return libs[macro]

    def cell_flat(macro: str) -> FlatLayout:
        if macro not in flat_cache:
            lib = cell_lib(macro)
            flat_cache[macro] = gds.flatten(lib, top=macro if merged is not None else None)
        return flat_cache[macro]

    # --- components: flatten each cell GDS under its placement transform ---
    for c in d.components:
        if not c.placed:
            continue
        sub = cell_flat(c.macro)                                  # cell-local nm coordinates
        m = lef.macros.get(c.macro)
        w_nm, h_nm = (int(round(m.size[0] * 1000)), int(round(m.size[1] * 1000))) if m else (0, 0)
        mirror, angle = ORIENT[c.orient]
        ref = Ref(c.macro, (0, 0), mirror_x=mirror, angle=angle)
        # placement point is the lower-left of the ORIENTED cell box
        corners = [gds._xform(p, ref, (0, 0)) for p in ((0, 0), (w_nm, 0), (0, h_nm), (w_nm, h_nm))]
        llx, lly = min(p[0] for p in corners), min(p[1] for p in corners)
        off = (int(round(c.x * scale)) - llx, int(round(c.y * scale)) - lly)
        prov = "%s/%s/%s" % (d.design, c.inst, c.macro)
        for r in sub.rects:
            fl.rects.append(FlatRect(r.layer, gds._xrect(r.rect, ref, off), prov))
        for tx in sub.texts:                                      # keep cell pin labels? no: they would name
            pass                                                  # every cell's A/Y alike; DEF nets name them
    # --- routing ---
    def wire_rects(w: DefWire) -> List[Tuple[str, Rect]]:
        lname = lef2tech.get(w.layer)
        out = []
        if lname is None or lname not in L:
            return out
        width_nm = int(round((w.width * scale) if w.width else lef.layers[w.layer].width_um * 1000))
        hw = width_nm // 2
        pts = [(int(round(x * scale)), int(round(y * scale))) for x, y in w.points]
        if len(pts) == 1:
            x, y = pts[0]
            out.append((lname, (x - hw, y - hw, x + hw, y + hw)))
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if x0 == x1:
                ya, yb = sorted((y0, y1)); out.append((lname, (x0 - hw, ya - hw, x0 + hw, yb + hw)))
            elif y0 == y1:
                xa, xb = sorted((x0, x1)); out.append((lname, (xa - hw, y0 - hw, xb + hw, y0 + hw)))
            else:
                raise ValueError("non-manhattan DEF wire in net")
        if w.via:
            v = lef.vias[w.via]
            x, y = pts[-1]
            for vl, (a, b, c2, e) in v.rects:
                tl = lef2tech.get(vl)
                if tl in L:
                    out.append((tl, (x + int(round(a * 1000)), y + int(round(b * 1000)),
                                     x + int(round(c2 * 1000)), y + int(round(e * 1000)))))
        return out

    for net in d.nets:
        prov = "%s/net:%s" % (d.design, net.name)
        first = None
        for w in net.wires:
            for lname, r in wire_rects(w):
                fl.rects.append(FlatRect(L[lname], r, prov))
                if first is None:
                    first = (lname, ((r[0] + r[2]) // 2, (r[1] + r[3]) // 2))
        if first is None:
            # unrouted net: label through a component pin port if we can
            for inst, pin in net.pins:
                comp = next((c for c in d.components if c.inst == inst), None)
                m = lef.macros.get(comp.macro) if comp else None
                if comp and m and pin in m.pins and m.pins[pin].ports:
                    pl, (a, b, c2, e) = m.pins[pin].ports[0]
                    mirror, angle = ORIENT[comp.orient]
                    ref = Ref(comp.macro, (0, 0), mirror_x=mirror, angle=angle)
                    w_nm, h_nm = int(round(m.size[0] * 1000)), int(round(m.size[1] * 1000))
                    corners = [gds._xform(p, ref, (0, 0)) for p in ((0, 0), (w_nm, 0), (0, h_nm), (w_nm, h_nm))]
                    off = (int(round(comp.x * scale)) - min(p[0] for p in corners),
                           int(round(comp.y * scale)) - min(p[1] for p in corners))
                    cx, cy = gds._xform((int(round((a + c2) / 2 * 1000)), int(round((b + e) / 2 * 1000))), ref, off)
                    first = (lef2tech.get(pl), (cx, cy))
                    break
        if first and first[0] in L:
            layer = L[first[0]]
            fl.texts.append(FlatText(layer, first[1], net.name))
    for p in d.pins:
        if p.rect and lef2tech.get(p.layer) in L:
            r = tuple(int(round(v * scale)) for v in p.rect)
            fl.rects.append(FlatRect(L[lef2tech[p.layer]], r, "%s/pin:%s" % (d.design, p.name)))
    return fl
