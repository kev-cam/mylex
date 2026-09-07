# layopt probes — kestrel PLL layout (2026-09-05)

Everything here is produced by the `layopt` package at the repository root
against kestrel `cd4757e` (`/usr/local/src/kestrel/layout/kestrel_pll.gds`,
sky130). No KLayout, Xyce or gdsfactory involved; python3.10 + numpy (+ Pillow
for the PNGs). Design record: `../../LAYOUT-OPT.md`.

## Commands

    cd /usr/local/src/mylex
    python3 -m layopt.tests.test_layopt                       # 9 PASS (inverter, kestrel golden, LEF/DEF, fingers, series stack)
    python3 -m layopt compare  $K/layout/kestrel_pll.gds $K/layout/kestrel_pll_flat_extracted.cir
    python3 -m layopt extract  $K/layout/kestrel_pll.gds -o evidence/kestrel_pll_layopt.cir
    python3 -m layopt rc       $K/layout/kestrel_pll.gds -o evidence/kestrel_pll.spef
    python3 -m layopt resize   $K/layout/kestrel_pll.gds 'delay_cell#2/Mtail' 9.0 -o /tmp/r9.gds
    python3 -m layopt render   $K/layout/kestrel_pll.gds 31 -1 45 17 -o cell2.svg
    python3 probes/layopt/vco_supply_balance.py               # the optimization probe (~70 s)

with `K=/usr/local/src/kestrel`.

## Evidence

