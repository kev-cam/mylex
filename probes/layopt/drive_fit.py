#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""Fit the two-edge driver model to sky130_fd_sc_hd's Liberty tables against
layopt's own extraction of the same cells.

    python3 probes/layopt/drive_fit.py

For each cell: the cell alone in a DEF (so its pin labels name its nets),
def2flat + extract, then per timing arc (input pin -> output pin) the
effective width of the transistors that pin turns on in the output stage --
parallel devices to the rail add, a series stack counts its depth -- and
the Liberty slope of delay vs load on each edge (R = slope / ln 2).
k_p = R_rise * W_p and k_n = R_fall * W_n should be constants; the report
shows how constant, the stack factor from the stacked arcs, and the
least-squares model.  Evidence: evidence/drive_fit.log.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
from layopt import drive, extract, lefdef, tech as techmod  # noqa: E402

T = techmod.SKY130
ORFS = os.path.expanduser("~/tools/orfs-sky130hd")
LIB = os.path.join(ORFS, "sky130_fd_sc_hd__tt_025C_1v80.lib")
P = "sky130_fd_sc_hd__"
CELLS = ["inv_1", "inv_2", "inv_4", "inv_6", "inv_8", "inv_12", "inv_16", "buf_1", "buf_2", "buf_4", "buf_8", "buf_12", "buf_16",
         "clkinv_1", "clkinv_2", "clkinv_4", "clkbuf_1", "clkbuf_4", "nand2_1", "nand2_2", "nand2_4", "nor2_1", "nor2_2", "nor2_4"]
SLEW_PS = 50.0        # the input slew at which the slope is taken (tables: 10 .. 1500 ps)


def cell_layout(lef, name):
    m = lef.macros[P + name]
    w, h = int(round(m.size[0] * 1000)), int(round(m.size[1] * 1000))
    deftext = """VERSION 5.8 ; DESIGN c ; UNITS DISTANCE MICRONS 1000 ; DIEAREA ( 0 0 ) ( %d %d ) ;
COMPONENTS 1 ; - u %s + PLACED ( 0 0 ) N ; END COMPONENTS
SPECIALNETS 2 ; - VPWR ( u VPWR ) + USE POWER ; - VGND ( u VGND ) + USE GROUND ; END SPECIALNETS
END DESIGN""" % (w, h, P + name)
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "c.def"), "w").write(deftext)
        lefs = [os.path.join(ORFS, "sky130_fd_sc_hd.tlef"), os.path.join(ORFS, "sky130_fd_sc_hd_merged.lef")]
        return lefdef.def2flat(os.path.join(td, "c.def"), lefs, "", T, gds_lib=os.path.join(ORFS, "sky130_fd_sc_hd.gds"))


def pin_nets(lef, ex, name):
    """{pin name: net id} from the LEF pin ports: the net whose li shape holds
    the port's centre (cell labels do not survive the merged-GDS flatten)."""
    m = lef.macros[P + name]
    out = {}
    for pname, pin in m.pins.items():
        for lname, (a, b, c, d) in pin.ports:
            if lname not in ("li1", "li", "met1"):
                continue
            x, y = int(round((a + c) / 2 * 1000)), int(round((b + d) / 2 * 1000))
            lay = "li" if lname.startswith("li") else lname
            for i, sh in enumerate(ex.shapes):
                if sh.layer == lay and sh.rect[0] <= x <= sh.rect[2] and sh.rect[1] <= y <= sh.rect[3]:
                    out[pname] = ex.net_of_shape[i]; break
            if pname in out:
                break
    return out


def stage_width(ex, o, g, s, kind):
    """Effective width and stack depth of the `kind` devices that net `g`
    turns on between output net `o` and supply net `s`: parallel devices add;
    a device whose far terminal is an internal node is one leg of a series
    stack whose depth is the number of gates between o and the supply."""
    w_par = 0.0; stack = 1
    for d in ex.devices:
        if d.kind != kind or d.g != g or o not in (d.s, d.d):
            continue
        far = d.d if d.s == o else d.s
        if far == s:
            w_par += d.w
        else:
            # walk the stack from the internal node to the supply
            depth, node, seen = 1, far, {o}
            while node != s and depth < 6:
                seen.add(node)
                nxt = [x for x in ex.devices if x.kind == kind and node in (x.s, x.d) and (x.d if x.s == node else x.s) not in seen]
                if not nxt:
                    break
                node = nxt[0].d if nxt[0].s == node else nxt[0].s; depth += 1
            w_par += d.w; stack = max(stack, depth)
    return w_par, stack


