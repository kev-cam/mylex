#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""layopt L2 probe: standard cells in, boundaries dissolved.

Builds a small two-row sky130_fd_sc_hd placement (DEF written from the LEF
sizes), routes a few nets on met1 with L1M1 vias, converts it with
layopt.lefdef.def2flat (cell GDS flattened under placement transforms,
provenance top/<inst>/<macro>), extracts, and checks:
  * device count per instance equals the cell's own extraction
  * VPWR / VGND are single nets spanning every instance (rail abutment,
    including the FS row sharing the VPWR rail)
  * routed nets are named from the DEF and connect the right pins
Then a MOVE on a standard cell: widen the nand2's PMOS pair (shared-provenance
footprint path), re-extract, check topology + rules.

Usage: l2_stdcell_row.py [--lib ~/tools/sky130_fd_sc_hd] [--scratch DIR]
"""
import glob
import os
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
from layopt import drc, extract, gds, lefdef, moves, rc, tech            # noqa: E402

LIB = os.path.expanduser(sys.argv[sys.argv.index("--lib") + 1] if "--lib" in sys.argv else "~/tools/sky130_fd_sc_hd")
SCR = sys.argv[sys.argv.index("--scratch") + 1] if "--scratch" in sys.argv else os.environ.get("LAYOPT_SCRATCH", "/tmp")
EVID = os.path.join(HERE, "evidence")
T = tech.SKY130
P = "sky130_fd_sc_hd__"
ROW1 = ["inv_1", "nand2_1", "inv_2", "dfxtp_1", "decap_4", "fill_1"]
ROW2 = ["buf_1", "nor2_1", "a21o_1", "inv_1", "fill_1", "decap_4"]


def pin_center(lef, comp, pin):
    """Absolute (um) centre of a pin's first port rect for a placed component."""
    m = lef.macros[comp.macro]
    lname, (a, b, c, d) = m.pins[pin].ports[0]
    mirror, angle = lefdef.ORIENT[comp.orient]
    ref = gds.Ref(comp.macro, (0, 0), mirror_x=mirror, angle=angle)
    w, h = int(round(m.size[0] * 1000)), int(round(m.size[1] * 1000))
    corners = [gds._xform(p, ref, (0, 0)) for p in ((0, 0), (w, 0), (0, h), (w, h))]
    off = (comp.x - min(p[0] for p in corners), comp.y - min(p[1] for p in corners))
    cx, cy = gds._xform((int(round((a + c) / 2 * 1000)), int(round((b + d) / 2 * 1000))), ref, off)
    return cx / 1000.0, cy / 1000.0, lname


