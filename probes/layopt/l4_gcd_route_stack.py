# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""gcd: mirror a nand2's NMOS series stack into the filler on its right and
bridge the far gate by routing around the P&R met1 in the field gap.

    python3 probes/layopt/l4_gcd_route_stack.py [_149_|_161_]

PMOS finger first (as the probe does), then the whole NMOS stack; prints the
li/met1/met2 geometry in the gap, the router's statistics and the new rects;
verifies with the guards and KLayout (`evidence/gcd_<inst>_stack_routed*`).
LAYOPT_ROUTE_PROBE="met1:65550:57970,..." (dbu) prints the raster state at
those points and every repair attempt of the router.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
sys.path.insert(0, HERE)
from layopt import extract, lefdef, moves as mv, drc as rules, tech as techmod, geom, gds as gdsmod, compare, route  # noqa: E402
T = techmod.SKY130
ORFS = os.path.expanduser("~/tools/orfs-sky130hd")
DEF = os.path.join(HERE, "gcd", "gcd.def")
EVID = os.path.join(HERE, "evidence")


def load():
    lefs = [os.path.join(ORFS, "sky130_fd_sc_hd.tlef"), os.path.join(ORFS, "sky130_fd_sc_hd_merged.lef")]
    return lefdef.def2flat(DEF, lefs, "", T, gds_lib=os.path.join(ORFS, "sky130_fd_sc_hd.gds"))


def main():
    inst = sys.argv[1] if len(sys.argv) > 1 else "_149_"
    fl = load()
    fl0 = None
    inv = {v: k for k, v in T.layers.items()}

    def pick(ex, kind):
        devs = [d for d in ex.devices if d.prov.split("/")[1] == inst and d.kind == kind]
        devs.sort(key=lambda x: -max(ex.shapes[g].rect[2] for g in x.gate_ids))
        return devs[0]
    ex = extract.extract(fl, T)
    sig = ex.signature(); base = {rules.key(v) for v in rules.check(fl, ex)}
    t = mv.add_finger(fl, ex, pick(ex, "p"), side="high")
    print("P finger ok: %d rects" % len(t))
    ex = extract.extract(fl, T)
    assert ex.signature() == sig
    dn = pick(ex, "n")
    g = [ex.shapes[q].rect for q in dn.gate_ids]
    gx = (min(r[0] for r in g), max(r[2] for r in g)); gy = (min(r[1] for r in g), max(r[3] for r in g))
    print("N outer gate %s net %s" % ([round(v / 1000, 3) for v in (gx[0], gy[0], gx[1], gy[1])], ex.nets[dn.g].name))
    src2net = {sh.src: ex.net_of_shape[k] for k, sh in enumerate(ex.shapes) if sh.src >= 0}
    win = (gx[0] - 2500, gy[1] - 200, gx[1] + 2500, gy[1] + 1300)
    print("gap window %s" % [round(v / 1000, 3) for v in win])
    for lay in ("li", "mcon", "met1", "via1", "met2"):
        print("--", lay)
        for k, r in enumerate(fl.rects):
            if inv.get(r.layer) == lay and geom.overlaps(r.rect, win):
                n = src2net.get(k)
                print("   %5d %-8s %s  %s" % (k, ex.nets[n].name if n is not None else "?", [round(v / 1000, 3) for v in r.rect], r.prov.split("/", 1)[1][:30]))
    try:
        t2 = mv.add_finger(fl, ex, dn, side="high")
    except mv.MoveError as e:
        print("REFUSED:", str(e)); return
    print("N stack ok: %d rects; route %s" % (len(t2), mv.LAST_PLAN_TALLY.get("maze route")))
    for i in t2:
        r = fl.rects[i]
        if inv.get(r.layer) in ("li", "mcon", "met1", "via1", "met2", "poly", "licon"):
            print("   new %-5s %s" % (inv.get(r.layer), [round(v / 1000, 3) for v in r.rect]))
    ex2 = extract.extract(fl, T)
    print("signature equal:", ex2.signature() == sig)
    nv = rules.new_violations(fl, ex2, t + t2, base)
    print("new violations:", len(nv), nv[:5])
    print("devices:", ["%s W=%.2f f=%d" % (x.kind, x.w, x.fingers) for x in ex2.devices if x.prov.split("/")[1] == inst])
    out = os.path.join(EVID, "gcd_%s_stack_routed.gds" % inst.strip("_"))
    gdsmod.write_flat(fl, out)
    from l2_real_def import klayout_extract
    cir = out.replace(".gds", "_klayout.cir")
    klayout_extract(out, cir)
    res = compare.compare_to_reference(ex2, cir)
    for k in ("ref_devices", "our_devices", "wl_match", "ref_nets", "our_nets", "degree_hist_match", "isomorphic"):
        print("%-20s %s" % (k, res[k]))


if __name__ == "__main__":
    main()
