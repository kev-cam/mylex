#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""layopt L3 probe: balance an isochronic fork by resizing its branch wires.

ASYNC-PLAN §4: QDI correctness rests on isochronic forks; formal enumerates
which forks, layout decides whether the branches are matched.  Here the path
set is given by hand (nulex's constraint extraction will emit it): on the L2
standard-cell row, net f leaves u1.Y and forks on met3 to two receivers, u2.A
one cell away and v4.A in the other row ~7 um away.  layopt extracts the RC
tree, computes the Elmore delay from the driver pin to each receiver pin, and
the optimizer resizes the two branches (met3 + met2 widths) to minimise the
delay spread under the topology + rule guard.

Usage: l3_fork_balance.py [--lib DIR] [--scratch DIR] [--iters N]
"""
import copy
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
sys.path.insert(0, HERE)
from layopt import drc, extract, gds, lefdef, moves, objective, optimize, rc, tech   # noqa: E402
import l2_stdcell_row as L2                                                           # noqa: E402

LIB = L2.LIB
SCR = sys.argv[sys.argv.index("--scratch") + 1] if "--scratch" in sys.argv else os.environ.get("LAYOPT_SCRATCH", "/tmp")
ITERS = int(sys.argv[sys.argv.index("--iters") + 1]) if "--iters" in sys.argv else 80
EVID = os.path.join(HERE, "evidence")
T = tech.SKY130
P = L2.P
R_DRIVE = 3000.0        # ohm, nominal inv_1 output resistance (sky130, 1.8 V)
C_IN = 2.1              # fF, inv_1 gate: Cox*W*L ~ 8.5 fF/um2 * (0.65+1.0)*0.15 um2
TRACK = 3.57            # um, met3 track for the fork (between the rows' pins, clear of L2's tracks)


def build_def(lef, path, b_layer="met2"):
    """L2's two rows plus one forked net f: u1.Y -> {u2.A, v4.A}.  b_layer: the
    long branch's detour layer -- met2 (low R) or li1 (12.8 ohm/sq, resistive)."""
    comps = []
    x = 0
    for k, c in enumerate(L2.ROW1):
        comps.append(lefdef.DefComponent("u%d" % (k + 1), P + c, x, 0, "N", True)); x += int(round(lef.macros[P + c].size[0] * 1000))
    w1 = x; x = 0
    for k, c in enumerate(L2.ROW2):
        comps.append(lefdef.DefComponent("v%d" % (k + 1), P + c, x, 2720, "FS", True)); x += int(round(lef.macros[P + c].size[0] * 1000))
    width = max(w1, x)
    by = {c.inst: c for c in comps}
    g = lambda v: int(round(v * 1000))
    xd, yd, _ = L2.pin_center(lef, by["u1"], "Y")
    xa, ya, _ = L2.pin_center(lef, by["u2"], "A")
    xb, yb, _ = L2.pin_center(lef, by["v4"], "A")
    ty = TRACK
    # Both branches take a met2 detour above the rows so the fork has real,
    # unequal RC: A loops out 30 um and back (~60 um), B loops out 90 um (~180 um).
    yA1, yA2, yB1, yB2 = 6.2, 6.9, 8.5, 10.0        # legs spaced so no allowed width (<= 6x) can merge them
    dA, dB = 30.0, 90.0
    seg = (" + ROUTED met1 ( %d %d ) L1M1_PR NEW met1 ( %d %d ) M1M2_PR NEW met2 ( %d %d ) ( %d %d ) M2M3_PR"
           " NEW met3 ( %d %d ) ( %d %d )" % (g(xd), g(yd), g(xd), g(yd), g(xd), g(yd), g(xd), g(ty), g(xd), g(ty), g(xa), g(ty)))
    # branch A: fork point (xa, ty) -> up -> out dA to the LEFT (clear of B's descent) -> up -> back to xa-0.5 -> down to ya -> met1 jog
    seg += (" NEW met3 ( %d %d ) M2M3_PR NEW met2 ( %d %d ) ( %d %d ) ( %d %d ) ( %d %d ) ( %d %d ) ( %d %d ) M1M2_PR"
            " NEW met1 ( %d %d ) ( %d %d ) L1M1_PR" % (
                g(xa), g(ty), g(xa), g(ty), g(xa), g(yA1), g(xa - dA), g(yA1), g(xa - dA), g(yA2), g(xa - 0.5), g(yA2), g(xa - 0.5), g(ya),
                g(xa - 0.5), g(ya), g(xa), g(ya)))
    # branch B: met3 on to xa+0.6 -> met2 up -> detour out dB and back on b_layer -> met2 down to yb -> met1 jog
    if b_layer == "met2":
        seg += (" NEW met3 ( %d %d ) ( %d %d ) M2M3_PR NEW met2 ( %d %d ) ( %d %d ) ( %d %d ) ( %d %d ) ( %d %d ) ( %d %d ) M1M2_PR"
                " NEW met1 ( %d %d ) ( %d %d ) L1M1_PR" % (
                    g(xa), g(ty), g(xa + 0.6), g(ty), g(xa + 0.6), g(ty), g(xa + 0.6), g(yB1), g(xa + dB), g(yB1), g(xa + dB), g(yB2),
                    g(xb + 0.5), g(yB2), g(xb + 0.5), g(yb), g(xb + 0.5), g(yb), g(xb), g(yb)))
    else:   # li1 detour: met2 up to yB1, down through M1M2 + L1M1 onto li1, loop on li1, back up to met2, down to the pin
        seg += (" NEW met3 ( %d %d ) ( %d %d ) M2M3_PR NEW met2 ( %d %d ) ( %d %d ) M1M2_PR NEW met1 ( %d %d ) L1M1_PR"
                " NEW li1 ( %d %d ) ( %d %d ) ( %d %d ) ( %d %d ) NEW met1 ( %d %d ) L1M1_PR NEW met1 ( %d %d ) M1M2_PR"
                " NEW met2 ( %d %d ) ( %d %d ) M1M2_PR NEW met1 ( %d %d ) ( %d %d ) L1M1_PR" % (
                    g(xa), g(ty), g(xa + 0.6), g(ty), g(xa + 0.6), g(ty), g(xa + 0.6), g(yB1), g(xa + 0.6), g(yB1),
                    g(xa + 0.6), g(yB1), g(xa + dB), g(yB1), g(xa + dB), g(yB2), g(xb + 0.5), g(yB2),
                    g(xb + 0.5), g(yB2), g(xb + 0.5), g(yB2), g(xb + 0.5), g(yB2), g(xb + 0.5), g(yb), g(xb + 0.5), g(yb), g(xb), g(yb)))
    width = max(width, g(xa + dB + 2))
    lines = ["VERSION 5.8 ;", "DIVIDERCHAR \"/\" ;", "BUSBITCHARS \"[]\" ;", "DESIGN l3fork ;", "UNITS DISTANCE MICRONS 1000 ;",
             "DIEAREA ( 0 0 ) ( %d %d ) ;" % (width, 11000), "", "COMPONENTS %d ;" % len(comps)]
    lines += ["- %s %s + PLACED ( %d %d ) %s ;" % (c.inst, c.macro, c.x, c.y, c.orient) for c in comps]
    lines += ["END COMPONENTS", "", "SPECIALNETS 2 ;",
              "- VPWR " + " ".join("( %s VPWR )" % c.inst for c in comps) + " + USE POWER ;",
              "- VGND " + " ".join("( %s VGND )" % c.inst for c in comps) + " + USE GROUND ;",
              "END SPECIALNETS", "", "NETS 1 ;", "- f ( u1 Y ) ( u2 A ) ( v4 A )" + seg + " ;", "END NETS", "", "END DESIGN"]
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return comps, (xd, yd), (xa, ya), (xb, yb)


def shape_at(ex, layer, x_um, y_um):
    x, y = int(round(x_um / ex.dbu_um)), int(round(y_um / ex.dbu_um))
    for i, s in enumerate(ex.shapes):
        if s.layer == layer and s.rect[0] <= x <= s.rect[2] and s.rect[1] <= y <= s.rect[3]:
            return i
    raise KeyError((layer, x_um, y_um))


def path_r(ex, net_id, drv, rcv):
    """Resistance along the Elmore tree path driver->receiver (ohm), for sanity."""
    import heapq
    segs = rc.net_segments(ex, net_id)
    adj = {}
    for sg in segs:
        adj.setdefault(sg.a, []).append((sg.b, max(sg.r, 1e-3))); adj.setdefault(sg.b, []).append((sg.a, max(sg.r, 1e-3)))
    dist = {drv: 0.0}; pq = [(0.0, drv)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, 1e30): continue
        for v, r in adj.get(u, []):
            if d + r < dist.get(v, 1e30): dist[v] = d + r; heapq.heappush(pq, (d + r, v))
    return dist.get(rcv, float("inf"))


def run_variant(lef, lefs, b_layer):
    def_path = os.path.join(SCR, "l3fork_%s.def" % b_layer)
    comps, drv, ra, rb = build_def(lef, def_path, b_layer)
    fl = lefdef.def2flat(def_path, lefs, LIB, T)
    ex = extract.extract(fl, T)
    fnet = [n for n in ex.nets.values() if n.name == "f"][0]
    print("== variant: long branch detour on %s -- fork net f: %d shapes, device terminals %s" % (b_layer, len(fnet.shapes), sorted(fnet.devices)))
    d_sid = shape_at(ex, "li", *drv); a_sid = shape_at(ex, "li", *ra); b_sid = shape_at(ex, "li", *rb)
    assert ex.net_of_shape[d_sid] == ex.net_of_shape[a_sid] == ex.net_of_shape[b_sid] == fnet.id
    fr = [i for i, r in enumerate(fl.rects) if r.prov == "l3fork/net:f"]
    inv = {v: k for k, v in T.layers.items()}
    long = lambda i: max(fl.rects[i].x1 - fl.rects[i].x0, fl.rects[i].y1 - fl.rects[i].y0) > 2000
    wireA = [i for i in fr if inv.get(fl.rects[i].layer) == "met2" and long(i) and 6000 < fl.rects[i].y0 < 7500]
    wireB = [i for i in fr if inv.get(fl.rects[i].layer) in ("met2", "li") and long(i) and fl.rects[i].y0 > 8000]
    print("   branch A detour: %s   branch B detour: %s" % (
        [(inv[fl.rects[i].layer], round((fl.rects[i].x1 - fl.rects[i].x0) / 1000, 1), round(moves.wire_width_um(fl, i), 3)) for i in wireA],
        [(inv[fl.rects[i].layer], round((fl.rects[i].x1 - fl.rects[i].x0) / 1000, 1), round(moves.wire_width_um(fl, i), 3)) for i in wireB]))

    def measure(ex_, fl_):
        net = [n for n in ex_.nets.values() if n.name == "f"][0].id
        dd = shape_at(ex_, "li", *drv); aa = shape_at(ex_, "li", *ra); bb = shape_at(ex_, "li", *rb)
        return objective.fork_balance(ex_, net, dd, [aa, bb], R_DRIVE, C_IN)

    g0 = measure(ex, fl)
    x0 = rc.net_rc(ex, fnet.id)
    print("   baseline: net C %.2f fF; path R driver->u2.A %.0f ohm, driver->v4.A %.0f ohm; Elmore %.2f / %.2f ps; spread %.2f ps (%.1f%% of mean)" % (
        x0.c_fF, path_r(ex, fnet.id, d_sid, a_sid), path_r(ex, fnet.id, d_sid, b_sid), g0.values[0], g0.values[1], g0.spread, 100 * g0.rel))

    def width_move(wires):
        def apply(f_, e_, scale):
            return [j for i in wires for j in moves.set_wire_width(
                f_, i, max(T.min_width[inv[f_.rects[i].layer]], moves.wire_width_um(fl, i) * scale))]
        return apply
    variables = [optimize.Variable("A_scale", 0.5, 6.0, 1.0, width_move(wireA)),
                 optimize.Variable("B_scale", 0.5, 6.0, 1.0, width_move(wireB))]
    area0 = objective.metal_area_um2(fl, wireA + wireB)
    def cost(f_, e_, x):
        gsp = measure(e_, f_)
        area = objective.metal_area_um2(f_, wireA + wireB)
        return gsp.spread / max(g0.spread, 1e-3) + 0.05 * gsp.mean / g0.mean + 0.02 * area / area0, {"spread_ps": gsp.spread, "mean_ps": gsp.mean, "area": area}
    prob = optimize.Problem(fl, T, variables, cost)
    best = optimize.solve(prob, max_iter=ITERS, verbose=False)
    g1 = measure(best.ex, best.fl)
    fnet1 = [n for n in best.ex.nets.values() if n.name == "f"][0]
    print("   optimized (%d evals, legal=%s): A_scale %.2f B_scale %.2f -> widths A %s B %s" % (
        len(prob.history), best.legal and best.signature_ok, best.x[0], best.x[1],
        [round(moves.wire_width_um(best.fl, i), 3) for i in wireA], [round(moves.wire_width_um(best.fl, i), 3) for i in wireB]))
    print("   result: path R driver->v4.A %.0f ohm; Elmore %.2f / %.2f ps; spread %.2f ps (%.1f%%), was %.2f ps; metal area x%.2f" % (
        path_r(best.ex, fnet1.id, shape_at(best.ex, "li", *drv), shape_at(best.ex, "li", *rb)),
        g1.values[0], g1.values[1], g1.spread, 100 * g1.rel, g0.spread, best.terms["area"] / area0))
    gds.write_flat(best.fl, os.path.join(EVID, "l3fork_%s_balanced.gds" % b_layer))
    return g0, g1


def main():
    os.makedirs(EVID, exist_ok=True)
    lefs = [os.path.join(LIB, "sky130_fd_sc_hd.tlef")] + sorted(glob.glob(os.path.join(LIB, P + "*.lef")))
    lef = lefdef.Lef()
    for f in lefs:
        lefdef.read_lef(f, lef)
    print("driver R %.0f ohm (inv_1 nominal), receiver Cin %.1f fF; a gate delay here is tens of ps" % (R_DRIVE, C_IN))
    run_variant(lef, lefs, "met2")
    run_variant(lef, lefs, "li1")


if __name__ == "__main__":
    main()
