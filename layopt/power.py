# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""Switched capacitance: the power side of a move.

Dynamic energy per transition of a net is C_net * Vdd^2, and C_net is what
the layout says it is: the wire (from the RC extraction), the gates it drives
(fitted from the Liberty pin capacitances against layopt's own extraction of
the same cells: 8.63 fF/um^2 of gate area, within 3.7 % over the family) and
the drain/source diffusion of the devices on it (the PDK's zero-bias junction
parameters: area, sidewall, and the gate-edge sidewall).  Activity is not
known here -- an asynchronous handshake toggles specific nets once per
cycle -- so the measure is energy per transition per net, and a move's
power price is the change of the sum over the nets it touched, or over the
design.  Relative, honest, and enough to price a finger against an implant.
"""
from typing import Dict, Iterable, Optional

from . import rc
from .extract import Extraction

VDD = 1.8


def gate_cap_fF(ex: Extraction, dev) -> float:
    return ex.tech.cgate_fF_um2 * dev.w * dev.l


def diffusion_cap_fF(ex: Extraction, dev, terminal: str) -> float:
    """Zero-bias junction capacitance of one S/D terminal: cj*A + cjsw*(P - W) + cjswg*W."""
    j = ex.tech.junction.get(dev.kind)
    if not j:
        return 0.0
    a, p = (dev.as_, dev.ps) if terminal == "S" else (dev.ad, dev.pd)
    return j["cj"] * a + j["cjsw"] * max(p - dev.w, 0.0) + j["cjswg"] * min(dev.w, p)


def net_cap(ex: Extraction, net_id: int) -> Dict[str, float]:
    """fF on a net: wire (extracted union C), gate (receivers), diff (S/D of devices on it)."""
    wire = rc.net_rc(ex, net_id).c_fF
    gate = diff = 0.0
    for dv in ex.devices:
        if dv.g == net_id:
            gate += gate_cap_fF(ex, dv)
        if dv.s == net_id:
            diff += diffusion_cap_fF(ex, dv, "S")
        if dv.d == net_id:
            diff += diffusion_cap_fF(ex, dv, "D")
    return {"wire": wire, "gate": gate, "diff": diff, "total": wire + gate + diff}


def energy_fJ(ex: Extraction, nets: Optional[Iterable[int]] = None, vdd: float = VDD, skip_supply: bool = True) -> float:
    """Sum of C * Vdd^2 over the nets (all signal nets by default), fJ per transition."""
    ids = list(nets) if nets is not None else [i for i, n in ex.nets.items() if not (skip_supply and n.name in ex.tech.supply_names)]
    return sum(net_cap(ex, i)["total"] for i in ids) * vdd * vdd


def report(ex: Extraction, net_id: int) -> str:
    c = net_cap(ex, net_id)
    return "%s: %.2f fF (wire %.2f, gate %.2f, diff %.2f) = %.1f fJ/transition" % (
        ex.nets[net_id].name, c["total"], c["wire"], c["gate"], c["diff"], c["total"] * VDD * VDD)
