#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""layopt L4 probe 2: balance two paths with a DISCRETE dissolve move.

Two identical inverters (inv_1, each followed by a fill_4) drive two receivers:
path A over a short wire, path B over a long met2 detour (~120 um, several
times the receiver's input capacitance).  B is slower.  Wire sizing cannot
speed B up much (metal R is already negligible against a 3 kohm driver), but
adding fingers to B's driver -- into the filler next to it -- can.  The greedy
discrete search chooses finger counts for both drivers (P and N separately)
under the topology + rule guard; the driver model is R_drv = R0 * W0 / W.

Usage: l4_path_balance.py [--lib DIR] [--scratch DIR]
"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
from layopt import drc, extract, gds, lefdef, moves, objective, optimize, rc, tech   # noqa: E402

LIB = os.path.expanduser(sys.argv[sys.argv.index("--lib") + 1] if "--lib" in sys.argv else "~/tools/sky130_fd_sc_hd")
SCR = sys.argv[sys.argv.index("--scratch") + 1] if "--scratch" in sys.argv else os.environ.get("LAYOPT_SCRATCH", "/tmp")
EVID = os.path.join(HERE, "evidence")
T = tech.SKY130
P = "sky130_fd_sc_hd__"
# driver resistances come from tech.SKY130.drive (two edges; probes/layopt/drive_fit.py)
C_IN = 2.1                # fF receiver gate
ROW = ["inv_1", "fill_4", "fill_4", "nand2_1", "fill_8", "inv_1", "fill_4", "fill_4", "nand2_1", "fill_8"]
DETOUR_B = 60.0           # um out (and back): ~120 um of met2 on path B


def pin_center(lef, comp, pin):
    m = lef.macros[comp.macro]
    lname, (a, b, c, d) = m.pins[pin].ports[0]
    return comp.x / 1000.0 + (a + c) / 2, comp.y / 1000.0 + (b + d) / 2, lname   # N orientation only


def build_def(lef, path):
    comps = []
    x = 0
    for k, c in enumerate(ROW):
        comps.append(lefdef.DefComponent("u%d" % (k + 1), P + c, x, 0, "N", True)); x += int(round(lef.macros[P + c].size[0] * 1000))
    by = {c.inst: c for c in comps}
    g = lambda v: int(round(v * 1000))
    nets = []
    # path A: u1.Y -> u4.A, straight: up to met2, over on met3, down
    xd, yd, _ = pin_center(lef, by["u1"], "Y"); xr, yr, _ = pin_center(lef, by["u4"], "A")
    ty = 3.6
    nets.append("- a ( u1 Y ) ( u4 A ) + ROUTED met1 ( %d %d ) L1M1_PR NEW met1 ( %d %d ) M1M2_PR NEW met2 ( %d %d ) ( %d %d ) M2M3_PR"
                " NEW met3 ( %d %d ) ( %d %d ) M2M3_PR NEW met2 ( %d %d ) ( %d %d ) NEW met1 ( %d %d ) M1M2_PR NEW met1 ( %d %d ) L1M1_PR ;" % (
                    g(xd), g(yd), g(xd), g(yd), g(xd), g(yd), g(xd), g(ty), g(xd), g(ty), g(xr), g(ty), g(xr), g(ty), g(xr), g(yr), g(xr), g(yr), g(xr), g(yr)))
    # path B: u6.Y -> u9.A with a met2 detour above the row
    xd, yd, _ = pin_center(lef, by["u6"], "Y"); xr, yr, _ = pin_center(lef, by["u9"], "A")
    y1, y2 = 5.0, 5.6
    nets.append("- b ( u6 Y ) ( u9 A ) + ROUTED met1 ( %d %d ) L1M1_PR NEW met1 ( %d %d ) M1M2_PR"
                " NEW met2 ( %d %d ) ( %d %d ) ( %d %d ) ( %d %d ) ( %d %d ) ( %d %d ) M1M2_PR NEW met1 ( %d %d ) ( %d %d ) L1M1_PR ;" % (
                    g(xd), g(yd), g(xd), g(yd),
                    g(xd), g(yd), g(xd), g(y1), g(xd + DETOUR_B), g(y1), g(xd + DETOUR_B), g(y2), g(xr + 0.5), g(y2), g(xr + 0.5), g(yr),
                    g(xr + 0.5), g(yr), g(xr), g(yr)))
    lines = ["VERSION 5.8 ;", "DESIGN l4b ;", "UNITS DISTANCE MICRONS 1000 ;", "DIEAREA ( 0 0 ) ( %d 6500 ) ;" % (x + g(DETOUR_B)),
             "COMPONENTS %d ;" % len(comps)]
    lines += ["- %s %s + PLACED ( %d %d ) %s ;" % (c.inst, c.macro, c.x, c.y, c.orient) for c in comps]
    lines += ["END COMPONENTS", "SPECIALNETS 2 ;",
              "- VPWR " + " ".join("( %s VPWR )" % c.inst for c in comps) + " + USE POWER ;",
              "- VGND " + " ".join("( %s VGND )" % c.inst for c in comps) + " + USE GROUND ;",
              "END SPECIALNETS", "NETS %d ;" % len(nets)] + nets + ["END NETS", "END DESIGN"]
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return comps


def shape_at(ex, layer, x_um, y_um):
    x, y = int(round(x_um / ex.dbu_um)), int(round(y_um / ex.dbu_um))
    for i, s in enumerate(ex.shapes):
        if s.layer == layer and s.rect[0] <= x <= s.rect[2] and s.rect[1] <= y <= s.rect[3]:
            return i
    raise KeyError((layer, x_um, y_um))


def path_delays(ex, lef, comps):
    """Elmore delay of path A and B (ps) on both edges: the driver's PMOS width
    sets R_rise, its NMOS width R_fall (tech.SKY130.drive, fitted from the
    Liberty).  Returns per path (worst edge, W_p, R_rise, C_fF, rise, fall,
    W_n, R_fall)."""
    by = {c.inst: c for c in comps}
    dm = T.drive
    out = {}
    for name, drv_inst, rcv_inst in (("a", "u1", "u4"), ("b", "u6", "u9")):
        net = [n for n in ex.nets.values() if n.name == name][0]
        wp = sum(d.w for d in ex.devices if d.prov.split("/")[1] == drv_inst and d.kind == "p")
        wn = sum(d.w for d in ex.devices if d.prov.split("/")[1] == drv_inst and d.kind == "n")
        r_rise, r_fall = dm.r_rise(wp), dm.r_fall(wn)
        xd, yd, _ = pin_center(lef, by[drv_inst], "Y"); xr, yr, _ = pin_center(lef, by[rcv_inst], "A")
        dd = shape_at(ex, "li", xd, yd); rr = shape_at(ex, "li", xr, yr)
        rise = rc.elmore_delays(ex, net.id, dd, [rr], r_rise, {rr: C_IN})[rr]
        fall = rc.elmore_delays(ex, net.id, dd, [rr], r_fall, {rr: C_IN})[rr]
        out[name] = (max(rise, fall), wp, r_rise, rc.net_rc(ex, net.id).c_fF, rise, fall, wn, r_fall)
    return out


def main():
    os.makedirs(EVID, exist_ok=True)
    lefs = [os.path.join(LIB, "sky130_fd_sc_hd.tlef")] + sorted(glob.glob(os.path.join(LIB, P + "*.lef")))
    lef = lefdef.Lef()
    for f in lefs:
        lefdef.read_lef(f, lef)
    def_path = os.path.join(SCR, "l4b.def")
    comps = build_def(lef, def_path)
    fl = lefdef.def2flat(def_path, lefs, LIB, T)
    ex = extract.extract(fl, T)
    d0 = path_delays(ex, lef, comps)
    print("== 1. two paths: A = u1(inv_1) -> u4 over %.0f fF; B = u6(inv_1) -> u9 over a %.0f um met2 detour, %.1f fF" % (d0["a"][3], 2 * DETOUR_B, d0["b"][3]))
    print("   baseline delays (worst edge): A %.1f ps (rise %.1f / fall %.1f), B %.1f ps (rise %.1f / fall %.1f); driver R_rise %.0f / R_fall %.0f ohm; imbalance %.1f ps" % (
        d0["a"][0], d0["a"][4], d0["a"][5], d0["b"][0], d0["b"][4], d0["b"][5], d0["a"][2], d0["a"][7], abs(d0["a"][0] - d0["b"][0])))

    def fingers(inst, kind):
        def apply(f_, e_, n):
            t = []
            for _ in range(n - 1):
                e_ = extract.extract(f_, T)
                dev = [d for d in e_.devices if d.prov.split("/")[1] == inst and d.kind == kind][0]
                t += moves.add_finger(f_, e_, dev, side="high")
            return t
        return apply
    variables = [optimize.IntVariable("u6_p", 1, 4, 1, fingers("u6", "p")), optimize.IntVariable("u6_n", 1, 4, 1, fingers("u6", "n")),
                 optimize.IntVariable("u1_p", 1, 4, 1, fingers("u1", "p")), optimize.IntVariable("u1_n", 1, 4, 1, fingers("u1", "n"))]
    spread0 = abs(d0["a"][4] - d0["b"][4]) + abs(d0["a"][5] - d0["b"][5])
    mean0 = (d0["a"][0] + d0["b"][0]) / 2
    def cost(f_, e_, x):
        d = path_delays(e_, lef, comps)
        # both edges must balance: rise against rise, fall against fall
        sp = abs(d["a"][4] - d["b"][4]) + abs(d["a"][5] - d["b"][5]); mean = (d["a"][0] + d["b"][0]) / 2
        extra = sum(x.values()) - len(x)               # fingers added: an area/power price
        return sp / spread0 + 0.05 * mean / mean0 + 0.02 * extra, {"A_rise": d["a"][4], "A_fall": d["a"][5], "B_rise": d["b"][4], "B_fall": d["b"][5], "spread_ps": sp}
    print("== 2. greedy search over finger counts (u6 P/N, u1 P/N in 1..4), each state rebuilt from the base layout")
    prob = optimize.DiscreteProblem(fl, T, variables, cost)
    best = optimize.greedy_search(prob, verbose=True)
    d1 = path_delays(best.ex, lef, comps)
    print("== 3. result: %s -> A rise/fall %.1f/%.1f ps, B %.1f/%.1f ps, imbalance rise+fall %.1f ps (was %.1f); legal=%s topology_ok=%s violations=%d; %d states evaluated" % (
        dict(zip([v.name for v in variables], best.x)), d1["a"][4], d1["a"][5], d1["b"][4], d1["b"][5], abs(d1["a"][4] - d1["b"][4]) + abs(d1["a"][5] - d1["b"][5]), spread0,
        best.legal, best.signature_ok, best.violations, len(prob.cache)))
    for inst in ("u1", "u6"):
        print("   %s devices: %s" % (inst, ["%s W=%.2f fingers=%d" % (d.kind, d.w, d.fingers) for d in best.ex.devices if d.prov.split("/")[1] == inst]))
    gds.write_flat(best.fl, os.path.join(EVID, "l4_path_balanced.gds"))
    print("   wrote evidence/l4_path_balanced.gds")


if __name__ == "__main__":
    main()
