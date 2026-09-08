# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""set_gate_length on the real layout: a gcd rebuffer's output stage from
L 0.15 to 0.18 (both polarities), guards, driven-net delay, switched energy,
KLayout isomorphism (KLayout reports the new L too).

    python3 probes/layopt/l4_set_gate_length.py [inst] [L_um]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
sys.path.insert(0, HERE)
from layopt import compare, drc as rules, extract, gds as gdsmod, lefdef, moves as mv, power, tech as techmod  # noqa: E402
from l2_real_def import klayout_extract  # noqa: E402
from l4_gcd_whitespace import net_delay, output_net  # noqa: E402

T = techmod.SKY130
EVID = os.path.join(HERE, "evidence")
ORFS = os.path.expanduser("~/tools/orfs-sky130hd")


def main():
    inst = sys.argv[1] if len(sys.argv) > 1 else "rebuffer12"
    l_um = float(sys.argv[2]) if len(sys.argv) > 2 else 0.18
    lefs = [os.path.join(ORFS, "sky130_fd_sc_hd.tlef"), os.path.join(ORFS, "sky130_fd_sc_hd_merged.lef")]
    fl = lefdef.def2flat(os.path.join(HERE, "gcd", "gcd.def"), lefs, "", T, gds_lib=os.path.join(ORFS, "sky130_fd_sc_hd.gds"))
    ex = extract.extract(fl, T)
    sig = ex.signature(); base = {rules.key(v) for v in rules.check(fl, ex)}
    net = output_net(ex, inst)
    wp0, r0, d0 = net_delay(ex, net, inst)
    e0 = power.energy_fJ(ex)
    touched = []
    for kind in ("p", "n"):
        ex = extract.extract(fl, T)
        net_now = output_net(ex, inst)                       # ids shift with a re-extraction
        dev = max((x for x in ex.devices if x.prov.split("/")[1] == inst and x.kind == kind and net_now in (x.s, x.d)), key=lambda x: x.fingers)
        try:
            t = mv.set_gate_length(fl, ex, dev, l_um)
        except mv.MoveError as e:
            print("   %s: refused -- %s" % (kind.upper(), str(e)[:160])); continue
        touched += t
        print("   %s %s L %.2f -> %.2f (%d fingers): %d rects" % (inst, kind.upper(), dev.l, l_um, dev.fingers, len(t)))
    ex2 = extract.extract(fl, T)
    net2 = output_net(ex2, inst)
    nv = rules.new_violations(fl, ex2, touched, base)
    print("   signature equal %s; new violations %d %s" % (ex2.signature() == sig, len(nv), nv[:3]))
    print("   %s devices now: %s" % (inst, ["%s L=%.2f W=%.2f f=%d" % (x.kind, x.l, x.w, x.fingers) for x in ex2.devices if x.prov.split("/")[1] == inst]))
    wp1, r1, d1 = net_delay(ex2, net2, inst)
    print("   output net %s: R_rise/R_fall %.0f/%.0f -> %.0f/%.0f ohm; worst-edge Elmore to %d receivers max %.1f -> %.1f ps" % (
        ex.nets[net].name, r0[0], r0[1], r1[0], r1[1], len(d0), max(d0.values()), max(d1.values())))
    print("   switched energy of the design: %.1f -> %.1f fJ/transition (gate area grows with L)" % (e0, power.energy_fJ(ex2)))
    out = os.path.join(EVID, "gcd_%s_L%d.gds" % (inst, int(round(l_um * 1000)))); gdsmod.write_flat(fl, out)
    cir = out.replace(".gds", "_klayout.cir"); klayout_extract(out, cir)
    res = compare.compare_to_reference(ex2, cir)
    print("   KLayout: devices %d/%d, W/L match %s, nets %d/%d, isomorphic %s" % (res["ref_devices"], res["our_devices"], res["wl_match"], res["ref_nets"], res["our_nets"], res["isomorphic"]))


if __name__ == "__main__":
    main()
