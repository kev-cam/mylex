#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""layopt L4 probe 3: balance two paths when the cheaper fix is to SLOW the
fast one -- the discrete search may add fingers to the slow driver (into the
filler next to it) or remove fingers from the fast one (remove_finger).

Path A: u1 = inv_4 over a short wire (fast).  Path B: u6 = inv_1 over a long
met2 detour (slow).  Variables are finger counts per polarity; a state below
the stock count removes fingers, above it adds them.  The cost is the delay
spread plus a small mean-delay term and an area term that charges added
fingers and credits removed ones.

Usage: l4_path_balance_twoway.py [--lib DIR] [--scratch DIR]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
sys.path.insert(0, HERE)
import l4_path_balance as pb                                       # noqa: E402
from layopt import extract, gds, lefdef, moves, optimize, power      # noqa: E402

T = pb.T
EVID = pb.EVID


def main():
    pb.ROW = ["inv_4", "fill_4", "fill_4", "nand2_1", "fill_8", "inv_1", "fill_4", "fill_4", "nand2_1", "fill_8"]
    lefs = [os.path.join(pb.LIB, "sky130_fd_sc_hd.tlef")] + sorted(set(os.path.join(pb.LIB, pb.P + c + ".lef") for c in pb.ROW))
    lef = lefdef.Lef()
    for f in lefs:
        lefdef.read_lef(f, lef)
    def_path = os.path.join(pb.SCR, "l4c.def")
    comps = pb.build_def(lef, def_path)
    fl = lefdef.def2flat(def_path, lefs, pb.LIB, T)
    ex = extract.extract(fl, T)
    d0 = pb.path_delays(ex, lef, comps)
    f0 = {(inst, kind): max(d.fingers for d in ex.devices if d.prov.split("/")[1] == inst and d.kind == kind)
          for inst in ("u1", "u6") for kind in ("p", "n")}
    print("== 1. A = u1(inv_4: P %d / N %d fingers) -> u4 short; B = u6(inv_1) -> u9 over %.0f um of met2" % (f0[("u1", "p")], f0[("u1", "n")], 2 * pb.DETOUR_B))
    print("   baseline 50%% delays driver+receiver: A rise/fall %.1f/%.1f ps (transitions %.0f/%.0f), B %.1f/%.1f ps (transitions %.0f/%.0f); imbalance rise+fall %.1f ps" % (
        d0["a"][4], d0["a"][5], d0["a"][8], d0["a"][9], d0["b"][4], d0["b"][5], d0["b"][8], d0["b"][9], abs(d0["a"][4] - d0["b"][4]) + abs(d0["a"][5] - d0["b"][5])))

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
        """0 = the library's hvt PMOS, 1 = standard Vt (the implant cut away): a free speed-up of the rising edge."""
        def apply(f_, e_, n):
            if n == 0:
                return []
            e_ = extract.extract(f_, T)
            dev = max((d for d in e_.devices if d.prov.split("/")[1] == inst and d.kind == "p"), key=lambda d: d.fingers)
            return moves.set_vt(f_, e_, dev, "std")
        return apply
    LENGTHS = [0.15, 0.18, 0.25]
    def glen(inst, kind):
        """gate length index into LENGTHS for the biggest device of that polarity: a slow-down at zero area."""
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
    spread0 = abs(d0["a"][4] - d0["b"][4]) + abs(d0["a"][5] - d0["b"][5]); mean0 = (d0["a"][0] + d0["b"][0]) / 2
    base_total = sum(f0.values())
    e_base = power.energy_fJ(ex)
    print("   switched energy of the design: %.1f fJ/transition" % e_base)
    def cost(f_, e_, x):
        d = pb.path_delays(e_, lef, comps)
        # both edges: an NMOS removed from the fast driver now slows its falling edge
        sp = abs(d["a"][4] - d["b"][4]) + abs(d["a"][5] - d["b"][5]); mean = (d["a"][0] + d["b"][0]) / 2
        # the power price is the switched capacitance the layout now carries, not a finger count:
        # a finger adds gate and diffusion C, a removed one takes it away, a Vt change adds none
        e = power.energy_fJ(e_)
        return sp / spread0 + 0.05 * mean / mean0 + 0.5 * (e - e_base) / e_base, {"A_rise": d["a"][4], "A_fall": d["a"][5], "B_rise": d["b"][4], "B_fall": d["b"][5], "spread_ps": sp, "E_fJ": e}
    print("== 2. greedy search: u1 P/N in 1..%d (stock %d), u6 P/N in 1..4 (stock 1), u6 PMOS Vt hvt/std; states rebuilt from the base" % (f0[("u1", "p")] + 1, f0[("u1", "p")]))
    prob = optimize.DiscreteProblem(fl, T, variables, cost)
    best = optimize.greedy_search(prob, verbose=True)
    d1 = pb.path_delays(best.ex, lef, comps)
    print("== 3. result: %s -> A rise/fall %.1f/%.1f ps, B %.1f/%.1f ps, imbalance rise+fall %.1f ps (was %.1f); fingers %d -> %d; switched energy %.1f -> %.1f fJ (%+.1f%%); legal=%s topology_ok=%s violations=%d; %d states" % (
        dict(zip([v.name for v in variables], best.x)), d1["a"][4], d1["a"][5], d1["b"][4], d1["b"][5], abs(d1["a"][4] - d1["b"][4]) + abs(d1["a"][5] - d1["b"][5]), spread0,
        base_total, sum(x for v, x in zip(variables, best.x) if not (v.name.endswith("_vt") or v.name[-3:-1] == "_l")), e_base, power.energy_fJ(best.ex), 100 * (power.energy_fJ(best.ex) - e_base) / e_base,
        best.legal, best.signature_ok, best.violations, len(prob.cache)))
    for inst in ("u1", "u6"):
        print("   %s devices: %s" % (inst, ["%s W=%.2f L=%.2f fingers=%d %s" % (d.kind, d.w, d.l, d.fingers, T.flavour_of_model(d.model)) for d in best.ex.devices if d.prov.split("/")[1] == inst]))
    gds.write_flat(best.fl, os.path.join(EVID, "l4_path_balanced_twoway.gds"))
    print("   wrote evidence/l4_path_balanced_twoway.gds")


if __name__ == "__main__":
    main()
