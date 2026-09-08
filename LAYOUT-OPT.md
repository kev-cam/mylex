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

## 2. What exists (2026-09-08) — measured

Package `layopt/` (this repository), probe and evidence in `probes/layopt/`.
kestrel is github.com/kev-cam/kestrel `cd4757e` at `/usr/local/src/kestrel`
(the path ldx/stat-sim scripts expect).

| Module | Does | Verified by |
|---|---|---|
| `gds.py` | GDSII read (BOUNDARY/PATH/SREF/AREF/TEXT), rectilinear→rects, flatten with provenance path per rect, flat write | round trip of kestrel_pll.gds: 3741 rects, identical set |
| `tech.py` | sky130 + IHP SG13G2: layers, via stack, RC (kestrel/stat-sim numbers), min width/space/enclosure | — |
| `extract.py` | connectivity (union-find over touching rects + cut stacks), MOS3 recognition on the *merged* poly and diffusion (gate=poly∩diff, S/D=diff−poly, well decides N/P; L-shaped poly and notched diffusion arrive as rectangles/slabs, so gates are merged from pieces), AS/AD/PS/PD with shared-region split, parallel-finger combine, SPICE out | **vs KLayout golden:** 131 devices (44 N/87 P), W/L multiset equal, AS/AD/PS/PD multiset equal, 335 device nets with identical degree histogram, device/net graph **isomorphic** (colour refinement). 0.3 s. |
| `compare.py` | reference-netlist comparison; topology signature (sizes excluded) used as the LVS-identity guard | as above; `layopt compare` → `RESULT MATCH`. **Standard cells vs KLayout** (`evidence/stdcells_vs_klayout.log`): inv_1, nand2_1, nor2_1, a21o_1, buf_1, dfxtp_1 all W/L-equal and isomorphic (2/4/4/8/4/24 devices); AS/AD/PS/PD agree on inv/buf and differ where S/D regions are shared (KLayout's split convention) |
| `rc.py` | per-net C from exact union area+perimeter; distributed R (centre-to-junction squares, via R per cut); Laplacian effective resistance (numpy pinv); SPEF writer | **vs KLayout 0.30.12 merged regions** (`probes/layopt/klayout_rc_xcheck.py`): per-(net, layer) union area and perimeter identical on all 335 device-connected nets (li and met3 totals equal to the nm; poly/met1/met2 differ only by the 22 device-less nets KLayout's `purge()` drops, VDD rail included). stat-sim's larger figures for the same GDS (67.9 vs 59.0 fF top net, 34.7 vs 17.1 fF rail) are its unmerged per-polygon sum double-counting kestrel's overlapping rectangles. SPEF read back by stat-sim `spef.py` (357 nets) |
| `moves.py` | `resize_device_w` (stretch along W: crossing rects grow, rects beyond shift, per finger), `set_wire_width`, `translate`, `add_rect`, provenance-based device footprint | Mtail of delay cell 2: 4.61→9.0 µm, 6 rects, topology preserved, 0 new violations; →12.0 µm: diff 0.18<0.27 and li 0.10<0.17 against the diff-pair row above — caught |
| `drc.py` | min width, same-layer spacing between different conductors (touching different-net rects = violation), cut enclosure against the metal union; `new_violations` = delta vs baseline | synthetic-inverter test: NFET pushed flush against PFET diffusion is flagged |
| `objective.py` | `supply_gradient` (R_eff feed→taps), `elmore_balance`, `metal_area_um2`, `Spread` | probe below |
| `optimize.py` | `Problem` (deepcopy → moves → re-extract → signature + delta-DRC → cost, illegal penalty), pure-Python Nelder-Mead with bounds | probe below |
| `lefdef.py` | LEF (tech + macro) and DEF readers; `def2flat`: cell GDS (per-cell files or one merged library) flattened under DEF placement/orientation (N/S/E/W/FN/FS/FE/FW) with provenance `top/<inst>/<macro>`, routed and special-net wires and vias as rectangles, nets labelled from the DEF | 12-cell two-row sky130_fd_sc_hd design (`probes/layopt/l2_stdcell_row.py`): every instance extracts the cell's own device count, all six routed nets reach both pins, VPWR and VGND span all 12 instances through rail abutment (FS row) and a met2 strap. **Independent check** (`probes/layopt/l2_real_def.py`): KLayout reads the same DEF with LEF + the real cell GDS, flattens, extracts with its own engine — isomorphic to def2flat + layopt (52/52 devices, W/L and degree histogram equal). Same probe runs on any place-and-route DEF |
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

**Probe `probes/layopt/l2_stdcell_row.py` — L2, standard cells in
(2026-09-05, log `evidence/l2_stdcell_row.log`):** a DEF is written from the
LEF sizes — six sky130_fd_sc_hd cells in a row, six more in a flipped (FS) row
sharing the VPWR rail, six nets routed li1→met1→met2→met3 with L1M1/M1M2/M2M3
vias, a met2 strap between the two VGND rails — and `def2flat` builds the flat
layout. Extraction: 52 devices, each instance equal to its cell alone; all six
routed nets reach both pins; VPWR and VGND single nets across all 12 instances.
The first standard-cell move is a headroom search on the nand2's shared PMOS
strip (one resize grows both devices, nothing else in the cell moves): growing
toward the rail is blocked immediately — the cell's poly ends already sit at
minimum spacing from the flipped row's nor2 poly across the rail; growing
toward the NMOS is blocked at +0.05 µm by the cell's own li strap; at +0.2 µm
the strap is shorted, which the topology guard reports while the spacing check
sees one net. Result: no legal growth in this placement without moving a
neighbour — the whitespace is in the other cell, which is exactly the diffusion
merge / whitespace-reclaim case of §5. Finding on the extractor along the way:
gate pieces split by polygon slabbing or by L-shaped poly were being dropped
(nor2_1 2 of 4 devices, dfxtp_1 14 of 24); fixed by merging poly and diffusion
before gate recognition, now equal to KLayout on all six cells.

**Probe `probes/layopt/l3_fork_balance.py` — L3, the isochronic fork in
geometry (2026-09-05, log `evidence/l3_fork_balance.log`):** the path set
(driver pin, receiver pins) is given by hand — it is what nulex's constraint
extraction will emit — and everything downstream is layopt: `rc.elmore_delays`
builds the net's RC tree from the driver (shortest-resistance tree over the
segment graph), gives each shape its capacitance and each receiver its Cin,
and returns the Elmore delay to every receiver; `objective.fork_balance` is
the spread. On the L2 row, net f leaves inv u1 and forks to u2 (60 µm met2
detour) and to v4 in the other row (180 µm detour). With the long branch on
met2: path R 66 vs 117 Ω, delays 81.2 vs 82.2 ps, imbalance 0.96 ps (1.2 %);
the optimizer widens the long branch to its 6× bound and leaves the short one
at minimum, imbalance 0.10 ps. With the long branch on li1 (12.8 Ω/sq): path R
6.8 kΩ, delays 88.6 vs 163.5 ps, imbalance 74.9 ps — a real fork violation
against a gate delay of tens of ps; sizing at its bound leaves 17 ps (14.7 %),
so the verdict is "reroute to metal or buffer", which is what a designer needs
to hear and what the met2 variant confirms. Two probe-routing mistakes on the
way were caught by the tool itself (a met2 crossing that shorted the branches;
widening that merged a detour's own legs): the RC tree simply reported the
bypass.

**Probe `probes/layopt/l4_dissolve_finger.py` — L4, the boundary dissolved
(2026-09-06, log `evidence/l4_dissolve_finger.log`):** `moves.add_finger`
grows a transistor across its cell edge by mirroring the gate and the inner
S/D column about the outer S/D region — new diffusion, contacts, strap and a
poly bridge in the field, shifted outward if the mirror image would violate
spacing — with the new rectangles taking the cell's provenance. On a row
fill_4 | inv_1 | fill_4 | nand2_1 | fill_1 | decap_4 the inverter's PMOS
goes from W 1.00 to 2.00 µm and its NMOS from 0.65 to 1.30 µm, each
re-extracting as ONE device of two combined fingers with the same nets,
topology preserved, no new rule violations; the cell's active geometry now
ends at x 3.29 µm against a LEF box ending at 3.22. KLayout extracts the
result independently as pfet W=2 µm / nfet W=1.3 µm, isomorphic to layopt's
netlist (`evidence/l4_fingered_vs_klayout.log`). The control — the same move
on the nand2, whose neighbour is a 0.46 µm fill_1 and then a decap with its
own diffusion — is refused: diffusion spacing 0 and a changed netlist. Two
tool corrections fell out: the enclosure rule is now sky130's two-opposite-
sides form (the four-sided version flagged every stock strap), and the new
column is placed at the first legal offset rather than the exact mirror
(asymmetric drain straps).

**Probe `probes/layopt/l4_path_balance.py` — L4, a discrete move balances
timing (2026-09-06, log `evidence/l4_path_balance.log`):** two inv_1 drivers,
each followed by fillers, drive two receivers — path A over 2 fF, path B over
a 120 µm met2 detour (10 fF). Baseline 13.7 vs 39.6 ps. Wire sizing cannot
help B (metal R is negligible against a 3 kΩ driver), fingers can:
`optimize.greedy_search` over integer finger counts for both drivers (P and N
separately, each state rebuilt from the base layout because geometry-
generating moves are not reversible edits) adds two fingers to B's PMOS,
W 1 → 3 µm, and B falls to 14.1 ps: imbalance 25.9 → 0.4 ps, 13 states, every
one legal and topology-identical; a fourth finger is declined as overshoot
plus area. The third finger needed the signal-net jumper (`add_finger` now
adds mcon + met1 from the inner strap to the new one when the inner S/D is
not a supply), and two rule-check refinements came out of it: min width is
judged on merged geometry (the stock drain strap is a 0.10 µm stub plus a wide
bar), and the jumper lands on the widest slab. KLayout extracts the result as
pfet W=3 µm, isomorphic (`evidence/l4_balanced_vs_klayout.log`). Deferred with
a reason: same-net diffusion merge across abutting cells changes area, not
timing, until a compaction move exists.

**Probe `probes/layopt/l5_variation_accept.py` — L5, acceptance under
variation, two tiers (2026-09-06, log `evidence/l5_variation_accept.log`):**
the L3 fork before and after sizing, judged as an isochronic fork: the slow
branch must arrive within one gate delay (40 ps) of the fast one. T2 is
layopt's own RC tree with per-layer sheet-resistance and capacitance scale
factors drawn from a stated variation model (1σ: li 15 %, metals 10 %, C 8 %,
Cin 10 %, driver 15 %), 4000 samples. T3 is stat-sim's event-driven runtime
under nvc: `rc.fork_branches` reduces the tree to trunk + branch RC, a
generated testbench wires `statsim_pl_rc` elements and `pl_load` taps, and 60
Monte-Carlo elaborations pass the same variation model in as top-level
generics. Results — met2 fork: skew ≈1 ps, p_fail 0 in both tiers, sized or
not. li1 fork, baseline: T0 74.9 ps, T2 75.1 ± 12.5 ps with p_fail 0.998, T3
nominal 48.6 ps and 6/6 launches hazardous, MC p_fail 0.92 — rejected. li1
fork, sized: T0 17.0 ps, T2 17.1 ± 2.8 ps with p_fail 0.000, T3 11.3 ps, 0/6
hazards, MC p_fail 0.000 — accepted. T3's skews are ln2 × T0's (stat-sim's
50 %-point convention against Elmore's first moment; 48.6 vs 51.9 and 11.3 vs
11.8), so the tiers agree on every verdict. The variation model is an
assumption stated in the probe, not a PDK fact — stat-sim's MC-characterized
τ is the flop side; interconnect variation here is a documented σ table.
Flop side, tried and put in its place: feeding the skew into stat-sim's
MTBF = exp(slack/τ)/(T0·f_c·f_d) with slack = gate delay − skew gives
microsecond MTBFs even for the balanced fork, because a 40 ps slack is below
the sky130 dfxtp's own 90 ps setup. A fork is not a flop-sampling event: its
acceptance is the tail probability of the skew distribution beyond the margin
(p_fail above); the MTBF formula belongs to a CDC receiver with a cycle of
settling, which stat-sim's latch already models.

**A real place-and-route result (2026-09-07, `probes/layopt/gcd/`,
`evidence/l2_real_def_gcd.log`):** OpenROAD `63fe72c` built from source on
this box (no prebuilt package exists for Ubuntu 22.04 any more; dependencies
via the project's installer with the OS check forced from Linux Mint to
Ubuntu, GUI off, test binaries skipped), Yosys synthesis of the ORFS `gcd`
design to sky130_fd_sc_hd, and a standalone Tcl flow — floorplan at 38 %
utilization, tap cells, PDN on met1/met4/met5, global and detailed placement,
CTS, global and detailed routing with 0 DRC violations, fillers — producing a
784-instance DEF. `def2flat` reads it with the merged cell GDS: 57 k
rectangles, 2472 devices, 2102 nets, 9 s; KLayout reading the same DEF with
the real cell geometry and extracting with its own engine agrees exactly
(W/L multiset, degree histogram, isomorphic). Three reader gaps were found and
closed on the way: DEF-defined vias (`VIAS` section, VIARULE-generated
geometry from cut size, spacing, enclosure and row/column count), DEF 5.8
`RECT` wire pieces and `TAPER`, and — the one that shorted VSS into a signal
net — special-net wires have flush ends where regular wires get the default
half-width extension. The reference itself needed care: kestrel's KLayout
recipe stops at met3 and fragments a power grid routed on met4/met5, so the
probe carries a full-stack extraction.

**L4 on the real layout (2026-09-07, `probes/layopt/l4_gcd_whitespace.py`,
`evidence/l4_gcd_whitespace.log`):** of gcd's 784 instances, 33 logic cells
have a fill_4 or fill_8 flush on their right — OpenROAD's own whitespace. Six
tried. Two `buf_4` rebuffers grow legally, 5 → 6 fingers per stage, topology
preserved, no new violations, and their driven nets speed up (Elmore 13.2 →
12.0 ps over 4 receivers, 17.6 → 15.8 ps over 8, with R_drv ∝ 1/W); KLayout
extracts the result isomorphic to layopt's (`evidence/l4_gcd_fingered_vs_klayout.log`).
Then the gate bridges were generalized (2026-09-07/08): when no poly bridge
meets spacing, a **column bridge** runs vertical poly to same-net poly already
aligned in the finger's column (the other transistor's added finger, or the
cell's own gate poly), and a **contact bridge** builds a poly tab into the
field with a licon, an li pad and a met1 bar to the gate net's li pin,
searched over tab length and height and reporting a tally of what rejected
each candidate when nothing fits. With those, and the inner S/D region now
bounded by the next gate on the strip whichever transistor owns it (a
nand2's PMOS share one strip — mirroring the device's own extent had shorted
VDD into the drain), five of the six cells take a legal finger: both nand2_1
PMOS pairs (outputs 21.0 → 15.4 ps and 11.5 → 8.5 ps), rebuffer12's PMOS,
rebuffer3 and rebuffer13 both stages; the nand2 result is KLayout-isomorphic.
Still refused, with the reason named: the nand2 NMOS (a series stack — the
node between its gates has no contacts, so the whole stack must be mirrored,
not one transistor) and the clkinv_1 / rebuffer12 NMOS (no met1 height clear
of other nets for the S/D jumper). One P&R met1 route had shorted a jumper
into net `_076_` with zero spacing flags before the jumper learned to look —
the topology guard caught it, which is what it is for. The move also learned
that the bridge must meet spacing, not just avoid overlap.

**Series stacks (2026-09-08).** `add_finger` now mirrors a *whole* series
stack when the node beyond the outermost gate is uncontacted: it walks inward
gate by gate until a contacted region, mirrors every gate and the middle
node(s) about the outer region, and bridges each new gate (poly bridge for
the near one, column or contact bridge for the far ones). The result is what
sky130 itself draws for a nand2_2: two parallel A–B stacks, each with its own
uncontacted middle node. That forced a guard decision. The extractor rightly
reports four 0.65 µm NMOS and two middle nets rather than two 1.3 µm devices —
KLayout says the same of the written GDS (`evidence/nand2_stack_fingered_vs_klayout.log`,
device W/L multisets equal, graph isomorphic) — so the plain graph signature
changed although the circuit had not. `compare.reduce_stacks` now puts the
netlist in series-parallel canonical form before hashing: an *internal node*
is an unlabelled net whose shapes are only diffusion and whose two terminals
are S/D of same-kind, same-L devices; devices chained through internal nodes
form a stack (ordered gate sequence between two external nets, orientation
canonicalized); parallel stacks with the same ends and gate sequence have
their middle nodes identified, after which the parallel fingers collapse
exactly as `combine_parallel` collapses single devices. The reference
isomorphism check keeps the raw graph (`stacks=False, with_w=True`). This is
the right identity for the guard: a middle node has no observable name, and
merging the two middle nodes with metal would only add capacitance.

On a bare nand2_1 between fillers both fingers are legal, PMOS pair 2.0 + 1.0
and NMOS as two stacks (`test_series_stack_nand2`) — but only in the order
PMOS then NMOS. The 0.6 µm field gap between the strips is the scarce
resource: the far gate's contact bridge must cross it on met1, and three
earlier habits took it first. The PMOS finger's mirrored Y strap ran the
full row height (as the original does, to reach the NMOS drain) straight
through the mirrored stack and shorted Y into B — the topology guard caught
it, spacing could not; the strap is now trimmed on the side away from its
rail wherever foreign li or cuts sit (never past its own contacts). The
PMOS poly bridge preferred the gap side; it now takes the rail side first.
The S/D jumper searched heights middle-out over the whole strap and landed in
the gap; it now searches its own strip first. With those, PMOS-then-NMOS
succeeds and the probes try both orders and keep the better. On the real gcd
layout the nand2 NMOS stacks were still refused at this point — the tally
named the P&R met1 in the gap and diffusion under every head candidate — and
rebuffer12's NMOS became legal because its jumper stays in its strip.

**Routing around the P&R wiring (2026-09-08, `layopt/route.py`).** Every
connection a move makes had been a straight bar, and a straight bar is what
a placed-and-routed layout does not have room for: next to gcd's `_149_` two
met1 wires of other nets cross the 0.6 µm field gap, one of them right over
every position the far gate's contact could take, so no mcon could sit on
the pad. The pieces of a route existed though — li up out of the gap past
the PMOS diffusion edge, a free met1 track at y ≈ 31.4, and the target net's
*own* P&R wire to land on. `route.maze_route` finds such paths: a Dijkstra
search over a 10 nm raster of the three lowest routing layers (li, met1,
met2) with mcon and via1 between them, other nets' shapes blocked after
growing by spacing plus half a wire width (and their cuts, which would short
a wire drawn over them), via cells requiring the cut clear of every cut on
that layer and both landing pads clear of other nets, and *any shape of the
connection's own net* a legal landing — its pin, or the wire the router
already gave it. The result is plain rectangles the move adds and the guards
then judge like everything else. The contact bridge and the S/D jumper call
it when no straight bar fits; a move's own new rects are passed as free
space for the route to start from, never as landings.

Two things it had to learn. (1) *Same-net spacing.* Own-net shapes are free
space because a wire merging into its own net is the point — but a wire
passing beside an own shape closer than spacing without touching it is a
notch, and a landing pad wider than the wire makes one where a wire would
not. The raster cannot say this per cell (a straight run's rectangle is the
union of its cells), so the router checks the finished rectangles against
own shapes and repairs: a faulty wire blocks the spacing band around the
shape except the corridors from which a run enters it head-on; a faulty pad
blocks via placement in the band unless the pad centre is inside the shape.
`_161_` took two repairs — its target net's own via stack sits exactly where
the natural landing was — and then a path of cost 200 (≈ 2 µm of wire) that
the guards accept. layopt's delta-DRC does not check same-net notches, so
this check is the only one until it does. (2) *A landing is a real overlap.*
The first landing rule accepted any touch and produced a 10 nm corner
overlap that the extractor did not treat as a connection (nor should it);
now the wire's centre line must lie inside the target. A third fix was older
than the router: a contact head placed beyond its first position had no poly
between it and the finger's overhang — a stem now joins them.

Result on gcd: both nand2_1 cells take the whole NMOS stack (`_149_`: li,
met1, via1, met2 hop, via1 onto the net's own met1 pad; `_161_` after two
repairs), and clkinv_1 `_110_`, refused before for want of any met1 height,
takes both fingers with a jumper routed on li alone — the two straps were
0.5 µm apart with nothing between them on li, a layer the straight-bar
planners never considered. Every result re-extracts with the original
netlist, adds no violation, and matches KLayout's extraction of the written
GDS (`evidence/gcd_149_stack_routed*`, `gcd_161_stack_routed*`,
`gcd_110_routed_jumper*`). Ten unit tests, including a bare nand2 row with a
foreign met1 wire laid straight through its gap (`test_route_around_met1`).
The router runs once per connection (≈ 0.1–3 s, 100–500k cells); the tally
on refusal now includes its statistics.

**Same-net notches in the delta-DRC, and filling them (2026-09-08).** The
spacing rule had skipped same-net pairs entirely ("they merge"). They do
when they touch; two parts of one net that do *not* touch and lie closer
than spacing are a notch, and sky130's spacing rules apply to them like any
other pair. The rule now is: same layer, same net, neither overlapping nor
sharing an edge, gap below spacing, and the gap rectangle between them
(facing span, or the corner square when diagonal) not covered by other
same-layer geometry — a slab decomposition of one polygon, or a wire landing
on a pad beside its route, is covered and passes. Turning it on flagged the
finger moves themselves: every mirrored gate finger had ended 0.07 µm from
its own net's pin tab, a violation KLayout's *extraction* (which is what the
evidence checked) does not see. So a move now ends with `fill_notches`: new
rectangles are labelled with a net by same-layer contact with extracted
geometry (propagated through touching new rectangles; the unlabelled are
left to the DRC), and each same-net notch a new rectangle makes is filled
when the fill keeps spacing from other nets and, on poly, crosses no
diffusion. A fill is at least min width both ways (a sliver is a width
violation, and a corner square touches its two shapes only at corners —
which the extractor rightly does not call a connection), and its edges are
aligned to nearby edges of the two shapes it joins, because a fill edge a few
nanometres off a neighbour's edge is the next slit; the pass iterates until
nothing is left. On the bare nand2 row the PMOS finger, the NMOS B' finger
and the B pin tab end up joined by one poly block in the field gap — the
same net, so the topology guard is unmoved, and the poly bridge the planner
built separately became redundant in that case. The fill pass also covers
the router's own repairs from the other side: the *unrepaired* `_161_` path
(`LAYOPT_ROUTE_NO_REPAIR=1`) now passes the guards because its met1 notches
against the target net's route are filled, i.e. wire and route merge.
Eleven tests (`test_same_net_notch`: a U of li flagged, filled U and slab
stack not, a separate island still flagged as different-net spacing). On gcd
the rule adds 77 flags to the baseline (935 → 1012: notches already in the
stock cells and P&R wiring, which the delta ignores by construction) and all
twelve fingers in the six candidate cells stay legal, the fills included.

**`remove_finger` (2026-09-08).** The inverse move, so sizing can go both
ways: the path balancer had only been able to speed up the slow driver, and
in a completion tree or a QDI slice slowing the fast one is often the cheaper
change (less area, less load on the previous stage). It takes a device's
outermost finger on one side: the finger's span (diffusion plus overhang) is
cut out of every poly rectangle covering the gate, and poly that then leads
nowhere — no gate under it, no contact, at most one other poly touching it —
is pruned repeatedly, which takes a bridge that only served that finger and
any stub to a bar while leaving a comb's bar over the remaining fingers; the
outer S/D region's contacts go and the diffusion is cut back to the inner
region's contacts plus enclosure, the way the stock cells end a strip (or to
the gate's inner edge when that region has none); implant and well rectangles
fitted to the old diffusion edge are trimmed with it. Then the li and metal
that only served the removed contacts — the mirrored strap, the jumper's
mcons and bar — are pruned as dead ends: a conductor in the vacated region
with at most one neighbour (same-layer contact, or the cut and metal it stacks
with), no remaining contact under it and no label, is deleted and its
neighbours re-examined, so the chain is followed back to where the net's
surviving geometry begins. The device must keep a finger and the finger must
be the strip's outermost. Deleting rectangles shifts ids; the move returns the
changed ids after deletion.

Verified: `add_finger` then `remove_finger` on the bare nand2 row gives back
the original netlist, sizes and rectangle count exactly (the drain region is
cut to its contacts plus 0.04 µm rather than the stock 0.055, the only
difference in coordinates); a stock buf_4 alone on a row loses one PMOS and
one NMOS finger of its output stage (4 → 3, W 4.0 → 3.0 and 2.6 → 1.95)
with the same netlist, no new violations and KLayout isomorphic; on gcd,
rebuffer3 loses a finger per stage the same way and its driven net's Elmore
delay rises 13.2 → 15.6 ps (47.6 → 59.6 ps worst-edge under the Liberty-fitted
model of the next entry) (`probes/layopt/l4_remove_finger.py`,
`evidence/l4_remove_finger.log`, `remove_finger_buf4*`,
`gcd_rebuffer3_removed*`). Writing the inverse found a bug in the forward
move: `add_finger` had been extending every implant and well rectangle that
overlapped the diffusion, including the neighbouring fillers' wells on the
side away from the growth; it now extends only the cell's own, on the growing
side. Thirteen tests.

With both moves the discrete search sizes in both directions
(`probes/layopt/l4_path_balance_twoway.py`): path A driven by an inv_4 over a
short wire (3.8 ps), path B by an inv_1 over 120 µm of met2 (39.6 ps). Finger
counts per polarity are the variables, a state below the stock count removes
fingers and above it adds them, and the cost charges added fingers and credits
removed ones. The greedy search first adds three PMOS fingers to B's driver
(the only way to get B under 11 ps), then takes two PMOS fingers off A's, and
lands at A 7.5 / B 10.7 ps — imbalance 35.8 → 3.2 ps — with fewer transistors
than it started with (10 fingers → 8), every state rebuilt from the base and
passed by both guards. One honest caveat: the driver model is PMOS-only, so the
search also strips A's NMOS to one finger purely for the area credit; a
two-edge model would stop it, and that is the model's job, not the move's.

**The two-edge driver model, from the Liberty (2026-09-08, `layopt/drive.py`,
`probes/layopt/drive_fit.py`, `evidence/drive_fit.log`).** Until here the
driver was one number, R = 3 kΩ · (1 µm / W_p), an assumption. A stage drives
its net through the PMOS on the rising edge and through the NMOS on the
falling one, so the model needs a resistance per edge, and the numbers should
come from something measured. sky130_fd_sc_hd's Liberty is that measurement:
for every cell, 50 % delay against input slew and output load on each edge.
The slope of delay against load at a fixed slew, divided by ln 2, is the
Elmore-equivalent driver resistance of that edge; the intercept is the stage's
intrinsic delay. Against layopt's own extraction of the same cells' GDS (the
cell alone in a DEF, nets named from the LEF pin ports since labels do not
survive the merged-GDS flatten; the width the arc's input pin switches in the
output stage, parallel devices adding, a series stack counted by its depth)
this gives R·W per edge across 24 cells — inverters, buffers, clock variants,
nand2, nor2, sizes 1 to 16:

| | NMOS | PMOS |
|---|---|---|
| R·W at W = 1 µm | 3209 Ω·µm | 8733 Ω·µm |
| exponent β in R ∝ W^−β (1 is ideal) | 0.933 | 0.839 |
| R·W spread, inv_1 → inv_16 | 3135 → 3953 | 8165 → 13613 |
| series stack of 2 vs same-size inverter | 1.52 – 1.71 (nand2) → 1.64 | 2.15 – 2.39 (nor2) → 2.28 |
| intrinsic t₀ (inv_1, zero load) | 27.8 ps | 36.0 ps |

Three things the table says that the old constant did not. The old 3 kΩ was
2.7× too optimistic for a PMOS and 1.6× for an NMOS (Elmore basis), which
matters when layopt's delays are compared with anything else. PMOS strength
does not scale with width: a 16× wider inverter has 65 % more R·W, so the
model carries β per polarity (`R = k · W^−β`) and fits every unstacked cell
within ±9 % except the two biggest buffers. And a series stack costs 1.6×
for NMOS and 2.3× for PMOS, not the schematic 2× — the model carries a
stack factor per polarity, fitted against the same-size inverter. The
constants live in `tech.SKY130.drive` (a `DriveModel`) and the fit probe
reports OK/UPDATE against them; a unit test re-derives inv_1, inv_4 and the
nand2 stack from the Liberty and checks the model within 10 %.

With both edges in the cost (rise against rise, fall against fall) the path
probes tell a different, more honest story than their single-edge numbers
above. The one-way probe (two inv_1 drivers, 120 µm of met2 on B): baseline
A 39.7/21.8 ps rise/fall, B 113.8/62.9; the search adds one PMOS and two NMOS
fingers to B's driver and ends at B 65.8/23.7 — combined imbalance 115 → 28 ps
(a third PMOS finger alongside three NMOS fingers is refused by the guards in
that gap). The two-way probe (inv_4 against inv_1): baseline A 13.6/6.6, B
113.8/62.9, combined 156.5 ps; the search takes A's PMOS from four fingers to
one but stops A's NMOS at three — removing the fourth would open the falling
edge, which the single-edge model had let it do for the area credit — and
gives B two PMOS and four NMOS fingers: A 43.2/8.6, B 65.8/18.3, combined
32.4 ps, with the transistor count unchanged (10 → 10). Two bugs surfaced on
the way and were the kind the inverse move was meant to find: the discrete
problem's touched-id list was stale after a deletion (it now checks the whole
layout when a move removed rectangles), and the delta-DRC's baseline was keyed
by rect id, so after `remove_finger` shifted ids every pre-existing flag read
as new and every removal state was illegal — violations are now keyed by the
geometry of the rectangles involved. The gcd whitespace figures under this
model (worst edge, receivers' Elmore): both nand2 output nets 97.8 → 54.4 and
56.4 → 32.1 ps with the stacks mirrored, clkinv_1 48.3 → 29.8 ps, the three
buf_4 rebuffers 21.2 → 19.4, 47.6 → 41.6 and 64.7 → 55.9 ps — the earlier
single-edge numbers in this section were computed with the 3 kΩ assumption and
stand as history.

**Input slew (2026-09-08).** A load-slope model prices a long wire only by
its Elmore moment; the wire also hands the receiver a slow edge, and the
receiver's own delay grows with it. The Liberty tables are two-dimensional,
so both effects are in the data. Per cell and edge, with R fixed from the
load slope, the 7 × 7 table (slews to 700 ps) fits

  delay(s, C) = t₀ + ln 2 · RC + κ · RC · s / (RC + μ · s),
  transition(s, C) = √((τ₀ + λ · RC)² + (ν · s)²)

within 5–20 ps rms for every single-stage cell. The delay's slew
sensitivity is not a constant: it saturates at κ ≈ 0.41 (rise) / 0.38
(fall) when the stage is slower than its input (RC ≫ s) and fades when the
stage is faster (RC ≪ s), which the rational form captures with a small μ
(0.011 / 0.071). The output transition is 0.99 · RC + 15.5 ps rising and
0.93 · RC + 7.2 ps falling, plus a slew-limited part ν · s with ν ≈ 0.22 when
the input is slower than the stage. The constants join `tech.SKY130.drive`;
`DriveModel.stage(edge, W, C_total, Elmore, slew_in)` returns the 50 % delay
and the output transition (the Elmore moment from `rc` enters as ln 2 · RC).
A unit test reproduces inv_1's table points within 10 % on delay and 15 % on
transition. The first attempt subtracted the Elmore moment itself from the
50 % delays and fitted nothing — the ln 2 between the first moment and the
50 % point is a convention the tool now states in one place.

The path probes now judge a path as two stages: the driver (input transition
50 ps, its Elmore to the receiver, its own RC for the slew terms) and the
receiver's delay on the opposite edge, driven by the transition the driver
hands it and loaded by a nominal 5 fF. That is where a long wire costs what
it really costs: not only R · C to the receiver but a slow edge into it. On
the one-way probe B's driver hands its receiver a 123 ps rising transition
against A's 50 ps; baseline A 97.9/85.6, B 163.2/130.2 ps rise/fall through
both stages, combined imbalance 110 → 27 ps after one PMOS and two NMOS
fingers on B's driver. The two-way probe: baseline A 73.6/66.9 (transitions
29/17 ps), B 163.2/130.2 (123/64 ps), combined 152.9 → 33.6 ps with the same
finger choices as before (A's PMOS 4 → 1, NMOS 4 → 3; B's PMOS 1 → 2, NMOS
1 → 4), transistor count unchanged. The remaining imbalance is B's rising
edge, 122 against 101 ps: B's driver wants a third PMOS finger and the guards
refuse it beside four NMOS fingers in that gap — the layout, not the model,
is now the limit, which is the right place for the limit to be.

**Moving a P&R wire when no route exists (2026-09-08, `route.reroute_around`).**
The router treats other nets' geometry as walls. Cell geometry is a wall; a
place-and-route wire is a choice someone made with the same information we
have less of, and in a dissolved layout it is as movable as anything else.
When the hard search fails, the search runs again with the other nets' P&R
wires (rects whose provenance names a DEF net, never cell geometry) passable
at a penalty of 400 per cell; the path it finds names the wires it conflicts
with. Each is cut around the path — its rect keeps the first piece, the other
pieces become new rects so ids stay valid, slivers below min width are
dropped — our geometry goes in, and each pair of consecutive pieces is
reconnected with the router, the far piece the only legal landing and our new
wire now an obstacle like any other. If one reconnection fails the whole thing
is rolled back and the refusal says which net could not be reconnected. The
guards then judge the result as they judge any move; since the moved net
connects devices its topology is under the signature too. Two details found
by the synthetic case: a cut can leave a sliver above a pad that nothing can
reach (dropped), and a path may cross a wire twice (pieces are reconnected
pairwise, not as one pair). The unit test (`test_move_pr_wire`) seals a bare
nand2 row with walls of another net on met1 and met2 across the field gap,
li walls beside the cell and rows sealed above and below; the mirrored NMOS
stack's far gate has no path, the wall is cut around the connection's pad and
reconnected with a met1 detour above it, the stack goes in, the wall's net
stays one net, no new violation.

What it bought on gcd, honestly: nothing yet, and the search for a case
where it would found something else. All 33 candidate cells were tried
(`--max 33`). Without the wire move 21 take at least one finger. The twelve
refusals split three ways. Seven are the mirrored strap meeting foreign li or
a licon of the neighbouring cell inside the contact span — cell geometry, not
wiring, and not a wire move's business. One (`_135_`, nand2b) is the guard
catching the extended diffusion corner-touching another diffusion of its own
cell; the move should check diffusion spacing when it extends, and does not
yet. Four were routing refusals, and with the wire move available every one
of them still failed — the refusal now says why: *not* "no path", but the
router's own same-net notch repair failing to converge among the driver's own
output geometry (rebuffer15's buf_4 comb, the nand3's pins). Since the move
ends with a fill pass that fills exactly such notches, the router now accepts
a path whose remaining notches are fillable (the gap grown to min width keeps
spacing from every other net) instead of repairing them away. With that,
rebuffer15 takes both fingers (net15 25.8 → 23.0 ps) and `_258_` mirrors its
whole three-transistor nand3 NMOS stack (output `_102_` 112 → 60 ps), 23 of
33 cells. The nor4's four-PMOS stack still has no room for a contact head
(diffusion and poly under every position) — geometry again. So the wire move
stands as a capability the synthetic case proves and gcd, so far, does not
need: on this placed-and-routed design the walls that stop a finger are the
neighbouring cells' own metal, and the wire move by design leaves those
alone. That is the correct restraint; it is also where the next lever is (a
neighbour's li strap is as movable as a P&R wire once the neighbour is
dissolved too).

**Diffusion spacing in `add_finger`, and a DRC false positive (2026-09-08).**
The `_135_` refusal above was the guard's, and it was wrong. The nand2b's P
diffusion is drawn as two rectangles sharing an edge — one polygon carrying
several nets — and the delta-DRC's spacing rule compared their net *sets*,
found them unequal, and flagged the shared edge as a zero-spacing violation
between different nets. That flag had always been there; the geometry-keyed
baseline (the fix for `remove_finger`) turned it into a new one the moment the
move stretched one of the two rectangles. Rectangles that overlap or share an
edge are one merged shape whatever nets they carry, and the rule now says so
(cuts excepted). With that `_135_` and `_121_` take their PMOS fingers. The
move itself, meanwhile, learned the rule it had been leaving to the guard:
before extending the diffusion it checks the new strip against every other
diffusion and tap rectangle within spacing, excusing only slabs of its own
strip in its own cell, and refuses with the rectangle named. A nand2_1 with an
inv_1 abutting on its right is the test: the extension would land in the
inverter's diffusion and the move says so (`test_add_finger_refuses_into_neighbour_diffusion`).
On gcd the merged-shape rule takes the baseline from 1012 flags to 598 — 414
of them had been the same false positive — and the 33-cell run goes to 32 of
33 cells with at least one legal finger (`evidence/l4_gcd_all33.log`). What
refuses now, per finger: the nor4's four-PMOS stack (no room for a contact
head) and, seven times, the neighbouring cell's li or licon inside the
mirrored strap's span — the next lever.

