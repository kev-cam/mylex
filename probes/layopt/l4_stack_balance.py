#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""layopt L4 probe 4: balance two paths when the slow driver is a series
STACK -- a nor4_1 whose rising edge goes through four PMOS in series -- and
the layout sits between real rows (a row of nand2_1 above, FS), so a far-gate
contact head cannot borrow the rail side.  The nor4's PMOS finger only exists
through the spread retry (`add_finger` mirrors the four-stack at one poly
pitch wider than stock, see LAYOUT-OPT.md "The nor4 stack heads").

Path A: u1 = inv_1 -> u4 (nand2_1) over a short wire.
Path B: u6 = nor4_1 -> u9 (nand2_1) over the same short wire; slow on the
rising edge by the stack, on the falling edge by its 0.65 um NMOS.  Path B's
input is the nor4's outermost one (the input whose devices a finger move
reaches); the other three are quiet.

Variables: fingers of u1 P/N and u6 P/N, u6 PMOS Vt (all four stacked gates),
u1 gate length (the way to slow the fast path at no area).  Cost as the
two-way probe: delay spread over both edges, a small mean term, switched energy.

Usage: l4_stack_balance.py [--lib DIR] [--scratch DIR]
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
import l4_path_balance as pb                                          # noqa: E402
from layopt import extract, gds, lefdef, moves, optimize, power, rc, tech   # noqa: E402

T = tech.SKY130
P = pb.P
EVID = pb.EVID
ROW = ["inv_1", "fill_4", "fill_4", "nand2_1", "fill_8", "nor4_1", "fill_8", "fill_8", "nand2_1", "fill_8"]
STACK = {"u1": (1, 1), "u6": (4, 1)}      # series depth of the pull-up / pull-down network per driver


def build_def(lef, path):
    comps = []
    x = 0
    for k, c in enumerate(ROW):
        comps.append(lefdef.DefComponent("u%d" % (k + 1), P + c, x, 0, "N", True)); x += int(round(lef.macros[P + c].size[0] * 1000))
    w_nand = int(round(lef.macros[P + "nand2_1"].size[0] * 1000))
    for k in range(int(math.ceil(x / w_nand))):
        comps.append(lefdef.DefComponent("r%d" % k, P + "nand2_1", k * w_nand, 2720, "FS", True))
    by = {c.inst: c for c in comps}
    g = lambda v: int(round(v * 1000))
    nets = []
    for name, drv, rcv, ty in (("a", "u1", "u4", 6.0), ("b", "u6", "u9", 6.4)):
        xd, yd, _ = pb.pin_center(lef, by[drv], "Y"); xr, yr, _ = pb.pin_center(lef, by[rcv], "A")
        nets.append("- %s ( %s Y ) ( %s A ) + ROUTED met1 ( %d %d ) L1M1_PR NEW met1 ( %d %d ) M1M2_PR NEW met2 ( %d %d ) ( %d %d ) M2M3_PR"
                    " NEW met3 ( %d %d ) ( %d %d ) M2M3_PR NEW met2 ( %d %d ) ( %d %d ) NEW met1 ( %d %d ) M1M2_PR NEW met1 ( %d %d ) L1M1_PR ;" % (
                        name, drv, rcv, g(xd), g(yd), g(xd), g(yd), g(xd), g(yd), g(xd), g(ty), g(xd), g(ty), g(xr), g(ty), g(xr), g(ty), g(xr), g(yr), g(xr), g(yr), g(xr), g(yr)))
    lines = ["VERSION 5.8 ;", "DESIGN l4d ;", "UNITS DISTANCE MICRONS 1000 ;", "DIEAREA ( 0 0 ) ( %d 7000 ) ;" % x,
             "COMPONENTS %d ;" % len(comps)]
    lines += ["- %s %s + PLACED ( %d %d ) %s ;" % (c.inst, c.macro, c.x, c.y, c.orient) for c in comps]
    lines += ["END COMPONENTS", "SPECIALNETS 2 ;",
              "- VPWR " + " ".join("( %s VPWR )" % c.inst for c in comps) + " + USE POWER ;",
              "- VGND " + " ".join("( %s VGND )" % c.inst for c in comps) + " + USE GROUND ;",
              "END SPECIALNETS", "NETS %d ;" % len(nets)] + nets + ["END NETS", "END DESIGN"]
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return comps


