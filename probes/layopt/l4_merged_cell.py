#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""Dissolved cells handed back to the router: on gcd's hinted pre-route
placement every hinted boundary that dissolves legally is dissolved (row
mode, cumulatively); each merged group becomes a LEF macro and a GDS cell
(`layopt/mergedcell.py`); the DEF is rewritten around them; OpenROAD routes
it; the routed result is flattened with the cell library plus the merged
cells, extracted, and compared with the original routed gcd (device-level
topology) and with KLayout.

    python3 probes/layopt/l4_merged_cell.py [--name gcd] [--flow DIR] [--ref routed.def] [--no-route]
"""
import copy
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
sys.path.insert(0, HERE)
from layopt import compare, drc as rules, extract, gds as gdsmod, lefdef, mergedcell, moves as mv, tech as techmod   # noqa: E402

T = techmod.SKY130
ORFS = os.path.expanduser("~/tools/orfs-sky130hd")
NAME = sys.argv[sys.argv.index("--name") + 1] if "--name" in sys.argv else "gcd"
FLOW = os.path.expanduser(sys.argv[sys.argv.index("--flow") + 1] if "--flow" in sys.argv else "~/src/%s-flow/hints" % NAME)
REF_DEF = sys.argv[sys.argv.index("--ref") + 1] if "--ref" in sys.argv else None      # the original routed DEF to compare topology with
OPENROAD = os.path.expanduser("~/tools/openroad/bin/openroad")
LEFS = [os.path.join(ORFS, "sky130_fd_sc_hd.tlef"), os.path.join(ORFS, "sky130_fd_sc_hd_merged.lef")]
GDS = os.path.join(ORFS, "sky130_fd_sc_hd.gds")
EVID = os.path.join(HERE, "evidence")


def main():
    hinted = os.path.join(FLOW, "%s_hints_placed.def" % NAME)
    hints = json.load(open(os.path.join(EVID, "%s_placer_hints.json" % NAME)))
    pairs = [(h["partner_left"], h["inst"]) for h in hints if h.get("partner_left")]
    t0 = time.time()
    lef = lefdef.Lef()
    for f in LEFS:
        lefdef.read_lef(f, lef)
    d = lefdef.read_def(hinted)
    fl = lefdef.def2flat(hinted, LEFS, "", T, gds_lib=GDS)
    ex = extract.extract(fl, T); sig = ex.signature(); base = {rules.key(v) for v in rules.check(fl, ex)}
    prov = {}
    for r in fl.rects:
        parts = r.prov.split("/")
        if len(parts) >= 3:
            prov.setdefault(parts[1], r.prov)
    print("== 1. %s: %d rects, %d devices, %d hinted boundaries (%.0fs)" % (os.path.basename(hinted), len(fl.rects), len(ex.devices), len(pairs), time.time() - t0))
    # 2. dissolve cumulatively, each boundary guarded on the running layout
    accepted = []; gained = 0.0
    for a, b in pairs:
        trial = copy.deepcopy(fl); ex_t = extract.extract(trial, T)
        try:
            t = mv.merge_boundary(trial, ex_t, prov[a], prov[b], shift_row=True)
        except mv.MoveError as e:
            print("   %s|%s: refused -- %s" % (a, b, str(e)[:90])); continue
        ex2 = extract.extract(trial, T); nv = rules.new_violations(trial, ex2, t, base)
        slid = mv.LAST_MERGE_DELTA[0] / 1000.0
        if ex2.signature() != sig or nv:
            print("   %s|%s: slid %.3f um but %s, %d new violations -- not taken" % (a, b, slid, "topology kept" if ex2.signature() == sig else "topology CHANGED", len(nv))); continue
        fl = trial; base = {rules.key(v) for v in rules.check(fl, ex2)}
        accepted.append((a, b)); gained += slid
        print("   %s|%s: dissolved, slid %.3f um" % (a, b, slid))
    print("== 2. %d of %d boundaries dissolved, %.2f um given back (%.0fs)" % (len(accepted), len(pairs), gained, time.time() - t0))
    # 3. groups (a cell may sit in two boundaries) -> merged cells
    parent = {}
    def find(x):
        while parent.get(x, x) != x:
            x = parent[x]
        return x
    for a, b in accepted:
        parent.setdefault(a, a); parent.setdefault(b, b); parent[find(a)] = find(b)
    groups = {}
    for a, b in accepted:
        groups.setdefault(find(a), set()).update((a, b))
    cells = []
    for k, (root, members) in enumerate(sorted(groups.items())):
        ordered = sorted(members, key=lambda i: fl.boxes[prov[i]][0])
        mc = mergedcell.MergedCell.build(fl, lef, T, d, [prov[i] for i in ordered], "layopt_m%d" % k)
        cells.append(mc)
        print("   %s = %s: %.3f x %.3f um, %d pins, %d obstruction rects" % (mc.name, "+".join(ordered), (mc.box[2] - mc.box[0]) / 1000, (mc.box[3] - mc.box[1]) / 1000, len(mc.pins), len(mc.obs)))
    merged_lef = os.path.join(FLOW, "merged.lef"); merged_gds = os.path.join(FLOW, "merged.gds"); merged_def = os.path.join(FLOW, "merged.def")
    mergedcell.lef_library(cells, merged_lef); mergedcell.gds_library(cells, merged_gds)
    open(merged_def, "w").write(mergedcell.rewrite_def(open(hinted).read(), d, fl, cells, scale=1000.0 / d.dbu_per_um))
    moved = sum(1 for c in d.components if c.placed and prov.get(c.inst) in fl.boxes and fl.boxes[prov[c.inst]][0] != c.x * 1000 // d.dbu_per_um)
    print("== 3. wrote merged.lef (%d macros), merged.gds, merged.def (%d instances moved by the dissolve)" % (len(cells), moved))
    for f in ("merged.lef", "merged.def"):
        os.system("cp %s %s" % (os.path.join(FLOW, f), os.path.join(EVID, NAME + "_" + f)))
    if "--no-route" in sys.argv or not os.path.exists(OPENROAD):
        return
    # 4. route
    t1 = time.time()
    log = os.path.join(FLOW, "route_merged.log")
    with open(log, "w") as fh:
        subprocess.run([OPENROAD, "-exit", "flow_route_merged.tcl"], cwd=FLOW, stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
    txt = open(log).read()
    import re
    wl = re.findall(r"Total wire length = (\d+) um", txt)
    drc = open(os.path.join(FLOW, "route_drc_merged.rpt")).read().count("violation type") if os.path.exists(os.path.join(FLOW, "route_drc_merged.rpt")) else -1
    print("== 4. routed in %.0fs: %s; wire %s um; DRC violations %d; errors: %s" % (time.time() - t1, "complete" if "Complete detail routing" in txt else "INCOMPLETE", wl[-1] if wl else "?", drc,
          [l for l in txt.split("\n") if l.startswith("[ERROR")][:3]))
    routed = os.path.join(FLOW, "%s_merged_routed.def" % NAME)
    if not os.path.exists(routed):
        return
    # 5. verify: flatten with library + merged cells, extract, compare with the original routed gcd
    t2 = time.time()
    fl_r = lefdef.def2flat(routed, LEFS + [merged_lef], "", T, gds_lib=[GDS, merged_gds])
    ex_r = extract.extract(fl_r, T)
    ref_def = REF_DEF or (os.path.join(HERE, "gcd", "gcd.def") if NAME == "gcd" else os.path.join(FLOW, "%s_base.def" % NAME))
    fl_ref = lefdef.def2flat(ref_def, LEFS, "", T, gds_lib=GDS)
    ex_ref = extract.extract(fl_ref, T)
    same = ex_r.signature() == ex_ref.signature()
    print("== 5. routed dissolved %s: %d devices / %d nets vs the routed reference %s: %d / %d; device-level topology %s (%.0fs)" % (
        NAME, len(ex_r.devices), len(ex_r.nets), os.path.basename(ref_def), len(ex_ref.devices), len(ex_ref.nets), "EQUAL" if same else "DIFFERENT", time.time() - t2))
    out = os.path.join(EVID, "%s_merged_routed.gds" % NAME); gdsmod.write_flat(fl_r, out)
    try:
        from l2_real_def import klayout_extract
        cir = out.replace(".gds", "_klayout.cir"); klayout_extract(out, cir)
        res = compare.compare_to_reference(ex_r, cir)
        print("   KLayout on the routed result: devices %d/%d wl %s nets %d/%d isomorphic %s" % (res["ref_devices"], res["our_devices"], res["wl_match"], res["ref_nets"], res["our_nets"], res["isomorphic"]))
    except Exception as e:
        print("   KLayout check not run: %s" % str(e)[:100])


if __name__ == "__main__":
    main()