def build_def(lef, path):
    comps = []
    x = 0
    for k, c in enumerate(ROW1):
        comps.append(lefdef.DefComponent("u%d" % (k + 1), P + c, x, 0, "N", True)); x += int(round(lef.macros[P + c].size[0] * 1000))
    w1 = x; x = 0
    for k, c in enumerate(ROW2):
        comps.append(lefdef.DefComponent("v%d" % (k + 1), P + c, x, 2720, "FS", True)); x += int(round(lef.macros[P + c].size[0] * 1000))
    width = max(w1, x)
    strap_x = min(w1, x) - 230                      # inside both rows (they differ in length)
    # nets: u1.Y -> u2.A ; u2.Y -> u3.A ; u3.Y -> u4.D ; v1.X -> v2.A ; v2.Y -> v3.A1 ; u4.Q -> v1.A (row to row)
    conns = [("n1", [("u1", "Y"), ("u2", "A")]), ("n2", [("u2", "Y"), ("u3", "A")]), ("n3", [("u3", "Y"), ("u4", "D")]),
             ("m1", [("v1", "X"), ("v2", "A")]), ("m2", [("v2", "Y"), ("v3", "A1")]), ("q", [("u4", "Q"), ("v1", "A")])]
    lines = ["VERSION 5.8 ;", "DIVIDERCHAR \"/\" ;", "BUSBITCHARS \"[]\" ;", "DESIGN l2row ;", "UNITS DISTANCE MICRONS 1000 ;",
             "DIEAREA ( 0 0 ) ( %d %d ) ;" % (width, 2 * 2720), "", "COMPONENTS %d ;" % len(comps)]
    for c in comps:
        lines.append("- %s %s + PLACED ( %d %d ) %s ;" % (c.inst, c.macro, c.x, c.y, c.orient))
    lines += ["END COMPONENTS", "", "SPECIALNETS 2 ;",
              "- VPWR " + " ".join("( %s VPWR )" % c.inst for c in comps) + " + USE POWER ;",
              "- VGND " + " ".join("( %s VGND )" % c.inst for c in comps) +
              " + ROUTED met1 ( %d 0 ) M1M2_PR NEW met2 200 ( %d 0 ) ( %d 5440 ) NEW met1 ( %d 5440 ) M1M2_PR + USE GROUND ;" % ((strap_x,) * 4),
              "END SPECIALNETS", "", "NETS %d ;" % len(conns)]
    # Routing: li1 pin -> L1M1 -> M1M2 -> met2 vertical -> M2M3 -> met3 track -> M2M3 -> met2 -> M1M2 -> L1M1.
    # Nothing but the via pads lands on met1, so cell-internal met1 (dfxtp has 12 rects) is never touched.
    tracks = [0.85, 1.53, 2.21, 3.23, 3.91, 4.59]
    g = lambda v: int(round(v * 1000))
    bycomp = {c.inst: c for c in comps}
    for (name, pins), ty in zip(conns, tracks):
        (i1, p1), (i2, p2) = pins
        x1, y1, l1 = pin_center(lef, bycomp[i1], p1)
        x2, y2, l2 = pin_center(lef, bycomp[i2], p2)
        seg = ("+ ROUTED met1 ( %d %d ) L1M1_PR NEW met1 ( %d %d ) M1M2_PR NEW met2 ( %d %d ) ( %d %d ) M2M3_PR "
               "NEW met3 ( %d %d ) ( %d %d ) M2M3_PR NEW met2 ( %d %d ) ( %d %d ) NEW met1 ( %d %d ) M1M2_PR NEW met1 ( %d %d ) L1M1_PR" % (
                   g(x1), g(y1), g(x1), g(y1), g(x1), g(y1), g(x1), g(ty), g(x1), g(ty), g(x2), g(ty), g(x2), g(ty), g(x2), g(y2),
                   g(x2), g(y2), g(x2), g(y2)))
        lines.append("- %s ( %s %s ) ( %s %s ) %s ;" % (name, i1, p1, i2, p2, seg))
    lines += ["END NETS", "", "END DESIGN"]
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return comps


