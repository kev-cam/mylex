# layopt — Post-Layout, Boundary-Free Geometry Optimizer

**Working name.** `layopt` is a placeholder in the same sense `nulex` is in
`ASYNC-PLAN.md`; nothing below depends on it.

License: PolyForm Noncommercial 1.0.0 (`LICENSE-ASYNC.md`), like every tool in
this repository. Pure Python 3.10+ with NumPy; Pillow optional (renders);
KLayout optional (signoff-grade extraction/DRC backend, not needed for the loop).

This document is the working plan and the design record, in the style of
`ASYNC-PLAN.md`: decisions get refined during implementation, the doc keeps the
architecture coherent. Section 2 records what is built and measured as of
2026-09-05.

---

## 1. The central idea

**Timing balance for RTL and asynchronous circuits is a geometry problem that
the standard-cell abstraction hides.** A cell library freezes transistor sizes,
contact arrays and rail widths behind a LEF abstract. Place-and-route can then
only swap discrete drive variants, insert buffers and re-route. Everything a
designer would actually want to do to balance two paths — make one transistor a
little wider, share a diffusion across what used to be a cell edge, thicken the
strap feeding one region so its supply does not sag relative to its
neighbour — is out of reach because the boundary is treated as a wall.

layopt dissolves the boundary:

```
 placed/routed GDS (cells + routing)      analog block GDS (kestrel)
                 │                                   │
                 └──────────── flatten ──────────────┘
                                 │   rectangles + provenance (which cell/instance
                                 ▼   each rectangle came from — remembered, not enforced)
                        ┌──────────────────┐
                        │  extraction      │  nets (connectivity), MOS devices (W, L, S/D/G,
                        │  (pure Python)   │  AS/AD/PS/PD), per-net RC, resistive graph
                        └────────┬─────────┘
                                 ▼
          ┌──── moves ──────────────────────────── guard ──────────────┐
          │ device W stretch · wire width ·      topology signature     │
          │ translate · add shape · (planned:    unchanged  +  no NEW   │
          │ contact growth, diffusion merge,     rule violation vs the  │
          │ whitespace reclaim, strap insert)    baseline layout        │
          └──────────────────────────┬─────────────────────────────────┘
                                     ▼
                        objective = SPREAD across comparable paths
                        (supply R to ring stages, Elmore delay across fork
                         branches / matched delays, drive across a completion
                         tree)  +  metal-area / mean-R regularizers
                                     ▼
                        derivative-free optimizer (Nelder-Mead), re-extract on
                        every evaluation
                                     ▼
                        flat GDS (boundaries gone, provenance kept) · SPEF for
                        stat-sim/nvc · SPICE netlist for Xyce
```

Three principles:

1. **The layout is the variable, extraction is the evaluator.** No model of the
   cell stands between the optimizer and the geometry. After every move the
   netlist is re-extracted from the rectangles; if the device/net graph is not
   isomorphic to the starting one the move is illegal. That is the LVS identity
   as an optimizer constraint, and it is what makes "dissolving" safe.
2. **Objectives are spreads, not absolutes.** QDI/NCL depends on isochronic
   forks and completion trees, bundled data on matched delays; ASYNC-PLAN §4
   says it directly — *gradients between adjacent paths are what break it*. A
   supply gradient across a ring or a pipeline is a delay gradient; an RC
   mismatch across the branches of a fork is a hazard; so the primary cost
   terms are `max−min` (or normalized spread) over a set of comparable paths,
   with area and mean-resistance as regularizers. For synchronous RTL the same
   machinery balances setup/hold slack; only the path sets and the weights
   change.
3. **Rules are a delta, not a gate.** Real layouts arrive with violations
   (kestrel's PLL has 506 by this tool's minimal rule table; kestrel documents
   that it is not yet DRC clean). A move is judged by the violations it *adds*.
   Signoff DRC remains KLayout's job downstream.

### Why start with kestrel's PLL

- A ring oscillator is the smallest real timing-balanced ring. Its stages are
  identical by construction, so every asymmetry the tool finds is geometry —
  exactly the situation of an NCL pipeline ring or a bundled-data stage chain.
