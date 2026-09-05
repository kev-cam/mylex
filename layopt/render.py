# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""Tiny SVG renderer for eyeballing a window of the flat layout."""
from typing import Tuple

from .gds import FlatLayout
from .tech import Tech

COLORS = {"nwell": "#e8e8c0", "diff": "#80c080", "tap": "#60a060", "poly": "#e06060", "nsdm": "none",
          "psdm": "none", "licon": "#404040", "li": "#c0a060", "mcon": "#202020", "met1": "#4060e0",
          "via1": "#101010", "met2": "#e040e0", "via2": "#101010", "met3": "#40c0c0", "text": "none"}
ORDER = ["nwell", "diff", "tap", "poly", "licon", "li", "mcon", "met1", "via1", "met2", "via2", "met3"]


def svg(fl: FlatLayout, tech: Tech, window_um: Tuple[float, float, float, float], path: str, scale: float = 40.0):
    inv = {v: k for k, v in tech.layers.items()}
    d = fl.dbu_um
    x0, y0, x1, y1 = window_um
    W, H = (x1 - x0) * scale, (y1 - y0) * scale
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (W, H, W, H),
           '<rect width="100%%" height="100%%" fill="white"/>']
    rank = {n: i for i, n in enumerate(ORDER)}
    rs = sorted(fl.rects, key=lambda r: rank.get(inv.get(r.layer, ""), 99))
    for r in rs:
        ln = inv.get(r.layer)
        col = COLORS.get(ln, "#999")
        if col == "none":
            continue
        rx0, ry0, rx1, ry1 = [c * d for c in r.rect]
        if rx1 < x0 or rx0 > x1 or ry1 < y0 or ry0 > y1:
            continue
        out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" fill-opacity="0.55" stroke="%s" stroke-width="0.5"><title>%s %s</title></rect>'
                   % ((rx0 - x0) * scale, (y1 - ry1) * scale, (rx1 - rx0) * scale, (ry1 - ry0) * scale, col, col, ln, r.prov))
    out.append("</svg>")
    with open(path, "w") as fh:
        fh.write("\n".join(out))


def png(fl: FlatLayout, tech: Tech, window_um: Tuple[float, float, float, float], path: str, scale: float = 40.0,
        highlight_prov: str = ""):
    """Rasterize with Pillow (optional dependency); highlighted provenance in red outline."""
    from PIL import Image, ImageDraw
    inv = {v: k for k, v in tech.layers.items()}
    d = fl.dbu_um
    x0, y0, x1, y1 = window_um
    W, H = int((x1 - x0) * scale), int((y1 - y0) * scale)
    img = Image.new("RGBA", (W, H), "white")
    rank = {n: i for i, n in enumerate(ORDER)}
    for r in sorted(fl.rects, key=lambda r: rank.get(inv.get(r.layer, ""), 99)):
        ln = inv.get(r.layer)
        col = COLORS.get(ln, "#999999")
        if col == "none":
            continue
        rx0, ry0, rx1, ry1 = [c * d for c in r.rect]
        if rx1 < x0 or rx0 > x1 or ry1 < y0 or ry0 > y1:
            continue
        box = [(rx0 - x0) * scale, (y1 - ry1) * scale, (rx1 - x0) * scale, (y1 - ry0) * scale]
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).rectangle(box, fill=col + "90", outline=(255, 0, 0, 255) if highlight_prov and highlight_prov in r.prov else col)
        img = Image.alpha_composite(img, layer)
    img.convert("RGB").save(path)
