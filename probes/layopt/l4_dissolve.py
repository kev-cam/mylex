# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""The boundary dissolve on the real layout: which abutting cell pairs in gcd
face each other with same-net S/D regions on both strips, how much each
boundary would give back, and the first few merged with the guards and KLayout.

    python3 probes/layopt/l4_dissolve.py [--apply N]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
sys.path.insert(0, HERE)
from layopt import compare, drc as rules, extract, gds as gdsmod, lefdef, moves as mv, power, tech as techmod  # noqa: E402
from l2_real_def import klayout_extract  # noqa: E402

T = techmod.SKY130
EVID = os.path.join(HERE, "evidence")
ORFS = os.path.expanduser("~/tools/orfs-sky130hd")
APPLY = int(sys.argv[sys.argv.index("--apply") + 1]) if "--apply" in sys.argv else 4


def main():
    lefs = [os.path.join(ORFS, "sky130_fd_sc_hd.tlef"), os.path.join(ORFS, "sky130_fd_sc_hd_merged.lef")]
    fl = lefdef.def2flat(os.path.join(HERE, "gcd", "gcd.def"), lefs, "", T, gds_lib=os.path.join(ORFS, "sky130_fd_sc_hd.gds"))
    ex = extract.extract(fl, T)
    sig = ex.signature(); base = {rules.key(v) for v in rules.check(fl, ex)}
    cands = mv.boundary_candidates(fl, ex)
    logic = {r.prov for r in fl.rects if r.prov.count("/") >= 2 and "fill" not in r.prov.lower() and "tap" not in r.prov.lower() and "decap" not in r.prov.lower() and "/net:" not in r.prov and "/pin:" not in r.prov}
    total_w = 0.0
    for inst in logic:
        try:
            b = mv._cell_box(fl, ex, inst)[1]; total_w += (b[2] - b[0]) / 1000.0
        except mv.MoveError:
            pass
    both = [c for c in cands if "fill" not in c[0].lower() and "fill" not in c[1].lower() and "tap" not in c[0].lower() and "tap" not in c[1].lower()]
    print("== gcd: %d logic cells, %.1f um of cell width; %d abutting logic pairs can compact (a strip merges where its regions are one net, keeps spacing otherwise)" % (len(logic), total_w, len(both)))
    tot = sum(c[2] for c in both) / 1000.0
    print("   a dissolve of every one gives back %.2f um = %.1f%% of the cell width (mean %.3f um per boundary); note only %d of %d abutments are logic|logic -- the rest have a filler on one side" % (
        tot, 100 * tot / total_w, tot / len(both) if both else 0, len(both), len(cands)))
    from collections import Counter
    print("   by nets: %s" % Counter("+".join(sorted(set(n))) for _, _, _, n in both).most_common(4))
    # apply to pairs with a filler beyond B (the freed space has to go somewhere local)
    done = 0
    for a, b, delta, nets in sorted(both, key=lambda c: -c[2]):
        if done >= APPLY:
            break
        if delta < 50:
            continue                                  # under 0.05 um is not worth a move
        ex = extract.extract(fl, T)
        try:
            touched = mv.merge_boundary(fl, ex, a, b)
        except mv.MoveError as e:
            print("   %s|%s: refused -- %s" % (a.split("/")[1], b.split("/")[1], str(e)[:120])); continue
        ex2 = extract.extract(fl, T)
        nv = rules.new_violations(fl, ex2, touched, base)
        ok = ex2.signature() == sig and not nv
        print("   %s|%s (%s): B slid %.3f um, %d rects; topology %s, new violations %d %s" % (
            a.split("/")[1], b.split("/")[1], "+".join(sorted(set(nets))), delta / 1000.0, len(touched), "same" if ex2.signature() == sig else "CHANGED", len(nv), [str(v)[:60] for v in nv[:2]]))
        if ok:
            base = {rules.key(v) for v in rules.check(fl, ex2)}; done += 1
    if done:
        ex2 = extract.extract(fl, T)
        out = os.path.join(EVID, "gcd_dissolved.gds"); gdsmod.write_flat(fl, out)
        cir = out.replace(".gds", "_klayout.cir"); klayout_extract(out, cir)
        res = compare.compare_to_reference(ex2, cir)
        print("   after %d dissolves: KLayout devices %d/%d, W/L match %s, nets %d/%d, isomorphic %s; switched energy %.1f -> %.1f fJ" % (
            done, res["ref_devices"], res["our_devices"], res["wl_match"], res["ref_nets"], res["our_nets"], res["isomorphic"], power.energy_fJ(extract.extract(lefdef.def2flat(os.path.join(HERE, "gcd", "gcd.def"), lefs, "", T, gds_lib=os.path.join(ORFS, "sky130_fd_sc_hd.gds")), T)), power.energy_fJ(ex2)))


if __name__ == "__main__":
    main()
