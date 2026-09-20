# Monte-Carlo Vt-Mismatch Reliability of the SG13G2 NCL Threshold Cells

Model-native Monte-Carlo characterization of the transistor-level SG13G2 NCL
threshold library (`th12`, `th13`, `th14`, `th22`, `th23`, `th33`, `th34w2`)
under **per-device local Vt mismatch**, quantifying functional yield and
propagation-delay spread before the RTL to NCL to cell flow is scaled up.

## Methodology

Each transistor carries an independent threshold shift injected the
**model-native** way: `DELVTO ~ AGAUSS(0, kvt·σ_Vt, 1)`, where
`σ_Vt = A_Vt/√(W·L)` (Pelgrom, `A_Vt ≈ 3.5 mV·µm` for 130 nm). `DELVTO` is a
native PSP103 instance parameter (`VFB_T = VFB_i + STVFB_i·ΔT + DELVTO_i`), so
the offset is applied at the physics level, not as an external hack. Because the
PyMS GiNaC device path normally bakes every parameter as a compile-time
constant (which would freeze `DELVTO` and make `.SAMPLING` inert), the value is
routed through the PyMS **runtime-callback param** path: with
`PYMS_CALLBACK_PARAMS=DELVTO`, `DELVTO` is kept symbolic in a single generated
`.so` per geometry (no per-sample rebuild) and fetched per-eval so each device
instance sees its own draw — true per-device local mismatch. On top of that,
Xyce `.SAMPLING` (`SAMPLE_TYPE=MC`, `SEED=1`) draws **N = 200 samples per level**
at mismatch scales **kvt = 1, 2, 3, 4** (kvt = 4 is a ~4x-nominal, deliberately
unphysical stress). Each deck applies a 5 ns/phase PWL stimulus that walks the
cell through its full function (the OR truth table for the combinational cells;
SET / HOLD-high / RESET / HOLD-low for the hysteretic cells), checks every
settled phase-end `V(y)` against HIGH > 0.72 V / LOW < 0.48 V for functional
yield, and times input-to-output propagation delays at the 0.6 V (VDD/2)
crossing. The nominal (kvt = 0, zero-mismatch) correctness gate is run
separately; where the zero-sigma `AGAUSS(0,0,1)` substitution triggers the PyMS
rebuild path, the nominal check falls back to the original plain cell netlist
(no `DELVTO`) per the documented escape hatch (see per-cell notes).

## Stimulus cross-verification

Every deck's PWL pattern was re-parsed edge-by-edge and the expected `V(y)` was
independently re-derived from the cell's authoritative threshold function. All
seven decks properly exercise their function and all reported nominal levels are
on the correct side of VDD/2:

| Cell | Kind | Function exercised | Decisive check | Stimulus OK |
|------|------|--------------------|----------------|:-----------:|
| th12 | comb | OR2: 00,10,01,11 → 0,1,1,1 | each input drives Y alone; all-high | yes |
| th13 | comb | OR3: single-A/B/C + all-high | each of 3 inputs drives Y independently | yes |
| th14 | comb | OR4: single-A/B/C/D + all-high | each of 4 inputs drives Y independently | yes |
| th22 | hyst | C-element set/hold/reset | 10 and 01 hold prior state | yes |
| th23 | hyst | 2-of-3 maj + hyst | 100 holds 1, 001 holds 0 (rules out OR / strict majority) | yes |
| th33 | hyst | 3-of-3 C-elem + hyst | same 110 holds 1 (P2) then 0 (P4) — pure history | yes |
| th34w2 | hyst | weighted 2A+B+C+D≥3 + hyst | P1 sets on 2 physical inputs (A,B) — impossible unweighted; B&C (=2) does not set | yes |

## Aggregate reliability table (N = 200 per level, SEED = 1)

Representative set/rise and reset/fall delays (mean ± sd, ps). Combinational
cells have no hysteretic reset; their "reset/fall" column is the Y-fall delay
(`trst_a`/`tf_a`/`trst`). Hysteretic and C-element cells report the true SET and
RESET edges (`tset1`, `trst`). th22 figures are carried from `README.md`.