def path_delays(ex, lef, comps):
    """Like l4_path_balance.path_delays, with the driver's series depth: the
    pull-up of a nor4 is four PMOS in series, so its effective width is the
    summed PMOS width over the depth (parallel branches) and the stack factor
    of the drive model applies; its pull-down is the one NMOS of the switching
    input (the outermost device)."""
    by = {c.inst: c for c in comps}
    dm = T.drive
    out = {}
    for name, drv_inst, rcv_inst in (("a", "u1", "u4"), ("b", "u6", "u9")):
        net = [n for n in ex.nets.values() if n.name == name][0]
        sp, sn = STACK[drv_inst]
        pdev = [d for d in ex.devices if d.prov.split("/")[1] == drv_inst and d.kind == "p"]
        ndev = [d for d in ex.devices if d.prov.split("/")[1] == drv_inst and d.kind == "n"]
        wp = sum(d.w for d in pdev) / sp
        if sn == 1 and len(ndev) > 1:      # parallel pull-downs: the switching input's device
            outer = max(ndev, key=lambda d: max(ex.shapes[g].rect[2] for g in d.gate_ids))
            wn = outer.w
        else:
            wn = sum(d.w for d in ndev) / sn
        rp = sum(d.w for d in ex.devices if d.prov.split("/")[1] == rcv_inst and d.kind == "p")
        rn = sum(d.w for d in ex.devices if d.prov.split("/")[1] == rcv_inst and d.kind == "n")
        flav = {}; glen = {}
        for inst in (drv_inst, rcv_inst):
            for kind in ("p", "n"):
                ds = [d for d in ex.devices if d.prov.split("/")[1] == inst and d.kind == kind]
                flav[(inst, kind)] = T.flavour_of_model(ds[0].model) if ds else None
                glen[(inst, kind)] = max(d.l for d in ds) if ds else None
        xd, yd, _ = pb.pin_center(lef, by[drv_inst], "Y"); xr, yr, _ = pb.pin_center(lef, by[rcv_inst], "A")
        dd = pb.shape_at(ex, "li", xd, yd); rr = pb.shape_at(ex, "li", xr, yr)
        c_net = rc.net_rc(ex, net.id).c_fF + pb.C_IN
        res = {}
        for edge, w, st, w_rcv, other in (("rise", wp, sp, rn, "fall"), ("fall", wn, sn, rp, "rise")):
            kd = "p" if edge == "rise" else "n"; kr = "p" if other == "rise" else "n"
            fd = flav[(drv_inst, kd)]; fr_ = flav[(rcv_inst, kr)]; ld = glen[(drv_inst, kd)]; lr = glen[(rcv_inst, kr)]
            r = dm.r_rise(w, st, flavour=fd, l_um=ld) if edge == "rise" else dm.r_fall(w, st, flavour=fd, l_um=ld)
            elm = rc.elmore_delays(ex, net.id, dd, [rr], r, {rr: pb.C_IN})[rr]
            d_drv, tr = dm.stage(edge, w, c_net, elm, pb.S_IN, st, flavour=fd, l_um=ld)
            r2 = dm.r_rise(w_rcv, flavour=fr_, l_um=lr) if other == "rise" else dm.r_fall(w_rcv, flavour=fr_, l_um=lr)
            d_rcv, _ = dm.stage(other, w_rcv, pb.C_RCV, r2 * pb.C_RCV / 1000.0, tr, flavour=fr_, l_um=lr)
            res[edge] = (d_drv + d_rcv, tr)
        out[name] = (max(res["rise"][0], res["fall"][0]), wp, dm.r_rise(wp, sp, flavour=flav[(drv_inst, "p")]), c_net - pb.C_IN, res["rise"][0], res["fall"][0], wn,
                     dm.r_fall(wn, sn, flavour=flav[(drv_inst, "n")]), res["rise"][1], res["fall"][1])
    return out


