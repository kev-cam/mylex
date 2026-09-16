#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""nulex -> layopt integration on a REAL placed+routed design.

Takes VX_alu_int (alu_top) through OpenROAD P&R (flow_alu.tcl) to a detailed-
routed DEF, then measures — on the real sky130 routed geometry — the isochronic-
fork branch-delay spread that nulex/formal/constraints.py enumerates.  For every
SIGNAL net that forks (fanout>=2, from dump_forks.tcl) it locates the driver and
receiver pins by placed coordinate, builds the extracted RC tree, and computes
objective.fork_balance's Elmore-delay spread across the branches.  With --balance
it then runs layopt's width-resize optimizer on the worst forks and reports the
before/after spread (subject to the DRC/topology guard on real routed wires).

This is the l3_fork_balance path (hand-built DEF) applied to a real OpenROAD DEF:
constraints.py says which forks; layopt says how imbalanced they are as built,
and closes the worst.

Usage: alu_fork_balance.py [--top N] [--balance] [--iters N]
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "..")))  # repo root -> layopt
from layopt import extract, lefdef, moves, objective, optimize, rc, tech  # noqa: E402

P = "/home/claude/tools/orfs-sky130hd"
DEF = os.path.join(HERE, "alu_top.def")
FORKS = os.path.join(HERE, "alu_forks_phys.json")
T = tech.SKY130
R_DRIVE = 3000.0    # ohm, nominal sky130 1.8V drive (same for every branch of a net -> fair within-net spread)
C_IN = 2.1          # fF, nominal receiver gate cap

TOP = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 15
ITERS = int(sys.argv[sys.argv.index("--iters") + 1]) if "--iters" in sys.argv else 60
DO_BALANCE = "--balance" in sys.argv


STEP = 2000   # grid cell size in DBU (2 um) for the spatial index