- kestrel already closes design → GDS → extract → RC → SPICE for that block
  (`layout/{gds_gen,extract,parasitics,iterate,spice_loop}.py`,
  `sim/opt/` Nelder-Mead sizer with pluggable simulator/extractor backends).
  layopt is that loop with the *geometry* as the variable instead of the
  design-engine parameters, so kestrel's SPICE-in-the-loop and optimizer
  backends are the natural next evaluation tier (§4).
- kestrel ships a KLayout-extracted golden netlist for its own GDS. That gave
  layopt an oracle for its pure-Python extractor on day one (§2).
- stat-sim's `klayout2spef.py` descends from kestrel's parasitics flow; the
  SPEF layopt writes is the form stat-sim's `spef.py` consumes, so the
  statistical/MTBF tier (ASYNC-PLAN §4) is already wired to accept the output.

## 2. What exists (2026-09-05) — measured

Package `layopt/` (this repository), probe and evidence in `probes/layopt/`.
kestrel is github.com/kev-cam/kestrel `cd4757e` at `/usr/local/src/kestrel`
(the path ldx/stat-sim scripts expect).

| Module | Does | Verified by |
|---|---|---|
| `gds.py` | GDSII read (BOUNDARY/PATH/SREF/AREF/TEXT), rectilinear→rects, flatten with provenance path per rect, flat write | round trip of kestrel_pll.gds: 3741 rects, identical set |
| `tech.py` | sky130 + IHP SG13G2: layers, via stack, RC (kestrel/stat-sim numbers), min width/space/enclosure | — |
| `extract.py` | connectivity (union-find over touching rects + cut stacks), MOS3 recognition (gate=poly∩diff, S/D=diff−poly, well decides N/P), AS/AD/PS/PD with shared-region split, parallel-finger combine, SPICE out | **vs KLayout golden:** 131 devices (44 N/87 P), W/L multiset equal, AS/AD/PS/PD multiset equal, 335 device nets with identical degree histogram, device/net graph **isomorphic** (colour refinement). 0.3 s. |
| `compare.py` | reference-netlist comparison; topology signature (sizes excluded) used as the LVS-identity guard | as above; `layopt compare` → `RESULT MATCH` |
| `rc.py` | per-net C from exact union area+perimeter; distributed R (centre-to-junction squares, via R per cut); Laplacian effective resistance (numpy pinv); SPEF writer | **vs KLayout 0.30.12 merged regions** (`probes/layopt/klayout_rc_xcheck.py`): per-(net, layer) union area and perimeter identical on all 335 device-connected nets (li and met3 totals equal to the nm; poly/met1/met2 differ only by the 22 device-less nets KLayout's `purge()` drops, VDD rail included). stat-sim's larger figures for the same GDS (67.9 vs 59.0 fF top net, 34.7 vs 17.1 fF rail) are its unmerged per-polygon sum double-counting kestrel's overlapping rectangles. SPEF read back by stat-sim `spef.py` (357 nets) |
| `moves.py` | `resize_device_w` (stretch along W: crossing rects grow, rects beyond shift, per finger), `set_wire_width`, `translate`, `add_rect`, provenance-based device footprint | Mtail of delay cell 2: 4.61→9.0 µm, 6 rects, topology preserved, 0 new violations; →12.0 µm: diff 0.18<0.27 and li 0.10<0.17 against the diff-pair row above — caught |
| `drc.py` | min width, same-layer spacing between different conductors (touching different-net rects = violation), cut enclosure against the metal union; `new_violations` = delta vs baseline | synthetic-inverter test: NFET pushed flush against PFET diffusion is flagged |
| `objective.py` | `supply_gradient` (R_eff feed→taps), `elmore_balance`, `metal_area_um2`, `Spread` | probe below |
| `optimize.py` | `Problem` (deepcopy → moves → re-extract → signature + delta-DRC → cost, illegal penalty), pure-Python Nelder-Mead with bounds | probe below |
| `render.py`, `cli.py` | SVG/PNG windows; `extract | rc | compare | flatten | render | resize` | evidence PNGs |
| `tests/test_layopt.py` | synthetic inverter: write/read/extract/resize/DRC; kestrel golden if present | `python3 -m layopt.tests.test_layopt` → 3 PASS |

**Probe `probes/layopt/vco_supply_balance.py`** (log and outputs in
`probes/layopt/evidence/`): the four VCO delay cells' PMOS-source MET2 pads
never reach the VCO VDD rail in kestrel's GDS (6.79 µm gap), so the probe
first adds the eight missing stubs, then treats rail width and per-cell stub
width as variables and minimizes the spread of effective resistance from the
PLL's VDD feed (right-hand side) to each cell. Baseline 16.6–19.4 Ω
(spread 2.9 Ω, 16 %); optimum 17.0–17.3 Ω (spread 0.4 Ω, 2.3 %) with the rail
2.0→3.87 µm, the far cell's stubs 0.33→0.59 µm and the near cells' stubs at
the 0.14 µm minimum — the optimizer *adds* resistance where the supply is
short and removes it where it is long, at 1.85× power-metal area, mean R
unchanged, 148 evaluations in 64 s, every accepted point topology-identical
and free of new rule violations. Small numbers (the feed is a single MET2
route), but the mechanism is the one that matters for async: equalize the
gradient, not the drop.

**Probe `probes/layopt/l1_xyce_loop.py` — L1, SPICE in the loop (2026-09-05,
log `evidence/l1_xyce_loop.log`, model `evidence/l1_t0_drive_model.json`):**
kestrel's PLL layout is regenerated with gdsfactory at the known-good VCO
sizing (the committed GDS uses the analytical sizing that kestrel itself says
undersizes for sky130), layopt extracts it (Mtail 40 µm as 8 fingers, diff
pair 20 µm as 4, loads 10 µm as 2, 1.58 fF of cell-local output wiring per
node), and kestrel's own Xyce testbench and `run_xyce` are driven from those
extracted numbers. A five-run Xyce sweep (tail ×0.8/1.0/1.25, +5/+10 fF) fits
the first-order T0 drive model f = k·(W_tail/W0)^a / (C_int + C_par) with
a = 0.338 and C_int = 110.8 fF at Vctrl 0.9 V. Then layopt moves the geometry
and T0 predicts the result before Xyce checks it: Mtail ×1.25 in all four
cells (80 rects, +6.4 % in Xyce, T0 error 1.34 %), output stubs ×2 width
(56 rects, −0.06 %, error 0.02 %), both together (error 1.34 %), and a
true held-out Mtail ×1.10 (+2.86 %, error 0.41 %). Every move
topology-identical, no new rule violations. Lesson recorded: sweep only what
the move changes — kestrel's `current_scale` scales tail and replica bias
together, which the Maneatis replica largely compensates (fitted a = 0.10,
4 % miss on the tail-only move) until the bias, which is not in the layout,
was held fixed.

**What the geometry says about kestrel's PLL layout** (all found by the
extractor, worth fixing upstream in `layout/gds_gen.py`):

