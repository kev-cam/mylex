#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""layopt L1 probe: kestrel's SPICE-in-the-loop, re-hosted on layout geometry.

  1. generate kestrel's PLL layout at the known-good (oscillating) VCO sizing
     with gdsfactory (scratch path; the committed GDS is not touched)
  2. layopt extracts it: per-transistor W (sum of fingers), L, and the delay
     cell's own share of the output-node wiring capacitance
  3. kestrel's Xyce testbench + run_xyce (layout/spice_loop.py) measure f_vco
     from THOSE numbers, for a small sweep of tail width and added C.  Only
     what the layout move changes is swept: the replica-bias transistor is
     not in kestrel's VCO layout, so it stays fixed (kestrel's own
     current_scale scales tail and bias together, which the Maneatis replica
     largely compensates -- a different experiment)
  4. fit the first-order T0 drive model  f = k * W_tail^a / (C_int + C_par)
  5. apply two layopt MOVES to the geometry (Mtail stretch x1.25 in all four
     cells; output stubs widened x2), re-extract, predict f with the fitted
     model, and check against fresh Xyce runs

Usage: l1_xyce_loop.py [--gds existing.gds]   (needs Xyce on PATH or ~/tools/xyce/bin)
"""
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
KESTREL = os.environ.get("KESTREL_DIR", "/usr/local/src/kestrel")
sys.path.insert(0, KESTREL)
os.environ["PATH"] = os.path.expanduser("~/tools/xyce/bin") + ":" + os.environ["PATH"]

from layopt import drc, extract, gds, moves, rc, tech            # noqa: E402
from layout.spice_loop import run_xyce, _MODEL_PREAMBLE, SIM_DIR  # noqa: E402

EVID = os.path.join(HERE, "evidence")
T = tech.SKY130
VCTRL = 0.9
SIM_NS = 500
CELL = "kestrel_delay_cell#0"


def known_good_gds(path):
    from kestrel.generators.pll.engine import PLLSpec, design_pll
    from layout.gds_gen import generate_pll_gds
    d = design_pll(PLLSpec(freq_min=400e6, freq_max=800e6, ref_freq=10e6, loop_bw=1e6, process="sky130"))
    d.vco_tail_w = 40e-6; d.vco_tail_l = 0.36e-6; d.vco_diff_w = 20e-6; d.vco_diff_l = 0.36e-6
    d.vco_load_w = 10e-6; d.vco_load_l = 0.36e-6; d.vco_bias_w = 20e-6; d.vco_bias_l = 0.36e-6
    d.vco_i_stage = 200e-6
    return generate_pll_gds(d, path)


def cell_sizes(ex, cell):
    """Layout truth for one delay cell: {name: (W_total_um, L_um)} and the cell's
    share of output-node C (its own shapes on the diff-pair drain nets)."""
    w, l = {}, {}
    for d in ex.devices:
        if cell + "/" in d.prov:
            t = d.prov.split("/")[-1]
            w[t] = w.get(t, 0.0) + d.w; l[t] = d.l
    outs = set()
    for d in ex.devices:
        if cell + "/" in d.prov and d.prov.endswith(("Mn1_diff", "Mn2_diff")):
            outs.add(d.d)
    prefix = None
    for d in ex.devices:
        if cell + "/" in d.prov:
            prefix = d.prov.rsplit("/", 1)[0]; break
    local = [s for n in outs for s in ex.nets[n].shapes if ex.shapes[s].prov.startswith(prefix)
             and ex.shapes[s].layer in T.routing]
    c_out = rc.shapes_c_fF(ex, local) / max(1, len(outs))     # per output node
    return w, l, c_out


def testbench(sz, L, c_par_fF, tail_scale=1.0, bias_w=20.0):
    um = lambda v: "%.4fu" % v
    n, p = "sky130_fd_pr__nfet_01v8__model.6", "sky130_fd_pr__pfet_01v8__model.6"
    tail, diff, load = sz["Mtail"] * tail_scale, sz["Mn1_diff"], sz["Mp1a_diode"]
    ls = [
        "* layopt L1: VCO testbench from layout-extracted sizes", _MODEL_PREAMBLE,
        '.INCLUDE "%s/models/sky130_nfet_xyce.spice"' % SIM_DIR,
        '.INCLUDE "%s/models/sky130_pfet_xyce.spice"' % SIM_DIR,
        ".SUBCKT kestrel_delay_cell outp outn inp inn vctrl vbn vdd vss",
        "Mtail tail vbn vss vss %s W=%s L=%s" % (n, um(tail), um(L["Mtail"])),
        "Mn1 outn inp tail vss %s W=%s L=%s" % (n, um(diff), um(L["Mn1_diff"])),
        "Mn2 outp inn tail vss %s W=%s L=%s" % (n, um(diff), um(L["Mn2_diff"])),
        "Mp1a outn outn vdd vdd %s W=%s L=%s" % (p, um(load), um(L["Mp1a_diode"])),
        "Mp1b outn vctrl vdd vdd %s W=%s L=%s" % (p, um(load), um(L["Mp1b_ctrl"])),
        "Mp2a outp outp vdd vdd %s W=%s L=%s" % (p, um(load), um(L["Mp2a_diode"])),
        "Mp2b outp vctrl vdd vdd %s W=%s L=%s" % (p, um(load), um(L["Mp2b_ctrl"])),
        "Cp_outp outp 0 %.3ff" % c_par_fF, "Cp_outn outn 0 %.3ff" % c_par_fF,
        ".ENDS kestrel_delay_cell",
        ".SUBCKT kestrel_vco_bias vbn vctrl vdd vss",
        "Mrep_n vbn vbn vss vss %s W=%s L=0.36u" % (n, um(bias_w)),        # bias is NOT in the layout: fixed
        "Mrep_pd vbn vbn vdd vdd %s W=%s L=0.36u" % (p, um(load)),
        "Mrep_pc vbn vctrl vdd vdd %s W=%s L=0.36u" % (p, um(load)),
        "Istart vdd vbn 5u", ".ENDS kestrel_vco_bias",
        ".SUBCKT kestrel_vco outp outn vctrl_ext vdd vss",
        "Xbias vbn vctrl_int vdd vss kestrel_vco_bias", "Rsw vctrl_ext vctrl 1", "Rbias vctrl_int vctrl 100k",
        "Xstage0 dp_0 dn_0 dn_3 dp_3 vctrl vbn vdd vss kestrel_delay_cell",
        "Xstage1 dp_1 dn_1 dp_0 dn_0 vctrl vbn vdd vss kestrel_delay_cell",
        "Xstage2 dp_2 dn_2 dp_1 dn_1 vctrl vbn vdd vss kestrel_delay_cell",
        "Xstage3 dp_3 dn_3 dp_2 dn_2 vctrl vbn vdd vss kestrel_delay_cell",
        "Routp dp_3 outp 1", "Routn dn_3 outn 1", ".ENDS kestrel_vco",
        "Vdd vdd 0 1.8", "Vss vss 0 0", "Vctrl vctrl 0 %g" % VCTRL,
        "Xvco outp outn vctrl vdd vss kestrel_vco",
        "Cload_p outp 0 10f", "Cload_n outn 0 10f", "Ediff diff 0 outp outn 1.0",
        "Ikick 0 Xvco:dp_0 PULSE(0 1m 0 50p 50p 10n 0)",
        ".TRAN 50p %dn" % SIM_NS, ".PRINT TRAN V(diff)",
        ".MEASURE TRAN t1 WHEN V(diff)=0 RISE=5 TD=100n", ".MEASURE TRAN t2 WHEN V(diff)=0 RISE=6 TD=100n", ".END"]
    return "\n".join(ls)


def xyce_f(sz, L, c_par, tail_scale=1.0, tag=""):
    t0 = time.time()
    r = run_xyce(testbench(sz, L, c_par, tail_scale))
    if not r["success"]:
        raise SystemExit("Xyce failed (%s): %s" % (tag, r["output"]))
    print("   Xyce %-28s tail x%.3f  C_par %6.2f fF  ->  f = %7.2f MHz  (%.1fs)" % (
        tag, tail_scale, c_par, r["frequency_hz"] / 1e6, time.time() - t0))
    return r["frequency_hz"]


def main():
    os.makedirs(EVID, exist_ok=True)
    gds_path = sys.argv[sys.argv.index("--gds") + 1] if "--gds" in sys.argv else None
    scratch = os.environ.get("LAYOPT_SCRATCH", "/tmp")
    if gds_path is None:
        gds_path = os.path.join(scratch, "kestrel_pll_kg.gds")
        print("== 0. generating kestrel PLL layout at known-good VCO sizing ->", gds_path)
        known_good_gds(gds_path)
    fl = gds.flatten(gds.read(gds_path))
    ex = extract.extract(fl, T)
    sz, L, c0 = cell_sizes(ex, CELL)
    print("== 1. layout truth for %s (%d rects, %d devices)" % (CELL, len(fl.rects), len(ex.devices)))
    for t in sorted(sz):
        print("   %-12s W=%.3f um  L=%.3f um" % (t, sz[t], L[t]))
    print("   cell-local output-node wiring C = %.3f fF per node" % c0)

    print("== 2. Xyce sweep (vctrl=%.1f V) for the T0 drive-model fit" % VCTRL)
    pts = []
    for ts in (0.8, 1.0, 1.25):
        pts.append((ts, c0, xyce_f(sz, L, c0, ts, "fit: tail")))
    for dc in (5.0, 10.0):
        pts.append((1.0, c0 + dc, xyce_f(sz, L, c0 + dc, 1.0, "fit: +C")))
    # fit f = k * ts^a / (Cint + Cpar):  from the C points, 1/f linear in Cpar -> Cint; from tail points, log-log slope a
    f_c = [(c, f) for ts, c, f in pts if ts == 1.0]
    (c1, f1), (c2, f2), (c3, f3) = sorted(f_c)
    slope = ((1 / f3) - (1 / f1)) / (c3 - c1)
    cint = (1 / f1) / slope - c1                       # 1/f = slope*(Cint + Cpar)
    f_t = [(ts, f) for ts, c, f in pts if c == c0]
    (t1, fa), (t2, fb), (t3, fc) = sorted(f_t)
    a = math.log(fc / fa) / math.log(t3 / t1)
    k = fb * (cint + c0)
    model = {"k_MHz_fF": k / 1e6, "a": a, "C_int_fF": cint, "vctrl": VCTRL, "sizes_um": sz, "L_um": L, "c0_fF": c0}
    pred = lambda ts, c: k * ts ** a / (cint + c)
    print("   fit: f = k * (W_tail/W0)^a / (C_int + C_par):  a = %.3f  C_int = %.2f fF  k = %.3g MHz*fF" % (a, cint, k / 1e6))
    print("   in-sample residuals: %s" % ", ".join("%.2f%%" % (100 * (pred(ts, c) / f - 1)) for ts, c, f in pts))

    print("== 3. layopt MOVES on the geometry, predicted by T0, checked by Xyce")
    base = {drc.key(v) for v in drc.check(fl, ex)}
    sig = ex.signature()
    results = []
    # Move A: stretch Mtail in all four cells by x1.25 (one call per cell grows every finger of that diffusion)
    flA = gds.flatten(gds.read(gds_path)); exA = extract.extract(flA, T)
    touched = []
    for k_cell in range(4):
        fing = [d for d in exA.devices if ("kestrel_delay_cell#%d/Mtail" % k_cell) in d.prov]
        touched += moves.resize_device_w(flA, exA, fing[0], fing[0].w * 1.25)
    exA2 = extract.extract(flA, T)
    szA, LA, cA = cell_sizes(exA2, CELL)
    violA = drc.new_violations(flA, exA2, touched, base)
    print("   move A (Mtail x1.25, 4 cells): Mtail W %.2f -> %.2f um, %d rects, topology %s, %d new violations, C_out %.3f fF" % (
        sz["Mtail"], szA["Mtail"], len(touched), "preserved" if exA2.signature() == sig else "CHANGED", len(violA), cA))
    tsA = szA["Mtail"] / sz["Mtail"]
    fA_pred = pred(tsA, cA); fA = xyce_f(szA, LA, cA, 1.0, "move A (held out)")
    results.append(("A: Mtail x1.25", fA_pred, fA))
    gds.write_flat(flA, os.path.join(EVID, "kestrel_pll_kg_mtail125.gds"))
    # Move B: widen the delay cells' output stubs (their own MET2 on the drain nets) x2
    flB = gds.flatten(gds.read(gds_path)); exB = extract.extract(flB, T)
    touchedB = []
    for k_cell in range(4):
        cell = "kestrel_delay_cell#%d" % k_cell
        outs = {d.d for d in exB.devices if cell + "/" in d.prov and d.prov.endswith(("Mn1_diff", "Mn2_diff"))}
        for n in outs:
            for s in exB.nets[n].shapes:
                sh = exB.shapes[s]
                if sh.layer == "met2" and sh.src >= 0 and (cell + "/") in sh.prov + "/" and cell in sh.prov:
                    touchedB += moves.set_wire_width(flB, sh.src, 2 * moves.wire_width_um(flB, sh.src))
    exB2 = extract.extract(flB, T)
    szB, LB, cB = cell_sizes(exB2, CELL)
    violB = drc.new_violations(flB, exB2, touchedB, base)
    print("   move B (output stubs x2 width, 4 cells): %d rects, topology %s, %d new violations, C_out %.3f -> %.3f fF" % (
        len(touchedB), "preserved" if exB2.signature() == sig else "CHANGED", len(violB), c0, cB))
    fB_pred = pred(1.0, cB); fB = xyce_f(szB, LB, cB, 1.0, "move B (held out)")
    results.append(("B: stubs x2", fB_pred, fB))
    # Held-out combined point
    fAB_pred = pred(tsA, cB); fAB = xyce_f(szA, LA, cB, 1.0, "A+B (held out)")
    results.append(("A+B", fAB_pred, fAB))
    # Move A2: Mtail x1.10 -- a tail width NOT in the fit sweep (the true held-out point)
    flC = gds.flatten(gds.read(gds_path)); exC = extract.extract(flC, T)
    touchedC = []
    for k_cell in range(4):
        fing = [d for d in exC.devices if ("kestrel_delay_cell#%d/Mtail" % k_cell) in d.prov]
        touchedC += moves.resize_device_w(flC, exC, fing[0], fing[0].w * 1.10)
    exC2 = extract.extract(flC, T)
    szC, LC, cC = cell_sizes(exC2, CELL)
    violC = drc.new_violations(flC, exC2, touchedC, base)
    print("   move A2 (Mtail x1.10, 4 cells): Mtail W %.2f -> %.2f um, topology %s, %d new violations" % (
        sz["Mtail"], szC["Mtail"], "preserved" if exC2.signature() == sig else "CHANGED", len(violC)))
    tsC = szC["Mtail"] / sz["Mtail"]
    fC_pred = pred(tsC, cC); fC = xyce_f(szC, LC, cC, 1.0, "move A2 (held out)")
    results.append(("A2: Mtail x1.10", fC_pred, fC))
    print("== 4. T0 prediction vs Xyce")
    f0 = [f for ts, c, f in pts if ts == 1.0 and c == c0][0]
    print("   %-16s %10s %10s %8s   %s" % ("move", "T0 MHz", "Xyce MHz", "error", "Xyce shift vs baseline"))
    worst = 0.0
    for name, fp, fx in results:
        e = 100 * (fp / fx - 1); worst = max(worst, abs(e))
        print("   %-16s %10.2f %10.2f %7.2f%%   %+.2f%%" % (name, fp / 1e6, fx / 1e6, e, 100 * (fx / f0 - 1)))
    print("   worst T0 error %.2f%% (kestrel's own SPICE-loop tolerance: 3%%)" % worst)
    model["results"] = [{"move": n, "f_T0_MHz": fp / 1e6, "f_xyce_MHz": fx / 1e6} for n, fp, fx in results]
    with open(os.path.join(EVID, "l1_t0_drive_model.json"), "w") as fh:
        json.dump(model, fh, indent=1)
    print("   wrote evidence/l1_t0_drive_model.json, evidence/kestrel_pll_kg_mtail125.gds")


if __name__ == "__main__":
    main()
