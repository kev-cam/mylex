# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""Cost terms.  Timing balance is expressed as spreads across a set of
comparable paths (ring stages, fork branches, matched delays), not as absolute
delay: that is what asynchronous circuits and matched-delay bundled data care
about, and it is also the quantity a supply gradient perturbs."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from . import rc
from .extract import Extraction
from .gds import FlatLayout


@dataclass
class Spread:
    values: List[float]
    mean: float
    spread: float           # max - min
    rel: float              # spread / mean


def spread(vals: Sequence[float]) -> Spread:
    v = list(vals)
    m = sum(v) / len(v) if v else 0.0
    s = (max(v) - min(v)) if v else 0.0
    return Spread(v, m, s, s / m if m else 0.0)


def supply_gradient(ex: Extraction, net_id: int, feed_shape: int, tap_shapes: Sequence[int]) -> Spread:
    """Effective resistance from the feed point to each tap on one supply net."""
    rn = rc.ResistiveNet(ex, net_id)
    return spread([rn.r_eff(feed_shape, t) for t in tap_shapes])


def elmore_balance(ex: Extraction, net_ids: Sequence[int], r_drive: float, c_in_fF: float) -> Spread:
    """Elmore delay per net with a common driver R and receiver load (ps)."""
    out = []
    for n in net_ids:
        x = rc.net_rc(ex, n)
        c = x.c_fF + c_in_fF
        tau_ps = (r_drive * c + x.r_ohm * (x.c_fF / 2.0 + c_in_fF)) * 1e-3     # ohm*fF = 1e-15 s = 1e-3 ps
        out.append(tau_ps)
    return spread(out)


def metal_area_um2(fl: FlatLayout, ids: Sequence[int]) -> float:
    d = fl.dbu_um
    return sum(fl.rects[i].area for i in ids) * d * d
