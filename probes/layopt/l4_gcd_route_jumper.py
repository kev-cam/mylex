# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""gcd: fingers on a cell whose S/D jumper found no straight met1 or met2
bar (clkinv_1 `_110_`): the jumper is routed instead.

    python3 probes/layopt/l4_gcd_route_jumper.py [_110_]

PMOS then NMOS finger, guards after each, KLayout at the end
(`evidence/gcd_<inst>_routed_jumper*`).
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
    inst = sys.argv[1] if len(sys.argv) > 1 else "_110_"
    fl = load()
    inv = {v: k for k, v in T.layers.items()}
    ex = extract.extract(fl, T); sig = ex.signature(); base = {rules.key(v) for v in rules.check(fl, ex)}
    print("before:", ["%s W=%.2f f=%d" % (x.kind, x.w, x.fingers) for x in ex.devices if x.prov.split("/")[1] == inst])
    touched_all = []
    for kind in ("p", "n"):
        ex = extract.extract(fl, T)
        devs = [d for d in ex.devices if d.prov.split("/")[1] == inst and d.kind == kind]
        devs.sort(key=lambda x: -max(ex.shapes[g].rect[2] for g in x.gate_ids))
        try:
            t = mv.add_finger(fl, ex, devs[0], side="high")
        except mv.MoveError as e:
            print(kind.upper(), "REFUSED:", str(e)[:600]); continue
        print(kind.upper(), "finger ok: %d rects; jumper tally %s" % (len(t), dict(mv.LAST_JUMPER_TALLY)))
        for i in t:
            r = fl.rects[i]
            if inv.get(r.layer) in ("li", "mcon", "met1", "via1", "met2"):
                print("   new %-5s %s" % (inv.get(r.layer), [round(v / 1000, 3) for v in r.rect]))
        ex2 = extract.extract(fl, T)
        print("   signature equal:", ex2.signature() == sig)
        nv = rules.new_violations(fl, ex2, t, base)
        print("   new violations:", len(nv), nv[:4])
        base = {rules.key(v) for v in rules.check(fl, ex2)}
        touched_all += t
    if not touched_all:
        return
    ex2 = extract.extract(fl, T)
    print("after:", ["%s W=%.2f f=%d" % (x.kind, x.w, x.fingers) for x in ex2.devices if x.prov.split("/")[1] == inst])
    out = os.path.join(EVID, "gcd_%s_routed_jumper.gds" % inst.strip("_"))
    gdsmod.write_flat(fl, out)
    from l2_real_def import klayout_extract
    cir = out.replace(".gds", "_klayout.cir"); klayout_extract(out, cir)
    res = compare.compare_to_reference(ex2, cir)
    for k in ("ref_devices", "our_devices", "wl_match", "ref_nets", "our_nets", "isomorphic"):
        print("%-20s %s" % (k, res[k]))


if __name__ == "__main__":
    main()