1. All inter-stage MET3 routes sit on one track (y ≈ 8.43 µm) and overlap, so
   the four stages' diff-pair drains are one net (net 1: 8 drain terminals,
   59 fF). The differential feedback pair is caught in the same short.
2. Multi-finger transistors are chained finger-to-finger, not strapped in
   parallel: each 3-finger PMOS load extracts as 3 series devices with
   private S/D nets (41 such nets), hence 87 PFETs.
3. No PMOS source reaches VDD; no NMOS tail reaches VSS; gate inputs are
   unconnected (287 of 335 device nets have a single terminal).
4. Rule-table hits in the shipped GDS: via2 drawn 0.15 µm (VIA1 size) below the
   0.20 minimum; MET2 route landing pads 0.02 µm from delay-cell MET2; nwell
   spacing below 1.27 µm; PFET licon/mcon 0.170 × 0.169 µm (1 nm snap artefact).

## 3. Data model

- **FlatRect** `(layer, rect, prov)` — the unit of geometry. `prov` is the
  instance path (`top/kestrel_vco/kestrel_delay_cell#2/Mtail`). In a
  standard-cell flow it is `top/<inst>/<cell>`; the cell is remembered so a
  move can be reported in the designer's vocabulary, but nothing stops a move
  from crossing it.
- **Shape** — a conducting rectangle in the connectivity graph: routing and
  cut layers straight from the layout, plus derived `gate` and `sd_n/sd_p`
  regions. Each shape knows its source FlatRect, so moves and rule checks map
  back to geometry.