def main():
    os.makedirs(EVID, exist_ok=True)
    lefs = [os.path.join(pb.LIB, "sky130_fd_sc_hd.tlef")] + sorted(set(os.path.join(pb.LIB, P + c + ".lef") for c in ROW))
    lef = lefdef.Lef()
    for f in lefs:
        lefdef.read_lef(f, lef)
    def_path = os.path.join(pb.SCR, "l4d.def")
    comps = build_def(lef, def_path)
    fl = lefdef.def2flat(def_path, lefs, pb.LIB, T)
    ex = extract.extract(fl, T)
    d0 = path_delays(ex, lef, comps)
    print("== 1. A = u1(inv_1) -> u4 short; B = u6(nor4_1: PMOS four-stack W %.2f, NMOS W %.2f) -> u9 short; a row of nand2_1 above (FS)" % (d0["b"][1], d0["b"][6]))
    print("   baseline 50%% delays driver+receiver: A rise/fall %.1f/%.1f ps, B %.1f/%.1f ps (R_rise %.0f / R_fall %.0f ohm); imbalance rise+fall %.1f ps" % (
        d0["a"][4], d0["a"][5], d0["b"][4], d0["b"][5], d0["b"][2], d0["b"][7], abs(d0["a"][4] - d0["b"][4]) + abs(d0["a"][5] - d0["b"][5])))
    f0 = {("u1", "p"): 1, ("u1", "n"): 1, ("u6", "p"): 1, ("u6", "n"): 1}

    def fingers(inst, kind):
        def apply(f_, e_, n):
            t = []
            for _ in range(abs(n - f0[(inst, kind)])):
                e_ = extract.extract(f_, T)
                devs = [d for d in e_.devices if d.prov.split("/")[1] == inst and d.kind == kind]
                dev = max(devs, key=lambda d: max(e_.shapes[g].rect[2] for g in d.gate_ids))     # outermost: the one a finger can mirror
                t += (moves.add_finger if n > f0[(inst, kind)] else moves.remove_finger)(f_, e_, dev, side="high")
                if kind == "p" and inst == "u6" and moves.LAST_SPREAD[0]:
                    print("      (u6 PMOS stack mirrored with a %.2f um spread)" % moves.LAST_SPREAD[0])
            return t
        return apply

    def vt(inst):
        """every PMOS of the instance to standard Vt: in a series stack all four
        gates carry the edge, so the implant has to leave all of them (the delay
        model takes the stack's flavour from its devices, and it must be one)"""
        def apply(f_, e_, n):
            if n == 0:
                return []
            t = []
            for _ in range(16):
                e_ = extract.extract(f_, T)
                left = [d for d in e_.devices if d.prov.split("/")[1] == inst and d.kind == "p" and T.flavour_of_model(d.model) != "std"]
                if not left:
                    break
                t += moves.set_vt(f_, e_, left[0], "std")       # sweeps the strip's companions along
            return t
        return apply

    LENGTHS = [0.15, 0.18, 0.25]
    def glen(inst, kind):
        """gate length of the fast driver's device: a slow-down at zero area"""
        def apply(f_, e_, n):
            if n == 0:
                return []
            e_ = extract.extract(f_, T)
            dev = max((d for d in e_.devices if d.prov.split("/")[1] == inst and d.kind == kind), key=lambda d: d.fingers)
            return moves.set_gate_length(f_, e_, dev, LENGTHS[n])
        return apply
    variables = [optimize.IntVariable("u1_p", 1, 3, 1, fingers("u1", "p")),
                 optimize.IntVariable("u1_n", 1, 3, 1, fingers("u1", "n")),
                 optimize.IntVariable("u6_p", 1, 2, 1, fingers("u6", "p")),
                 optimize.IntVariable("u6_n", 1, 3, 1, fingers("u6", "n")),
                 optimize.IntVariable("u6_vt", 0, 1, 0, vt("u6")),
                 optimize.IntVariable("u1_lp", 0, 2, 0, glen("u1", "p")),
                 optimize.IntVariable("u1_ln", 0, 2, 0, glen("u1", "n"))]
    spread0 = abs(d0["a"][4] - d0["b"][4]) + abs(d0["a"][5] - d0["b"][5]); mean0 = (d0["a"][0] + d0["b"][0]) / 2
    e_base = power.energy_fJ(ex)
    print("   switched energy of the design: %.1f fJ/transition" % e_base)

    def cost(f_, e_, x):
        d = path_delays(e_, lef, comps)
        sp = abs(d["a"][4] - d["b"][4]) + abs(d["a"][5] - d["b"][5]); mean = (d["a"][0] + d["b"][0]) / 2
        e = power.energy_fJ(e_)
        return sp / spread0 + 0.05 * mean / mean0 + 0.5 * (e - e_base) / e_base, {"A_rise": d["a"][4], "A_fall": d["a"][5], "B_rise": d["b"][4], "B_fall": d["b"][5], "spread_ps": sp, "E_fJ": e}
    print("== 2. greedy search: u1 P/N 1..3, u1 gate length in %s, u6 P 1..2 (the stack, spread retry), u6 N 1..3, u6 PMOS Vt; states rebuilt from the base" % LENGTHS)
    prob = optimize.DiscreteProblem(fl, T, variables, cost)
    best = optimize.greedy_search(prob, verbose=True)
    d1 = path_delays(best.ex, lef, comps)
    print("== 3. result: %s -> A rise/fall %.1f/%.1f ps, B %.1f/%.1f ps, imbalance rise+fall %.1f ps (was %.1f); switched energy %.1f -> %.1f fJ (%+.1f%%); legal=%s topology_ok=%s violations=%d; %d states" % (
        dict(zip([v.name for v in variables], best.x)), d1["a"][4], d1["a"][5], d1["b"][4], d1["b"][5], abs(d1["a"][4] - d1["b"][4]) + abs(d1["a"][5] - d1["b"][5]), spread0,
        e_base, power.energy_fJ(best.ex), 100 * (power.energy_fJ(best.ex) - e_base) / e_base, best.legal, best.signature_ok, best.violations, len(prob.cache)))
    for inst in ("u1", "u6"):
        print("   %s devices: %s" % (inst, ["%s W=%.2f L=%.2f fingers=%d %s" % (d.kind, d.w, d.l, d.fingers, T.flavour_of_model(d.model)) for d in best.ex.devices if d.prov.split("/")[1] == inst]))
    gds.write_flat(best.fl, os.path.join(EVID, "l4_stack_balanced.gds"))
    print("   wrote evidence/l4_stack_balanced.gds")


if __name__ == "__main__":
    main()