def main():
    os.makedirs(EVID, exist_ok=True)
    lef = lefdef.read_lef(os.path.join(LIB, "sky130_fd_sc_hd.tlef"))
    for f in sorted(glob.glob(os.path.join(LIB, P + "*.lef"))):
        lefdef.read_lef(f, lef)
    def_path = os.path.join(SCR, "l2row.def")
    comps = build_def(lef, def_path)
    print("== 1. DEF written: %s (%d components, 2 rows, second row FS)" % (def_path, len(comps)))
    fl = lefdef.def2flat(def_path, [os.path.join(LIB, "sky130_fd_sc_hd.tlef")] + sorted(glob.glob(os.path.join(LIB, P + "*.lef"))),
                         LIB, T)
    ex = extract.extract(fl, T)
    print("== 2. def2flat + extract: %d rects, %d shapes, %d nets, %d devices" % (len(fl.rects), len(ex.shapes), len(ex.nets), len(ex.devices)))
    # per-instance device count vs the cell alone
    per_inst = collections.Counter(d.prov.split("/")[1] for d in ex.devices)
    ok = True
    for c in comps:
        alone = extract.extract(gds.flatten(gds.read(os.path.join(LIB, c.macro + ".gds"))), T)
        got = per_inst.get(c.inst, 0)
        flag = "ok" if got == len(alone.devices) else "MISMATCH"; ok &= got == len(alone.devices)
        print("   %-4s %-24s %2d devices (cell alone %2d) %s" % (c.inst, c.macro, got, len(alone.devices), flag))
    named = {n.name: n for n in ex.nets.values() if not n.name.isdigit()}
    print("   named nets: %s" % sorted(named))
    for sup in ("VPWR", "VGND"):
        n = named.get(sup)
        insts = sorted({ex.shapes[s].prov.split("/")[1] for s in n.shapes if "/" in ex.shapes[s].prov and not ex.shapes[s].prov.split("/")[1].startswith("net:")}) if n else []
        print("   %s: one net, %d device terminals, spans %d/%d instances %s" % (sup, len(n.devices) if n else 0, len(insts), len(comps), "ok" if len(insts) == len(comps) else "INCOMPLETE"))
        ok &= len(insts) == len(comps)
    for nm in ("n1", "n2", "n3", "m1", "m2", "q"):
        n = named.get(nm)
        pins = sorted({(dv, t) for dv, t in n.devices}) if n else []
        insts = sorted({ex.devices[int(dv[1:]) - 1].prov.split("/")[1] for dv, t in n.devices}) if n else []
        print("   %-3s %d device terminals across %s" % (nm, len(pins), insts))
    gds.write_flat(fl, os.path.join(EVID, "l2row_flat.gds"))
    extract.write_spice(ex, os.path.join(EVID, "l2row_layopt.cir"))
    # move: widen nand2 (u2) PMOS pair -- headroom search.  The two PMOS share one
    # diffusion strip, so one resize grows both (like Mtail's fingers).  Nothing
    # else in the cell moves (rails, taps: the cell's contract), so the growth
    # must fit the whitespace; the rule check + topology guard say how much does.
    print("== 3. move on a standard cell: u2 (nand2_1) PMOS strip, headroom search (shared-provenance footprint)")
    base = {drc.key(v) for v in drc.check(fl, ex)}
    sig = ex.signature()
    inv = {v: k for k, v in T.layers.items()}
    pm = [d for d in ex.devices if d.prov.startswith("l2row/u2/") and d.kind == "p"]
    fp, ids = moves.device_footprint(fl, ex, pm[0])
    print("   footprint %s um, %d rects (prov shared by %d devices)" % ([round(v / 1000, 3) for v in fp], len(ids), sum(1 for d in ex.devices if d.prov == pm[0].prov)))
    best = None
    import copy
    for side, w in (("high", 1.3), ("high", 1.1), ("high", 1.05), ("low", 1.3), ("low", 1.2), ("low", 1.1), ("low", 1.05)):
        fl2 = copy.deepcopy(fl)
        touched = moves.resize_device_w(fl2, ex, pm[0], w, side=side)
        ex2 = extract.extract(fl2, T)
        pm2 = [d for d in ex2.devices if d.prov.startswith("l2row/u2/") and d.kind == "p"]
        viol = drc.new_violations(fl2, ex2, touched, base)
        topo = ex2.signature() == sig
        legal = topo and not viol
        print("   W -> %.2f um (%s side): PMOS W %s, %d rects, topology %s, %d new violations%s" % (
            w, side, [round(d.w, 3) for d in pm2], len(set(touched)), "preserved" if topo else "CHANGED", len(viol), "  LEGAL" if legal else ""))
        for v in viol[:4]:
            a, b = fl2.rects[v.a], fl2.rects[v.b] if v.b >= 0 else None
            print("      %s   [%s %s%s]" % (v, inv.get(a.layer, a.layer), a.prov.split("/", 1)[1],
                                            "" if b is None else " vs %s %s" % (inv.get(b.layer, b.layer), b.prov.split("/", 1)[1])))
        if legal and (best is None or w > best[0]):
            best = (w, fl2, side)
    if best:
        print("   largest legal PMOS width without moving anything else in the cell: %.2f um (from 1.00), growing on the %s side" % (best[0], best[2]))
        gds.write_flat(best[1], os.path.join(EVID, "l2row_nand2_pmos_grown.gds"))
    else:
        print("   no legal growth in either direction: nand2_1's PMOS strip has no whitespace in this placement")
    print("   wrote evidence/l2row_flat.gds, l2row_layopt.cir")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
