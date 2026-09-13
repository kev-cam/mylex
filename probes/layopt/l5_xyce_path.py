#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""layopt L5 probe 1: Xyce on the extracted path.  The two-way balance layout
(u1 = inv_4 -> u4 over a short wire; u6 = inv_1 -> u9 over 120 um of met2)
is extracted and each path's cells and wiring go to Xyce as a deck of the
layout's own transistors and distributed RC (layopt/spice.py).  Measured:
the driver's 50 % delay to the receiver's gate, the receiver's own delay,
the transition at the receiver, and the switched energy, at the library's
three corners (tt 1.8 V 25 C, ss 1.6 V 100 C, ff 1.95 V -40 C) -- and the
same quantities from the Liberty-fitted drive model at tt, which is what the
balance probes have used so far.

    python3 probes/layopt/l5_xyce_path.py [--scratch DIR] [--corners tt,ss,ff]
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
import l4_path_balance as pb                                          # noqa: E402
from layopt import extract, lefdef, rc, spice, tech                   # noqa: E402

T = tech.SKY130
SCR = sys.argv[sys.argv.index("--scratch") + 1] if "--scratch" in sys.argv else os.environ.get("LAYOPT_SCRATCH", "/tmp")
CORN = (sys.argv[sys.argv.index("--corners") + 1] if "--corners" in sys.argv else "tt,ss,ff").split(",")


def path_deck(ex, lef, comps, drv, rcv, models, corner, edge):
    """A deck for one path: the driver and receiver cells, the wire between, the
    step at the driver's input; delays at the receiver's input pin and output."""
    by = {c.inst: c for c in comps}
    xa, ya, _ = pb.pin_center(lef, by[drv], "A"); xd, yd, _ = pb.pin_center(lef, by[drv], "Y")
    xr, yr, _ = pb.pin_center(lef, by[rcv], "A"); xo, yo, _ = pb.pin_center(lef, by[rcv], "Y")
    s_in, s_drv, s_rcv, s_out = (rc.shape_at(ex, "li", x, y) for x, y in ((xa, ya), (xd, yd), (xr, yr), (xo, yo)))
    d = spice.Deck(ex, {drv, rcv}, models, corner)
    d.stimulus(s_in, edge=edge, slew_ps=pb.S_IN)
    other = "fall" if edge == "rise" else "rise"
    d.measure("d_drv", (s_in, 0.5, edge), (s_rcv, 0.5, other))            # driver + wire: input 50 % -> receiver pin 50 %
    d.measure("d_rcv", (s_rcv, 0.5, other), (s_out, 0.5, edge))           # the receiver's own stage
    d.measure_slew("tr_rcv", s_rcv, other)
    # the receiver drives C_RCV like the model does
    d.extra.append("CRCV %s 0 %gf" % (d.node(s_out), pb.C_RCV))
    return d


def main():
    lefs = [os.path.join(pb.LIB, "sky130_fd_sc_hd.tlef")] + sorted({os.path.join(pb.LIB, pb.P + c + ".lef") for c in pb.ROW})
    pb.ROW[:] = ["inv_4", "fill_4", "fill_4", "nand2_1", "fill_8", "inv_1", "fill_4", "fill_4", "nand2_1", "fill_8"]
    lefs = [os.path.join(pb.LIB, "sky130_fd_sc_hd.tlef")] + sorted({os.path.join(pb.LIB, pb.P + c + ".lef") for c in pb.ROW})
    lef = lefdef.Lef()
    for f in lefs:
        lefdef.read_lef(f, lef)
    def_path = os.path.join(SCR, "l5a.def")
    comps = pb.build_def(lef, def_path)
    fl = lefdef.def2flat(def_path, lefs, pb.LIB, T)
    ex = extract.extract(fl, T)
    model = pb.path_delays(ex, lef, comps)
    print("== 1. the two-way balance layout: A = u1(inv_4) -> u4 short, B = u6(inv_1) -> u9 over %.0f um of met2; %d devices extracted" % (2 * pb.DETOUR_B, len(ex.devices)))
    print("   drive model at tt (driver+receiver, both edges): A %.1f/%.1f ps, B %.1f/%.1f ps; transitions at the receivers A %.0f/%.0f, B %.0f/%.0f ps" % (
        model["a"][4], model["a"][5], model["b"][4], model["b"][5], model["a"][8], model["a"][9], model["b"][8], model["b"][9]))
    print("== 2. Xyce on the extracted cells and wiring (per finger BSIM4, distributed RC)")
    print("   %-6s %-5s %-6s | %8s %8s %8s %8s | %8s %8s | %8s" % ("corner", "path", "edge", "d_drv", "d_rcv", "total", "model", "tr_rcv", "model", "E fJ"))
    for cname in CORN:
        models = spice.Models(T, cname, scratch=os.path.join(SCR, "xyce_models"))
        corner = spice.Corner.named(cname)
        for name, drv, rcv in (("A", "u1", "u4"), ("B", "u6", "u9")):
            for edge in ("rise", "fall"):        # the edge at the driver's OUTPUT
                t0 = time.time()
                d = path_deck(ex, lef, comps, drv, rcv, models, corner, "fall" if edge == "rise" else "rise")
                res = d.run(os.path.join(SCR, "l5_%s_%s_%s.cir" % (name, edge, corner.tag)))
                if not res["_ok"] or res.get("d_drv") is None:
                    print("   %-6s %-5s %-6s | Xyce failed: %s" % (cname, name, edge, res["_log"][-200:].replace("\n", " | "))); continue
                key = 4 if edge == "rise" else 5; tkey = 8 if edge == "rise" else 9
                m = model[name.lower()]
                dd, dr = res["d_drv"] * 1e12, res["d_rcv"] * 1e12
                print("   %-6s %-5s %-6s | %8.1f %8.1f %8.1f %8.1f | %8.1f %8.1f | %8.2f   (%d M, %d R, %d C, %.0fs)" % (
                    cname, name, edge, dd, dr, dd + dr, m[key] if cname == "tt" else float("nan"), res["tr_rcv"] * 1e12, m[tkey] if cname == "tt" else float("nan"),
                    res.get("energy_fJ", float("nan")), d.stats["devices"], d.stats["resistors"], d.stats["capacitors"], time.time() - t0))


if __name__ == "__main__":
    main()
