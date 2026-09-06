#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""layopt L5 probe: variation-aware acceptance of a balanced fork, two tiers.

The L3 fork (inv u1 -> u2 and -> v4, long branch on met2 or on li1), before
and after layopt's branch sizing.  The isochronic-fork requirement: the slow
branch must arrive within one gate delay (T_GATE) of the fast one, or the
acknowledging gate can fire before the other branch has settled.

  T2 (layopt, statistical): layopt's RC tree with per-layer sheet-resistance
      and capacitance scale factors drawn from a variation model; N samples of
      the branch skew; p_fail = P(|skew| > T_GATE).
  T3 (stat-sim under nvc, event-driven): the same fork reduced to trunk +
      branch RC (rc.fork_branches) and run through stat-sim's statsim_pl_rc
      wire elements and pl_load taps -- the runtime the CDC/MTBF flow uses --
      nominal, then M Monte-Carlo elaborations with the same variation model
      passed as top-level generics; hazards counted by a checker at the two
      receiver nodes.

Usage: l5_variation_accept.py [--samples N] [--mc M]
Needs: nvc (/usr/local/src/nvc/build), stat-sim (/usr/local/src/stat-sim), sky130 cells.
"""
import copy
import glob
import math
import os
import random
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
sys.path.insert(0, HERE)
from layopt import extract, lefdef, moves, rc, tech           # noqa: E402
import l3_fork_balance as L3                                   # noqa: E402

LIB = L3.LIB
SCR = os.environ.get("LAYOPT_SCRATCH", "/tmp")
EVID = os.path.join(HERE, "evidence")
NVC = os.environ.get("NVC", "/usr/local/src/nvc/build/bin/nvc")
NVCLIB = os.environ.get("NVCLIB", "/usr/local/src/nvc/build/lib")
STATSIM = os.environ.get("STATSIM", "/usr/local/src/stat-sim")
T = tech.SKY130
NSAMP = int(sys.argv[sys.argv.index("--samples") + 1]) if "--samples" in sys.argv else 4000
NMC = int(sys.argv[sys.argv.index("--mc") + 1]) if "--mc" in sys.argv else 60
R_DRIVE, C_IN = L3.R_DRIVE, L3.C_IN
T_GATE_PS = 40.0
# flop side (stat-sim specs/sky130_dfxtp.json): tau = T0 = 15.7 ps; launches at 500 MHz
TAU_PS, T0_PS, F_LAUNCH = 15.7, 15.7, 500e6


def mtbf_s(skew_ps):
    """stat-sim's MTBF = exp(t_slack/tau) / (T0 f_c f_d) with slack = T_GATE - |skew|."""
    slack = (T_GATE_PS - abs(skew_ps)) * 1e-12
    return math.exp(slack / (TAU_PS * 1e-12)) / (T0_PS * 1e-12 * F_LAUNCH * F_LAUNCH)


def fmt_t(sec):
    if sec == float("inf"): return "inf"
    for unit, k in (("y", 3.156e7), ("d", 86400.0), ("h", 3600.0), ("s", 1.0), ("ms", 1e-3), ("us", 1e-6), ("ns", 1e-9)):
        if sec >= k: return "%.3g %s" % (sec / k, unit)
    return "%.3g s" % sec
# variation model (1-sigma relative): thin li varies more than thick metal
SIG_R = {"li": 0.15, "met1": 0.10, "met2": 0.10, "met3": 0.10, "poly": 0.12}
SIG_C = 0.08
SIG_CIN = 0.10
SIG_RDRV = 0.15
SEED = 20260906


def sized_layout(fl, ex, inv, wireA, wireB, scaleA, scaleB):
    fl2 = copy.deepcopy(fl)
    for i in wireA:
        moves.set_wire_width(fl2, i, max(T.min_width[inv[fl2.rects[i].layer]], moves.wire_width_um(fl, i) * scaleA))
    for i in wireB:
        moves.set_wire_width(fl2, i, max(T.min_width[inv[fl2.rects[i].layer]], moves.wire_width_um(fl, i) * scaleB))
    return fl2, extract.extract(fl2, T)


