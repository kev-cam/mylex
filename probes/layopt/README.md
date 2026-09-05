# layopt probes — kestrel PLL layout (2026-09-05)

Everything here is produced by the `layopt` package at the repository root
against kestrel `cd4757e` (`/usr/local/src/kestrel/layout/kestrel_pll.gds`,
sky130). No KLayout, Xyce or gdsfactory involved; python3.10 + numpy (+ Pillow
for the PNGs). Design record: `../../LAYOUT-OPT.md`.

## Commands

    cd /usr/local/src/mylex
    python3 -m layopt.tests.test_layopt                       # 3 PASS (synthetic inverter + kestrel golden)
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

## Findings about the kestrel layout (report upstream)

1. Inter-stage MET3 routes share track y≈8.43 µm and overlap: all four stages'
   diff-pair drains are one net (8 D terminals, 59 fF).
2. Multi-finger devices are finger-chained in series, not strapped (87 PFETs
   extracted, 41 finger-private S/D nets).
3. PMOS sources stop 6.79 µm short of the VDD rail; tails never reach VSS;
   gate inputs unconnected (287/335 device nets have one terminal).
4. via2 drawn at VIA1 size (0.15 < 0.20 µm); route landing pads 0.02 µm from
   delay-cell MET2; nwell spacing < 1.27 µm; licon/mcon 0.170×0.169 µm.
