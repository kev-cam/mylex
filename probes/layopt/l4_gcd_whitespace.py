#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""layopt L4 on a real place-and-route result: grow drivers into the filler
cells OpenROAD left beside them (gcd on sky130hd, probes/layopt/gcd/gcd.def).

For each candidate cell with a fill_4/fill_8 flush on its right: add a finger
to its PMOS and NMOS, re-extract the whole 57k-rect layout, apply the
topology + delta-DRC guard, and report the Elmore delay of the cell's output
net before/after with R_drv scaled by 1/W (receivers' Cin from their gate
area at 8.5 fF/um^2).

Usage: l4_gcd_whitespace.py [--def path] [--max N] [--only inst1,inst2] [--local | --global]
(--local, the default for a DEF other than gcd's: each candidate judged on its three-row window)
"""
import copy
import glob
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
from layopt import drc, extract, gds, lefdef, moves, power, rc, tech   # noqa: E402

ORFS = os.path.expanduser("~/tools/orfs-sky130hd")
DEF = sys.argv[sys.argv.index("--def") + 1] if "--def" in sys.argv else os.path.join(HERE, "gcd", "gcd.def")
MAXC = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 6
EVID = os.path.join(HERE, "evidence")
T = tech.SKY130
COX = 8.5                      # fF/um^2 gate capacitance for receiver Cin


def candidates(lef, d, sizes):
    rows = {}
    for c in d.components:
        rows.setdefault(c.y, []).append(c)
    out = []
    for y, cs in rows.items():
        cs.sort(key=lambda c: c.x)
        for a, b in zip(cs, cs[1:]):
            if any(k in a.macro for k in ("fill", "tap", "decap")):
                continue
            if ("fill_4" in b.macro or "fill_8" in b.macro) and a.orient == "N" and a.x + sizes[a.macro] == b.x:
                out.append((a, b))
    prio = {"nand2_1": 0, "clkinv_1": 1, "inv_1": 1, "buf_4": 2, "nor2_1": 0}
    out.sort(key=lambda ab: prio.get(ab[0].macro.replace("sky130_fd_sc_hd__", ""), 9))
    return out


def output_net(ex, inst):
    """The cell's output net: the net driven by its PMOS drains that is not a supply."""
    for dv in ex.devices:
        if dv.prov.split("/")[1] == inst and dv.kind == "p":
            for n in (dv.d, dv.s):
                nm = ex.nets[n].name
                if nm not in ("VDD", "VSS", "VPWR", "VGND"):
                    return n
    return None


def net_delay(ex, net_id, inst):
    """Elmore (ps) from the driver's output shape to each receiver gate on the
    net, on the worse edge: R_rise from the cell's PMOS width, R_fall from its
    NMOS width (tech.SKY130.drive; a series stack of n costs its fitted
    factor).  Returns (W_p, (R_rise, R_fall), {receiver: max(rise, fall)})."""
    net = ex.nets[net_id]
    sup = {i for i, n in ex.nets.items() if n.name in T.supply_names}
    # the output stage: the cell's devices with a terminal on the output net; one whose
    # other terminal is an internal node (not a supply) is a leg of a series stack
    stage = [dv for dv in ex.devices if dv.prov.split("/")[1] == inst and net_id in (dv.s, dv.d)]
    def eff(kind):
        legs = [dv for dv in stage if dv.kind == kind]
        stacked = [dv for dv in legs if (dv.d if dv.s == net_id else dv.s) not in sup]
        if stacked and len(stacked) == len(legs):
            return sum(dv.w for dv in legs), 2
        return sum(dv.w for dv in legs), 1
    wp, sp = eff("p"); wn, sn = eff("n")
    dm = T.drive
    flav = lambda kind: next((T.flavour_of_model(dv.model) for dv in stage if dv.kind == kind), None)
    glen = lambda kind: max([dv.l for dv in stage if dv.kind == kind] or [None])
    r_rise, r_fall = dm.r_rise(wp, sp, flav("p"), glen("p")), dm.r_fall(wn, sn, flav("n"), glen("n"))
    r_drv = (r_rise, r_fall)
    drv = next(s for s in net.shapes if ex.shapes[s].layer.startswith("sd_") and ex.shapes[s].prov.split("/")[1] == inst)
    recv = {}
    for name, term in net.devices:
        dv = ex.devices[int(name[1:]) - 1]
        if term == "G" and dv.prov.split("/")[1] != inst:
            gs = dv.gate_ids[0]
            recv[gs] = recv.get(gs, 0.0) + COX * dv.w * dv.l
    if not recv:
        return wp, r_drv, {}
    dr = rc.elmore_delays(ex, net_id, drv, list(recv), r_rise, recv)
    df = rc.elmore_delays(ex, net_id, drv, list(recv), r_fall, recv)
    return wp, r_drv, {k: max(dr[k], df[k]) for k in dr}


def main():
    os.makedirs(EVID, exist_ok=True)
    lefs = [os.path.join(ORFS, "sky130_fd_sc_hd.tlef"), os.path.join(ORFS, "sky130_fd_sc_hd_merged.lef")]
    lef = lefdef.Lef()
    for f in lefs:
        lefdef.read_lef(f, lef)
    d = lefdef.read_def(DEF)
    sizes = {m.name: int(round(m.size[0] * 1000)) for m in lef.macros.values()}
    t0 = time.time()
    local = "--local" in sys.argv or ("--global" not in sys.argv and "gcd" not in os.path.basename(DEF))
    fl = lefdef.def2flat(DEF, lefs, "", T, gds_lib=os.path.join(ORFS, "sky130_fd_sc_hd.gds"))
    if local:
        # a large design: each candidate is judged on the three-row window around it (a deep
        # copy of the band plus every DEF wire and label, so nets keep their names); the
        # whole layout is never extracted
        ex = sig = base = None
        print("== %s: %d instances, %d rects; candidates judged on three-row windows (%.0fs to flatten)" % (
            os.path.basename(DEF), len(d.components), len(fl.rects), time.time() - t0))
    else:
        ex = extract.extract(fl, T)
        sig = ex.signature()
        base = {drc.key(v) for v in drc.check(fl, ex)}
        print("== %s: %d instances, %d rects, %d devices; baseline rule flags %d (%.0fs)" % (
            os.path.basename(DEF), len(d.components), len(fl.rects), len(ex.devices), len(base), time.time() - t0))
    cands = candidates(lef, d, sizes)
    only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
    if only:
        cands = [(a, b) for a, b in cands if a.inst in only]
    maxc = len(cands) if only else MAXC
    print("   %d logic cells have a fill_4/fill_8 flush on their right; trying %d" % (len(cands), min(maxc, len(cands))))
    results = []
    for a, b in cands[:maxc]:
        if local:
            prov_a = next(p for p in fl.boxes if "/%s/" % a.inst in p)
            bx = fl.boxes[prov_a]
            y0, y1 = bx[1] - 2720, bx[3] + 2720
            fw = gds.FlatLayout(dbu_um=fl.dbu_um, top=fl.top)
            # the band, plus the supply nets' DEF wires wherever they are (their labels name the
            # supplies); a routed design's signal wires come along only where they cross the band
            fw.rects = copy.deepcopy([r for r in fl.rects if (r.y1 > y0 and r.y0 < y1) or ("/net:" in r.prov and r.prov.rsplit(":", 1)[-1] in T.supply_names)])
            fw.texts = copy.deepcopy(list(getattr(fl, "texts", [])))
            fw.boxes = {p_: b_ for p_, b_ in fl.boxes.items() if b_[3] > y0 and b_[1] < y1}
            tw = time.time()
            exw = extract.extract(fw, T); sigw = exw.signature(); basew = {drc.key(v) for v in drc.check(fw, exw)}
            print("   [window %d rects, %d devices, %.0fs]" % (len(fw.rects), len(exw.devices), time.time() - tw))
            evaluate(fw, exw, basew, sigw, a, b, results, write_gds=False)
        else:
            evaluate(fl, ex, base, sig, a, b, results, write_gds=True)
    print("   legal moves: %d of %d attempted" % (sum(1 for _, l in results if l), len(results)))


def evaluate(fl, ex, base, sig, a, b, results, write_gds=True):
    """One candidate cell on the given layout (the whole design, or its window)."""
    inst = a.inst
    net = output_net(ex, inst)
    wp0, r0, d0 = net_delay(ex, net, inst) if net is not None else (0, 0, {})
    # both orders: a series stack's far-gate bridge needs the field gap's met1 before a
    # PMOS jumper takes it, and vice versa; keep whichever order legalizes more fingers
    best_state = None
    for order in (("p", "n"), ("n", "p")):
        st = attempt_order(fl, ex, base, sig, inst, a, b, net, order)
        if best_state is None or len(st[2]) > len(best_state[2]):
            best_state = st
        if len(best_state[2]) == 2:
            break
    fl2, touched, done = best_state
    if not done:
        return
    ex3 = extract.extract(fl2, T)
    legal = True
    wp1, r1, d1 = (0, 0, {})
    try:
        wp1, r1, d1 = net_delay(ex3, net, inst) if net is not None else (0, 0, {})
    except StopIteration:
        pass
    devs = ["%s W=%.2f f=%d" % (x.kind, x.w, x.fingers) for x in ex3.devices if x.prov.split("/")[1] == inst]
    print("      result (%s): %s" % ("+".join(done), "; ".join(devs)))
    # the power price: switched capacitance of the nets the cell touches, before and after
    touched_nets0 = {n for x in ex.devices if x.prov.split("/")[1] == inst for n in (x.g, x.s, x.d) if ex.nets[n].name not in T.supply_names}
    names = {ex.nets[n].name for n in touched_nets0}
    touched_nets1 = {i for i, n in ex3.nets.items() if n.name in names}
    e0 = power.energy_fJ(ex, touched_nets0); e1 = power.energy_fJ(ex3, touched_nets1)
    print("      switched energy of the cell's nets: %.1f -> %.1f fJ/transition (+%.1f, %+.0f%%)" % (e0, e1, e1 - e0, 100 * (e1 - e0) / e0 if e0 else 0))
    if net is not None and d0 and d1:
        print("      output net %s: PMOS W %.2f -> %.2f um, R_rise/R_fall %.0f/%.0f -> %.0f/%.0f ohm; worst-edge Elmore to %d receivers max %.1f -> %.1f ps, mean %.1f -> %.1f ps" % (
            ex.nets[net].name, wp0, wp1, r0[0], r0[1], r1[0], r1[1], len(d0), max(d0.values()), max(d1.values()),
            sum(d0.values()) / len(d0), sum(d1.values()) / len(d1)))
    results.append((inst, legal))
    if write_gds and legal and not any(r[1] for r in results[:-1]):
        gds.write_flat(fl2, os.path.join(EVID, "gcd_%s_fingered.gds" % inst.strip("_")))


def attempt_order(fl, ex, base, sig, inst, a, b, net, order):
    """Apply fingers in the given order; return (layout, touched, kinds done)."""
    fl2 = copy.deepcopy(fl)
    touched = []
    done = []
    if True:
        for kind in order:
            ex2 = extract.extract(fl2, T) if touched else ex
            dev = [x for x in ex2.devices if x.prov.split("/")[1] == inst and x.kind == kind]
            if not dev:
                continue
            dev.sort(key=lambda x: -max(ex2.shapes[g].rect[2] for g in x.gate_ids))       # outermost gate on the right
            trial = copy.deepcopy(fl2)
            try:
                t_new = moves.add_finger(trial, ex2, dev[0], side="high")
            except moves.MoveError as e:
                print("   %s (%s, %s to its right) [%s]: %s finger refused -- %s" % (inst, a.macro.replace("sky130_fd_sc_hd__", ""), b.macro.replace("sky130_fd_sc_hd__", ""), "".join(order).upper(), kind.upper(), str(e)))
                continue
            ex_t = extract.extract(trial, T)
            viol_t = drc.new_violations(trial, ex_t, t_new, base)
            topo_t = ex_t.signature() == sig
            if topo_t and not viol_t:
                fl2 = trial; touched += t_new; done.append(kind.upper())
                print("   %s (%s, %s to its right) [%s]: %s finger LEGAL (%d rects)" % (inst, a.macro.replace("sky130_fd_sc_hd__", ""), b.macro.replace("sky130_fd_sc_hd__", ""), "".join(order).upper(), kind.upper(), len(t_new)))
            else:
                inv = {v: k for k, v in T.layers.items()}
                print("   %s (%s, %s to its right): %s finger REJECTED by the guard: topology %s, %d new violations" % (
                    inst, a.macro.replace("sky130_fd_sc_hd__", ""), b.macro.replace("sky130_fd_sc_hd__", ""), kind.upper(), "preserved" if topo_t else "CHANGED", len(viol_t)))
                for v in viol_t[:3]:
                    ra = trial.rects[v.a]; rb = trial.rects[v.b] if v.b >= 0 else None
                    print("      %s  [%s %s%s]" % (v, inv.get(ra.layer, ra.layer), ra.prov.split("/", 1)[1], "" if rb is None else " vs %s %s" % (inv.get(rb.layer, rb.layer), rb.prov.split("/", 1)[1])))
    return fl2, touched, done


if __name__ == "__main__":
    main()
