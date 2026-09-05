#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""layopt probe: balance the VDD supply resistance seen by the four VCO delay
cells of the kestrel PLL layout by resizing power wiring.

Steps
  1. flatten + extract kestrel_pll.gds; report what the geometry says
  2. repair: add the eight MET2 stubs from the delay cells' VDD pads to the
     VCO rail (kestrel's generator leaves them unconnected)
  3. baseline: effective resistance from the PLL's VDD feed to each stub
  4. optimize rail width + per-cell stub widths for minimum spread
  5. write the optimized flat GDS and a SPEF

Usage: vco_supply_balance.py [kestrel_pll.gds] [--iters N]
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
from layopt import drc, extract, gds, geom, moves, objective, optimize, rc, tech   # noqa: E402

GDS = next((a for a in sys.argv[1:] if a.endswith(".gds")), None) or os.environ.get(
    "KESTREL_GDS", "/usr/local/src/kestrel/layout/kestrel_pll.gds")
ITERS = int(sys.argv[sys.argv.index("--iters") + 1]) if "--iters" in sys.argv else 120
EVID = os.path.join(HERE, "evidence")
os.makedirs(EVID, exist_ok=True)
T = tech.SKY130
um = lambda r, d: [round(c * d, 3) for c in r]


def main():
    t0 = time.time()
    fl = gds.flatten(gds.read(GDS))
    ex = extract.extract(fl, T)
    d = fl.dbu_um
    print("== 1. extraction of %s" % GDS)
    print("   %d rects -> %d shapes, %d nets, %d devices (%d n, %d p) in %.2fs" % (
        len(fl.rects), len(ex.shapes), len(ex.nets), len(ex.devices),
        sum(x.kind == "n" for x in ex.devices), sum(x.kind == "p" for x in ex.devices), time.time() - t0))
    big = max(ex.nets.values(), key=lambda n: len(n.devices))
    print("   largest net %s: %d device terminals %s -- the four stages' diff-pair drains are one net"
          % (big.name, len(big.devices), sorted({t for _, t in big.devices})))
    chains = 0
    for dv in ex.devices:
        if dv.kind == "p" and dv.prov.split("/")[-1].startswith("Mp"):
            for n in (dv.s, dv.d):
                net = ex.nets[n]
                if len(net.devices) == 2 and all(ex.devices[int(nm[1:]) - 1].prov == dv.prov for nm, _ in net.devices):
                    chains += 1
    print("   %d PFET finger-to-finger S/D nets local to one transistor cell: fingers are chained in series, not strapped" % (chains // 2))

    # VCO rail (MET2, 2 um tall, in kestrel_vco, top)
    met2 = T.layers["met2"]
    rails = [i for i, r in enumerate(fl.rects) if r.layer == met2 and r.prov.endswith("kestrel_vco") and r.h == int(round(2.0 / d))]
    rail_idx = max(rails, key=lambda i: fl.rects[i].y0)
    rail = fl.rects[rail_idx]
    print("   VCO VDD rail: rect %d %s um, net %s with %d devices" % (
        rail_idx, um(rail.rect, d), ex.net_of_shape[[s for s in range(len(ex.shapes)) if ex.shapes[s].src == rail_idx][0]],
        len(ex.nets[ex.net_of_shape[[s for s in range(len(ex.shapes)) if ex.shapes[s].src == rail_idx][0]]].devices)))

    # delay-cell VDD pads: PFET terminal nets inside a delay cell that carry MET2
    pads = {}
    for dv in ex.devices:
        if dv.kind != "p" or "kestrel_delay_cell" not in dv.prov:
            continue
        cell = dv.prov.rsplit("/", 1)[0]
        for n in (dv.s, dv.d):
            for s in ex.nets[n].shapes:
                sh = ex.shapes[s]
                if sh.layer == "met2" and sh.src >= 0:
                    pads.setdefault(cell, set()).add(sh.src)
    print("   delay-cell PMOS-source MET2 pads: %s (none reaches the rail; gap %.2f um)" % (
        {k.split("/")[-1]: len(v) for k, v in sorted(pads.items())},
        (rail.y0 - max(fl.rects[i].y1 for v in pads.values() for i in v)) * d))

    # ---- 2. repair: stubs from each pad to the rail centre-line ----------------
    print("== 2. repair: add MET2 stubs pad -> rail")
    rail_cy = (rail.y0 + rail.y1) / 2.0 * d
    stubs = {}
    for cell, ids in sorted(pads.items()):
        for i in sorted(ids):
            p = fl.rects[i]
            sid = moves.add_rect(fl, met2, (p.x0 * d, p.y1 * d, p.x1 * d, rail_cy), cell + "/vdd_stub")
            stubs.setdefault(cell, []).append(sid)
    ex = extract.extract(fl, T)
    src2shape = {sh.src: k for k, sh in enumerate(ex.shapes) if sh.src >= 0}
    vdd = ex.net_of_shape[src2shape[rail_idx]]
    ex.nets[vdd].name = "VDD"
    print("   VDD net now has %d device terminals: %s" % (len(ex.nets[vdd].devices), sorted(ex.nets[vdd].devices)))
    feed = min((s for s in ex.nets[vdd].shapes), key=lambda s: ex.shapes[s].rect[3])
    print("   feed taken at the lowest VDD shape (PLL pin side): %s %s um" % (ex.shapes[feed].layer, um(ex.shapes[feed].rect, d)))
    stub_ids = [i for v in stubs.values() for i in v]
    cells = sorted(stubs)

    def taps_of(ex_):
        m = {sh.src: k for k, sh in enumerate(ex_.shapes) if sh.src >= 0}
        return [m[i] for i in stub_ids], m

    def gradient(ex_):
        taps, m = taps_of(ex_)
        net = ex_.net_of_shape[m[rail_idx]]
        fd = min((s for s in ex_.nets[net].shapes), key=lambda s: ex_.shapes[s].rect[3])
        return objective.supply_gradient(ex_, net, fd, taps)

    # ---- 3. baseline ------------------------------------------------------------
    g0 = gradient(ex)
    area0 = objective.metal_area_um2(fl, [rail_idx] + stub_ids)
    print("== 3. baseline: R(feed -> stub) per cell, ohm")
    for k, cell in enumerate(cells):
        print("   %-22s %s" % (cell.split("/")[-1], ["%.1f" % g0.values[2 * k + j] for j in range(2)]))
    print("   mean %.1f  spread %.1f  (%.1f%%)  power-metal area %.1f um2" % (g0.mean, g0.spread, 100 * g0.rel, area0))

    # ---- 4. optimize -------------------------------------------------------------
    print("== 4. optimize rail width + per-cell stub widths (Nelder-Mead, %d iters max)" % ITERS)
    variables = [optimize.Variable("rail_w", 0.5, 6.0, 2.0,
                                   lambda f, e, v: moves.set_wire_width(f, rail_idx, v))]
    for cell in cells:
        ids = stubs[cell]
        variables.append(optimize.Variable(cell.split("/")[-1] + "_stub_w", T.min_width["met2"], 1.5,
                                           moves.wire_width_um(fl, ids[0]),
                                           lambda f, e, v, ids=ids: sum((moves.set_wire_width(f, i, v) for i in ids), [])))

    def cost(f, e, x):
        g = gradient(e)
        area = objective.metal_area_um2(f, [rail_idx] + stub_ids)
        c = g.spread / g0.spread + 0.1 * g.mean / g0.mean + 0.05 * area / area0
        return c, {"spread": g.spread, "mean": g.mean, "area": area}

    prob = optimize.Problem(fl, T, variables, cost)
    print("   baseline rule violations already in the layout (ignored unless a move adds one): %d" % len(prob.baseline))
    t1 = time.time()
    best = optimize.solve(prob, max_iter=ITERS)
    print("   %d evaluations in %.1fs; best legal=%s topology_ok=%s new_violations=%d" % (
        len(prob.history), time.time() - t1, best.legal, best.signature_ok, best.violations))
    for var, v in zip(variables, best.x):
        print("   %-24s %.3f um" % (var.name, v))
    g1 = gradient(best.ex)
    print("== 5. result: R(feed -> stub) per cell, ohm")
    for k, cell in enumerate(cells):
        print("   %-22s %s" % (cell.split("/")[-1], ["%.1f" % g1.values[2 * k + j] for j in range(2)]))
    print("   mean %.1f  spread %.1f  (%.1f%%)  power-metal area %.1f um2" % (
        g1.mean, g1.spread, 100 * g1.rel, best.terms["area"]))
    print("   spread %.1f -> %.1f ohm (x%.2f), mean %.1f -> %.1f ohm, area x%.2f" % (
        g0.spread, g1.spread, g1.spread / g0.spread, g0.mean, g1.mean, best.terms["area"] / area0))
    out_gds = os.path.join(EVID, "kestrel_pll_vdd_balanced.gds")
    gds.write_flat(best.fl, out_gds)
    nets = rc.all_nets_rc(best.ex, with_segments=True)
    rc.write_spef(nets, os.path.join(EVID, "kestrel_pll_vdd_balanced.spef"), "kestrel_pll_top")
    extract.write_spice(best.ex, os.path.join(EVID, "kestrel_pll_vdd_balanced.cir"))
    print("   wrote %s (+ .spef, .cir); total %.1fs" % (out_gds, time.time() - t0))


if __name__ == "__main__":
    main()
