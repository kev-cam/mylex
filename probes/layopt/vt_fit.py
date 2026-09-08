#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""Vt flavour as a sizing lever: how much faster or slower is a sky130
transistor with the low-Vt (lvtn) or high-Vt (hvtp) implant?

    python3 probes/layopt/vt_fit.py [--models DIR] [--scratch DIR]

An inv_1-sized inverter (P 1.0/0.15, N 0.65/0.15) driven by a 50 ps ramp
into loads of 2..40 fF, in Xyce with the PDK's tt models (fetched from
skywater-pdk-libs-sky130_fd_pr, converted the way kestrel converts them:
subcircuit wrapper off, comment lines out of the .model continuations).  The
slope of the 50 % delay against load, divided by ln 2, is the Elmore-
equivalent R of the switching device -- the same quantity the Liberty fit
gives for the standard flavour -- so the ratio lvt/std, hvt/std per polarity
is the multiplier a Vt move applies to tech.SKY130.drive.
Evidence: evidence/vt_fit.log.
"""
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = sys.argv[sys.argv.index("--models") + 1] if "--models" in sys.argv else os.path.expanduser("~/tools/sky130_fd_pr")
SCR = sys.argv[sys.argv.index("--scratch") + 1] if "--scratch" in sys.argv else os.environ.get("LAYOPT_SCRATCH", "/tmp")
XYCE = os.path.expanduser("~/tools/xyce/bin/Xyce")
FLAVOURS = {"n": ["nfet_01v8", "nfet_01v8_lvt"], "p": ["pfet_01v8", "pfet_01v8_lvt", "pfet_01v8_hvt"]}
SCALE = 20                              # Xyce's BSIM4 (oldest version) fails the transient DC point for the
                                        # standard nfet below ~2 um width; kestrel's devices are 20-40 um.
                                        # R*W is what we want, so characterise inv_1 scaled up, loads too.
WP, WN, LG = 1.0 * SCALE, 0.65 * SCALE, 0.15   # um
LOADS_FF = [c * SCALE for c in (2.0, 5.0, 10.0, 20.0, 40.0)]
SLEW_PS = 50.0


def convert(cell):
    """The PDK tt model file made Xyce-ready (kestrel's recipe)."""
    cell = cell.split("@")[0]
    src = os.path.join(MODELS, "sky130_fd_pr__%s__tt.pm3.spice" % cell)
    dst = os.path.join(SCR, "sky130_%s_xyce.spice" % cell)
    lines = open(src).read().split("\n")
    out = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith(".subckt") or ln.startswith(".ends") or ln.lower().startswith("msky130"):
            i += 1; continue
        if ln.startswith("+") and out and out[-1].strip() == "":
            pass
        # a comment between a card and its continuation breaks the continuation
        if ln.startswith("*") and i + 1 < len(lines) and lines[i + 1].startswith("+"):
            i += 1; continue
        out.append(ln); i += 1
    open(dst, "w").write("\n".join(out))
    return dst


def bins(path):
    """[(model name, lmin, lmax, wmin, wmax)] in metres."""
    txt = open(path).read()
    res = []
    for m in re.finditer(r"^\.model\s+(\S+)\s+\w+\s*\n((?:\+.*\n)*)", txt, re.M):
        name, body = m.group(1), m.group(2)
        g = {k: float(v) for k, v in re.findall(r"(lmin|lmax|wmin|wmax)\s*=\s*([-+0-9.eE]+)", body)}
        if len(g) == 4:
            res.append((name, g["lmin"], g["lmax"], g["wmin"], g["wmax"]))
    return res


def pick(path, l_um, w_um):
    l, w = l_um * 1e-6, w_um * 1e-6
    for name, lmin, lmax, wmin, wmax in bins(path):
        if lmin <= l < lmax and wmin <= w < wmax:
            return name
    # the geometry bins are sometimes given in um in the corner files; try that reading
    for name, lmin, lmax, wmin, wmax in bins(path):
        if lmin <= l_um < lmax and wmin <= w_um < wmax:
            return name
    raise KeyError("no model bin for L=%g W=%g in %s" % (l_um, w_um, path))


def gate_len(cell):
    if "@" in cell:
        return float(cell.split("@")[1])
    return 0.35 if cell.endswith("_lvt") else LG


def run(nf, pf, load_fF):
    nfile, pfile = convert(nf), convert(pf)
    ln, lp = gate_len(nf), gate_len(pf)
    nmod, pmod = pick(nfile, ln, WN), pick(pfile, lp, WP)
    cir = os.path.join(SCR, "vt_inv_%s_%s_%g.cir" % (nf.replace("@", "_L"), pf.replace("@", "_L"), load_fF))
    # the PDK model expressions refer to per-cell symbols: the corner file defines
    # the junction multipliers, the mismatch/process slopes are meant to come from
    # a statistics block -- a nominal run sets them to zero (kestrel's testbench
    # does the same by hand); here every referenced-but-undefined symbol gets 0,
    # or 1 if it is a multiplier
    # (kestrel's recipe: nominal pm3 models, every corner/mismatch symbol zero,
    # junction multipliers one; the tt corner file's offsets made Xyce's DC
    # operating point fail for the standard flavour, so they are not applied)
    pre = []
    for cell, mfile in ((nf.split("@")[0], nfile), (pf.split("@")[0], pfile)):
        mtxt = open(mfile).read()
        used = set(re.findall(r"(sky130_fd_pr__%s__\w+)" % cell, mtxt))
        defined = set(re.findall(r"^\.param\s+(sky130_fd_pr__\w+)", mtxt, re.M | re.I))     # the file's own (the *_spectre ones)
        for name in sorted(used - defined):
            if name.endswith("__model") or "__model." in name:
                continue
            pre.append(".PARAM %s = %s" % (name, "1.0" if "mult" in name else "0.0"))
    lines = ["* inverter %s / %s, load %g fF" % (nf, pf, load_fF)] + pre + [
             '.INCLUDE "%s"' % nfile, '.INCLUDE "%s"' % pfile,
             "VDD vdd 0 1.8", "VSS vss 0 0",
             "VIN in 0 PWL(0 0 1n 0 %gn 1.8 3n 1.8 %gn 0 6n 0)" % (1 + SLEW_PS * 1e-3, 3 + SLEW_PS * 1e-3),
             "Mp out in vdd vdd %s W=%gu L=%gu AS=%gp AD=%gp PS=%gu PD=%gu" % (pmod, WP, lp, 0.29 * WP, 0.29 * WP, 0.58 + WP, 0.58 + WP),
             "Mn out in vss vss %s W=%gu L=%gu AS=%gp AD=%gp PS=%gu PD=%gu" % (nmod, WN, ln, 0.29 * WN, 0.29 * WN, 0.58 + WN, 0.58 + WN),
             "CL out 0 %gf" % load_fF,
             ".TRAN 1p 6n",
             ".MEASURE TRAN tfall TRIG V(in)=0.9 RISE=1 TARG V(out)=0.9 FALL=1",
             ".MEASURE TRAN trise TRIG V(in)=0.9 FALL=1 TARG V(out)=0.9 RISE=1",
             ".OPTIONS TIMEINT RELTOL=1e-4 ABSTOL=1e-12",
             ".END"]
    open(cir, "w").write("\n".join(lines) + "\n")
    p = subprocess.run([XYCE, cir], capture_output=True, text=True, timeout=600, cwd=SCR)
    txt = p.stdout + p.stderr
    try:
        mt = open(cir + ".mt0").read()
    except OSError:
        mt = ""
    got = {}
    for k in ("tfall", "trise"):
        m = re.search(r"%s\s*=\s*([-+0-9.eE]+)" % k, mt, re.I) or re.search(r"%s\s*=\s*([-+0-9.eE]+)" % k, txt, re.I)
        got[k] = float(m.group(1)) * 1e12 if m else None
    if got["tfall"] is None or got["trise"] is None:
        raise RuntimeError("Xyce gave no measures for %s/%s: %s" % (nf, pf, txt[-600:]))
    return got


def slope(xs, ys):
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx, my - mx * sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx


def main():
    os.makedirs(SCR, exist_ok=True)
    print("== Xyce inv_1 x%d (P %.1f / N %.1f, L %.2f um), input ramp %.0f ps, loads %s fF; R reported per 1 um-equivalent (x%d)" % (SCALE, WP, WN, LG, SLEW_PS, LOADS_FF, SCALE))
    print("   (lvt gates are drawn at L = 0.35 um: sky130 poly.1b requires it; @0.35 marks a standard device at that length)")
    print("   %-16s %-16s | %7s %6s | %7s %6s" % ("nfet", "pfet", "R_rise", "t0r", "R_fall", "t0f"))
    res = {}
    combos = [(n, "pfet_01v8") for n in FLAVOURS["n"]] + [("nfet_01v8", p) for p in FLAVOURS["p"] if p != "pfet_01v8"]
    combos += [("nfet_01v8@0.18", "pfet_01v8"), ("nfet_01v8", "pfet_01v8@0.18"), ("nfet_01v8@0.25", "pfet_01v8"), ("nfet_01v8", "pfet_01v8@0.25"),
               ("nfet_01v8@0.35", "pfet_01v8"), ("nfet_01v8", "pfet_01v8@0.35")]
    for nf, pf in combos:
        rise, fall = [], []
        for c in LOADS_FF:
            g = run(nf, pf, c); rise.append(g["trise"]); fall.append(g["tfall"])
        sr, t0r = slope(LOADS_FF, rise); sf, t0f = slope(LOADS_FF, fall)
        rr, rf = sr * 1000.0 / math.log(2) * SCALE, sf * 1000.0 / math.log(2) * SCALE   # ps/fF -> ohm, Elmore basis, at inv_1 size
        res[(nf, pf)] = (rr, rf, t0r, t0f)
        print("   %-16s %-16s | %7.0f %6.1f | %7.0f %6.1f" % (nf, pf, rr, t0r, rf, t0f))
    base = res[("nfet_01v8", "pfet_01v8")]
    print("== multipliers on the standard flavour's R (the Vt move's effect):")
    for (nf, pf), (rr, rf, _, _) in res.items():
        if nf != "nfet_01v8":
            print("   NMOS %-16s: R_fall x %.3f" % (nf.replace("nfet_01v8", "std").replace("std_", ""), rf / base[1]))
        if pf != "pfet_01v8":
            print("   PMOS %-16s: R_rise x %.3f" % (pf.replace("pfet_01v8", "std").replace("std_", ""), rr / base[0]))
    print("   Liberty (std) for comparison: R_rise 8165, R_fall 4823 ohm (inv_1, 50 ps slew); Xyce std here: %.0f / %.0f" % (base[0], base[1]))


if __name__ == "__main__":
    main()
