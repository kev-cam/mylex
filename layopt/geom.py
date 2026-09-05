# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""Rectangle geometry: intersections, subtraction, a bin index, union-find,
and exact union area/perimeter of rectangle sets."""
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

Rect = Tuple[int, int, int, int]


def inter(a: Rect, b: Rect) -> Optional[Rect]:
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    if x0 < x1 and y0 < y1:
        return (x0, y0, x1, y1)
    return None


def touches(a: Rect, b: Rect) -> bool:
    """Overlap or share an edge segment of positive length (not a corner point)."""
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    if x0 > x1 or y0 > y1:
        return False
    if x0 == x1 and y0 == y1:
        return False
    return True


def overlaps(a: Rect, b: Rect) -> bool:
    return inter(a, b) is not None


def contains(outer: Rect, inner: Rect) -> bool:
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]


def area(r: Rect) -> int:
    return (r[2] - r[0]) * (r[3] - r[1])


def subtract(r: Rect, holes: Sequence[Rect]) -> List[Rect]:
    """r minus the union of holes, as rectangles (coordinate-compressed cells,
    merged along y then x)."""
    hs = [h for h in (inter(r, h) for h in holes) if h]
    if not hs:
        return [r]
    xs = sorted({r[0], r[2], *(h[0] for h in hs), *(h[2] for h in hs)})
    ys = sorted({r[1], r[3], *(h[1] for h in hs), *(h[3] for h in hs)})
    cells: List[Rect] = []
    for i in range(len(xs) - 1):
        col: List[Rect] = []
        for j in range(len(ys) - 1):
            c = (xs[i], ys[j], xs[i + 1], ys[j + 1])
            cx, cy = (c[0] + c[2]) / 2.0, (c[1] + c[3]) / 2.0
            if any(h[0] < cx < h[2] and h[1] < cy < h[3] for h in hs):
                continue
            if col and col[-1][3] == c[1] and col[-1][0] == c[0] and col[-1][2] == c[2]:
                col[-1] = (col[-1][0], col[-1][1], col[-1][2], c[3])
            else:
                col.append(c)
        cells.extend(col)
    # merge horizontally adjacent cells with identical y-span
    cells.sort(key=lambda c: (c[1], c[3], c[0]))
    out: List[Rect] = []
    for c in cells:
        if out and out[-1][1] == c[1] and out[-1][3] == c[3] and out[-1][2] == c[0]:
            out[-1] = (out[-1][0], out[-1][1], c[2], out[-1][3])
        else:
            out.append(c)
    return out


class BinIndex:
    """Uniform-grid spatial index over rectangles (ids are ints)."""

    def __init__(self, cell: int = 2000):
        self.cell = cell
        self.bins: Dict[Tuple[int, int], List[int]] = {}
        self.rects: Dict[int, Rect] = {}

    def _keys(self, r: Rect):
        c = self.cell
        for bx in range(r[0] // c, r[2] // c + 1):
            for by in range(r[1] // c, r[3] // c + 1):
                yield (bx, by)

    def add(self, rid: int, r: Rect):
        self.rects[rid] = r
        for k in self._keys(r):
            self.bins.setdefault(k, []).append(rid)

    def candidates(self, r: Rect) -> Set[int]:
        out: Set[int] = set()
        for k in self._keys(r):
            b = self.bins.get(k)
            if b:
                out.update(b)
        return out

    def query_touch(self, r: Rect) -> List[int]:
        return [i for i in self.candidates(r) if touches(self.rects[i], r)]

    def query_overlap(self, r: Rect) -> List[int]:
        return [i for i in self.candidates(r) if overlaps(self.rects[i], r)]


class UnionFind:
    def __init__(self, n: int = 0):
        self.p = list(range(n))

    def add(self) -> int:
        self.p.append(len(self.p)); return len(self.p) - 1

    def find(self, a: int) -> int:
        p = self.p
        while p[a] != a:
            p[a] = p[p[a]]; a = p[a]
        return a

    def union(self, a: int, b: int):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def union_area_perimeter(rects: Iterable[Rect]) -> Tuple[int, int]:
    """Exact area and outer+hole perimeter of the union of rectangles (dbu, dbu^2)."""
    rs = list(rects)
    if not rs:
        return 0, 0
    xs = sorted({v for r in rs for v in (r[0], r[2])})
    ys = sorted({v for r in rs for v in (r[1], r[3])})
    xi = {v: i for i, v in enumerate(xs)}; yi = {v: i for i, v in enumerate(ys)}
    nx, ny = len(xs) - 1, len(ys) - 1
    cov = [[False] * ny for _ in range(nx)]
    for r in rs:
        for i in range(xi[r[0]], xi[r[2]]):
            row = cov[i]
            for j in range(yi[r[1]], yi[r[3]]):
                row[j] = True
    a = 0; per = 0
    for i in range(nx):
        w = xs[i + 1] - xs[i]
        for j in range(ny):
            if not cov[i][j]:
                continue
            h = ys[j + 1] - ys[j]
            a += w * h
            if i == 0 or not cov[i - 1][j]: per += h
            if i == nx - 1 or not cov[i + 1][j]: per += h
            if j == 0 or not cov[i][j - 1]: per += w
            if j == ny - 1 or not cov[i][j + 1]: per += w
    return a, per


def bbox(rects: Iterable[Rect]) -> Optional[Rect]:
    rs = list(rects)
    if not rs:
        return None
    return (min(r[0] for r in rs), min(r[1] for r in rs), max(r[2] for r in rs), max(r[3] for r in rs))