| file | what |
|---|---|
| `compare_klayout_golden.log` | pure-Python extraction vs KLayout's netlist of the same GDS: 131/131 devices, W/L + AS/AD/PS/PD multisets equal, 335 nets same degree histogram, graph isomorphic → `RESULT MATCH` |
| `extract_kestrel_pll.log`, `kestrel_pll_layopt.cir` | our extracted SPICE (357 nets incl. 22 metal-only) |
| `rc_kestrel_pll.log`, `kestrel_pll.spef` | per-net RC; 246.6 fF total; top net 59.0 fF / 1346 Ω (stat-sim's KLayout flow: 67.9 fF / 1.4 kΩ); SPEF parses in stat-sim `spef.py` |
| `resize_mtail.log` | device-W move: 4.61→9.0 µm legal; →12.0 µm hits the diff-pair row (diff 0.18<0.27, li 0.10<0.17) |
| `cell2_before.png`, `cell2_after9.png` | delay cell 2 before/after the 9 µm Mtail stretch (Mtail outlined red) |
| `vco_supply_balance.log` | the probe: baseline vs optimized supply-R spread across the four delay cells |
| `vco_before.png`, `vco_balanced.png` | VCO row before / after (rail 3.87 µm, stubs outlined red) |
| `kestrel_pll_vdd_balanced.{gds,spef,cir}` | the optimized flat layout and its extraction |

## Result of the probe

Feed→cell effective resistance (Ω), two stubs per cell:

| cell | baseline | optimized |
|---|---|---|
| #0 (far) | 19.4 / 18.7 | 17.3 / 17.0 |
| #1 | 18.2 / 17.5 | 17.3 / 17.0 |
| #2 | 16.7 / 16.8 | 17.3 / 17.2 |
| #3 (near feed) | 16.6 / 16.5 | 17.0 / 17.0 |
| spread | 2.9 (16 %) | 0.4 (2.3 %) |

Variables at the optimum: rail 3.87 µm (from 2.0), stub widths 0.59 / 0.30 /
0.14 / 0.14 µm (from 0.33). Power-metal area ×1.85, mean R 17.5→17.2 Ω. 148
evaluations, each a full re-extraction; all accepted points topology-identical
to the start and free of new rule violations (506 pre-existing ones ignored).

## L1 — SPICE in the loop (`l1_xyce_loop.py`, `evidence/l1_xyce_loop.log`)

Needs Xyce (`~/tools/xyce/bin/Xyce`) and gdsfactory. Regenerates kestrel's PLL
GDS at the oscillating VCO sizing into `$LAYOPT_SCRATCH`, extracts it with
layopt, drives kestrel's Xyce testbench from the extracted sizes and the
cell-local output wiring C, fits the T0 drive model from 5 Xyce runs, then
applies layopt moves and compares T0's prediction with fresh Xyce runs:

| move (all 4 delay cells) | Xyce shift | T0 error |
|---|---|---|
| Mtail 40→50 µm (×1.25) | +6.41 % | 1.34 % |
| output stubs ×2 width (C 1.58→1.63 fF) | −0.06 % | 0.02 % |
| both | +6.37 % | 1.34 % |
| Mtail 40→44 µm (×1.10, held out) | +2.86 % | 0.41 % |

Fitted model (Vctrl 0.9 V): f = k·(W_tail/40 µm)^0.338 / (110.8 fF + C_par);
`evidence/l1_t0_drive_model.json`. The replica-bias transistor is held fixed
because it is not in the layout; scaling it with the tail (kestrel's
`current_scale`) is a different circuit and gives a = 0.10.

## L2 — standard cells in (`l2_stdcell_row.py`, `evidence/l2_stdcell_row.log`)

Needs `~/tools/sky130_fd_sc_hd/` (tech LEF + a few cell GDS/LEF from
google/skywater-pdk-libs-sky130_fd_sc_hd). Writes a two-row DEF (row 2 FS,
sharing VPWR), routes six nets on li1/met1/met2/met3 with vias and a VGND
strap, converts with `layopt.lefdef.def2flat`, extracts, and checks devices
per instance, pin connectivity and supply nets; then runs a headroom search on
the nand2 PMOS strip in both directions.

| check | result |
|---|---|
| devices per instance vs cell alone | 12/12 equal (52 devices) |
| routed nets reaching both pins | 6/6 |
| VPWR / VGND spanning all instances | 12/12 each |
| nand2 PMOS growth toward rail | blocked at +0.05 µm: poly at min spacing to the flipped row's nor2 |
| nand2 PMOS growth toward NMOS | blocked at +0.05 µm by the cell's own li; +0.2 µm shorts (topology guard) |

`evidence/stdcells_vs_klayout.log`: layopt vs KLayout per cell — W/L equal and
isomorphic for inv_1, nand2_1, nor2_1, a21o_1, buf_1, dfxtp_1.

## L3 — isochronic fork balance (`l3_fork_balance.py`, `evidence/l3_fork_balance.log`)

L2 row plus a forked net (inv u1 → u2 one cell away, and → v4 in the other
row), each branch with a met2 detour (60 / 180 µm). Elmore delay from the
driver pin to each receiver on the extracted RC tree (`rc.elmore_delays`,
driver 3 kΩ, receiver 2.1 fF); the optimizer scales branch widths.

| long branch on | path R A / B | imbalance before | after sizing | verdict |
|---|---|---|---|---|
| met2 | 66 / 117 Ω | 0.96 ps (1.2 %) | 0.10 ps (B widened 6×) | balanced |
| li1 | 66 / 6780 Ω | 74.9 ps (59 %) | 17.0 ps (B at 6× bound) | reroute to metal or buffer |

## L4 — dissolve: add a finger across the cell edge (`l4_dissolve_finger.py`, `evidence/l4_dissolve_finger.log`)

Row fill_4 | inv_1 | fill_4 | nand2_1 | fill_1 | decap_4 (+ flipped fills).
`moves.add_finger` on the inverter, growing right into the fill_4:

| device | W before | W after | extraction | guard |
|---|---|---|---|---|
| inv_1 PMOS | 1.00 | 2.00 µm | one device, 2 fingers, same nets | topology preserved, 0 new violations |
| inv_1 NMOS | 0.65 | 1.30 µm | one device, 2 fingers, same nets | topology preserved, 0 new violations |
| nand2_1 PMOS (control) | 1.00 | — | netlist changed | refused: diff spacing 0 to the decap |

KLayout extracts `evidence/l4_inv1_fingered.gds` as pfet 2 µm / nfet 1.3 µm,
isomorphic to layopt (`evidence/l4_fingered_vs_klayout.log`).

## L4 — a discrete move balances two paths (`l4_path_balance.py`, `evidence/l4_path_balance.log`)

Two inv_1 drivers with fillers beside them; path A over 2 fF, path B over a
120 µm met2 detour (10 fF). `optimize.greedy_search` over finger counts
(u6 P/N, u1 P/N in 1..4), each state rebuilt from the base layout:

| state | A | B | imbalance |
|---|---|---|---|
| baseline | 13.7 ps | 39.6 ps | 25.9 ps |
| u6 PMOS 2 fingers | 13.7 | 20.2 | 6.4 |
| u6 PMOS 3 fingers (chosen) | 13.7 | 14.1 | 0.4 |

13 states, all legal and topology-identical; KLayout extracts the result as
pfet W=3 µm, isomorphic (`evidence/l4_balanced_vs_klayout.log`). The third
finger exercises the signal-net jumper (mcon + met1 to the drain strap).

## L5 — acceptance under variation (`l5_variation_accept.py`, `evidence/l5_variation_accept.log`)

The L3 fork before/after sizing as an isochronic fork (slow branch within a
40 ps gate delay of the fast one). T2: layopt RC tree, 4000 samples of a
stated variation model. T3: stat-sim `statsim_pl_rc` + `pl_load` under nvc,
60 Monte-Carlo elaborations via generics. Needs nvc and stat-sim.

| fork | T0 skew | T2 skew (p_fail) | T3 skew (MC p_fail) | verdict |
|---|---|---|---|---|
| met2, baseline | 0.96 ps | 0.96 ± 0.12 (0.000) | 0.29 (0.000) | pass |
| met2, sized | 0.10 | 0.10 ± 0.02 (0.000) | 0.04 (0.000) | pass |
| li1, baseline | 74.9 | 75.1 ± 12.5 (0.998) | 48.6 (0.917) | reject |
| li1, sized | 17.0 | 17.1 ± 2.8 (0.000) | 11.3 (0.000) | pass |

T3 skews are ln2 × T0 (50 %-point vs Elmore first moment).

## A real DEF: gcd through OpenROAD (`gcd/`, `l2_real_def.py`, `evidence/l2_real_def_gcd.log`)

`gcd/` holds the Yosys script, the OpenROAD Tcl flow, the synthesized netlist
and the routed DEF (784 instances, 0 DRC violations). `l2_real_def.py gcd/gcd.def`
runs def2flat + extraction (2472 devices, 2102 nets, ~10 s) and KLayout's
own DEF reader + full-stack LayoutToNetlist on the same inputs, then compares:
W/L equal, degree histogram equal, isomorphic. Needs `~/tools/orfs-sky130hd`
(ORFS sky130hd platform files) and the `klayout` wheel.

## L4 on the real layout (`l4_gcd_whitespace.py`, `evidence/l4_gcd_whitespace.log`)

Fingers into the fillers OpenROAD placed in gcd. 33 candidates; six tried,
each transistor judged on its own (eight fingers legal in five cells):

| cell | neighbour | PMOS | NMOS | output net (Elmore) |
|---|---|---|---|---|
| _149_ nand2_1 | fill_4 | legal (contact/poly bridge) | refused: stack mirrored, no bridge for the far gate (P&R met1 in the gap, diffusion under every head) | 21.0 → 15.4 ps |
| _161_ nand2_1 | fill_8 | legal | refused: same | 11.5 → 8.5 ps |
| _110_ clkinv_1 | fill_4 | refused: no met1 height for the jumper | refused: same | — |
| rebuffer12 buf_4 | fill_4 | legal | legal (jumper kept in its strip) | 6.0 → 5.7 ps |
| rebuffer3 buf_4 | fill_8 | legal | legal | 13.2 → 12.0 ps |
| rebuffer13 buf_4 | fill_8 | legal | legal | 17.6 → 15.8 ps |

`evidence/gcd_149_fingered.gds` extracts isomorphic in KLayout
(`evidence/l4_gcd_fingered_vs_klayout.log`). Refusal messages carry the
obstacle; the planners add a tally of rejected candidates. The probe tries
both orders (PMOS then NMOS, NMOS then PMOS) and keeps the better: the
0.6 µm gap between the strips is shared by the far-gate bridge of a mirrored
stack and the S/D jumper of the other transistor.

**Series stack on a bare row** (`test_series_stack_nand2`,
`evidence/nand2_stack_fingered.gds`, `evidence/nand2_stack_fingered_vs_klayout.log`):
nand2_1 between fill_4 and fill_8, PMOS finger then the whole NMOS stack
mirrored (both gates, uncontacted middle node, far gate by contact bridge).
KLayout: 6 devices, W/L multisets equal, isomorphic — four 0.65 µm NMOS in two
parallel A–B stacks, which the stack-canonical topology guard treats as the
original nand2 (LAYOUT-OPT §2, §7).

## Findings about the kestrel layout (report upstream)

1. Inter-stage MET3 routes share track y≈8.43 µm and overlap: all four stages'
   diff-pair drains are one net (8 D terminals, 59 fF).
2. Multi-finger devices are finger-chained in series, not strapped (87 PFETs
   extracted, 41 finger-private S/D nets).
3. PMOS sources stop 6.79 µm short of the VDD rail; tails never reach VSS;
   gate inputs unconnected (287/335 device nets have one terminal).
4. via2 drawn at VIA1 size (0.15 < 0.20 µm); route landing pads 0.02 µm from
   delay-cell MET2; nwell spacing < 1.27 µm; licon/mcon 0.170×0.169 µm.
