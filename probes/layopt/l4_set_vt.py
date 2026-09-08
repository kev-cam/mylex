# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""set_vt on the real layout: a gcd rebuffer's output PMOS from the library's
high-Vt to standard Vt (the hvtp implant cut away over its gates), guards,
driven-net delay on both edges, KLayout isomorphism.

    python3 probes/layopt/l4_set_vt.py [inst]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
sys.path.insert(0, HERE)
from layopt import compare, drc as rules, extract, gds as gdsmod, lefdef, moves as mv, tech as techmod  # noqa: E402
from l2_real_def import klayout_extract  # noqa: E402
from l4_gcd_whitespace import net_delay, output_net  # noqa: E402

T = techmod.SKY130
EVID = os.path.join(HERE, "evidence")
ORFS = os.path.expanduser("~/tools/orfs-sky130hd")


def main():
    inst = sys.argv[1] if len(sys.argv) > 1 else "rebuffer3"
    lefs = [os.path.join(ORFS, "sky130_fd_sc_hd.tlef"), os.path.join(ORFS, "sky130_fd_sc_hd_merged.lef")]
    fl = lefdef.def2flat(os.path.join(HERE, "gcd", "gcd.def"), lefs, "", T, gds_lib=os.path.join(ORFS, "sky130_fd_sc_hd.gds"))
    ex = extract.extract(fl, T)
    sig = ex.signature(); base = {rules.key(v) for v in rules.check(fl, ex)}
    models = sorted({(d.kind, d.model) for d in ex.devices})
    print("== gcd: %d devices; models %s" % (len(ex.devices), models))
    net = output_net(ex, inst)
    wp0, r0, d0 = net_delay(ex, net, inst)
    dev = max((x for x in ex.devices if x.prov.split("/")[1] == inst and x.kind == "p"), key=lambda x: x.fingers)
    print("   %s output PMOS: %s W=%.2f fingers=%d" % (inst, dev.model, dev.w, dev.fingers))
    t = mv.set_vt(fl, ex, dev, "std")
    ex2 = extract.extract(fl, T)
    nv = rules.new_violations(fl, ex2, t, base)
    print("   set_vt std: %d rects changed, swept along %s; signature equal %s; new violations %d %s" % (len(t), mv.LAST_VT_SWEPT, ex2.signature() == sig, len(nv), nv[:3]))
    print("   %s devices now: %s" % (inst, ["%s %s W=%.2f f=%d" % (x.kind, T.flavour_of_model(x.model), x.w, x.fingers) for x in ex2.devices if x.prov.split("/")[1] == inst]))
    wp1, r1, d1 = net_delay(ex2, net, inst)
    print("   output net %s: R_rise/R_fall %.0f/%.0f -> %.0f/%.0f ohm; worst-edge Elmore to %d receivers max %.1f -> %.1f ps" % (
        ex.nets[net].name, r0[0], r0[1], r1[0], r1[1], len(d0), max(d0.values()), max(d1.values())))
    out = os.path.join(EVID, "gcd_%s_stdvt.gds" % inst); gdsmod.write_flat(fl, out)
    cir = out.replace(".gds", "_klayout.cir"); klayout_extract(out, cir)
    res = compare.compare_to_reference(ex2, cir)
    print("   KLayout: devices %d/%d, W/L match %s, nets %d/%d, isomorphic %s" % (res["ref_devices"], res["our_devices"], res["wl_match"], res["ref_nets"], res["our_nets"], res["isomorphic"]))


if __name__ == "__main__":
    main()