| Cell | kind | kvt | Functional | Set/rise (ps) | Reset/fall (ps) |
|------|------|----:|-----------:|--------------:|----------------:|
| th12 | comb | 1 | 200/200 | 180.5 ± 5.7 | 272.5 ± 5.4 |
| th12 | comb | 2 | 200/200 | 181.5 ± 11.8 | 273.0 ± 11.0 |
| th12 | comb | 3 | 200/200 | 183.1 ± 18.8 | 273.8 ± 16.7 |
| th12 | comb | 4 | 200/200 | 185.4 ± 27.2 | 275.2 ± 23.0 |
| th13 | comb | 1 | 200/200 | 221.1 ± 8.1 | 348.0 ± 7.5 |
| th13 | comb | 2 | 200/200 | 221.8 ± 16.7 | 348.7 ± 15.1 |
| th13 | comb | 3 | 200/200 | 223.3 ± 26.2 | 350.1 ± 23.1 |
| th13 | comb | 4 | 200/200 | 225.7 ± 37.8 | 352.1 ± 31.6 |
| th14 | comb | 1 | 200/200 | 278.1 ± 12.1 | 333.7 ± 7.7 |
| th14 | comb | 2 | 200/200 | 280.2 ± 24.7 | 334.2 ± 15.4 |
| th14 | comb | 3 | 200/200 | 283.5 ± 38.7 | 335.3 ± 23.2 |
| th14 | comb | 4 | 200/200 | 288.3 ± 55.2 | 336.9 ± 31.3 |
| th22 | hyst | 1 | 200/200 | 356 ± 12 | 440 ± 15 |
| th22 | hyst | 2 | 200/200 | 358 ± 24 | 442 ± 31 |
| th22 | hyst | 3 | 200/200 | 361 ± 38 | 446 ± 48 |
| th22 | hyst | 4 | 200/200 | 366 ± 54 | 452 ± 67 |
| th23 | hyst | 1 | 200/200 | 272.9 ± 5.3 | 585.1 ± 16.7 |
| th23 | hyst | 2 | 200/200 | 273.5 ± 10.7 | 589.3 ± 33.8 |
| th23 | hyst | 3 | 200/200 | 274.5 ± 16.3 | 595.3 ± 52.0 |
| th23 | hyst | 4 | 200/200 | 276.1 ± 22.3 | 603.1 ± 71.9 |
| th33 | hyst | 1 | 200/200 | 353.8 ± 7.6 | 472.2 ± 13.5 |
| th33 | hyst | 2 | 200/200 | 354.5 ± 15.3 | 474.5 ± 27.4 |
| th33 | hyst | 3 | 200/200 | 356.3 ± 23.5 | 478.1 ± 42.0 |
| th33 | hyst | 4 | 200/200 | 359.3 ± 32.6 | 483.1 ± 58.1 |
| th34w2 | hyst | 1 | 200/200 | 316.5 ± 6.1 | 746.9 ± 21.0 |
| th34w2 | hyst | 2 | 200/200 | 316.6 ± 12.3 | 751.7 ± 42.9 |
| th34w2 | hyst | 3 | 200/200 | 317.3 ± 18.6 | 758.5 ± 66.2 |
| th34w2 | hyst | 4 | 200/200 | 318.4 ± 25.3 | 767.7 ± 92.0 |

**Aggregate functional yield: 5600 / 5600 samples functional** (7 cells x 4
mismatch scales x 200), i.e. **0 functional failures**, including at the
~4x-nominal kvt = 4 stress.

**Delay-sigma trend.** Across every cell the delay standard deviation scales
essentially **linearly with kvt** while the mean barely shifts — the signature
of zero-mean per-device Vt mismatch adding spread, not bias. Examples of the
1x→2x→3x→4x sd progression: th12 tset_a 5.7/11.8/18.8/27.2 ps; th14 tset1
12.1/24.7/38.7/55.2 ps; th23 trst 16.7/33.8/52.0/71.9 ps; th34w2 trst
21.0/42.9/66.2/92.0 ps. Means move only single-digit-percent over the whole
sweep (e.g. th14 tset1 278→288 ps, th23 trst 585→603 ps).

## Per-cell findings

- **th12 (OR2, combinational, keeper-less).** 800/800 functional. Rail-to-rail
  DC levels (highs = 1.200 V, lows ≤ ~0.2 µV); mismatch appears only in timing.
  Y-fall (272 ps) slower than Y-rise (180 ps), consistent with the series-PMOS
  pull-up of a NOR+inverter OR2. No keeper (correct for a degenerate 1-of-2
  threshold). No anomalies.

