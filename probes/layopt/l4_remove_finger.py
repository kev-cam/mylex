# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""remove_finger: the inverse move, on a stock cell and on the real layout.

    python3 probes/layopt/l4_remove_finger.py

1. A stock buf_4 alone on a row loses one PMOS and one NMOS finger of its
   output stage (4 -> 3); guards, then KLayout on the written GDS.
2. gcd: rebuffer3 (buf_4) loses one finger per stage; the driven net's
   Elmore delay rises accordingly (the move the path balancer needs to slow
   a fast driver instead of only speeding up the slow one).
Evidence: evidence/remove_finger_buf4*.{gds,cir,log}, evidence/gcd_rebuffer3_removed*.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
sys.path.insert(0, HERE)
from layopt import compare, drc as rules, extract, gds as gdsmod, lefdef, moves as mv, tech as techmod  # noqa: E402
from layopt.tests.test_layopt import _bare_row  # noqa: E402
from l2_real_def import klayout_extract  # noqa: E402
from l4_gcd_whitespace import net_delay, output_net  # noqa: E402

T = techmod.SKY130
EVID = os.path.join(HERE, "evidence")
ORFS = os.path.expanduser("~/tools/orfs-sky130hd")


def remove_both(fl, inst_match):
    """Remove one outer finger of the biggest P and N device matching inst_match; return touched ids."""
    out = []
    for kind in ("p", "n"):
        ex = extract.extract(fl, T)
        dev = max((x for x in ex.devices if x.kind == kind and inst_match(x)), key=lambda x: x.fingers)
        sig = ex.signature(); base = {rules.key(v) for v in rules.check(fl, ex)}
        t = mv.remove_finger(fl, ex, dev, side="high")
        ex2 = extract.extract(fl, T)
        assert ex2.signature() == sig, kind
        nv = rules.new_violations(fl, ex2, t, base)
        print("   %s: %s fingers %d -> %d, W %.2f -> %.2f; new violations %d" % (
            kind.upper(), dev.name, dev.fingers, max((x.fingers for x in ex2.devices if x.kind == kind and inst_match(x))), dev.w,
            max((x.w for x in ex2.devices if x.kind == kind and inst_match(x))), len(nv)))
        assert not nv, nv[:3]
        out += t
    return out


def klayout(fl, ex, stem):
    out = os.path.join(EVID, stem + ".gds"); gdsmod.write_flat(fl, out)
    cir = os.path.join(EVID, stem + "_klayout.cir"); klayout_extract(out, cir)
    res = compare.compare_to_reference(ex, cir)
    print("   KLayout: devices %d/%d, W/L match %s, nets %d/%d, isomorphic %s" % (
        res["ref_devices"], res["our_devices"], res["wl_match"], res["ref_nets"], res["our_nets"], res["isomorphic"]))
    return res["isomorphic"]


def main():
    print("== 1. stock buf_4 on a bare row")
    fl = _bare_row([("fill_4", 0.0), ("buf_4", 1.84), ("fill_8", 4.60)])
    remove_both(fl, lambda x: "buf_4" in x.prov)
    ok1 = klayout(fl, extract.extract(fl, T), "remove_finger_buf4")
    print("== 2. gcd rebuffer3")
    lefs = [os.path.join(ORFS, "sky130_fd_sc_hd.tlef"), os.path.join(ORFS, "sky130_fd_sc_hd_merged.lef")]
    fl = lefdef.def2flat(os.path.join(HERE, "gcd", "gcd.def"), lefs, "", T, gds_lib=os.path.join(ORFS, "sky130_fd_sc_hd.gds"))
    ex = extract.extract(fl, T)
    inst = "rebuffer3"
    net = output_net(ex, inst)
    wp0, r0, d0 = net_delay(ex, net, inst)
    remove_both(fl, lambda x: x.prov.split("/")[1] == inst)
    ex2 = extract.extract(fl, T)
    wp1, r1, d1 = net_delay(ex2, net, inst)
    print("   output net %s: PMOS W %.2f -> %.2f um, R_rise/R_fall %.0f/%.0f -> %.0f/%.0f ohm; worst-edge Elmore to %d receivers max %.1f -> %.1f ps" % (
        ex.nets[net].name, wp0, wp1, r0[0], r0[1], r1[0], r1[1], len(d0), max(d0.values()), max(d1.values())))
    ok2 = klayout(fl, ex2, "gcd_rebuffer3_removed")
    print("RESULT", "MATCH" if ok1 and ok2 else "MISMATCH")


if __name__ == "__main__":
    main()