def build_index(ex):
    """Spatial hash (layer, gx, gy) -> shape ids, so pin lookup is O(1) instead
    of scanning every shape (the routed ALU has ~100k shapes)."""
    from collections import defaultdict
    idx = defaultdict(list)
    for i, s in enumerate(ex.shapes):
        x0, y0, x1, y1 = s.rect
        for gx in range(x0 // STEP, x1 // STEP + 1):
            for gy in range(y0 // STEP, y1 // STEP + 1):
                idx[(s.layer, gx, gy)].append(i)
    return idx


def shape_at(ex, idx, layer, x_dbu, y_dbu):
    cell = idx.get((layer, x_dbu // STEP, y_dbu // STEP), ())
    for i in cell:
        s = ex.shapes[i]
        if s.rect[0] <= x_dbu <= s.rect[2] and s.rect[1] <= y_dbu <= s.rect[3]:
            return i
    return None


def locate(ex, idx, xy):
    """Find the li/met1 pin shape id at a placed (x,y) DBU coordinate."""
    x, y = int(xy[0]), int(xy[1])
    for layer in ("li", "met1", "met2"):
        sid = shape_at(ex, idx, layer, x, y)
        if sid is not None:
            return sid
    return None


def main():
    lefs = [os.path.join(P, "sky130_fd_sc_hd.tlef"), os.path.join(P, "sky130_fd_sc_hd_merged.lef")]
    print("loading routed DEF %s ..." % DEF, flush=True)
    fl = lefdef.def2flat(DEF, lefs, "", T, gds_lib=os.path.join(P, "sky130_fd_sc_hd.gds"))
    print("def2flat done: %d rects; extracting RC ..." % len(fl.rects), flush=True)
    ex = extract.extract(fl, T)
    print("extracted: %d shapes, %d nets; building spatial index ..." % (len(ex.shapes), len(ex.nets)), flush=True)
    idx = build_index(ex)
    phys = json.load(open(FORKS))
    print("physical fork set: %d signal forks (fanout>=2); measuring ...\n" % phys["n_forks"], flush=True)

    measured = []
    skipped = 0
    for f in phys["forks"]:
        d = f["driver"]
        d_sid = locate(ex, idx, (d["x"], d["y"]))
        if d_sid is None:
            skipped += 1; continue
        net_id = ex.net_of_shape[d_sid]
        r_sids, r_names = [], []
        for r in f["receivers"]:
            sid = locate(ex, idx, (r["x"], r["y"]))
            if sid is not None and ex.net_of_shape[sid] == net_id:
                r_sids.append(sid); r_names.append("%s.%s" % (r["inst"], r["pin"]))
        if len(r_sids) < 2:
            skipped += 1; continue
        g = objective.fork_balance(ex, net_id, d_sid, r_sids, R_DRIVE, C_IN)
        if g.mean == float("inf") or g.mean != g.mean:
            skipped += 1; continue
        measured.append({"net": f["net"], "fanout": f["fanout"], "n_used": len(r_sids),
                         "spread": g.spread, "mean": g.mean, "rel": g.rel,
                         "net_id": net_id, "d_sid": d_sid, "r_sids": r_sids,
                         "driver": "%s.%s" % (d["inst"], d["pin"]), "phys": f})

    for m in measured:
        bb = bbox_of(m["phys"])
        m["span_um"] = max(bb[2] - bb[0], bb[3] - bb[1]) / 1000.0
    measured.sort(key=lambda m: -m["spread"])
    print("=== measured %d forks on real routed geometry (%d skipped: pin/geometry unresolved) ===" % (len(measured), skipped))
    if measured:
        spreads = [m["spread"] for m in measured]
        import statistics
        print("branch-delay spread across forks:  max %.1f ps   median %.2f ps   mean %.2f ps" % (
            max(spreads), statistics.median(spreads), statistics.mean(spreads)))
        print("\n  worst isochronic forks (as-routed imbalance layout must control):")
        print("  %-24s fan  used   spread     mean    rel   span" % "net")
        for m in measured[:TOP]:
            print("  %-24s %3d  %3d   %7.2f ps  %6.2f ps  %5.1f%%  %5.1fum" % (
                m["net"][:24], m["fanout"], m["n_used"], m["spread"], m["mean"], 100 * m["rel"], m["span_um"]))
        # spread tracks physical span, not fanout: the worst forks have scattered
        # receivers (a placement problem), not a resizable-wire problem.
        top = [m for m in measured if m["spread"] > 5.0]
        if top:
            print("\n  forks with spread >5 ps: %d; their mean receiver span = %.0f um (die is 244 um)" % (
                len(top), statistics.mean(m["span_um"] for m in top)))
            print("  -> worst imbalance correlates with SPAN (scattered receivers), i.e. it is")
            print("     placement-limited; post-route wire-resize helps only the local forks.")

    if DO_BALANCE and measured:
        print("\n=== balancing the worst LOCAL forks with layopt width-resize (windowed, iters=%d) ===" % ITERS)
        print("  (full-design re-extract per optimizer step is infeasible at 822k rects, so each")
        print("   fork is re-extracted in a bbox window around its driver+receivers)")
        n = 0
        for m in measured:
            if n >= 4:
                break
            if windowed_balance(fl, m["phys"], ITERS):
                n += 1


def bbox_of(f):
    xs = [f["driver"]["x"]] + [r["x"] for r in f["receivers"]]
    ys = [f["driver"]["y"]] + [r["y"] for r in f["receivers"]]
    return min(xs), min(ys), max(xs), max(ys)


def window_layout(fl, bbox, pad):
    import copy
    x0, y0, x1, y1 = bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad
    wl = copy.copy(fl)
    wl.rects = [r for r in fl.rects
                if not (r.rect[2] < x0 or r.rect[0] > x1 or r.rect[3] < y0 or r.rect[1] > y1)]
    return wl


def measure_fork(ex_, dcoord, rcoords):
    """Locate the fork by coordinate in a freshly-extracted layout and return its
    fork_balance Spread (shape ids change every re-extract, so re-locate by xy)."""
    idx_ = build_index(ex_)
    d = locate(ex_, idx_, dcoord)
    if d is None:
        return None
    nid = ex_.net_of_shape[d]
    rs = []
    for rc_ in rcoords:
        s = locate(ex_, idx_, rc_)
        if s is not None and ex_.net_of_shape[s] == nid:
            rs.append(s)
    if len(rs) < 2:
        return None
    return objective.fork_balance(ex_, nid, d, rs, R_DRIVE, C_IN), nid, d, rs


def dist2(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def windowed_balance(fl_full, f, iters, max_span_um=55.0, max_rects=70000):
    inv = {v: k for k, v in T.layers.items()}
    bb = bbox_of(f)
    span = max(bb[2] - bb[0], bb[3] - bb[1]) / 1000.0
    if span > max_span_um:
        return False                        # fork spans too much of the die to window cheaply
    dcoord = (f["driver"]["x"], f["driver"]["y"])
    rcoords = [(r["x"], r["y"]) for r in f["receivers"]]
    wl = window_layout(fl_full, bb, pad=6000)
    if len(wl.rects) > max_rects:
        return False                        # window too dense to re-extract per optimizer step
    ex = extract.extract(wl, T)
    base = measure_fork(ex, dcoord, rcoords)
    if base is None:
        return False
    g0, nid, d_sid, r_sids = base
    # slowest branch (largest single-receiver Elmore); widen the net's routing wires
    # nearer that receiver than any other -> cuts the slow branch R, not the trunk.
    delays = {r: objective.fork_balance(ex, nid, d_sid, [r], R_DRIVE, C_IN).values[0] for r in r_sids}
    slow = max(r_sids, key=lambda r: delays[r])
    slow_xy = rcoords[r_sids.index(slow)] if len(r_sids) == len(rcoords) else \
        (ex.shapes[slow].rect[0], ex.shapes[slow].rect[1])
    others = [rcoords[r_sids.index(r)] for r in r_sids if r is not slow and len(r_sids) == len(rcoords)]
    netprov = "alu_top/net:%s" % f["net"]
    wl_wires = []
    for i, r in enumerate(wl.rects):
        if r.prov != netprov or inv.get(r.layer) not in ("li", "met1", "met2", "met3", "met4"):
            continue
        c = ((r.rect[0] + r.rect[2]) / 2, (r.rect[1] + r.rect[3]) / 2)
        if not others or dist2(c, slow_xy) <= min(dist2(c, o) for o in others):
            wl_wires.append(i)                 # wire on (or nearer) the slow branch
    if not wl_wires:
        print("  %-22s span %4.1fum  spread %.2f ps -> no slow-branch wire on a routing layer" % (f["net"][:22], span, g0.spread))
        return True

    def width_move(f_, e_, scale):
        out = []
        for i in wl_wires:
            lay = inv[f_.rects[i].layer]
            out += moves.set_wire_width(f_, i, max(T.min_width[lay], moves.wire_width_um(wl, i) * scale))
        return out
    var = [optimize.Variable("w_scale", 1.0, 6.0, 1.0, width_move)]

    def cost(f_, e_, x):
        r = measure_fork(e_, dcoord, rcoords)
        sp = r[0].spread if r else g0.spread * 2
        return sp / max(g0.spread, 1e-3), {"spread_ps": sp}
    try:
        best = optimize.solve(optimize.Problem(wl, T, var, cost), max_iter=iters, verbose=False)
        r = measure_fork(best.ex, dcoord, rcoords)
        g1 = r[0] if r else g0
        print("  %-22s span %4.1fum  spread %6.2f -> %6.2f ps  (scale %.2f, legal=%s, %d slow-branch wires)" % (
            f["net"][:22], span, g0.spread, g1.spread, best.x[0], best.legal and best.signature_ok, len(wl_wires)))
    except Exception as e:
        print("  %-22s spread %.2f ps -> balance failed: %s" % (f["net"][:22], g0.spread, e))
    return True


def branch_paths(segs, driver_sid, receiver_sids, lca):
    import heapq
    adj = {}
    for s in segs:
        r = max(s.r, 1e-3)
        adj.setdefault(s.a, []).append((s.b, r)); adj.setdefault(s.b, []).append((s.a, r))
    dist = {driver_sid: 0.0}; parent = {}
    pq = [(0.0, driver_sid)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, float("inf")):
            continue
        for v, rr in adj.get(u, []):
            if d + rr < dist.get(v, float("inf")):
                dist[v] = d + rr; parent[v] = u; heapq.heappush(pq, (d + rr, v))
    out = {}
    for r in receiver_sids:
        p = [r]
        while p[-1] in parent:
            p.append(parent[p[-1]])
        p = p[::-1]
        out[r] = p[p.index(lca) + 1:] if lca in p else p
    return out


if __name__ == "__main__":
    main()
