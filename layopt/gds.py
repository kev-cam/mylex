# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""Minimal GDSII stream reader/writer and flattener (pure Python).

Reads BOUNDARY, PATH (manhattan), SREF/AREF (manhattan transforms), TEXT.
Produces a FlatLayout of axis-aligned rectangles in database units with a
provenance string per rectangle (instance path), which is what "dissolving"
a cell boundary needs: the geometry is flat, the origin is remembered.
"""
import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# record types
HEADER, BGNLIB, LIBNAME, UNITS, ENDLIB, BGNSTR, STRNAME, ENDSTR = 0, 1, 2, 3, 4, 5, 6, 7
BOUNDARY, PATH, SREF, AREF, TEXT, LAYER, DATATYPE, WIDTH, XY, ENDEL = 8, 9, 10, 11, 12, 13, 14, 15, 16, 17
SNAME, COLROW, TEXTTYPE, PRESENTATION, STRING, STRANS, MAG, ANGLE = 18, 19, 22, 23, 25, 26, 27, 28
PATHTYPE, PROPATTR, PROPVALUE, BOX, BOXTYPE, BGNEXTN, ENDEXTN = 33, 43, 44, 45, 46, 48, 49

Rect = Tuple[int, int, int, int]          # x0, y0, x1, y1 in dbu, x0<x1, y0<y1


def _real8(b: bytes) -> float:
    s = -1.0 if b[0] & 0x80 else 1.0
    e = (b[0] & 0x7F) - 64
    m = int.from_bytes(b[1:8], "big") / float(1 << 56)
    return s * m * (16.0 ** e)


def _to_real8(v: float) -> bytes:
    if v == 0:
        return bytes(8)
    s = 0x80 if v < 0 else 0
    v = abs(v)
    e = 0
    while v >= 1.0:
        v /= 16.0; e += 1
    while v < 1.0 / 16.0:
        v *= 16.0; e -= 1
    m = int(v * (1 << 56))
    return bytes([s | (e + 64)]) + m.to_bytes(7, "big")


@dataclass
class Element:
    kind: str                                  # 'boundary' | 'path' | 'text'
    layer: int
    datatype: int
    xy: List[Tuple[int, int]]
    width: int = 0
    pathtype: int = 0
    text: str = ""


@dataclass
class Ref:
    sname: str
    xy: Tuple[int, int]
    mirror_x: bool = False                     # STRANS bit 15: reflect about X axis before rotation
    angle: float = 0.0
    mag: float = 1.0
    cols: int = 1
    rows: int = 1
    col_step: Tuple[int, int] = (0, 0)
    row_step: Tuple[int, int] = (0, 0)


@dataclass
class Struct:
    name: str
    elements: List[Element] = field(default_factory=list)
    refs: List[Ref] = field(default_factory=list)


@dataclass
class Library:
    name: str = "layopt"
    dbu_um: float = 0.001                      # user units per dbu (um)
    dbu_m: float = 1e-9
    structs: Dict[str, Struct] = field(default_factory=dict)

    def top_cells(self) -> List[str]:
        referenced = {r.sname for s in self.structs.values() if not s.name.startswith("$$$")
                      for r in s.refs}
        return [n for n in self.structs if n not in referenced and not n.startswith("$$$")]


def read(path: str) -> Library:
    data = open(path, "rb").read()
    lib = Library()
    i = 0
    cur: Optional[Struct] = None
    el: Optional[Element] = None
    ref: Optional[Ref] = None
    layer = dtype = 0
    while i < len(data):
        n, = struct.unpack(">H", data[i:i + 2])
        if n < 4:
            break
        rt = data[i + 2]
        body = data[i + 4:i + n]
        i += n
        if rt == LIBNAME:
            lib.name = body.decode("ascii", "replace").rstrip("\0")
        elif rt == UNITS:
            lib.dbu_um = _real8(body[:8])      # user units (um by convention) per dbu
            lib.dbu_m = _real8(body[8:16])     # meters per dbu
        elif rt == BGNSTR:
            cur = Struct("")
        elif rt == STRNAME:
            cur.name = body.decode("ascii", "replace").rstrip("\0")
        elif rt == ENDSTR:
            lib.structs[cur.name] = cur
            cur = None
        elif rt in (BOUNDARY, PATH, TEXT, BOX):
            el = Element({BOUNDARY: "boundary", PATH: "path", TEXT: "text", BOX: "boundary"}[rt], 0, 0, [])
        elif rt in (SREF, AREF):
            ref = Ref("", (0, 0))
        elif rt == LAYER:
            layer = struct.unpack(">h", body)[0]
        elif rt in (DATATYPE, TEXTTYPE, BOXTYPE):
            dtype = struct.unpack(">h", body)[0]
        elif rt == WIDTH:
            el.width = struct.unpack(">i", body)[0]
        elif rt == PATHTYPE:
            el.pathtype = struct.unpack(">h", body)[0]
        elif rt == SNAME:
            ref.sname = body.decode("ascii", "replace").rstrip("\0")
        elif rt == STRANS:                  # also legal inside TEXT (presentation transform): ignore there
            if ref is not None:
                ref.mirror_x = bool(body[0] & 0x80)
        elif rt == MAG:
            if ref is not None:
                ref.mag = _real8(body)
        elif rt == ANGLE:
            if ref is not None:
                ref.angle = _real8(body)
        elif rt == COLROW:
            ref.cols, ref.rows = struct.unpack(">hh", body)
        elif rt == STRING:
            el.text = body.decode("ascii", "replace").rstrip("\0")
        elif rt == XY:
            k = len(body) // 8
            pts = struct.unpack(">%di" % (2 * k), body)
            xy = [(pts[2 * j], pts[2 * j + 1]) for j in range(k)]
            if ref is not None:
                ref.xy = xy[0]
                if len(xy) == 3:              # AREF: origin, col end, row end
                    ref.col_step = ((xy[1][0] - xy[0][0]) // max(ref.cols, 1),
                                    (xy[1][1] - xy[0][1]) // max(ref.cols, 1))
                    ref.row_step = ((xy[2][0] - xy[0][0]) // max(ref.rows, 1),
                                    (xy[2][1] - xy[0][1]) // max(ref.rows, 1))
            else:
                el.xy = xy
        elif rt == ENDEL:
            if ref is not None:
                cur.refs.append(ref); ref = None
            elif el is not None:
                el.layer, el.datatype = layer, dtype
                cur.elements.append(el); el = None
        elif rt == ENDLIB:
            break
    return lib


# ----------------------------------------------------------------------------
# Geometry helpers: polygons -> rectangles
# ----------------------------------------------------------------------------

def rect_of_points(xy) -> Optional[Rect]:
    """Return the rect if the closed polygon is an axis-aligned rectangle."""
    pts = list(xy)
    if len(pts) >= 2 and pts[0] == pts[-1]:
        pts = pts[:-1]
    if len(pts) != 4:
        return None
    xs = sorted({p[0] for p in pts}); ys = sorted({p[1] for p in pts})
    if len(xs) != 2 or len(ys) != 2:
        return None
    for p in pts:
        if p[0] not in xs or p[1] not in ys:
            return None
    return (xs[0], ys[0], xs[1], ys[1])


def rectilinear_to_rects(xy) -> List[Rect]:
    """Decompose a rectilinear polygon into rectangles by vertical slabs."""
    pts = list(xy)
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    r = rect_of_points(pts)
    if r:
        return [r]
    n = len(pts)
    for a, b in zip(pts, pts[1:] + pts[:1]):
        if a[0] != b[0] and a[1] != b[1]:
            raise ValueError("non-rectilinear polygon not supported")
    xs = sorted({p[0] for p in pts})
    out: List[Rect] = []
    for x0, x1 in zip(xs, xs[1:]):
        xm = (x0 + x1) / 2.0
        # vertical edges crossing this slab? none by construction; collect horizontal edges spanning xm
        ys = []
        for a, b in zip(pts, pts[1:] + pts[:1]):
            if a[1] == b[1] and min(a[0], b[0]) < xm < max(a[0], b[0]):
                ys.append(a[1])
        ys.sort()
        for y0, y1 in zip(ys[0::2], ys[1::2]):
            out.append((x0, y0, x1, y1))
    return out


def path_to_rects(xy, width: int, pathtype: int = 0) -> List[Rect]:
    """Manhattan path with width -> rectangles (square/flush ends)."""
    hw = width // 2
    ext = hw if pathtype in (1, 2) else 0
    out: List[Rect] = []
    for (x0, y0), (x1, y1) in zip(xy, xy[1:]):
        if x0 == x1:
            ya, yb = sorted((y0, y1))
            out.append((x0 - hw, ya - ext, x0 + hw, yb + ext))
        elif y0 == y1:
            xa, xb = sorted((x0, x1))
            out.append((xa - ext, y0 - hw, xb + ext, y0 + hw))
        else:
            raise ValueError("non-manhattan path not supported")
    return out


# ----------------------------------------------------------------------------
# Flattening with provenance
# ----------------------------------------------------------------------------

@dataclass
class FlatRect:
    layer: Tuple[int, int]
    rect: Rect
    prov: str                                  # instance path, e.g. top/vco/delay_cell#2/Mtail

    @property
    def x0(self): return self.rect[0]
    @property
    def y0(self): return self.rect[1]
    @property
    def x1(self): return self.rect[2]
    @property
    def y1(self): return self.rect[3]
    @property
    def w(self): return self.rect[2] - self.rect[0]
    @property
    def h(self): return self.rect[3] - self.rect[1]
    @property
    def area(self): return self.w * self.h


@dataclass
class FlatText:
    layer: Tuple[int, int]
    xy: Tuple[int, int]
    text: str


@dataclass
class FlatLayout:
    dbu_um: float
    rects: List[FlatRect] = field(default_factory=list)
    texts: List[FlatText] = field(default_factory=list)
    top: str = ""

    def by_layer(self, layer: Tuple[int, int]) -> List[FlatRect]:
        return [r for r in self.rects if r.layer == layer]


def _xform(pt, ref: Ref, off):
    x, y = pt
    if ref.mag != 1.0:
        x, y = x * ref.mag, y * ref.mag
    if ref.mirror_x:
        y = -y
    a = int(round(ref.angle)) % 360
    if a == 90:
        x, y = -y, x
    elif a == 180:
        x, y = -x, -y
    elif a == 270:
        x, y = y, -x
    elif a != 0:
        raise ValueError("non-manhattan rotation %g not supported" % ref.angle)
    return (int(round(x + off[0])), int(round(y + off[1])))


def _xrect(r: Rect, ref: Ref, off) -> Rect:
    ax, ay = _xform((r[0], r[1]), ref, off)
    bx, by = _xform((r[2], r[3]), ref, off)
    return (min(ax, bx), min(ay, by), max(ax, bx), max(ay, by))


def flatten(lib: Library, top: Optional[str] = None) -> FlatLayout:
    if top is None:
        tops = lib.top_cells()
        if not tops:
            raise ValueError("no top cell")
        top = tops[0]
    fl = FlatLayout(dbu_um=lib.dbu_um, top=top)
    ident = Ref(top, (0, 0))

    def walk(sname: str, prov: str, chain: List[Tuple[Ref, Tuple[int, int]]]):
        s = lib.structs[sname]
        for e in s.elements:
            if e.kind == "text":
                pt = e.xy[0]
                for ref, off in chain:
                    pt = _xform(pt, ref, off)
                fl.texts.append(FlatText((e.layer, e.datatype), pt, e.text))
                continue
            if e.kind == "path":
                rects = path_to_rects(e.xy, e.width, e.pathtype)
            else:
                rects = rectilinear_to_rects(e.xy)
            for r in rects:
                for ref, off in chain:
                    r = _xrect(r, ref, off)
                fl.rects.append(FlatRect((e.layer, e.datatype), r, prov))
        counts: Dict[str, int] = {}
        for ref in s.refs:
            k = counts.get(ref.sname, 0); counts[ref.sname] = k + 1
            for ci in range(ref.cols):
                for ri in range(ref.rows):
                    off = (ref.xy[0] + ci * ref.col_step[0] + ri * ref.row_step[0],
                           ref.xy[1] + ci * ref.col_step[1] + ri * ref.row_step[1])
                    tag = ref.sname if (counts.get(ref.sname) is not None and len([x for x in s.refs if x.sname == ref.sname]) == 1) else "%s#%d" % (ref.sname, k)
                    if ref.cols > 1 or ref.rows > 1:
                        tag += "[%d,%d]" % (ci, ri)
                    # innermost transform first: child coords -> this ref -> parents
                    walk(ref.sname, prov + "/" + tag, [(ref, off)] + chain)

    walk(top, top, [])
    return fl


# ----------------------------------------------------------------------------
# Writer (flat)
# ----------------------------------------------------------------------------

def _rec(rt: int, dt: int, body: bytes = b"") -> bytes:
    return struct.pack(">HBB", 4 + len(body), rt, dt) + body


def _str(s: str) -> bytes:
    b = s.encode("ascii")
    return b + (b"\0" if len(b) % 2 else b"")


def write_flat(fl: FlatLayout, path: str, name: Optional[str] = None, dbu_m: float = 1e-9):
    """Write the flat layout as one GDS structure (hierarchy dissolved)."""
    import time
    t = time.localtime()
    ts = struct.pack(">12h", t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec,
                     t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
    out = [_rec(HEADER, 2, struct.pack(">h", 600)), _rec(BGNLIB, 2, ts), _rec(LIBNAME, 6, _str("layopt")),
           _rec(UNITS, 5, _to_real8(fl.dbu_um) + _to_real8(dbu_m)),
           _rec(BGNSTR, 2, ts), _rec(STRNAME, 6, _str(name or fl.top))]
    for r in fl.rects:
        x0, y0, x1, y1 = r.rect
        pts = struct.pack(">10i", x0, y0, x0, y1, x1, y1, x1, y0, x0, y0)
        out += [_rec(BOUNDARY, 0), _rec(LAYER, 2, struct.pack(">h", r.layer[0])),
                _rec(DATATYPE, 2, struct.pack(">h", r.layer[1])), _rec(XY, 3, pts), _rec(ENDEL, 0)]
    for tx in fl.texts:
        out += [_rec(TEXT, 0), _rec(LAYER, 2, struct.pack(">h", tx.layer[0])),
                _rec(TEXTTYPE, 2, struct.pack(">h", tx.layer[1])),
                _rec(XY, 3, struct.pack(">2i", *tx.xy)), _rec(STRING, 6, _str(tx.text)), _rec(ENDEL, 0)]
    out += [_rec(ENDSTR, 0), _rec(ENDLIB, 0)]
    with open(path, "wb") as fh:
        fh.write(b"".join(out))
