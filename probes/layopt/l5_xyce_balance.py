#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""layopt L5 probe 2: the two-way balance judged by Xyce over the corners.
Same layout and moves as l4_path_balance_twoway (fingers on u1 and u6, u6
PMOS Vt, u1 gate length), but every state is re-extracted and simulated at
tt, ss and ff (layopt/spice.py); the cost is the WORST-corner delay spread
between the paths over both edges, plus a small mean-delay term and the
simulated switched energy.  The question: does a balance struck on the
fitted model at tt hold over the operating range, and what does the
simulation choose instead?

    python3 probes/layopt/l5_xyce_balance.py [--scratch DIR] [--corners tt,ss,ff]
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
import l4_path_balance as pb                                          # noqa: E402
import l5_xyce_path as xp                                             # noqa: E402
from layopt import extract, gds, lefdef, moves, optimize, spice, tech   # noqa: E402

T = tech.SKY130
SCR = xp.SCR
CORN = xp.CORN
EVID = os.path.join(HERE, "evidence")


def simulate(ex, lef, comps, models_by_corner, tag):
    """{corner: {path: {edge: (total ps, transition ps, energy fJ)}}} for both paths, both edges."""
    out = {}
    for cname, models in models_by_corner.items():
        corner = spice.Corner.named(cname); out[cname] = {}
        for name, drv, rcv in (("a", "u1", "u4"), ("b", "u6", "u9")):
            out[cname][name] = {}
            for edge in ("rise", "fall"):
                d = xp.path_deck(ex, lef, comps, drv, rcv, models, corner, "fall" if edge == "rise" else "rise")
                res = d.run(os.path.join(SCR, "l5b_%s_%s_%s_%s.cir" % (tag, name, edge, cname)))
                if not res["_ok"] or res.get("d_drv") is None or res.get("d_rcv") is None:
                    raise RuntimeError("Xyce failed for %s %s %s: %s" % (tag, name, edge, res["_log"][-300:]))
                out[cname][name][edge] = ((res["d_drv"] + res["d_rcv"]) * 1e12, (res.get("tr_rcv") or 0) * 1e12, res.get("energy_fJ", 0.0))
    return out


def spread(sim):
    """worst over corners of the rise+fall imbalance, and the mean delay and energy over corners"""
    worst = 0.0; means = []; es = []
    for c, r in sim.items():
        sp = abs(r["a"]["rise"][0] - r["b"]["rise"][0]) + abs(r["a"]["fall"][0] - r["b"]["fall"][0])
        worst = max(worst, sp)
        means.append(sum(r[p][e][0] for p in ("a", "b") for e in ("rise", "fall")) / 4)
        es.append(sum(r[p][e][2] for p in ("a", "b") for e in ("rise", "fall")) / 4)
    return worst, sum(means) / len(means), sum(es) / len(es)


