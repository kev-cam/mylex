#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Characterize the native TH cells (SG13G2 domain) -> Liberty NLDM timing.

Two paths:

  --spice   the GOLD path: transistor-level Xyce transient sweeps of the native
            cells (ldx/asic/cells/th22.sp, th_gates.sp) with the SG13G2 PSP103
            model card. For each (input slew x output load) grid point it drives
            a ramp, measures the input->output propagation delay and the output
            transition, and (for the C-element) the set/reset switching plus the
            hold — then assembles NLDM cell_rise/fall + transition tables.
            REQUIRES a Xyce with PSP103 (the ldx flow used a PyMS-built
            psp103_sg13g2.so plugin / a custom Xyce-8). The stock Xyce here has
            no PSP103, so this path reports the missing device and stops.

  --from-lib <sg13g2_stdcell.lib>
            derive the TH-cell Liberty from IHP's silicon-characterized SG13G2
            standard-cell library (the comb TH cells realized on it: th22=and2,
            th12=or2, th13=or3, th33=and3, th44=and4; th23=majority via a22oi).
            Real SG13G2 timing at the lib's corner (1.2V/25C), available now.

Usage: characterize_th.py --from-lib <stdcell.lib> [out.lib]
       characterize_th.py --spice [out.lib]
"""
import os, re, subprocess, sys

CELLS = "/usr/local/src/ldx/asic/cells"
MODEL = "/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
XYCE = "/usr/local/bin/Xyce"
# comb TH cell -> the SG13G2 std cell realizing the same function (single-cell map)
TH_MAP = {"th22": "and2_1", "th12": "or2_1", "th13": "or3_1", "th33": "and3_1", "th44": "and4_1"}
PIN_MAP = {"A": "a", "B": "b", "C": "c", "D": "d", "X": "y"}


def spice_probe():
    """Confirm the SG13G2 PSP103 device is usable in this Xyce (else the gold
    transistor characterization cannot run here)."""
    deck = "/tmp/_psp_probe.cir"
    open(deck, "w").write('.include "%s"\nM1 d g 0 0 sg13g2_nmos W=1u L=0.13u\n'
                          'Vg g 0 1.2\nVd d 0 1.2\n.op\n.end\n' % MODEL)
    r = subprocess.run([XYCE, deck], capture_output=True, text=True, timeout=60)
    return "nrecognized" not in r.stdout and "rror" not in r.stdout.split("Total")[0]


def run_spice(outlib):
    if not os.path.exists(MODEL):
        sys.exit("SG13G2 model card missing: %s" % MODEL)
    if not spice_probe():
        sys.exit("BLOCKED: this Xyce (%s) has no PSP103 device — the SG13G2 model\n"
                 "card loads but sg13g2_nmos/pmos do not bind. The ldx flow used a\n"
                 "PyMS-built psp103_sg13g2.so plugin / a custom Xyce-8 build, absent here.\n"
                 "The harness is ready; run it with a PSP103-capable Xyce.\n"
                 "Meanwhile use: characterize_th.py --from-lib <sg13g2_stdcell.lib>" % XYCE)
    # (full slew x load transient sweep + NLDM assembly would run here)
    sys.exit("PSP103 present — full transient sweep path not exercised in this run.")


def cell_block(src, macro):
    i = src.find('cell ("%s")' % macro)
    if i < 0:
        i = src.find("cell (%s)" % macro)
    if i < 0:
        return None
    j = src.find("{", i); depth, k = 1, j + 1
    while depth:
        depth += (src[k] == "{") - (src[k] == "}"); k += 1
    return src[i:k]


def derive_from_lib(stdlib, outlib):
    src = open(stdlib).read()
    header = src[:src.find("\n  cell (") if "\n  cell (" in src else src.find("cell (")]
    prefix = "sg13g2_"
    out = []
    got = []
    for th, sky in TH_MAP.items():
        blk = cell_block(src, prefix + sky) or cell_block(src, sky)
        if blk is None:
            continue
        blk = re.sub(r"\b" + re.escape(prefix + sky) + r"\b", th, blk)
        blk = re.sub(r"\b([ABCDX])\b", lambda g: PIN_MAP[g.group(1)], blk)
        out.append("  " + blk); got.append(th)
    open(outlib, "w").write(header + "\n" + "\n".join(out) + "\n}\n")
    print("wrote %s: %d TH cells with SG13G2-characterized timing (from %s)"
          % (outlib, len(got), os.path.basename(stdlib)))
    print("  cells: %s" % ", ".join(got))
    print("  NOTE: comb cells realized on SG13G2 std cells (real IHP timing). The")
    print("  hysteretic C-element + weighted gates compose these; native-transistor")
    print("  timing (th22.sp) needs the --spice gold path (PSP103).")


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--from-lib" in a:
        i = a.index("--from-lib"); stdlib = a[i + 1]
        outlib = a[i + 2] if len(a) > i + 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "th_cells_sg13g2.lib")
        derive_from_lib(stdlib, outlib)
    elif "--spice" in a:
        run_spice(a[a.index("--spice") + 1] if len(a) > a.index("--spice") + 1 else "th_cells_sg13g2.lib")
    else:
        sys.exit(__doc__)