- **Net** — union-find class of shapes; named by layout text on a conducting
  layer or by a coordinate probe (`--label VDD=met2,x,y`).
- **Device** — MOS with G/S/D nets, W, L, AS/AD/PS/PD, flow axis, finger list,
  provenance.
- **NetRC / ResistiveNet** — per-net C (exact union), segment list (R per
  junction / cut), Laplacian for effective resistance.
- **Extraction.signature()** — colour-refinement hash of the device/net graph
  with sizes excluded: the LVS identity a move must preserve.

## 4. Evaluation tiers

| Tier | Evaluator | Use |
|---|---|---|
| T0 | analytic RC, Elmore, Laplacian R_eff (this package) | inner loop, every evaluation |
| T1 | Xyce on the extracted netlist + SPEF (kestrel `spice_loop.py`, `sim/opt/backends.py`) | calibrate T0, accept a candidate |
| T2 | stat-sim: variability models, quantified MTBF, EM/IR hot-spots (`klayout2spef`, `hotspot`) | accept under variation; async gradient margins |
| T3 | nvc with SPEF taps (stat-sim `spef.py` → `pl_wire/pl_load`) | system-level check of the balanced design |

T0 is deliberately cheap: exact geometry (§2), analytic RC, and a drive
model whose constants come from T1 — L1 fitted f = k·W^a/(C_int + C_par) from
five Xyce runs and predicted layout moves within 1.34 %. Its job is to rank
moves; T1/T2 decide. The drive constants are per cell type and operating
point (`evidence/l1_t0_drive_model.json` is for the kestrel delay cell at
Vctrl 0.9 V) — a library of them is what a `drive.py` module will hold.

## 5. Moves

Implemented: device W stretch (contact arrays do not grow yet — the stretched
S/D region simply carries the same contacts), wire width about the
centre-line, translate, add rectangle.

Planned, in the order the async objectives need them:

1. Contact-array growth and finger add/remove on W changes (keeps R_contact
   proportional).
2. **Same-net diffusion merge across a former cell edge** — the payoff move of
   dissolving: two abutting cells with the same net on facing S/D regions
   become one diffusion with a shared contact row.
3. Whitespace reclaim: shift a device column into neighbouring slack when a
   stretch would otherwise violate spacing (today the move is simply
   rejected).
4. Strap/stub insertion on supply nets (the probe did this by hand).
5. Via insertion/removal for redundancy and R.

Placement moves are out of scope until a real router is in the loop.

## 6. Objectives

Implemented: supply gradient (R_eff spread feed→taps), Elmore-delay spread
across a set of nets with common driver R and receiver C, metal area.

Planned:

- **Fork-branch balance from the RT constraint set.** nulex's
  `formal/constraints.py` (ASYNC-PLAN §8) enumerates which forks must be
  isochronic; each becomes a path set for `elmore_balance` with per-branch
  Elmore from this tool's distributed RC.
- **Completion-tree drive balance** (device W and load per branch).
- **Matched-delay margin** for bundled-data boundaries (contract field (d),
  ASYNC-PLAN §3), as a lower bound rather than a spread.
- **Sync slack/hold** — same path-set machinery with setup/hold margins.
- **Variation-aware gradient** — T2 evaluation of the spread under stat-sim's
  variability models.
- **EM/IR limits** as hard constraints (stat-sim `hotspot` DCCURRENTDENSITY).

## 7. Guards

- Topology signature equality (sizes excluded) — the netlist is the same
  netlist. Fast (ms) and exact up to colour-refinement resolution; a full VF2
  isomorphism check is a drop-in if a case ever needs it.
- Delta-DRC: min width, spacing between different conductors, cut enclosure
  against the metal union — only *new* violations relative to the input
  layout count. The rule table is deliberately minimal; signoff is KLayout.
- Bounds on every variable (min width from the tech table).

## 8. Interfaces to the federation

- **stat-sim**: `rc.write_spef` → `spef.py` (verified); `klayout2spef.py` is
  the accurate extraction backend when KLayout is available; `hotspot` for EM.