**The "neighbour's li strap" (2026-09-08).** Followed to the geometry, the
seven were not a neighbour's straps at all, and not movable ones. Every one
was a li strap of the *cell's own* layout sitting just past the diffusion end
— a supply tab from the rail into the outer S/D region with that region's
licon and the rail mcon under it, or an internal column with contacts on the
other strip — exactly where the mirror of the inner strap lands. A strap over
contacts cannot be cut and rerouted the way a P&R wire can; the licons need
li over them. What can move is *our* column: the mirrored gate finger, its
contacts and strap can sit further out at the price of a wider outer region
(more diffusion, a little capacitance). The spacing shift had estimated that
from the straps alone in one pass; it is now a search — grid steps up to
0.6 µm until the mirrored straps clear every other net's li by spacing and
cover none of its cuts, the mirrored contacts clear other cuts, the new
finger clears other poly, and the mirrored strap is not itself a same-net
notch against the inner strap (0.16 µm apart is a violation the fill pass
cannot always cure: on `_129_` the fill was blocked by the rail tab's
corner). The strap trim was rewritten around the part of the strap that must
exist, the contact span: anything within spacing of that span refuses,
anything beyond it trims that side, and a cut of another net counts only by
overlap (li has no spacing rule against a cut; it must merely not cover it) —
the old version had refused rail mcons at 0.11 µm and looked on the wrong
side for a P device. Three router fixes fell out of the same seven cells: a
strap clipped to its contact span left no source point (the route now starts
at its centre); a repair that changes nothing (the run stops short inside the
corridor the band exempts) now closes the corridor next time; and a notch
fill near another rect of the same route is a same-net notch the iterating
fill pass will fill, not a reason to call the path unfillable. Result: all
seven cells take at least one finger (`evidence/l4_gcd_strap7.log`) — and2_0,
mux2_1, xnor2_2 and lpflow_inputiso1p both; the three lpflow_isobufsrc their
PMOS, their NMOS still stopped by the rail tab or by a same-net notch the
guard catches. The nor4's four-PMOS stack stays refused for a reason now
seen: at the stack's 0.42 µm finger pitch the second far gate's contact head
cannot sit beside the first's (a head and the next finger's stem need 0.84),
and the rail side has the next row's diffusion 0.08 µm past the first
position. A head centred on its finger — the narrowest legal one, cut plus
two enclosures — is now a candidate and is what a mirrored stack needs, but
the fix for four in a row is heads alternating sides or a wider mirrored
pitch; not done. Which brings the question of whether this saves area or
power: honestly, not yet. The fingers spend filler area that was already
there and add gate width, i.e. switched capacitance; the two-way balance kept
the transistor count constant. The saving is indirect — a flow that fixes
handshake skew with larger cells, inserted buffers or delay padding pays in
area and power, balancing in place pays in neither — and the direct saving
would come from dissolving the boundary itself (implant and well enclosure
between abutting cells), which is not done. Power is not measured; the
extraction has every net's C, so switched capacitance before and after is the
next measurement. A zero-area, zero-wire sizing move the process does allow:
Vt flavour by implant (sky130's lvtn / hvtp layers), which the next entry
takes up. With the shift search in place the 33-cell run reaches 33 of 33
cells with at least one legal finger (`evidence/l4_gcd_all33.log`); what
refuses is per finger — the nor4 stack's heads, three lpflow NMOS fingers
whose strap meets the cell's rail tab, and one guard catch of a topology
change that the move should have seen: poly of another net crossing the
extended diffusion makes a transistor, and the move now refuses that itself.

**Device speed by doping and by gate length (2026-09-08, `probes/layopt/vt_fit.py`,
`evidence/vt_fit.log`).** The architect's suggestion: change the device, not
just its width. sky130 has three Vt flavours per polarity selected purely by
implant — lvtn (125/44) on an NMOS makes a `nfet_01v8_lvt`, hvtp (78/44) on a
PMOS a `pfet_01v8_hvt` — so a Vt change is a rectangle on one layer: no area,
no wire, and (for hvt) less leakage. The PDK's tt models for the five devices
were fetched from skywater-pdk-libs-sky130_fd_pr and converted the way kestrel
converts its own (subcircuit wrapper off; every corner or mismatch symbol the
model references and does not define set to zero, multipliers to one — the
same recipe as kestrel's testbench, and the recipe that matters: the tt
corner file's own offsets make Xyce's operating point fail, and defining the
file's `_spectre` symbols a second time does the same). An inv_1 (P 1.0,
N 0.65, L 0.15) driven by a 50 ps ramp into 2–40 fF, its 50 % delay against
load, slope over ln 2 — the same quantity the Liberty gave for the standard
flavour. One obstacle was the simulator, not the model: Xyce's oldest BSIM4
fails the transient's operating point for the standard nfet below about 2 µm
width (kestrel's devices are 20–40 µm and never met it), so the inverter is
characterised at twenty times inv_1's size with loads scaled the same and
R·W reported at inv_1's size; the standard flavour lands at 7098 / 4299 Ω
against the Liberty's 8165 / 4823 — 11–13 % lower, the same order.

| device | R relative to standard at L = 0.15 |
|---|---|
| PMOS hvt, L 0.15 | R_rise × 1.56 |
| PMOS lvt (L 0.35, the shortest the rules allow) | R_rise × 1.09 |
| NMOS lvt (L 0.35) | R_fall × 1.35 |
| standard, L 0.18 | P × 1.28, N × 1.15 |
| standard, L 0.25 | P × 1.92, N × 1.37 |
| standard, L 0.35 | P × 2.87, N × 1.68 |

Two conclusions, neither the one expected. Low Vt is not a speed-up here:
sky130's DRC (poly.1b) requires a low-Vt gate to be at least 0.35 µm long,
and at that length the lvt PMOS is 9 % *slower* than a standard 0.15 µm gate
and the lvt NMOS 35 % slower — the longer channel eats the threshold gain.
High Vt on the PMOS is the real lever: 1.56× on the rising edge for a single
implant rectangle, plus lower leakage, and there is no high-Vt NMOS in this
process. Gate length is a second lever in the same direction and works on
both polarities — 0.15 → 0.18 costs 28 % on P and 15 % on N — though it
moves poly edges and so contacts, which fingers in whitespace can afford and
stock geometry may not. For a balancer that has fast paths to slow down at
zero area and power, these are the two moves; the next entry builds the
first.

**`set_vt` (2026-09-08).** Building it turned the finding around once more.
The extractor now reads the implant layers (an hvtp rect over a P gate makes
the device `pfet_01v8_hvt`, lvtn over an N gate `nfet_01v8_lvt`), and the
first thing it reported was that every PMOS in sky130_fd_sc_hd is already
high-Vt — the cell netlists say `pfet_01v8_hvt`, and every cell, fillers
included, carries an hvtp rectangle over its P strip. So the Liberty-fitted
k_p *is* the hvt value, and the useful direction of the move is the reverse
of the one planned: cutting the implant away over a PMOS makes it a standard
device and speeds its rising edge by 1/1.56, for the price of an edit on one
layer — no area, no wire, a little more leakage. The tech record now carries
the flavours (layer, gate enclosure 0.18, model, minimum gate length, measured
multiplier) and the library's default per polarity; the drive model's
multipliers are relative to that default (P: std 0.643, hvt 1.0; N: lvt
1.348 at its 0.35 µm gate). The move: "std" cuts a window — the device's
gates plus enclosure — out of every implant rect over them; a neighbouring
gate the remaining implant would then enclose by less than 0.18 is taken into
the window (0.42 µm pitch, 0.27 between gates, less than twice 0.18: in a
two-stage buffer the first stage's PMOS goes along with the output stage's,
and the move says so); leftover slivers below the implant's 0.38 µm width go
too. "hvt" draws the rect back with the same sweep and merges with implant
within spacing. The DRC learned the implant rules: width and spacing 0.38,
and a gate the implant touches must be enclosed by 0.18 on every side while
a gate it does not touch must be 0.18 clear — a partly covered gate is two
devices, and a hand-drawn edge through a gate is flagged
(`test_set_vt`). A flavour is a size to the topology guard: the signature
does not carry the model. Removed rectangles are kept degenerate so ids
stay valid, and the DRC skips them. One rule the deck itself does not
enforce was dropped from the move: "hvtp inside nwell" is commented out in
sky130's own deck, and the hd cells' implant runs 0.055 µm past their well.

What it buys. On gcd, rebuffer3's output PMOS to standard Vt: one rect
changed (the first-stage PMOS swept along), no new violation, KLayout
isomorphic, R_rise 2729 → 1755 Ω, the driven net's worst-edge Elmore
47.6 → 31.8 ps — at zero area (`evidence/l4_set_vt.log`). In the two-way
balance probe the slow driver's Vt is a fifth variable, and it is free in
the cost; the search takes it at round 3 and ends at A 101.2/69.9 ps against
B 101.5/82.4 — combined imbalance 152.9 → 12.8 ps, the rising edges within
0.3 ps, with the transistor count unchanged (10 → 10). Compare 33.6 ps
without it. That is the answer to the area-and-power question in miniature:
the balance a sizing-only flow buys with fingers, this one gets with an
implant edit and the same silicon.

**Switched capacitance — the power measure (2026-09-08, `layopt/power.py`).**
The question deserved numbers. Dynamic energy per transition of a net is
C · Vdd², and C is what the layout says: the wire (the RC extraction's union
capacitance), the gates the net drives, and the drain/source diffusion of the
devices on it. The gate term was fitted from the Liberty's pin capacitances
against layopt's own extraction of the same cells' gate area: 8.63 fF/µm²
fits 16 input pins of 12 cells within 3.7 % rms (a per-width overlap term
adds nothing at one gate length), and inv_1's input comes out 2.14 fF against
the Liberty's 2.30. The junction terms are the PDK models' zero-bias values
for the library's devices (nfet_01v8 and the hd library's pfet_01v8_hvt):
area, sidewall, and the gate-edge sidewall over W. Activity is not known here
— an asynchronous handshake toggles particular nets once per cycle — so the
measure is energy per transition per net, and a move's power price is the
change over the nets it touched, or over the design. Relative and honest, and
enough to price a finger against an implant: a finger adds gate C on its
input net and diffusion C on its output net, `remove_finger` takes both away,
and `set_vt` adds nothing (`test_power_switched_capacitance`). The gcd
whitespace probe now prints, per cell, the switched energy of the nets the
cell touches before and after; the two-way balance probe's cost carries the
design's switched energy instead of a finger count, so what it minimises is
delay spread against real capacitance. With that cost the two-way probe ends
where it did — combined imbalance 152.9 → 12.8 ps, the same five choices —
and the design's switched energy goes 136.4 → 134.3 fJ per transition, 1.6 %
*below* the start: the fast inverter's three removed PMOS fingers give back
more capacitance than the slow driver's five added fingers take, and the Vt
edit costs nothing. So the direct answer to the question is: this balance
saves a little power, adds no area, and a sizing-only flow would have paid
for the same skew with both. On gcd, where the whitespace probe only adds,
the price of a finger is now a number: 10–16 fJ per transition on the cell's
nets, 3–15 % of what they carried — `_149_`'s nand2 pays 14.3 fJ (+12 %) for
97.8 → 54.4 ps on its output, rebuffer13 12.6 fJ (+8 %) for 64.7 → 55.9 ps;
the whole design's signal nets carry 17.6 pJ per transition, and one finger
off rebuffer3 gives back 9 fJ of it (`evidence/l4_gcd_whitespace.log`,
`l4_remove_finger.log`, `l4_set_vt.log`).

**Gate length as a move (2026-09-08, `set_gate_length`).** The Xyce table
made gate length the second slow-down lever, and the drive model now carries
it: R × (L/0.15)^γ with γ_p = 1.256 and γ_n = 0.615, fitted on the
0.18/0.25/0.35 rows within 2 %. The move itself could not be what was first
written — widen the poly finger about its centre. A standard cell has no
slack beside a gate: inv_1's contacts sit exactly 0.05 µm from it (licon.11a)
and exactly 0.04 µm inside the diffusion end (licon.5), both sides, both
polarities. A longer gate cannot be cut into that stripe in place; what can
move is everything beyond it. So the move stretches the cell at the gate:
just inside the outer edge of each of the device's fingers, outermost first,
every rect of the cell beyond the cut shifts outward by the length change and
every rect crossing the cut — the poly stripe, the diffusion, well and
implant, a li strap over the gate — is stretched by it; the filler abutting
the cell gives the space, its rails and wells shrinking from the near edge
(its boundary is where its rails start; a well pokes past it). DEF wiring over
the cell follows it, shifted or stretched; over the filler it stays, since
its cuts sit on the filler's own rail cuts. A poly stripe usually gates both
a P and an N device, so both lengthen, and the move names the companion.
Shortening is the same with the sign reversed and restores the geometry
exactly (`test_set_gate_length`: inv_1 0.15 → 0.18 → 0.15, R_rise × 1.257,
the layout identical afterwards). Two lessons from the real layout: one cut
lengthens only the fingers on that stripe, so a four-finger device came back
half lengthened and split into two device groups (legal, KLayout-isomorphic,
not what was asked), hence the cut per finger; and the first version shifted
the DEF mcons over the filler onto the filler's own, hence the bound. In the
two-way balance probe the fast driver's P and N lengths are variables
(0.15/0.18/0.25); with fingers and the Vt edit already available the search
never took them — the same 12.8 ps at the same energy — which is the model's
honest answer there, not a failure of the move. On gcd, rebuffer12's output
stage goes 0.15 → 0.18 on both polarities in one move (79 rects shift or
stretch), no new violation, KLayout isomorphic and reporting the new lengths,
R_rise 2729 → 3432 Ω, the driven net 21.2 → 26.3 ps, the design's switched
energy up 5.9 fJ for the gate area (`evidence/l4_set_gate_length.log`). One
more rail lesson on the way: the cell's own rail contacts and well taps are
duplicated by the neighbouring row's cells across the shared rail, so they
must stay where they are while the rail stretches over them — the first
version moved them and split them from their twins.

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

T0's driver is the two-edge Liberty-fitted model of §2 (`tech.SKY130.drive`):
R_rise from the stage's PMOS width, R_fall from its NMOS width, series stacks
by their fitted factor, input slew through κ and the output transition through
λ, ν; a path is judged on both edges, driver plus receiver.

| Tier | Evaluator | Use |
|---|---|---|
| T0 | analytic RC, Elmore, Laplacian R_eff (this package) | inner loop, every evaluation |
| T1 | Xyce on the extracted netlist + SPEF (kestrel `spice_loop.py`, `sim/opt/backends.py`) | calibrate T0, accept a candidate |
| T2 | stat-sim: variability models, quantified MTBF, EM/IR hot-spots (`klayout2spef`, `hotspot`) | accept under variation; async gradient margins |
| T3 | nvc with SPEF taps (stat-sim `spef.py` → `pl_wire/pl_load`; `statsim_pl_rc` for RC in the path) | system-level check of the balanced design — exercised in L5 |

T0 is deliberately cheap: exact geometry (§2), analytic RC, and a drive
model whose constants come from T1 — L1 fitted f = k·W^a/(C_int + C_par) from
five Xyce runs and predicted layout moves within 1.34 %. Its job is to rank
moves; T1/T2 decide. The drive constants are per cell type and operating
point (`evidence/l1_t0_drive_model.json` is for the kestrel delay cell at
Vctrl 0.9 V) — a library of them is what a `drive.py` module will hold.

## 5. Moves

Implemented: device W stretch toward either end of the gate (`side`;
contact arrays do not grow yet — the stretched S/D region simply carries the
same contacts; in a shared-provenance cell nothing else moves), wire width
about the centre-line, translate, add rectangle, **add finger across the cell
edge** (`add_finger`: mirrored gate + S/D column, implant/well extension;
gate tied by a poly bridge (rail side first), a column bridge to aligned
same-net poly, or a contact bridge (poly tab, licon, li pad, met1 bar to the
pin); a series stack is mirrored whole, gates and uncontacted middle node,
each new gate bridged; supply sources connect through the rail that continues
into the neighbour, signal-net S/D through an mcon + met1 jumper placed
inside the device's own strip when it can be; the mirrored strap is trimmed
clear of foreign li on the side away from its rail; works on devices that
already have fingers; refuses when the transistor is not the outermost on its
strip, when the stack reaches the diffusion edge without a contacted node,
or when neither a straight bar nor the maze router (`route.py`: li/met1/met2
with mcon/via1, landing on any shape of the net), nor moving the P&R wire in
the way (`route.reroute_around`: cut it around the path and reconnect its
pieces) can make the connection —
every refusal names the obstacle, the planners with a tally of rejected
candidates and the router's statistics; `LAYOPT_PLAN_DEBUG=1` prints the
surviving head candidates, `LAYOPT_ROUTE_PROBE=layer:x:y,...` the raster
state at given points and each repair attempt).

**Gate length by stretching the cell at the gate** (`set_gate_length`: a cut
just inside each finger's outer edge, everything beyond shifts, everything
crossing stretches, the abutting filler gives the space; both devices on the
stripe lengthen; shortening restores exactly).

**Vt flavour by implant** (`set_vt`: "std" cuts the implant window over the
device's gates, sweeping in gates it would half-cover; a flavour name draws it
back; sky130_fd_sc_hd PMOS are hvt by default, so "std" is the speed-up).

**Remove finger across the cell edge** (`remove_finger`, the inverse:
outermost finger's poly cut out and dead-end poly pruned, outer contacts
removed, diffusion cut back to the inner contacts plus enclosure, implant and
well trimmed, dangling li/metal pruned to the net's surviving geometry;
refuses a single-finger device or a finger that is not the strip's outermost).

Planned, in the order the async objectives need them:

1. Contact-array growth on W changes (keeps R_contact proportional); a
   `remove_finger` inverse for balancing by slowing.
2. **Same-net diffusion merge across a former cell edge** — the other payoff
   move: two abutting cells with the same net on facing S/D regions become one
   diffusion with a shared contact row.
3. Whitespace reclaim: shift a device column into neighbouring slack when a
   stretch would otherwise violate spacing (today the move is simply
   rejected).
4. Strap/stub insertion on supply nets (the probe did this by hand).
5. Via insertion/removal for redundancy and R.

Placement moves are out of scope until a real router is in the loop.

## 6. Objectives

Implemented: supply gradient (R_eff spread feed→taps), Elmore-delay spread
across a set of nets with common driver R and receiver C, **fork balance**
(per-receiver Elmore on one net's RC tree, `rc.elmore_delays`), metal area.

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
  isomorphism check is a drop-in if a case ever needs it. Series stacks are
  hashed in series-parallel canonical form (§2, `compare.reduce_stacks`): a
  stack drawn as two parallel fingers with separate uncontacted middle nodes
  is the same netlist, as it is for KLayout's `combine_devices` in spirit.
- Delta-DRC: min width, spacing between different conductors, cut enclosure
  against the metal union — only *new* violations relative to the input
  layout count. The rule table is deliberately minimal; signoff is KLayout.
  A move that shorts two nets is seen by the topology guard, not by the
  spacing check (after the move they are one net): the two guards are
  complementary, neither is sufficient alone. Same-net spacing: two parts of
  one net that do not touch, closer than spacing, with the gap between them
  uncovered, are a notch (§2); moves fill the notches they make
  (`moves.fill_notches`) before the check. Rectangles that overlap or share
  an edge are one merged shape whatever nets they carry (a diffusion drawn as
  two slabs) and are never a spacing pair; cuts excepted.
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
- **L2 — standard-cell input — DONE (2026-09-07).** `lefdef.def2flat`
  builds the flat layout from LEF/DEF + cell GDS (`top/<inst>/<macro>`
  provenance); verified on a 12-cell two-row design, per cell against KLayout,
  and on a real OpenROAD place-and-route of `gcd` (784 instances, 2472
  devices, isomorphic to KLayout's independent extraction, §2). The first
  standard-cell move showed that sky130_fd_sc_hd cells have no internal
  whitespace to grow into: the payoff moves are L4's. Still to come: the ldx
  TH cells on SG13G2.
- **L3 — async objective — geometric half DONE (2026-09-05).** Fork-branch
  Elmore balance on a real RC tree, sized under the guard, with the verdict
  when sizing cannot close the gap (§2). Waiting on nulex for the path sets;
  completion-tree drive balance and a QDI-bound `VX_alu_int` slice follow.
- **L4 — dissolve for real — DONE for the finger move (2026-09-06/07).**
  `add_finger` grows a transistor into the neighbouring filler (supply or
  signal S/D), verified by re-extraction, the guards and KLayout; the discrete
  search uses it to balance two paths 25.9 → 0.4 ps; on OpenROAD's gcd it
  grows five of six candidate cells into real filler whitespace, nand2
  included, through poly, column or contact bridges; series stacks mirror
  whole (nand NMOS, legal on a bare row, guard made stack-canonical) (§2).
  Connections route around P&R wiring on li/met1/met2 (`route.py`): all six
  gcd candidate cells now take fingers, twelve in total, KLayout-confirmed.
  Same-net notch rule in the delta-DRC with a notch-fill pass after each
  move. `remove_finger` as the inverse (stock cells and added fingers alike,
  KLayout-confirmed on gcd). Two-edge driver model fitted from the Liberty
  (§2, §4) with slew; the balance probes cost both edges. P&R wires in the
  way of a connection are moved (cut and reconnected, §2). Vt flavour by
  implant (`set_vt`; Xyce-measured multipliers); gate length by stretching
  the cell at the gate (`set_gate_length`); switched capacitance as the power
  measure (`power.py`). Remaining: diffusion merge across abutting cells
  (needs compaction to pay), contact growth.
- **L5 — variation-aware acceptance — DONE for the fork (2026-09-06).**
  T2 (layopt MC over a stated variation model) and T3 (stat-sim's
  `statsim_pl_rc` runtime under nvc, MC via generics) agree: the sized li1
  fork passes, the unsized one fails (§2). Next: the flop side — stat-sim's
  metastable latch as the receiver, so a fork skew becomes an MTBF.

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