- **th13 (OR3, combinational).** 800/800 functional across all 9 phase-level
  checks per sample. Per-input delays ordered tr_c < tr_b < tr_a (and likewise
  for falls), reflecting the series-PMOS stack position of each input; the
  all-inputs rise `tr_all` is fastest and least variable (parallel NMOS,
  averaging reduces effective sigma). Nominal gate ran from the plain cell
  because the kvt = 0 zero-sigma AGAUSS triggers the PyMS rebuild path
  (operational, not a correctness issue). No anomalies.

- **th14 (OR4, combinational).** 800/800 functional; each of the four inputs
  independently drives Y high, and Y is held high across the A→B→C→D single-high
  handoff, falling only at the all-release edge. `trst` (Y-fall) sigma grows more
  slowly than `tset1` (Y-rise) sigma. No anomalies.

- **th22 (Muller C-element, hysteretic).** Reference cell (results from
  `README.md`). 800/800 functional; reset (440 ps) slower than set (357 ps) —
  the keeper-fight signature. Delay sigma linear in kvt.

- **th23 (2-of-3 majority + NCL hysteresis).** 800/800 functional. The stimulus
  decisively separates hysteresis from both OR and strict majority: with exactly
  one input high, Y holds its prior value in both directions (100 holds 1, 001
  holds 0). Reset (~585–603 ps) is ~2.3x slower than set (~253–276 ps) — the
  keeper-fight signature. No anomalies.

- **th33 (3-of-3 C-element + NCL hysteresis).** 800/800 functional. The most
  decisive hysteresis evidence in the suite: the identical input pattern 110
  holds Y = 1 at P2 but Y = 0 at P4, output determined purely by history. Reset
  (472–483 ps) slower than set (333–359 ps). Nominal gate ran from the plain
  cell netlist (`th_gates.sp`, subckt th33) because the zero-sigma nominal
  substitution hit the PyMS rebuild fallback; the plain-cell nominal passed all
  six levels cleanly (operational note, not a correctness defect).

- **th34w2 (weighted 3-of-4, A weight 2, + NCL hysteresis).** 800/800
  functional. Weighting is proven directly: P1 SETs on only two physical inputs
  high (A&B, 2+1 = 3) which no unweighted 3-of-4 could do, while B&C (also two
  inputs, 1+1 = 2) at P4 correctly does NOT set. Both hysteretic hold directions
  verified (A-alone weight 2 holds high; B&C weight 2 holds low). Reset (~747–768
  ps) is the slowest and most sigma-sensitive path in the whole library
  (all-PMOS-series keeper pull-up), ~2.3x slower than set (~317 ps). No
  anomalies.

## Anomalies / rework

- **No functional failures and no correctness anomalies in any cell.** Every
  stimulus was independently re-verified to exercise its full function, every
  nominal level is on the correct side of VDD/2, and every reported
  `nominal_ok` is logically justified. **No cell needs rework.**
- **Operational note (not a result defect).** For the hysteretic/high-fanin
  geometries (th13, th33, th34w2, and initial th23/th14 runs), the kvt = 0
  nominal `AGAUSS(0,0,1)` zero-sigma substitution triggers the PyMS
  "full build failed / retry without zero-valued params" `.so` rebuild path, and
  first-touch of a not-yet-cached per-geometry `.so` occasionally hit the 300 s
  Xyce wall under concurrent sibling-agent load. Per the documented escape
  hatch, the affected nominal checks were run from the original plain cell
  netlists (no `DELVTO`) and passed; once each `.so` was cached, all four
  200-sample MC runs completed in tens of seconds each. This is a build-path /
  scheduling caveat only and does not affect any yield or delay number above.

## Overall verdict

The native SG13G2 NCL threshold library is **functionally robust to local Vt
mismatch**: 0 failures in 5600 Monte-Carlo samples across all seven cells even
at 4x-nominal Pelgrom spread. Mismatch manifests purely as timing spread — delay
sigma grows linearly with mismatch magnitude while means stay put — and the
hysteretic cells consistently show reset slower than set (the keeper-fight
signature), with th34w2's weighted all-PMOS-series reset the slowest, most
variation-sensitive path in the family.