def t2_mc(ex, net_id, d, a, b, rng, n):
    """Skew samples (ps) with per-layer R and C scale factors."""
    segs0 = rc.net_segments(ex, net_id)
    tech0 = ex.tech
    out = []
    for _ in range(n):
        rs = {l: rng.gauss(1.0, s) for l, s in SIG_R.items()}
        cs = rng.gauss(1.0, SIG_C)
        segs = [rc.Segment(s.a, s.b, s.r * rs.get(s.layer, 1.0) if s.kind == "wire" else s.r, s.layer, s.kind) for s in segs0]
        t2 = copy.copy(tech0)
        t2.carea = {k: v * cs for k, v in tech0.carea.items()}
        t2.cfringe = {k: v * cs for k, v in tech0.cfringe.items()}
        ex.tech = t2
        cin = {a: C_IN * rng.gauss(1.0, SIG_CIN), b: C_IN * rng.gauss(1.0, SIG_CIN)}
        dl = rc.elmore_delays(ex, net_id, d, [a, b], R_DRIVE * rng.gauss(1.0, SIG_RDRV), cin, segments=segs)
        out.append(dl[b] - dl[a])
    ex.tech = tech0
    return out


TB = """library ieee; use ieee.std_logic_1164.all;
library statsim; use statsim.statsim_disc_pkg.all;
entity l5_fork_tb is
  generic ( RT : real := %(RT)g; CT : real := %(CT)g; RA : real := %(RA)g; CA : real := %(CA)g;
            RB : real := %(RB)g; CB : real := %(CB)g; CINA : real := %(CIN)g; CINB : real := %(CIN)g;
            TGATE_FS : integer := %(TGATE_FS)d; NLAUNCH : integer := 6 );
end entity;
architecture tb of l5_fork_tb is
  signal launch : std_ulogic := '0';
  signal n_drv, n_fork, n_a, n_b : resolved_pl;
  signal t_a, t_b : time := 0 fs;
  signal seen_a, seen_b : boolean := false;
  signal hazards, launches : natural := 0;
begin
  launch <= not launch after 2 ns;
  inv   : entity statsim.statsim_inv port map (i => launch, o => n_drv);
  trunk : entity statsim.statsim_pl_rc generic map (C => CT, R => RT) port map (a => n_drv, b => n_fork);
  bra   : entity statsim.statsim_pl_rc generic map (C => CA, R => RA) port map (a => n_fork, b => n_a);
  brb   : entity statsim.statsim_pl_rc generic map (C => CB, R => RB) port map (a => n_fork, b => n_b);
  la    : entity statsim.statsim_pl_load generic map (CIN => CINA) port map (n => n_a);
  lb    : entity statsim.statsim_pl_load generic map (CIN => CINB) port map (n => n_b);
  mon_a : process(n_a) begin
    if n_a.px < 0.5 and (n_a.p1 > 0.5 or n_a.p0 > 0.5) then t_a <= now; seen_a <= true; end if;
  end process;
  mon_b : process(n_b) begin
    if n_b.px < 0.5 and (n_b.p1 > 0.5 or n_b.p0 > 0.5) then t_b <= now; seen_b <= true; end if;
  end process;
  chk : process(t_a, t_b)
    variable skew : time;
  begin
    if seen_a and seen_b and t_a > 0 fs and t_b > 0 fs and abs(t_a - t_b) < 1 ns then
      skew := t_b - t_a;
      report "L5 SKEW " & integer'image(skew / 1 fs) severity note;
    end if;
  end process;
  ctl : process
    variable skew : time; variable haz : natural := 0; variable n : natural := 0;
  begin
    wait for 1 ns;
    for k in 1 to NLAUNCH loop
      wait until launch'event; wait for 1 ns;               -- both arrivals settled well before the next launch
      n := n + 1;
      skew := t_b - t_a;
      if abs(skew) > TGATE_FS * 1 fs then haz := haz + 1; end if;
    end loop;
    report "L5 DONE launches=" & integer'image(n) & " hazards=" & integer'image(haz) severity note;
    std.env.finish;
  end process;
end architecture;
"""


