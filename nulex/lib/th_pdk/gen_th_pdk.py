#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Generate the TH-cell PHYSICAL views (LEF / Liberty / GDS) so a structural
threshold-gate netlist (map_ncl_struct) can go through OpenROAD P&R and layopt.

Real custom TH-cell transistor layout is out of scope; instead each comb TH cell
is REALIZED on its sky130_fd_sc_hd equivalent and its physical views are derived
from that cell by renaming the macro + signal pins (A,B,C,D->a,b,c,d ; X->y),
keeping the power pins and the geometry. Same site (unithd) and rails as sky130,
so TH cells place-and-route alongside sky130 fillers/taps.

    gen_th_pdk.py [outdir]   ->  th_cells.lef, th_cells.lib, th_cells.gds
"""
import os
import re
import sys

SKY = "/home/claude/tools/orfs-sky130hd"
MLEF = SKY + "/sky130_fd_sc_hd_merged.lef"
MLIB = SKY + "/sky130_fd_sc_hd__tt_025C_1v80.lib"
MGDS = SKY + "/sky130_fd_sc_hd.gds"

# comb TH cell -> sky130 cell realizing the same Boolean function
TH_MAP = {
    "th22": "and2_1",   # a & b                 (2-of-2)
    "th12": "or2_1",    # a | b                 (1-of-2)
    "th13": "or3_1",    # a | b | c             (1-of-3)
    "th14": "or4_1",    # a | b | c | d         (1-of-4)
    "th33": "and3_1",   # a & b & c             (3-of-3)
    "th23": "maj3_1",   # majority(a,b,c)       (2-of-3)
    "th44": "and4_1",   # a & b & c & d         (4-of-4)
}
PIN_MAP = {"A": "a", "B": "b", "C": "c", "D": "d", "X": "y"}


def rename_pins(text):
    for k, v in PIN_MAP.items():
        text = re.sub(r"\b%s\b" % k, v, text)
    return text


def gen_lef(outdir):
    src = open(MLEF).read()
    out = ["VERSION 5.8 ;", "BUSBITCHARS \"[]\" ;", "DIVIDERCHAR \"/\" ;", ""]
    for th, sky in TH_MAP.items():
        macro = "sky130_fd_sc_hd__" + sky
        m = re.search(r"^MACRO %s\b.*?^END %s\b" % (re.escape(macro), re.escape(macro)),
                      src, re.S | re.M)
        if not m:
            sys.exit("LEF macro %s not found" % macro)
        blk = m.group(0)
        blk = blk.replace(macro, th)                      # macro + FOREIGN name
        # rename only signal pins (PIN A/B/C/D/X); power pins have no bare A..X
        blk = re.sub(r"\b([ABCDX])\b", lambda g: PIN_MAP[g.group(1)], blk)
        out.append(blk)
        out.append("")
    open(os.path.join(outdir, "th_cells.lef"), "w").write("\n".join(out) + "\n")
    print("wrote th_cells.lef (%d cells)" % len(TH_MAP))


def cell_block(src, macro):
    """extract the balanced-brace liberty cell(...) block for a macro."""
    i = src.find('cell ("%s")' % macro)
    if i < 0:
        sys.exit("liberty cell %s not found" % macro)
    j = src.find("{", i)
    depth, k = 1, j + 1
    while depth:
        if src[k] == "{": depth += 1
        elif src[k] == "}": depth -= 1
        k += 1
    return src[i:k]


def gen_lib(outdir):
    src = open(MLIB).read()
    header = src[:src.find('\n    cell (')]                # library preamble + templates
    cells = []
    for th, sky in TH_MAP.items():
        blk = cell_block(src, "sky130_fd_sc_hd__" + sky)
        blk = blk.replace("sky130_fd_sc_hd__" + sky, th)   # cell + footprint name
        blk = re.sub(r"\b([ABCDX])\b", lambda g: PIN_MAP[g.group(1)], blk)  # pins in fns/timing
        cells.append("    " + blk)
    open(os.path.join(outdir, "th_cells.lib"), "w").write(header + "\n" + "\n".join(cells) + "\n}\n")
    print("wrote th_cells.lib (%d cells)" % len(TH_MAP))


def gen_gds(outdir):
    sys.path.insert(0, "/usr/local/src/mylex")
    from layopt import gds
    lib = gds.read(MGDS)
    for th, sky in TH_MAP.items():                        # flatten each sky130 cell, rename struct -> th
        flat = gds.flatten(lib, top="sky130_fd_sc_hd__" + sky)
        gds.write_flat(flat, os.path.join(outdir, "%s.gds" % th), name=th)
    print("wrote <th>.gds per cell (%d; structure named by the TH cell)" % len(TH_MAP))


if __name__ == "__main__":
    outdir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    gen_lef(outdir)
    gen_lib(outdir)
    gen_gds(outdir)