def main():
    pb.ROW[:] = ["inv_4", "fill_4", "fill_4", "nand2_1", "fill_8", "inv_1", "fill_4", "fill_4", "nand2_1", "fill_8"]
    lefs = [os.path.join(pb.LIB, "sky130_fd_sc_hd.tlef")] + sorted({os.path.join(pb.LIB, pb.P + c + ".lef") for c in pb.ROW})
    lef = lefdef.Lef()
    for f in lefs:
        lefdef.read_lef(f, lef)
    def_path = os.path.join(SCR, "l5b.def")
    comps = pb.build_def(lef, def_path)
    fl = lefdef.def2flat(def_path, lefs, pb.LIB, T)
    ex = extract.extract(fl, T)
    models = {c: spice.Models(T, c, scratch=os.path.join(SCR, "xyce_models")) for c in CORN}
    t0 = time.time()
    sim0 = simulate(ex, lef, comps, models, "base")
    w0, m0, e0 = spread(sim0)
    print("== 1. A = u1(inv_4) -> u4 short; B = u6(inv_1) -> u9 over %.0f um of met2.  Xyce at %s (%.0fs for 12 decks)" % (2 * pb.DETOUR_B, ",".join(CORN), time.time() - t0))
    for c in CORN:
        r = sim0[c]
        print("   %-3s A rise/fall %6.1f/%6.1f  B %6.1f/%6.1f  imbalance %6.1f ps  energy %.1f fJ" % (c, r["a"]["rise"][0], r["a"]["fall"][0], r["b"]["rise"][0], r["b"]["fall"][0],
              abs(r["a"]["rise"][0] - r["b"]["rise"][0]) + abs(r["a"]["fall"][0] - r["b"]["fall"][0]), sum(r[p][e][2] for p in ("a", "b") for e in ("rise", "fall")) / 4))
    print("   worst-corner imbalance %.1f ps" % w0)
    f0 = {(inst, kind): max(d.fingers for d in ex.devices if d.prov.split("/")[1] == inst and d.kind == kind) for inst in ("u1", "u6") for kind in ("p", "n")}

    def fingers(inst, kind):
        base_f = f0[(inst, kind)]
        def apply(f_, e_, n):
            t = []
            for _ in range(abs(n - base_f)):
                e_ = extract.extract(f_, T)
                dev = max((d for d in e_.devices if d.prov.split("/")[1] == inst and d.kind == kind), key=lambda d: d.fingers)
                t += (moves.add_finger if n > base_f else moves.remove_finger)(f_, e_, dev, side="high")
            return t
        return apply
    def vt(inst):
        def apply(f_, e_, n):
            if n == 0:
                return []
            e_ = extract.extract(f_, T)
            dev = max((d for d in e_.devices if d.prov.split("/")[1] == inst and d.kind == "p"), key=lambda d: d.fingers)
            return moves.set_vt(f_, e_, dev, "std")
        return apply
    LENGTHS = [0.15, 0.18, 0.25]
    def glen(inst, kind):
        def apply(f_, e_, n):
            if n == 0:
                return []
            e_ = extract.extract(f_, T)
            dev = max((d for d in e_.devices if d.prov.split("/")[1] == inst and d.kind == kind), key=lambda d: d.fingers)
            return moves.set_gate_length(f_, e_, dev, LENGTHS[n])
        return apply
    variables = [optimize.IntVariable("u1_p", 1, f0[("u1", "p")] + 1, f0[("u1", "p")], fingers("u1", "p")),
                 optimize.IntVariable("u1_n", 1, f0[("u1", "n")] + 1, f0[("u1", "n")], fingers("u1", "n")),
                 optimize.IntVariable("u6_p", 1, 4, 1, fingers("u6", "p")),
                 optimize.IntVariable("u6_n", 1, 4, 1, fingers("u6", "n")),
                 optimize.IntVariable("u6_vt", 0, 1, 0, vt("u6")),
                 optimize.IntVariable("u1_lp", 0, 2, 0, glen("u1", "p")),
                 optimize.IntVariable("u1_ln", 0, 2, 0, glen("u1", "n"))]
    counter = [0]
    def cost(f_, e_, x):
        counter[0] += 1
        sim = simulate(e_, lef, comps, models, "s%d" % counter[0])
        w, m, e = spread(sim)
        return w / w0 + 0.05 * m / m0 + 0.5 * (e - e0) / e0, {"worst_ps": round(w, 1), "mean_ps": round(m, 1), "E_fJ": round(e, 1),
                                                                 "tt": round(abs(sim["tt"]["a"]["rise"][0] - sim["tt"]["b"]["rise"][0]) + abs(sim["tt"]["a"]["fall"][0] - sim["tt"]["b"]["fall"][0]), 1) if "tt" in sim else None}
    print("== 2. greedy search, every state simulated at the corners; cost = worst-corner imbalance + 0.05 mean + 0.5 dE/E")
    prob = optimize.DiscreteProblem(fl, T, variables, cost)
    best = optimize.greedy_search(prob, verbose=True)
    sim1 = simulate(best.ex, lef, comps, models, "best")
    w1, m1, e1 = spread(sim1)
    print("== 3. result: %s" % dict(zip([v.name for v in variables], best.x)))
    for c in CORN:
        r = sim1[c]
        print("   %-3s A rise/fall %6.1f/%6.1f  B %6.1f/%6.1f  imbalance %6.1f ps  energy %.1f fJ" % (c, r["a"]["rise"][0], r["a"]["fall"][0], r["b"]["rise"][0], r["b"]["fall"][0],
              abs(r["a"]["rise"][0] - r["b"]["rise"][0]) + abs(r["a"]["fall"][0] - r["b"]["fall"][0]), sum(r[p][e][2] for p in ("a", "b") for e in ("rise", "fall")) / 4))
    print("   worst-corner imbalance %.1f -> %.1f ps; mean delay %.1f -> %.1f ps; energy %.1f -> %.1f fJ; legal=%s topology_ok=%s violations=%d; %d states, %d Xyce decks" % (
        w0, w1, m0, m1, e0, e1, best.legal, best.signature_ok, best.violations, len(prob.cache), counter[0] * 12))
    for inst in ("u1", "u6"):
        print("   %s devices: %s" % (inst, ["%s W=%.2f L=%.2f fingers=%d %s" % (d.kind, d.w, d.l, d.fingers, T.flavour_of_model(d.model)) for d in best.ex.devices if d.prov.split("/")[1] == inst]))
    gds.write_flat(best.fl, os.path.join(EVID, "l5_xyce_balanced.gds"))


if __name__ == "__main__":
    main()
