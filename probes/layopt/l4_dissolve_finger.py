#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""layopt L4 probe: dissolve the cell boundary -- grow a transistor into the
filler next to it by adding a finger.

Row (sky130_fd_sc_hd): fill_4 | inv_1 | fill_4 | nand2_1 | fill_1 | decap_4,
plus a flipped row of fills above sharing VPWR.  moves.add_finger mirrors the
inverter's gate and inner S/D column about the outer S/D region so the new
finger's diffusion, contacts and source strap land inside the fill_4 to the
right; a poly bridge ties the gates.  Re-extraction must show ONE PMOS (two
parallel fingers combined) of doubled W, the same netlist otherwise, and no
new rule violation.  Then the same for the NMOS.  Finally a control: the same
move on the nand2, whose right-hand neighbour is a 0.46 um fill_1 followed by
a decap with its own diffusion -- expected to fail the rule check.
"""
import copy
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
from layopt import drc, extract, gds, lefdef, moves, tech            # noqa: E402

LIB = os.path.expanduser(sys.argv[sys.argv.index("--lib") + 1] if "--lib" in sys.argv else "~/tools/sky130_fd_sc_hd")
SCR = sys.argv[sys.argv.index("--scratch") + 1] if "--scratch" in sys.argv else os.environ.get("LAYOPT_SCRATCH", "/tmp")
EVID = os.path.join(HERE, "evidence")
T = tech.SKY130
P = "sky130_fd_sc_hd__"
ROW1 = ["fill_4", "inv_1", "fill_4", "nand2_1", "fill_1", "decap_4"]
ROW2 = ["fill_8", "fill_8", "fill_4"]


def build_def(lef, path):
    comps = []
    x = 0
    for k, c in enumerate(ROW1):
        comps.append(lefdef.DefComponent("u%d" % (k + 1), P + c, x, 0, "N", True)); x += int(round(lef.macros[P + c].size[0] * 1000))
    w1 = x; x = 0
    for k, c in enumerate(ROW2):
        comps.append(lefdef.DefComponent("v%d" % (k + 1), P + c, x, 2720, "FS", True)); x += int(round(lef.macros[P + c].size[0] * 1000))
    lines = ["VERSION 5.8 ;", "DESIGN l4 ;", "UNITS DISTANCE MICRONS 1000 ;", "DIEAREA ( 0 0 ) ( %d 5440 ) ;" % max(w1, x),
             "COMPONENTS %d ;" % len(comps)]
    lines += ["- %s %s + PLACED ( %d %d ) %s ;" % (c.inst, c.macro, c.x, c.y, c.orient) for c in comps]
    lines += ["END COMPONENTS", "SPECIALNETS 2 ;",
              "- VPWR " + " ".join("( %s VPWR )" % c.inst for c in comps) + " + USE POWER ;",
              "- VGND " + " ".join("( %s VGND )" % c.inst for c in comps) + " + USE GROUND ;",
              "END SPECIALNETS", "END DESIGN"]
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return comps


def devices_of(ex, inst):
    return sorted((d for d in ex.devices if d.prov.split("/")[1] == inst), key=lambda d: (d.kind, d.w))


def summarize(ex, inst):
    return ["%s W=%.2f L=%.2f fingers=%d G=%s S=%s D=%s" % (d.kind, d.w, d.l, d.fingers, ex.nets[d.g].name, ex.nets[d.s].name, ex.nets[d.d].name)
            for d in devices_of(ex, inst)]


def attempt(fl, ex, base, sig, inst, kind, label):
    fl2 = copy.deepcopy(fl)
    dev = [d for d in devices_of(ex, inst) if d.kind == kind][0]
    try:
        touched = moves.add_finger(fl2, ex, dev, side="high")
    except moves.MoveError as e:
        print("   %s: move refused -- %s" % (label, e)); return None
    ex2 = extract.extract(fl2, T)
    viol = drc.new_violations(fl2, ex2, touched, base)
    topo = ex2.signature() == sig
    print("   %s: %d rects added/changed; %s; topology %s; %d new violations%s" % (
        label, len(touched), "; ".join(summarize(ex2, inst)), "preserved" if topo else "CHANGED", len(viol), "  LEGAL" if topo and not viol else ""))
    inv = {v: k for k, v in T.layers.items()}
    for v in viol[:5]:
        a = fl2.rects[v.a]; b = fl2.rects[v.b] if v.b >= 0 else None
        print("      %s   [%s %s%s]" % (v, inv.get(a.layer, a.layer), a.prov.split("/", 1)[1], "" if b is None else " vs %s %s" % (inv.get(b.layer, b.layer), b.prov.split("/", 1)[1])))
    return (fl2, ex2) if topo and not viol else None


def main():
    os.makedirs(EVID, exist_ok=True)
    lefs = [os.path.join(LIB, "sky130_fd_sc_hd.tlef")] + sorted(glob.glob(os.path.join(LIB, P + "*.lef")))
    lef = lefdef.Lef()
    for f in lefs:
        lefdef.read_lef(f, lef)
    def_path = os.path.join(SCR, "l4.def")
    comps = build_def(lef, def_path)
    fl = lefdef.def2flat(def_path, lefs, LIB, T)
    ex = extract.extract(fl, T)
    print("== 1. row: %s  (+ flipped fills above); %d rects, %d devices" % (" | ".join(ROW1), len(fl.rects), len(ex.devices)))
    print("   u2 inv_1 before: %s" % "; ".join(summarize(ex, "u2")))
    base = {drc.key(v) for v in drc.check(fl, ex)}
    sig = ex.signature()
    print("== 2. add a finger to u2's PMOS, growing right into the fill_4")
    r = attempt(fl, ex, base, sig, "u2", "p", "PMOS +1 finger")
    if r:
        fl_p, ex_p = r
        print("== 3. then the NMOS, same side")
        base_p = {drc.key(v) for v in drc.check(fl_p, ex_p)}
        r2 = attempt(fl_p, ex_p, base_p, sig, "u2", "n", "NMOS +1 finger")
        final = r2 if r2 else r
        gds.write_flat(final[0], os.path.join(EVID, "l4_inv1_fingered.gds"))
        extract.write_spice(final[1], os.path.join(EVID, "l4_inv1_fingered.cir"))
        # what the cell now occupies
        cell = [x.rect for x in final[0].rects if x.prov == "l4/u2/" + P + "inv_1" and x.layer in (T.layers["diff"], T.layers["poly"], T.layers["li"])]
        bb = [c / 1000 for c in (min(c[0] for c in cell), max(c[2] for c in cell))]
        print("   u2's active geometry now spans x %.2f..%.2f um (cell box was 1.84..3.22): the boundary is dissolved into the filler" % tuple(bb))
    print("== 4. control: the same move on u4 nand2_1's PMOS (right neighbour: 0.46 um fill_1, then a decap with diffusion)")
    attempt(fl, ex, base, sig, "u4", "p", "nand2 PMOS +1 finger")
    print("   wrote evidence/l4_inv1_fingered.gds, .cir")


if __name__ == "__main__":
    main()