- **nulex** (ASYNC-PLAN): RT constraint set → path sets (§6). The mapper's
  in-process RTLIL is *not* what layopt consumes; layopt sits after P&R.
- **kestrel**: GDS in; `spice_loop.py`/`sim/opt` as T1; the findings in §2
  go back as issues.
- **ldx**: TH cells on SG13G2 are the first standard-cell-shaped input once
  they have layout (ASYNC-PLAN P2); `tech.SG13G2` is already in the table.
- **Standard-cell flows**: needs a DEF/LEF-placement → flat merge reader
  (`def2flat`, not written) so that a Yosys/OpenROAD result of `VX_alu_int` or
  a TH22 chain can be dissolved.

## 9. Milestones

- **L0 — DONE (2026-09-05).** Extractor matches KLayout on kestrel's PLL; RC
  and SPEF; W and wire moves under topology + delta-DRC guard; Nelder-Mead
  loop; supply-gradient balance demonstrated on the VCO rail.
- **L1 — kestrel loop re-hosted — DONE (2026-09-05).** kestrel's Xyce VCO
  testbench driven from layopt-extracted sizes and wiring C; layopt moves
  (Mtail ×1.25 / ×1.10, stubs ×2) predicted by the fitted T0 drive model
  within 1.34 % worst case, 0.41 % on the held-out point, against kestrel's
  3 % tolerance (§2, `probes/layopt/l1_xyce_loop.py`). Xyce provenance: Trilinos 14.4 (`~/tools/trilinos`,
  Fortran off, system BLAS/LAPACK/AMD runtimes) and Xyce 7.11 from
  `/usr/local/src/xyce` were both built with smak (`~/src/trilinos-build`,
  `~/src/xyce-build`; wrapper `~/tools/xyce/bin/Xyce` supplies the library
  path). It reproduces kestrel's `sim/kes_vco_xyce.cir` sweep: no oscillation
  below Vctrl 0.7 V, 295→470 MHz over 0.7–1.5 V saturating above 1.0 V, as
  the kestrel plan records; 13 STEP points in 46 s. The Python side is now
  complete too: pip 22 + `klayout` 0.30.12 and `gdsfactory` 8.32.2 wheels in
  the user site (`attrs` had to be upgraded over Ubuntu's 21.2, which lacks
  the `attrs` module name). kestrel's `layout/gds_gen.py` regenerates the
  committed GDS bit-identically (3741 rects), so its routing defects (§2) can
  be fixed upstream and re-extracted here.
- **L2 — standard-cell input.** `def2flat`: LEF/DEF placement + cell GDS →
  FlatLayout with `top/<inst>/<cell>` provenance. Target: a small placed
  block (sky130_fd_sc_hd) or ldx TH22 chain on SG13G2.
- **L3 — async objective.** Path sets from nulex's constraint extraction;
  fork-branch Elmore balance and completion-tree drive balance on a QDI-bound
  `VX_alu_int` slice.
- **L4 — dissolve for real.** Diffusion merge across cell edges, contact
  growth, whitespace reclaim.
- **L5 — variation-aware acceptance** through stat-sim (T2) and nvc (T3).

## 10. Open decisions and risks

- Name.
- Output hierarchy: today the result is flat (that *is* the point), with
  provenance only in memory. Foundry flows may want cell-based LVS; keep
  provenance as GDS properties or emit a per-instance report. Decide at L2.
- Where the RT constraint set is emitted (ASYNC-PLAN §12 open decision) — the
  same decision fixes layopt's path-set input format.
- Rule-table fidelity: enough to keep moves legal, not to sign off. Do not let
  it grow into a DRC deck; call KLayout instead.
- T0 accuracy: the geometry side is settled (exact agreement with KLayout's
  merged regions, §2); what remains is the model — no coupling term, analytic
  fringe, centre-to-junction R. Calibrate against T1 (Xyce) at L1 before
  trusting rankings on tight margins. stat-sim's `klayout2spef.py` should
  merge each net's region before summing (`.merged()`); as written it
  over-reports C wherever a net's rectangles overlap.
- kestrel's PLL is half-routed (§2). Ring-delay balance — the objective this
  tool exists for — cannot be demonstrated on it until the inter-stage
  routing is fixed upstream. The supply-gradient probe stands in.