def run_nvc(work, tb_path, gens):
    lib = ["--std=2040", "-L", NVCLIB, "--work=statsim:%s/statsim" % work]
    gargs = ["-g%s=%s" % (k, v) for k, v in gens.items()]
    subprocess.run([NVC] + lib + ["-e", "l5_fork_tb"] + gargs, check=True, capture_output=True, cwd=work)
    r = subprocess.run([NVC] + lib + ["-r", "l5_fork_tb", "--stop-time=40ns"], capture_output=True, text=True, cwd=work)
    out = r.stdout + r.stderr
    m = re.search(r"L5 DONE launches=(\d+) hazards=(\d+)", out)
    skews = [int(x) for x in re.findall(r"L5 SKEW (-?\d+)", out)]
    if not m:
        raise SystemExit("nvc run failed:\n" + out[-2000:])
    return int(m.group(1)), int(m.group(2)), (skews[-1] / 1000.0 if skews else float("nan"))


def main():
    os.makedirs(EVID, exist_ok=True)
    rng = random.Random(SEED)
    lefs = [os.path.join(LIB, "sky130_fd_sc_hd.tlef")] + sorted(glob.glob(os.path.join(LIB, L3.P + "*.lef")))
    lef = lefdef.Lef()
    for f in lefs:
        lefdef.read_lef(f, lef)
    inv = {v: k for k, v in T.layers.items()}
    # stat-sim library once
    work = os.path.join(SCR, "l5_nvc"); os.makedirs(work, exist_ok=True)
    subprocess.run([NVC, "--std=2040", "-L", NVCLIB, "--work=statsim:%s/statsim" % work, "-a",
                    os.path.join(STATSIM, "lib/statsim_disc.vhd"), os.path.join(STATSIM, "lib/statsim_taps.vhd"),
                    os.path.join(STATSIM, "lib/statsim_io.vhd")], check=True, capture_output=True, cwd=work)
    print("variation model (1 sigma): Rsh li %.0f%%, metals %.0f%%, C %.0f%%, Cin %.0f%%, driver R %.0f%%; gate delay reference %.0f ps; T2 samples %d, T3 MC runs %d" % (
        100 * SIG_R["li"], 100 * SIG_R["met2"], 100 * SIG_C, 100 * SIG_CIN, 100 * SIG_RDRV, T_GATE_PS, NSAMP, NMC))
    for lay in ("met2", "li1"):
        def_path = os.path.join(SCR, "l5_%s.def" % lay)
        comps, drv, ra, rb = L3.build_def(lef, def_path, lay)
        fl0 = lefdef.def2flat(def_path, lefs, LIB, T); ex0 = extract.extract(fl0, T)
        fr = [i for i, r in enumerate(fl0.rects) if r.prov == "l3fork/net:f"]
        long = lambda i: max(fl0.rects[i].x1 - fl0.rects[i].x0, fl0.rects[i].y1 - fl0.rects[i].y0) > 2000
        wireA = [i for i in fr if inv.get(fl0.rects[i].layer) == "met2" and long(i) and 6000 < fl0.rects[i].y0 < 7500]
        wireB = [i for i in fr if inv.get(fl0.rects[i].layer) in ("met2", "li") and long(i) and fl0.rects[i].y0 > 8000]
        fl1, ex1 = sized_layout(fl0, ex0, inv, wireA, wireB, 0.5, 6.0)      # L3's optimum: A at minimum, B at the 6x bound
        print("== fork with the long branch on %s" % lay)
        for label, fl, ex in (("baseline", fl0, ex0), ("sized   ", fl1, ex1)):
            net = [n for n in ex.nets.values() if n.name == "f"][0]
            d = L3.shape_at(ex, "li", *drv); a = L3.shape_at(ex, "li", *ra); b = L3.shape_at(ex, "li", *rb)
            el = rc.elmore_delays(ex, net.id, d, [a, b], R_DRIVE, {a: C_IN, b: C_IN})
            skew0 = el[b] - el[a]
            fb = rc.fork_branches(ex, net.id, d, [a, b])
            (RT, CT), (RA, CA), (RB, CB) = fb["trunk"], fb["branches"][a], fb["branches"][b]
            # T2
            sk = t2_mc(ex, net.id, d, a, b, rng, NSAMP)
            mu = sum(sk) / len(sk); sd = math.sqrt(sum((x - mu) ** 2 for x in sk) / len(sk))
            pf2 = sum(1 for x in sk if abs(x) > T_GATE_PS) / len(sk)
            # T3 nominal + MC
            gens0 = dict(RT=RT, CT=CT * 1e-15, RA=RA, CA=CA * 1e-15, RB=RB, CB=CB * 1e-15, CIN=C_IN * 1e-15, TGATE_FS=int(T_GATE_PS * 1000))
            tb = os.path.join(work, "l5_fork_tb.vhd")
            open(tb, "w").write(TB % gens0)
            subprocess.run([NVC, "--std=2040", "-L", NVCLIB, "--work=statsim:%s/statsim" % work, "-a", tb], check=True, capture_output=True, cwd=work)
            n0, h0, skew3 = run_nvc(work, tb, {})
            haz = 0; runs = 0
            layB = "li" if lay == "li1" else "met2"
            for _ in range(NMC):
                g = dict(RT=RT * rng.gauss(1, SIG_R["met2"]), RA=RA * rng.gauss(1, SIG_R["met2"]), RB=RB * rng.gauss(1, SIG_R[layB]),
                         CT=CT * 1e-15 * rng.gauss(1, SIG_C), CA=CA * 1e-15 * rng.gauss(1, SIG_C), CB=CB * 1e-15 * rng.gauss(1, SIG_C),
                         CINA=C_IN * 1e-15 * rng.gauss(1, SIG_CIN), CINB=C_IN * 1e-15 * rng.gauss(1, SIG_CIN))
                n, h, _ = run_nvc(work, tb, {k: "%.6g" % v for k, v in g.items()})
                runs += 1; haz += (1 if h > 0 else 0)
            pf3 = haz / runs
            print("   %s  trunk R %5.0f C %5.2f fF | A R %5.0f C %5.2f | B R %6.0f C %5.2f fF" % (label, RT, CT, RA, CA, RB, CB))
            print("            T0 Elmore skew %7.2f ps | T2 MC skew %7.2f +/- %5.2f ps, p_fail(|skew|>%.0f ps) = %.4f | "
                  "T3 stat-sim/nvc skew %7.2f ps (ln2 x T0 = %7.2f), nominal hazards %d/%d, MC p_fail = %.3f (%d runs)" % (
                      skew0, mu, sd, T_GATE_PS, pf2, skew3, skew0 * math.log(2), h0, n0, pf3, runs))
            m_nom = mtbf_s(skew0)
            m_var = 1.0 / (sum(1.0 / mtbf_s(x) for x in sk) / len(sk))     # harmonic mean over the variation samples
            print("            if a sky130 dfxtp (tau=T0=%.1f ps) sampled the slow branch at the fast one's arrival, %.0f MHz: settling slack %.0f ps - |skew| gives MTBF %s nominal, %s under variation"
                  " -- below the flop's 90 ps setup: a fork is judged by p_fail, MTBF belongs to the CDC receiver" % (
                      TAU_PS, F_LAUNCH / 1e6, T_GATE_PS, fmt_t(m_nom), fmt_t(m_var)))
    print("   (T3 skews carry stat-sim's ln2 50%-point convention; T0/T2 are Elmore. Acceptance = p_fail against the gate-delay reference.)")


if __name__ == "__main__":
    main()