def main():
    lef = lefdef.Lef()
    for f in ("sky130_fd_sc_hd.tlef", "sky130_fd_sc_hd_merged.lef"):
        lefdef.read_lef(os.path.join(ORFS, f), lef)
    lib = drive.read_liberty(LIB, [P + c for c in CELLS])
    print("== %d cells from %s; slope taken at input slew %.0f ps" % (len(lib), os.path.basename(LIB), SLEW_PS))
    print("   %-10s %-4s %5s %5s %6s %7s %7s | %5s %5s %6s %7s %7s" % ("cell", "pin", "Wp", "stk", "Rrise", "kp", "t0r", "Wn", "stk", "Rfall", "kn", "t0f"))
    flat_p, flat_n, stacked = [], [], []
    arcs_by_cell = {}
    for name in CELLS:
        c = lib.get(P + name)
        if c is None or c.output() is None:
            continue
        fl = cell_layout(lef, name)
        ex = extract.extract(fl, T)
        pins = pin_nets(lef, ex, name)
        out = c.output()
        if out.name not in pins or "VPWR" not in pins or "VGND" not in pins:
            print("   %-10s pins not resolved (%s)" % (name, sorted(pins))); continue
        o, vdd, gnd = pins[out.name], pins["VPWR"], pins["VGND"]
        for arc in out.arcs:
            if arc.related_pin not in pins:
                continue
            g = pins[arc.related_pin]
            wp, sp = stage_width(ex, o, g, vdd, "p")
            wn, sn = stage_width(ex, o, g, gnd, "n")
            # a buffer's output stage is driven by its internal node, not the input pin
            if wp == 0 and wn == 0:
                for cand in ex.nets:
                    if cand in (o, g, vdd, gnd):
                        continue
                    wp, sp = stage_width(ex, o, cand, vdd, "p"); wn, sn = stage_width(ex, o, cand, gnd, "n")
                    if wp and wn:
                        break
            if not (wp and wn):
                print("   %-10s %-4s no output-stage devices found" % (name, arc.related_pin)); continue
            fr = drive.edge_fit(arc, "rise", SLEW_PS); ff = drive.edge_fit(arc, "fall", SLEW_PS)
            kp = fr.r_ohm * wp / sp; kn = ff.r_ohm * wn / sn
            print("   %-10s %-4s %5.2f %5d %6.0f %7.0f %7.1f | %5.2f %5d %6.0f %7.0f %7.1f" % (name, arc.related_pin, wp, sp, fr.r_ohm, kp, fr.t0_ps, wn, sn, ff.r_ohm, kn, ff.t0_ps))
            (flat_p if sp == 1 else stacked).append((name, wp, sp, fr))
            (flat_n if sn == 1 else stacked).append((name, wn, sn, ff))
            arcs_by_cell.setdefault(name, []).append((arc, fr, ff))
    # R = k * W^(alpha-1) in log space over the unstacked arcs (inverters and buffers;
    # the ideal 1/W would be alpha = 1)
    inv_p = {wp: fr.r_ohm for name, wp, _, fr in flat_p if name.startswith("inv_")}
    inv_n = {wn: ff.r_ohm for name, wn, _, ff in flat_n if name.startswith("inv_")}
    k_p, a_p = drive.loglog_fit([(wp, fr.r_ohm) for _, wp, _, fr in flat_p])
    k_n, a_n = drive.loglog_fit([(wn, ff.r_ohm) for _, wn, _, ff in flat_n])
    # stack factor per polarity: a stacked arc's R against the same-size inverter's R
    facs_p, facs_n = [], []
    for name, w, stk, f in stacked:
        ref = inv_p if name.startswith("nor") else inv_n
        if w in ref and stk == 2:
            (facs_p if name.startswith("nor") else facs_n).append((name, f.r_ohm / ref[w]))
    s_p = sum(f for _, f in facs_p) / len(facs_p) if facs_p else 2.0
    s_n = sum(f for _, f in facs_n) / len(facs_n) if facs_n else 2.0
    t0r = inv_p and sum(fr.t0_ps for name, _, _, fr in flat_p if name == "inv_1") or 0.0
    t0f = inv_n and sum(ff.t0_ps for name, _, _, ff in flat_n if name == "inv_1") or 0.0
    # slew: per single-stage cell and edge, delay = t0 + ln2 RC + kappa RC s/(RC + mu s), trans = sqrt((tau0 + lam RC)^2 + (nu s)^2)
    print("== slew fits (single-stage cells; rms over the 7x7 table with slews <= 700 ps):")
    print("   %-10s %-4s %-4s %6s %6s %6s %5s %6s %6s %5s" % ("cell", "pin", "edge", "t0", "kappa", "mu", "lam", "tau0", "nu", "rms"))
    sl = {"rise": [], "fall": []}
    for name, arcs in arcs_by_cell.items():
        if name.startswith(("buf", "clkbuf")):
            continue
        for arc, fr, ff in arcs:
            for edge, f0 in (("rise", fr), ("fall", ff)):
                sf = drive.slew_fit(arc, edge, f0.r_ohm)
                sl[edge].append(sf)
                print("   %-10s %-4s %-4s %6.1f %6.3f %6.3f %5.2f %6.1f %6.3f %5.1f" % (name, arc.related_pin, edge, sf.t0_ps, sf.kappa, sf.mu, sf.lam, sf.tau0_ps, sf.nu, sf.rms_ps))
    mean = lambda fs, attr: sum(getattr(f, attr) for f in fs) / len(fs)
    print("   pooled: rise kappa %.3f mu %.3f lam %.2f tau0 %.1f nu %.3f | fall kappa %.3f mu %.3f lam %.2f tau0 %.1f nu %.3f" % (
        mean(sl["rise"], "kappa"), mean(sl["rise"], "mu"), mean(sl["rise"], "lam"), mean(sl["rise"], "tau0_ps"), mean(sl["rise"], "nu"),
        mean(sl["fall"], "kappa"), mean(sl["fall"], "mu"), mean(sl["fall"], "lam"), mean(sl["fall"], "tau0_ps"), mean(sl["fall"], "nu")))
    print("== fit: R_rise = %.0f * Wp^-%.3f, R_fall = %.0f * Wn^-%.3f  [ohm, um]; at W=1: ratio %.2f" % (k_p, a_p, k_n, a_n, k_p / k_n))
    print("   residuals (per cell, fitted/measured R): p %s" % ", ".join("%s %.2f" % (n, k_p * wp ** (-a_p) / fr.r_ohm) for n, wp, _, fr in flat_p))
    print("                                          n %s" % ", ".join("%s %.2f" % (n, k_n * wn ** (-a_n) / ff.r_ohm) for n, wn, _, ff in flat_n))
    print("   series stacks of 2 vs the same-size inverter: PMOS (nor2) %s -> %.2f; NMOS (nand2) %s -> %.2f" % (
        ", ".join("%s %.2f" % x for x in facs_p), s_p, ", ".join("%s %.2f" % x for x in facs_n), s_n))
    print("   intrinsic t0 (inv_1, zero load): rise %.1f ps, fall %.1f ps" % (t0r, t0f))
    dm = getattr(T, "drive", None)
    if dm is not None:
        ok = all(abs(a - b) / b < 0.05 for a, b in ((dm.k_p, k_p), (dm.k_n, k_n), (dm.stack_p, s_p), (dm.stack_n, s_n))) and abs(dm.beta_p - a_p) < 0.02 and abs(dm.beta_n - a_n) < 0.02
        ok = ok and abs(dm.kappa_rise - mean(sl["rise"], "kappa")) < 0.03 and abs(dm.kappa_fall - mean(sl["fall"], "kappa")) < 0.03 \
            and abs(dm.nu_rise - mean(sl["rise"], "nu")) < 0.03 and abs(dm.nu_fall - mean(sl["fall"], "nu")) < 0.03
        print("   tech.SKY130.drive: k_p %.0f beta_p %.3f k_n %.0f beta_n %.3f stack_p %.2f stack_n %.2f kappa %.3f/%.3f nu %.3f/%.3f -> %s" % (
            dm.k_p, dm.beta_p, dm.k_n, dm.beta_n, dm.stack_p, dm.stack_n, dm.kappa_rise, dm.kappa_fall, dm.nu_rise, dm.nu_fall, "OK" if ok else "UPDATE"))
    print("RESULT k_p=%.0f beta_p=%.3f k_n=%.0f beta_n=%.3f stack_p=%.2f stack_n=%.2f t0_rise=%.1f t0_fall=%.1f" % (k_p, a_p, k_n, a_n, s_p, s_n, t0r, t0f))

if __name__ == "__main__":
    main()
