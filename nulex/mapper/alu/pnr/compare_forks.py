#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Before/after the fork-driven placement hints: measure each relocated wide
fork's branch-delay spread on the baseline routed DEF vs the hinted routed DEF,
matched by net name. Shows whether moving the driver buffer toward the receiver
centroid (flow_hinted.tcl) closed the placement-limited imbalance.

Usage: compare_forks.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "..")))
import alu_fork_balance as A                                     # noqa: E402
from layopt import extract, lefdef                               # noqa: E402

LEFS = [os.path.join(A.P, "sky130_fd_sc_hd.tlef"), os.path.join(A.P, "sky130_fd_sc_hd_merged.lef")]
GDS = os.path.join(A.P, "sky130_fd_sc_hd.gds")


def load(defp):
    fl = lefdef.def2flat(defp, LEFS, "", A.T, gds_lib=GDS)
    ex = extract.extract(fl, A.T)
    return ex, A.build_index(ex)


def measure_named(ex, idx, forks_by_name, names):
    out = {}
    for nm in names:
        f = forks_by_name.get(nm)
        if not f:
            continue
        r = A.measure_fork(ex, (f["driver"]["x"], f["driver"]["y"]), [(x["x"], x["y"]) for x in f["receivers"]])
        if r:
            bb = A.bbox_of(f)
            out[nm] = (r[0].spread, r[0].mean, max(bb[2] - bb[0], bb[3] - bb[1]) / 1000.0, f["fanout"])
    return out


def main():
    moved = [ln.split()[0].strip("{}") for ln in open(os.path.join(HERE, "fork_targets.tcl"))
             if ln.strip().startswith("{")]
    base_phys = {f["net"]: f for f in json.load(open(os.path.join(HERE, "alu_forks_phys.json")))["forks"]}
    hint_phys = {f["net"]: f for f in json.load(open(os.path.join(HERE, "alu_forks_phys_hinted.json")))["forks"]}
    print("relocated wide forks: %d; measuring on baseline + hinted routed DEFs ..." % len(moved), flush=True)

    exb, idxb = load(os.path.join(HERE, "alu_top.def"))
    print("baseline extracted", flush=True)
    exh, idxh = load(os.path.join(HERE, "alu_top_hinted.def"))
    print("hinted extracted\n", flush=True)

    b = measure_named(exb, idxb, base_phys, moved)
    h = measure_named(exh, idxh, hint_phys, moved)
    common = [n for n in moved if n in b and n in h]
    print("  %-12s fan   span b/h (um)      spread before -> after" % "net")
    tb = th = 0.0
    for nm in sorted(common, key=lambda n: -b[n][0]):
        sb, mb, spb, fo = b[nm]
        sh, mh, sph, _ = h[nm]
        tb += sb; th += sh
        print("  %-12s %3d   %5.0f -> %5.0f      %7.2f -> %7.2f ps  (%+.0f%%)" % (
            nm, fo, spb, sph, sb, sh, 100 * (sh - sb) / max(sb, 1e-3)))
    if common:
        print("\n  %d forks matched; summed spread %.1f -> %.1f ps  (%+.1f%%)" % (
            len(common), tb, th, 100 * (th - tb) / max(tb, 1e-3)))


if __name__ == "__main__":
    main()
