#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""The placer hand-off, end to end on gcd: layopt's flip-and-abut hints go into
OpenROAD after detailed placement and `optimize_mirroring`, before routing;
the router's bill for them (wire length, timing, DRC) is read from the two
routing runs; then the dissolve is applied to the hinted placement to see
whether the hinted boundaries give back what the hints promised.

Needs the split flow in ~/src/gcd-flow/hints (flow_place.tcl -> gcd_placed.def
and .odb; flow_route.tcl, env TAG and HINTS) and ~/tools/openroad/bin/openroad.
Without OpenROAD the probe still plans the hints and, if the route logs exist,
reads them.

    python3 probes/layopt/l4_placer_handoff.py [--name gcd] [--flow DIR] [--no-route] [--no-dissolve]
"""
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
sys.path.insert(0, HERE)
from layopt import drc as rules, extract, lefdef, mergedcell, moves as mv, placer, tech as techmod   # noqa: E402

T = techmod.SKY130
ORFS = os.path.expanduser("~/tools/orfs-sky130hd")
NAME = sys.argv[sys.argv.index("--name") + 1] if "--name" in sys.argv else "gcd"           # design: <name>_placed.def in the flow dir
FLOW = os.path.expanduser(sys.argv[sys.argv.index("--flow") + 1] if "--flow" in sys.argv else "~/src/%s-flow/hints" % NAME)
OPENROAD = os.path.expanduser("~/tools/openroad/bin/openroad")
LEFS = [os.path.join(ORFS, "sky130_fd_sc_hd.tlef"), os.path.join(ORFS, "sky130_fd_sc_hd_merged.lef")]
GDS = os.path.join(ORFS, "sky130_fd_sc_hd.gds")
EVID = os.path.join(HERE, "evidence")


def route(tag, hints_tcl=None):
    env = dict(os.environ, TAG=tag)
    if hints_tcl:
        env["HINTS"] = hints_tcl
    log = os.path.join(FLOW, "route_%s.log" % tag)
    with open(log, "w") as fh:
        subprocess.run([OPENROAD, "-exit", "flow_route.tcl"], cwd=FLOW, env=env, stdout=fh, stderr=subprocess.STDOUT, timeout=6 * 3600)
    return log


def read_route(tag):
    log = os.path.join(FLOW, "route_%s.log" % tag)
    if not os.path.exists(log):
        return None
    txt = open(log).read()
    g = lambda pat: (re.findall(pat, txt) or [None])[-1]
    drc = os.path.join(FLOW, "route_drc_%s.rpt" % tag)
    n_drc = txt.count("violation type") if not os.path.exists(drc) else open(drc).read().count("violation type")
    return {"wire_um": float(g(r"Total wire length = (\d+) um") or 0), "wns": float(g(r"wns max ([-\d.]+)") or 0), "tns": float(g(r"tns max ([-\d.]+)") or 0),
            "area": g(r"Design area (\d+) um\^2"), "drc": n_drc, "overlaps": g(r"Overlap check failed \((\d+)\)"), "ok": "DPL-0033" not in txt and "Complete detail routing" in txt}


def main():
    os.makedirs(EVID, exist_ok=True)
    placed = os.path.join(FLOW, "%s_placed.def" % NAME)
    if not os.path.exists(placed):
        print("no %s: run flow_place.tcl first" % placed); return
    t0 = time.time()
    F = placer.Faces(LEFS, GDS, T, cache_path=os.path.join(EVID, "pair_slides.json"))
    hints = placer.plan_hints(placed, LEFS, GDS, T, abut=True, measure=True, faces=F)
    sm = placer.summary(hints)
    tcl = os.path.join(FLOW, "hints.tcl"); n = placer.write_openroad_tcl(hints, tcl); placer.write_json(hints, os.path.join(FLOW, "hints.json"))
    placer.write_json(hints, os.path.join(EVID, "%s_placer_hints.json" % NAME))
    print("== 1. hints for %s (%.0fs, %d pair layouts): %d logic cells, %d flipped, %d slid (%.2f um of movement), %d boundaries kept (%d two-strip, %d one-strip) worth %.2f um" % (
        os.path.basename(placed), time.time() - t0, len(F._slide), sm["cells"], sm["flipped"], sm["moved"], sm["moved_um"], sm["boundaries"], sm["strips_2"], sm["strips_1"], sm["slide_um"]))
    for h in hints:
        if h.note:
            print("   not asked: %s -- %s" % (h.inst, h.note))
    print("   hints.tcl touches %d cells (setOrient / setLocation / FIRM)" % n)
    if "--no-route" not in sys.argv and os.path.exists(OPENROAD):
        for tag, hp in (("base", None), ("hints", tcl)):
            if not os.path.exists(os.path.join(FLOW, "route_%s.log" % tag)) or tag == "hints":
                t1 = time.time(); route(tag, hp); print("   routed %s in %.0fs" % (tag, time.time() - t1))
    rb, rh = read_route("base"), read_route("hints")
    for tag, r in (("base", rb), ("hints", rh)):
        if r and not r["ok"]:
            print("== 2. the %s routing log is incomplete or failed (no 'Complete detail routing', or the placement check failed): rerun it" % tag)
    if rb and rh and rb["ok"] and rh["ok"]:
        print("== 2. the router's bill: base -> hints: wire %.0f -> %.0f um (%+.1f%%), WNS %.2f -> %.2f ns, TNS %.2f -> %.2f ns, DRC %d -> %d, placement check %s" % (
            rb["wire_um"], rh["wire_um"], 100 * (rh["wire_um"] - rb["wire_um"]) / rb["wire_um"], rb["wns"], rh["wns"], rb["tns"], rh["tns"], rb["drc"], rh["drc"], "ok" if rh["ok"] else "FAILED (%s overlaps)" % rh["overlaps"]))
    hinted = os.path.join(FLOW, "%s_hints_placed.def" % NAME)
    if "--no-dissolve" in sys.argv or not os.path.exists(hinted):
        return
    # 3. the dissolve on the hinted placement: every kept boundary, one at a time from the base
    #    (shift_row: before routing there are no fillers to take the freed space, so the cells
    #    to the right of the boundary slide left with it -- the compaction the hints are for)
    t2 = time.time()
    fl0 = lefdef.def2flat(hinted, LEFS, "", T, gds_lib=GDS)
    ex0 = extract.extract(fl0, T); sig = ex0.signature(); base = {rules.key(v) for v in rules.check(fl0, ex0)}
    prov = {}
    for r in fl0.rects:
        if r.prov.count("/") >= 2 and "/net:" not in r.prov and "/pin:" not in r.prov:
            prov.setdefault(mergedcell.inst_of(r.prov), r.prov)
    print("== 3. dissolve on the hinted placement (%d rects, %d devices, %.0fs to flatten):" % (len(fl0.rects), len(ex0.devices), time.time() - t2))
    import copy
    got = 0.0; n_ok = 0; n_try = 0
    for h in hints:
        if not h.partner_left:
            continue
        a, b = prov.get(h.partner_left), prov.get(h.inst)
        if a is None or b is None:
            print("   %s|%s: not in the layout" % (h.partner_left, h.inst)); continue
        n_try += 1
        fl = copy.deepcopy(fl0); ex = extract.extract(fl, T)
        try:
            t = mv.merge_boundary(fl, ex, a, b, shift_row=True)     # pre-route: no fillers yet, the row's remainder slides
        except mv.MoveError as e:
            print("   %s|%s: refused -- %s" % (h.partner_left, h.inst, str(e)[:100])); continue
        ex2 = extract.extract(fl, T)
        nv = rules.new_violations(fl, ex2, t, base)
        slid = mv.LAST_MERGE_DELTA[0] / 1000.0 if hasattr(mv, "LAST_MERGE_DELTA") else float("nan")
        ok = ex2.signature() == sig and not nv
        n_ok += ok; got += slid if ok else 0
        print("   %s|%s: promised %.3f um, slid %.3f um -> topology %s, %d new violations%s" % (h.partner_left, h.inst, h.slide_left_um, slid, "kept" if ex2.signature() == sig else "CHANGED", len(nv), "" if ok else "  <-- not counted"))
    print("   %d of %d hinted boundaries dissolve legally on the hinted placement, %.2f um given back (hints promised %.2f)" % (n_ok, n_try, got, sm["slide_um"]))


if __name__ == "__main__":
    main()
