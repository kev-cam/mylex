#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""Calibrate layopt's Elmore basis against OpenSTA on a routed SG13G2 DEF.

Per stage of OpenSTA's worst paths (report_checks -fields {capacitance slew
input_pins nets fanout}), rebuild the stage delay the way layopt will price a
move after the cell is no longer the library cell:

  gate = t0(arc, slew_in) + ln2 * R(arc, slew_in) * C_total
  wire = ln2 * (Elmore moment from the driver pin shape to the receiver pin
                shape over layopt's extracted RC tree)

with t0 and R the intercept/slope of the Liberty delay-vs-load row at the
reported input slew (drive.edge_fit -- the same fit that built sky130's
DriveModel), C_total = layopt's extracted wire C plus the Liberty input caps
of every receiver on the net.  OpenSTA's own gate delay (output-pin line) and
wire delay (next input-pin line) are read from the report.  The table, the
per-stage correlation and the mean offset are what make later ELMORE-BASIS
deltas defensible.

Usage: elmore_calibrate_ihp.py routed.def sta_report.log [--paths N] [--out DIR]
"""
import math
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
from layopt import drive, extract, gds, lefdef, rc, tech        # noqa: E402

PDK = os.environ.get("IHP_PDK", "/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell")
LIB = PDK + "/lib/sg13g2_stdcell_typ_1p20V_25C.lib"
T = tech.SG13G2
LN2 = math.log(2.0)


def arg(flag, default):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


# ---------------------------------------------------------------- STA report
PIN_RE = re.compile(r"^\s*(?:(\d+)\s+)?(?:([\d.]+)\s+)?([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\^v])\s+(\S+)/(\S+)\s+\((\S+)\)")


def parse_paths(path, max_paths=10):
    """Yield paths as lists of pin events {inst, pin, cell, edge, fanout, cap_fF,
    slew_ps, delay_ps, time_ps, is_out}.  Columns: [Fanout] [Cap] Slew Delay Time."""
    paths, cur = [], None
    for line in open(path):
        if line.strip().startswith("Startpoint:"):
            cur = []
            continue
        if cur is None:
            continue
        if "data arrival time" in line:
            paths.append(cur); cur = None
            if len(paths) >= max_paths:
                break
            continue
        m = PIN_RE.match(line)
        if not m:
            continue
        fanout, cap, slew, delay, tm, edge, inst, pin, cell = m.groups()
        cur.append(dict(inst=inst, pin=pin, cell=cell, edge=edge,
                        fanout=int(fanout) if fanout else None,
                        cap_fF=float(cap) * 1000.0 if cap else None,
                        slew_ps=float(slew) * 1000.0,
                        delay_ps=float(delay) * 1000.0,
                        time_ps=float(tm) * 1000.0,
                        is_out=cap is not None))
    return paths


# ------------------------------------------------------------- pin locations
def pin_center_nm(lef, d, comps_by, inst, pin):
    """Die coordinates (nm) of the centre of a component pin's first port rect,
    the same transform def2flat uses for unrouted-net labels."""
    comp = comps_by[inst]
    m = lef.macros[comp.macro]
    pl, (a, b, c2, e) = m.pins[pin].ports[0]
    mirror, angle = lefdef.ORIENT[comp.orient]
    ref = gds.Ref(comp.macro, (0, 0), mirror_x=mirror, angle=angle)
    w_nm, h_nm = int(round(m.size[0] * 1000)), int(round(m.size[1] * 1000))
    corners = [gds._xform(p, ref, (0, 0)) for p in ((0, 0), (w_nm, 0), (0, h_nm), (w_nm, h_nm))]
    scale = 1000.0 / d.dbu_per_um
    off = (int(round(comp.x * scale)) - min(p[0] for p in corners),
           int(round(comp.y * scale)) - min(p[1] for p in corners))
    cx, cy = gds._xform((int(round((a + c2) / 2 * 1000)), int(round((b + e) / 2 * 1000))), ref, off)
    lt = (T.lef2tech or {}).get(pl, pl)
    return lt, cx, cy


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    def_path, rpt = sys.argv[1], sys.argv[2]
    max_paths = int(arg("--paths", "10"))
    lefs = [PDK + "/lef/sg13g2_tech.lef", PDK + "/lef/sg13g2_stdcell.lef"]
    lef = lefdef.Lef()
    for p in lefs:
        lefdef.read_lef(p, lef)
    d = lefdef.read_def(def_path)
    comps_by = {c.inst: c for c in d.components}
    net_of_pin = {}
    pins_of_net = defaultdict(list)
    for net in d.nets:
        for inst, pin in net.pins:
            net_of_pin[(inst, pin)] = net.name
            pins_of_net[net.name].append((inst, pin))

    print("== def2flat + extract %s" % def_path)
    fl = lefdef.def2flat(def_path, lefs, "", T, gds_lib=PDK + "/gds/sg13g2_stdcell.gds")
    ex = extract.extract(fl, T)
    print("   %d rects -> %d nets, %d devices" % (len(fl.rects), len(ex.nets), len(ex.devices)))
    nets_by_name = {}
    for n in ex.nets.values():
        nets_by_name.setdefault(n.name, n)

    from layopt import geom
    idx = {}
    for i, s in enumerate(ex.shapes):
        idx.setdefault(s.layer, geom.BinIndex()).add(i, s.rect)

    def shape_at(lname, x, y, net_id=None):
        bi = idx.get(lname)
        if not bi:
            return None
        for sid in bi.candidates((x, y, x, y)):
            r = ex.shapes[sid].rect
            if r[0] <= x <= r[2] and r[1] <= y <= r[3]:
                if net_id is None or ex.net_of_shape[sid] == net_id:
                    return sid
        return None

    paths = parse_paths(rpt, max_paths)
    print("== %d paths from %s" % (len(paths), rpt))
    cells = drive.read_liberty(LIB)     # all cells: input caps for every receiver

    def cin_fF(inst, pin):
        c = cells.get(comps_by[inst].macro)
        p = c.pins.get(pin) if c else None
        return p.capacitance_fF if p else 0.0

    def fit(cellname, related, out_edge, slew_ps):
        """Worst (max-delay) Liberty arc fit for this input->output edge."""
        c = cells.get(cellname)
        o = c.output() if c else None
        best = None
        for a in (o.arcs if o else []):
            if a.related_pin != related:
                continue
            f = drive.edge_fit(a, "rise" if out_edge == "^" else "fall", slew_ps=slew_ps)
            mid = f.t0_ps + LN2 * f.r_ohm * a.loads[len(a.loads) // 2] / 1000.0
            if best is None or mid > best[1]:
                best = (f, mid)
        return best[0] if best else None

    rows = []
    fails = []
    for pi, pth in enumerate(paths):
        # stage pairs: input-pin line followed by output-pin line of the same inst
        for k in range(len(pth) - 1):
            a, b = pth[k], pth[k + 1]
            if a["is_out"] or not b["is_out"] or a["inst"] != b["inst"]:
                continue
            inst, cellname = a["inst"], a["cell"]
            netname = net_of_pin.get((inst, b["pin"]))
            # OpenSTA wire delay: the next input-pin line (the path's receiver)
            rec = pth[k + 2] if k + 2 < len(pth) else None
            sta_gate = b["delay_ps"]
            sta_wire = rec["delay_ps"] if rec and not rec["is_out"] else 0.0
            f = fit(cellname, a["pin"], b["edge"], a["slew_ps"])
            if f is None or netname is None or netname not in nets_by_name:
                fails.append((pi, inst, cellname, "no arc fit" if f is None else "net %r not extracted" % netname))
                continue
            net = nets_by_name[netname]
            # every receiver pin: shape + input cap
            c_in = {}
            rsid = dsid = None
            for (ri, rp) in pins_of_net[netname]:
                if ri not in comps_by:              # ( PIN name ): a top-level port, no macro pin
                    continue
                lt, x, y = pin_center_nm(lef, d, comps_by, ri, rp)
                sid = shape_at(lt, x, y, net.id)
                if sid is None:
                    continue
                if (ri, rp) == (inst, b["pin"]):
                    dsid = sid
                else:
                    c_in[sid] = c_in.get(sid, 0.0) + cin_fF(ri, rp)
                    if rec and (ri, rp) == (rec["inst"], rec["pin"]):
                        rsid = sid
            if dsid is None or (rec and rsid is None):
                fails.append((pi, inst, cellname, "pin shape not found on net %s" % netname))
                continue
            segs = rc.net_segments(ex, net.id)
            targets = [rsid] if rsid is not None else []
            mom = rc.elmore_delays(ex, net.id, dsid, targets, r_drive=f.r_ohm, c_in_fF=c_in, segments=segs)
            c_wire = rc.shapes_c_fF(ex, net.shapes)
            c_total = c_wire + sum(c_in.values())
            m_total = mom[rsid] if rsid is not None else f.r_ohm * c_total * 1e-3
            gate_est = f.t0_ps + LN2 * f.r_ohm * c_total * 1e-3
            wire_est = LN2 * max(m_total - f.r_ohm * c_total * 1e-3, 0.0)
            rows.append(dict(path=pi, inst=inst, cell=cellname, arc="%s->%s %s" % (a["pin"], b["pin"], b["edge"]),
                             net=netname, sta_cap=b["cap_fF"], our_cap=c_total,
                             sta_gate=sta_gate, our_gate=gate_est,
                             sta_wire=sta_wire, our_wire=wire_est,
                             sta_tot=sta_gate + sta_wire, our_tot=gate_est + wire_est))
    # ---- report ----
    print("\n%-4s %-12s %-22s %-16s | %7s %7s | %7s %7s | %7s %7s | %7s %7s" % (
        "path", "inst", "cell", "arc", "C_sta", "C_lay", "g_sta", "g_lay", "w_sta", "w_lay", "t_sta", "t_lay"))
    for r in rows:
        print("%-4d %-12s %-22s %-16s | %7.1f %7.1f | %7.1f %7.1f | %7.1f %7.1f | %7.1f %7.1f" % (
            r["path"], r["inst"][:12], r["cell"][:22], r["arc"], r["sta_cap"], r["our_cap"],
            r["sta_gate"], r["our_gate"], r["sta_wire"], r["our_wire"], r["sta_tot"], r["our_tot"]))
    def stats(xs, ys, label):
        n = len(xs)
        if n < 2:
            return
        mx, my = sum(xs) / n, sum(ys) / n
        cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        vx = sum((x - mx) ** 2 for x in xs); vy = sum((y - my) ** 2 for y in ys)
        r_ = cov / math.sqrt(vx * vy) if vx > 0 and vy > 0 else float("nan")
        err = [y - x for x, y in zip(xs, ys)]
        me = sum(err) / n
        rms = math.sqrt(sum(e * e for e in err) / n)
        ratio = sum(ys) / sum(xs) if sum(xs) else float("nan")
        print("   %-18s n=%3d  r=%.4f  mean offset %+7.2f ps  rms %7.2f ps  sum ratio %.3f" % (label, n, r_, me, rms, ratio))
    print("\n== calibration (layopt vs OpenSTA), per stage (all path stages):")
    stats([r["sta_gate"] for r in rows], [r["our_gate"] for r in rows], "gate (ELMORE)")
    stats([r["sta_wire"] for r in rows], [r["our_wire"] for r in rows], "wire (ELMORE)")
    stats([r["sta_tot"] for r in rows], [r["our_tot"] for r in rows], "stage total")
    stats([r["sta_cap"] for r in rows], [r["our_cap"] for r in rows], "net C (fF)")
    seen = set(); uniq = []
    for r in rows:
        k = (r["inst"], r["arc"])
        if k not in seen:
            seen.add(k); uniq.append(r)
    print("== unique stages (worst paths share their launch chains; each stage once):")
    stats([r["sta_gate"] for r in uniq], [r["our_gate"] for r in uniq], "gate (ELMORE)")
    stats([r["sta_wire"] for r in uniq], [r["our_wire"] for r in uniq], "wire (ELMORE)")
    stats([r["sta_tot"] for r in uniq], [r["our_tot"] for r in uniq], "stage total")
    stats([r["sta_cap"] for r in uniq], [r["our_cap"] for r in uniq], "net C (fF)")
    per_path_sta = defaultdict(float); per_path_our = defaultdict(float)
    for r in rows:
        per_path_sta[r["path"]] += r["sta_tot"]; per_path_our[r["path"]] += r["our_tot"]
    print("== per path sums (stage-covered part of the path):")
    for pi in sorted(per_path_sta):
        print("   path %2d: OpenSTA %8.1f ps  layopt %8.1f ps  (%+.1f%%)" % (
            pi, per_path_sta[pi], per_path_our[pi],
            100.0 * (per_path_our[pi] - per_path_sta[pi]) / per_path_sta[pi]))
    if fails:
        print("== stages not calibrated (%d):" % len(fails))
        for f_ in fails[:12]:
            print("   path %d %s (%s): %s" % f_)


if __name__ == "__main__":
    main()
