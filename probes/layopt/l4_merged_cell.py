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

    python3 probes/layopt/l4_merged_cell.py [--name gcd] [--flow DIR] [--ref routed.def] [--no-route] [--local | --global]

`--local` (the default for designs other than gcd) applies and guards each
dissolve on the three-row window around it, so a 4000-cell design costs
seconds per boundary instead of minutes; the whole layout is extracted once
at the end and compared with the base.
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


ROW_UM = 2.72


def row_window(fl, y0, y1):
    """A FlatLayout sharing the rect OBJECTS of `fl` that overlap the band
    [y0, y1] (dbu): a dissolve applied to it mutates the full layout's rects
    in place; what it appends or deletes is reconciled by `transplant`."""
    from layopt.gds import FlatLayout
    sub = FlatLayout(dbu_um=fl.dbu_um, top=fl.top)
    # every rect in the band, plus every DEF net wire (the PDN, whose labels name the
    # supply nets -- without the names the rail-cut logic cannot tell a supply) and all labels
    sub.rects = [r for r in fl.rects if (r.y1 > y0 and r.y0 < y1) or "/net:" in r.prov]
    sub.texts = list(getattr(fl, "texts", []))
    sub.boxes = {p: b for p, b in fl.boxes.items() if b[3] > y0 and b[1] < y1}
    return sub


def transplant(fl, sub, before_objs):
    """After a move on `sub`: rects `sub` dropped leave `fl`, rects it added join it, boxes follow."""
    now = set(id(r) for r in sub.rects)
    dropped = set(id(r) for r in before_objs) - now
    added = [r for r in sub.rects if id(r) not in set(id(x) for x in before_objs)]
    if dropped:
        fl.rects = [r for r in fl.rects if id(r) not in dropped]
    fl.rects += added
    fl.boxes.update(sub.boxes)


def dissolve_local(fl, a_prov, b_prov, base_sig_cache):
    """merge_boundary(shift_row) on the three-row window around the boundary,
    guarded on that window (topology signature and DRC keys before/after);
    on failure the window is restored.  Returns (ok, slid_um, message).
    Rows are 2.72 um; the band takes the row and both neighbours so shared
    rails, twinned rail cuts and li overhangs are all in view."""
    import copy
    from layopt import drc as rules, extract, moves as mv
    box = fl.boxes[b_prov]
    y0, y1 = box[1] - int(ROW_UM * 1000), box[3] + int(ROW_UM * 1000)
    sub = row_window(fl, y0, y1)
    snapshot = [(r, r.rect) for r in sub.rects]; boxes0 = dict(sub.boxes); before_objs = list(sub.rects)
    ex = extract.extract(sub, T)
    sig0 = ex.signature(); keys0 = {rules.key(v) for v in rules.check(sub, ex)}
    try:
        t = mv.merge_boundary(sub, ex, a_prov, b_prov, shift_row=True)
    except mv.MoveError as e:
        return False, 0.0, "refused -- %s" % str(e)[:90]
    slid = mv.LAST_MERGE_DELTA[0] / 1000.0
    ex2 = extract.extract(sub, T)
    nv = rules.new_violations(sub, ex2, t, keys0)      # among the rects the move touched, as the global guard does
    ok = ex2.signature() == sig0 and not nv
    if not ok:
        for r, rect in snapshot:
            r.rect = rect
        sub.rects = [r for r, _ in snapshot]; sub.boxes = boxes0
        fl.boxes.update(boxes0)
        return False, slid, "slid %.3f um but %s, %d new violations -- not taken" % (slid, "topology kept" if ex2.signature() == sig0 else "topology CHANGED", len(nv))
    transplant(fl, sub, before_objs)
    return True, slid, "dissolved, slid %.3f um" % slid


def main():
    local = "--local" in sys.argv or ("--global" not in sys.argv and NAME != "gcd")
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
        if local:
            ok, slid, msg = dissolve_local(fl, prov[a], prov[b], None)
            print("   %s|%s: %s" % (a, b, msg))
            if ok:
                accepted.append((a, b)); gained += slid
            continue
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
    print("== 2. %d of %d boundaries dissolved, %.2f um given back (%.0fs%s)" % (len(accepted), len(pairs), gained, time.time() - t0, "; guarded on three-row windows" if local else ""))
    if local:
        ex = extract.extract(fl, T)          # the whole layout once, for the record
        print("   whole layout after the dissolves: %d rects, %d devices, topology %s the base" % (len(fl.rects), len(ex.devices), "EQUAL to" if ex.signature() == sig else "DIFFERENT from"))
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
