# Nulex — Binding Selection Rule

This document formalizes `ASYNC-PLAN.md:29-49` — *"Every boundary in a design
carries an NCL-defined contract. Every boundary gets an implementation binding
... Different boundaries in the same design bind differently, and that is the
normal case, not a compromise"* — into a mechanical procedure with measured
thresholds, from the 2026-09 three-way campaign (CMOS / QDI / QAL /
bundled-data on IHP SG13G2 130 nm). The numeric basis lives in
`stat-sim/qal/` (memory of record: `threeway_gals_campaign`); the two
validation blocks are `sha_slice` (SHA-256 Maj+Ch+8-bit CPA, 105 generic
cells) and the Vortex `alu_top` (4,721 real cells + 5 `$scopeinfo` — the
circulated "4,726" counted scopeinfo). Whole-design calibration comes from the
full Vortex `mini` config run on hello/saxpy/sgemm
(`/home/claude/vortex_activity/*.tsv`, `/home/claude/vortex_static_char/`).

Every figure is tagged **[M]** MEASURED (file read or recomputed this
campaign), **[C]** COMPOSED-FROM-MEASURED, **[D]** DERIVED (algebra on
measured inputs; weak input named), or **[A]** ASSUMED.

Like ASYNC-PLAN.md, this is a working record, not a spec. Where the evidence
is one block deep, it says so.

---

## 0. Maturity — what can actually be emitted (evaluated before any scoring)

Of the five candidate approaches, **only two are emittable today**. Any
output selecting BD or QAL is a research recommendation, not a build
instruction, and must be printed as such.

| binding | tier | evidence |
|---|---|---|
| SYNC | T0 | full flow; `.sdc` (`nulex/mapper/alu/pnr/constraint.sdc`), placed netlists, VCD-driven power |
| QDI direct-threshold, combinational | T0 for cone support ≤ 4 | cells characterized (`nulex/asic/chr/th_cells_sg13g2*.lib`), layout (`nulex/lib/th_pdk/*.gds` + lef/lib); 151,584 vectors / 0 mismatches, 300 random-delay QDI runs / 0 failures [M] |
| QDI registers | T1 | emitter exists (`map_ncl_struct.py:243-280`) but costs 3W+(W−1) TH cells/stage = 751 cells for the ALU's 188 bits vs 188 DFFs; a 4-phase RTZ latch, not an edge-triggered register; no scan |
| DESYNC | T1/T2 | `--reg desync` targets VHDL only (`map_ncl_struct.py:233`); cyclic logic "out of scope" (`:342-343`). And `ncl_reg_desync.vhd:25` implements it as `en <= ncl_complete(d) after TCOMB` — **a local matched-delay clock, i.e. bundled-data**. The framework's only stateful-async route IS BD with a local clock. |
| BUNDLED-DATA | T2 | **no mapper exists.** `ASYNC-PLAN.md:459` plans `bindings/bundled.py`; grep over nulex finds nothing. All BD figures in this campaign are analysis of an unbuilt binding. |
| SRAM binding | T2 | `ASYNC-PLAN.md:460` plans `bindings/sram.py`; nothing on disk. Worse: the flow **lowers** memories (`synth_exec.ys:4` etc. run `memory_map`), turning a 256×8 into 2048 DFFs — 43.6× the macro's retention leakage plus a clock floor where the macro's is exactly zero. |
| ARBITER/MUTEX cell | T2 | grep for mutex\|arbiter\|metastab over nulex = 0 hits |
| QAL | T2 | no mapper, no cell library, no DFT concept, no P&R story for the 278 nH inductor; the zero-current detector has now been designed and MEASURED (`stat-sim/qal/zcd/`, 2026-09-27, skeptic-reproduced) and the result is a REFUTATION: a 3-stage armed SG13G2 comparator at ~120 µA/1.2 V (144.3–200.5 fJ full arm-detect-reset cycle) never resolves the true 74 µV/ps zero within the 342 ps beat — its only fires lock on the switch-OPENING transient ~431 ps late, useless for ZCS. Every measured QAL number still assumes a free, perfect, jitterless ZCS that this comparator class cannot provide (the ZCS decks drive the switch from an ideal PWL source); the surviving alternative, a per-bank calibrated predictive timer, is **now built and costed** (`stat-sim/qal/timer/` + `qal/sar/`, 2026-09-27, stat-sim 28dcece) and it does not rescue the arm: the timer hardware costs **399.8 fJ/hop** where the ideal-PWL decks booked 3.56 fJ, of which **302.8 fJ is per-bank taps that do NOT divide by B** → N_min 412–535, worse than the refuted ZCD's ≥221. QAL admission at SG13G2 hinged on one unmeasured thing — recovering the switch-gate charge — and that is now MEASURED too (`stat-sim/qal/recov/` + `skeptic/`, 2026-09-27, UNCOMMITTED, §3 G2b): stepwise-capacitive and switched-resonant and lower-VGH all FAIL outright, a **free-running multi-harmonic resonant network** does drive the gt/gtp taps for **2.974 fJ** with every completeness gate PASS, but the **park's real driver measures 15.0–15.5 fJ against a 9.77 fJ headroom** → complete ledger **17.911 fJ/bank/hop, N_min 69.2, fpsat-63 EXCLUDED**. QAL at SG13G2 is EXCLUDED, not open; the one untried thing is a resonant park tap |

---

## 1. Hard gates (eliminate; do not score)

**G-A — register CYCLES, not registers.** Run `pipeline_stages()`
(`map_ncl_struct.py:300-343`). ≥1 register cycle → pure 4-phase QDI illegal
(the `SystemExit` is at **:342-343**; the `:327-329` citation that propagated
through three reports is wrong). Zero cycles → QDI structurally legal as a
feed-forward pipeline. "Any block with state cannot be pure QDI" is too
strong: the Vortex ALU has 188 registers and **zero cycles** (stages
{0: 152, 1: 36}) [M]. Refinement from the whole-Vortex run: cyclic content is
a *fraction* — most islands are 1–8% cyclic (carve the cyclic core out for
desync); `mem_coalescer` is 84.5% and `schedule` 38.6% cyclic and must not be
QDI-pipelined at all [M].

**G-B — cone support, MAXSUP = 4.** For every PO and register-D cone,
support > 4 has no direct-threshold form (`map_ncl_direct.py:81`, enforced
`:483-486`) and falls to DIMS, which is strictly dominated [M:
`work/async_recost.json`, 524 cells / 6,972 fJ / 5,575 ps vs 113 / 2,712 /
2,533 on the same function] — and DIMS netlists as emitted **never ran** (616
constant-pinned hysteretic cells on `alu_dims.v` cannot return to NULL).
Threshold: cones over MAXSUP covering >10% of cell mass → QDI out for the
block. **Score support, never MUX count** (§4). ALU: 68.1% of register-D
cones exceed MAXSUP → QDI eliminated [M].

**G-C — non-determinism → SYNC, unconditionally.** Arbitration and
memory-response ordering: `ASYNC-PLAN.md:62-67` states sync-binding
verification does not transfer there, and no mutex cell exists. The block
that scores best on G-A/G-B is exactly the one already written down as
unverifiable.

**G-D — macro content → SYNC at the interface, unconditionally.** No SRAM
binding exists, and every energy number here is *cell* energy — the rule is
blind to bitcells and sense amps. Do not let it answer from the ~10% of a
macro block that is gates. Also: the SRAM has **no completion signal**
(`A_DLY` is a static trim, not a strobe), so even a fully QDI block cannot be
QDI at its memory boundary — the memory boundary is forced to matched-delay
or a small clocked domain.

**G-E — wire dominance → abstain, default SYNC.** All models are liberty
internal power + per-instance C_L. On interconnect-dominated blocks
(crossbar/shuffle, Rent p ≈ 1) the rule has no basis. Testable with
stat-sim's `klayout2spef.py` (`ASYNC-PLAN.md:95, :225`).

---

## 2. Quantitative discriminants

Four independent axes (graph topology, function support, level-profile
shape, workload), plus dependent scores:

| # | discriminant | crossover | conf |
|---|---|---|---|
| D1 | register-cycle topology | binary gate (G-A) | **M** |
| D7 | cone-support distribution | ≤4 viable; >10% mass over → QDI out (G-B) | **M** |
| D6 | level-profile shape (bush/tail) | knee where per-level population < N_min; tail = control path | **M** |
| D3 | duty / activity | α\* = (E_async − E_floor)/k; for a combinational block E_floor = 0 so α\* is undefined and clock-elimination buys nothing — the prize is proportional to *sequential fraction*, not cell count | **M** |
| D4 | QAL bank population | N_min = (39.6 + E_timing)/(h − 0.0361); per-hop ZCD MEASURED ≥ 144.3 fJ → N_min ≥ 221, and the hybrid tuned timer that replaces it MEASURED at 302.8 fJ/bank of taps → **N_min 412–535 as built**; switch-gate-charge recovery was the open lever and is now MEASURED (2026-09-27, §3 G2b): the resonant gt/gtp pair reaches 2.974 fJ with every completeness gate PASS, but the park's real driver costs 15.0–15.5 fJ measured against a 9.77 fJ headroom → **complete ledger 17.911 fJ/bank/hop, N_min 69.2, fpsat-63 EXCLUDED**. Note the level error: **η is load-referenced, E_timer is driver-referenced — "≤ 12.75 fJ ⇔ ≥ 71–74%" is NOT an equivalence** (as-built ratio 7.0×). Quote the fJ | **M/D** |
| D5 | QAL bank level-span | d_max = τ/4 ≈ 4.3 levels at RC_g = 20 ps — **the weakest derived input in the QAL branch**; RC_g is `qal_crossover_map.py:17`'s stated anchor, not a measurement (12 ps → 7.1; 30 ps → 2.9) | **D** |
| D8 | primitive mix | dual-rail 2:1 MUX = 8 TH cells/bit, proven minimal (§4); 4:1 MUX support 6 → no direct form | **M** |
| D9 | delay variance | harvestable only with completion detection *and* an elastic consumer; on zero-variance logic (maj/ch, 0.0–0.1% spread) a timing oracle is never worth paying for | **M** |
| D10 | boundary ratio ρ = E_island/W_boundary | QDI island needs ρ ≫ 124.7 fJ/bit — but see §5 provenance warning | **D/A** |
| D11 | burst length | amortizes **only fill+drain**; per-bank overheads are per-op (§3) | **M** |
| D2 | BD width/depth | W\*(D) = 7.98 + 1.23·D — a 9× extrapolation off one add8 fit, **no loop-latency term, invalid on cyclic topology**; do not apply where G-A routed the block | **D/A** |

Whole-design calibration facts the discriminants now rest on [M]:
chip duty 0.307/0.643/0.793 and per-bit α 0.0042/0.0080/0.0094 across
hello/saxpy/sgemm; per-block duty spans 0.0002–0.949 (4,700×) on one kernel —
no scalar stands in for it; 63 of 431 blocks ≥500 bits never wake in any
kernel and 67 live in exactly one (**coverage, not precision, is the binding
constraint**); duty rank does not survive a kernel change (Spearman
0.63–0.89; 38% of non-FPU blocks flip the duty<0.05 branch). The campaign's
invented α = 0.476 was white noise at duty 1.0 by construction
(`work/tb_slice.v`); as a switching activity it is 1.7–2.4× high, and the
correction moves CMOS **down** while moving no RTZ async arm at all — two
independent missing terms (external-load 2 fF [A], no interconnect model)
also biased the same way.

---

## 3. QAL admission — a levelization-shape test

Depth is nearly free (sustained throughput 1/342 ps = 2.924 Gop/s,
independent of D; fill amortizes at B ≳ 20). **Width is everything.**

**Step 2 (mechanical): levelize, find the knee, run the bank DP.** Never
evaluate bank population per level — min_i N_i is a property of the chosen
level→bank *partition*, a free variable with a cheap exact solution
(contiguous-run DP maximizing min bank under a level-span cap d ≤ 4). The
per-level reading is what misread the ALU twice. Measured fact with general
force: **the deep tail of a real functional unit is its control path, not a
carry ripple** — the ALU's deepest 22 cells are two 2-wide lanes of
reduce-OR→NOT→AND→MUX→…→clock-enable unmapping, 2 cells wide for 7 levels
because tail width is the number of independent control signals. Control
paths are structurally QAL-hostile in every block; they are also narrow and
therefore cheap to cut off (§5C).

**G1 — margin (no CMOS number; absolute feasibility).** At dV = 1.0 [M:
`qal_bankN_sqrtN_analysis.json`]: rail σ = 15.45 mV at N=8, clean 1/√N;
worst-case endpoints scale-invariant (e0 0.632 / eN 0.544 V); cliff 0.500 V
[A] → budget 82.7 mV. Per-hop droop at the real w=10 µm switch is 13.6% [M:
`qal_trackC.py:12-17`], so **K = 1 (top up every hop) is mandatory** — K=2
spends 79 of the 82.7 mV. That kills the K-amortization the energy model
wanted. → N ≥ 20–48 for one hop of 3σ headroom; hops survived scales
linearly with N.

**G2 — amortization, with a measured ZCD-independent floor.** Per-bank
per-hop overhead fits Ov(N) = 39.6 + 0.0361·N fJ [D from two measured points,
`qal_pulse_topup.json` K=1]. Break-even N_min = (39.6 + E_ZCD)/(h − 0.0361):

- generic-gate basis (h = 0.867 fJ): **N_min = 48 at E_ZCD = 0** — the floor
  that survives the comparator going to zero; 84 / 168 / 409 at
  30/100/300 fJ.
- stdcell basis (h = 2.800): 14 / 25 / 51 / 123. The 56-vs-105 gate-count
  basis is a ±1.9× ambiguity on the QAL logic term; use the generic basis.
- **E_ZCD is now MEASURED, not assumed** (`stat-sim/qal/zcd/RESULTS.json`,
  2026-09-27, pre-registered bands, skeptic-reproduced in full incl. the
  bank DP by brute force): the cheapest full arm-detect-reset cycle of a
  real SG13G2 comparator on the committed hop is **144.3 fJ — and it never
  fires on the true zero** (energy of a NON-functional detection); the
  configuration that does fire costs 200.5 fJ and locks on the
  switch-opening transient (~431 ps late, sense-size-independent), useless
  for ZCS. Generic basis: **N_min ≥ 221** (≈289 at the fired
  configuration). The former working/confident thresholds (50/150) and the
  **50–400 UNDECIDABLE band are RETIRED — every block parked in that band
  resolves to NOT ADMITTED** and no block's verdict improves. The rider
  outranks the arithmetic: no functional per-hop zero-current detection was
  achieved at ANY energy in the old 30–300 fJ band — **per-hop analog ZCS
  tracking is refuted for simple continuous comparators** at 0.13 µm/1.2 V
  against the 74 µV/ps signal (failure is DELAY, ≥538 ps vs the 342 ps
  beat, GBW-limited at gm/C ≈ 2.5e10 /s — offset never even binds). The
  surviving alternative is a per-bank calibrated predictive timer: it
  abandons per-hop tracking, leaves the 61.6 ps/16.9% data-dependent t_zcs
  spread uncorrected (energetically cheap — the committed record itself
  opens every hop 50 ps late at I=−100 µA with E_hop still 10.74 fJ — but
  a level/settling-margin cost), and its energy is unscoped. Switch–ZCD
  coupling (skeptic): the tg15p switch optimum steepens the sensing signal
  5.1× [M: −376 µV/ps, R_eff 179 Ω], relaxing the ±20 ps true-zero offset
  need from ±1.48 mV to ±7.5 mV (marginal, no longer hopeless) — but the
  delay refutation stands, and if tg15p's per-gate number feeds h then
  N_min(144.3) ≈ 163 [D] — no verdict flips either way.

**G2b — the hybrid tuned timer: BUILT, COSTED, and the cost is now the whole
verdict** (2026-09-27; `stat-sim/qal/timer/README.md` + `RESULTS.json`,
`stat-sim/qal/sar/RESULTS_SAR.json`, both committed at stat-sim 28dcece).
The user's architecture decision replaced per-hop detection with *"a
pulse-width generator you tune occasionally on just a representative piece of
logic, rather than ZCD everywhere"* — which dissolves the ZCD refutation by
construction (calibration is offline and repeatable, so detector delay is
irrelevant and detector energy amortizes). It is now the FIRST deck in the
campaign whose switch gates are driven by transistors instead of ideal PWL
sources — the bookkeeping hole every previous QAL number carried.

- **The mechanism works.** Tapped `sg13g2_inv_1` line + NAND pulse gate +
  three taps (gtp/gt/pk) lands the tuned window at 269.84 ps against a
  271.5 ps target with both completeness gates PASS: VBEND **0.6846**
  (+1.3% of the ideal-drive 0.6759), VA_open 0.108 (rail drains),
  E_hop_open **8.109 fJ** — **−3.3%** vs the ideal-drive 8.383 and **−24%**
  vs the tg60 ring-robust 10.69 anchor, so the tg15p switch win survives
  real edges [M]. **ATTRIBUTION CORRECTED (verify round, 2026-09-27,
  `qal/timer/verify/`): the −3.3% number is right but it is NOT a better
  transfer** — 81% of it is the E_sup_static(VBEND) subtraction, i.e. charge
  the timer *delivered* into bank B (2.03 fC arriving, 0.317 fC surviving,
  now metered with 1 Ω ammeters, books closing three independent ways).
  Bank A's actual expenditure EA_C is FLAT: 17.762 vs 17.814 fJ = **−0.29%**,
  and ±0.4% across the whole valid mistiming map. Read it as "real edges cost
  bank A nothing measurable", not as a transfer win. Cut ORDER is a hard
  constraint, not a preference: pMOS
  (gtp) early-or-with, nMOS (gt) at the tuned zero, park AFTER the nMOS cut.
  v1 got it backwards (nMOS first) and FAILED completeness — the LC rang to
  −70 µA through the still-on pMOS, un-transferring the rail (VBEND 0.651),
  and burned 508 fJ [M, recorded in `tl_hop.json`].
- **Slow gate edges are BENIGN** — the real stdcell edges (30.5/16.3 ps)
  cost only −3.3% E_hop, and the damage they do lands on the *sending*
  bank's post-transfer ring ("bank A's corpse", V(bka) pk-pk 0.29 → 0.71 V)
  not on the delivered payload (V(bkb) ripple after park **2.1 mV**, vs
  47 mV post-open excursion in the ideal run) [M — but those two figures mix
  definitions; at matched definitions (verify round) it is 4.07 vs 49.14 mV at
  park+5 ps and 0.65 vs 28.41 mV at park+20 ps, which makes the conclusion
  *stronger*, not weaker]. Tap drivers therefore do
  not need to be fast, which is precisely what admits the slow-by-nature
  recovery drives below.
- **Calibration is essentially free — with one named exception.** SAR loop of
  18 trial hops / 14 decisions, E_cal ≈ 1.5 pJ/event [D design point, band
  0.7–4.0 pJ; the trial-hop energies 8.25–9.92 fJ are M], amortizing to
  ≤ 0.3% of the 0.8309 denominator at 10 kHz / B = 8 / full duty [D]. The
  user's "tune occasionally" half is vindicated. **Exception — dark
  silicon:** overhead scales as 1/duty, so at duty ≤ 1% and 10 kHz it is
  0.27 fJ/hop = 33% of the denominator. That corner (the SNN / dark-silicon
  workload) must **calibrate on wake**: one event per burst, < 0.03 fJ/hop
  over a ≥ 10⁴-hop burst [D]; wall-clock drift only matters when a bank is
  about to fire. Also measured: a *designated real bank* beats a replica —
  the replica needs its own 277.8 nH inductor (the architecture's scarcest
  component) and transfers ±2–4 ps of L/C mismatch the real bank never sees.
- **THE COST: E_timer = 399.8 fJ/hop = 302.8 per-bank taps (gt 118.0 + gtp
  109.8 + park 75.0) + 97.0 line + 5.4 trigger** [M] — **and that is the
  SINGLE-SHOT figure. CORRECTED (verify round, 2026-09-27): per hop in steady
  state it is 633.3 fJ, +58%** — the committed deck's trigger rises once and
  never returns, so the line/park RESET every subsequent hop needs is
  unmetered (line 97.0 → 269.8 fJ, ×2.78, because CTRIM's two 12.5 fF caps sit
  on same-parity nodes so the metered half is the cheap one; park 75.0 →
  135.3 fJ, ×1.80; gt/gtp are complete inside the window and stand). Admission
  on the full cycle: **N_min 485 (B → ∞) … 812 (B = 1)**. Also note the split
  sums to 405.2, not 399.8 — the total excludes the trigger rail.
  The line and trigger
  are shared by every bank on the chain; **the taps are not, and the taps
  ARE the cost** — so the hoped-for "one shared line collapses N_min back
  toward 48" is **RETRACTED**. Admission as built,
  N_min = (39.6 + 302.8 + 102.4/B)/0.8309 → **412 (B → ∞) … 535 (B = 1)**
  gates/bank, i.e. **worse than the refuted ZCD's ≥ 221** [M/D]. The
  ideal-PWL decks booked **3.56 fJ** for these same drives: ideal sources
  RECOVER the CV² a real driver dissipates, and that hid two orders of
  magnitude. The hybrid beats ZCD on *mechanism*, not (yet) on energy.
- **The layered timing stack** (the user's design; each layer now carries its
  own evidence). **STRUCTURE = the tapped line** [M]: 29.43 ps/stage at
  1.5 V, CTRIM cap-DAC linear at 2.06 ps/fF, achievable widths odd
  stage-multiples with the DAC covering the gap; two SAR iterations landed
  269.8 ps on a 271.5 ps target. **TRACKING = same-die co-drift** [M, and it
  **FAILS in magnitude**]: the hop zero is LC-governed (+0.74% at 85 C) while
  the line is RC-governed (+10.23%) → **tracking ratio 16.4 cold / 13.9
  hot** — the line is a replica of gate RC, not of the zero. Only the SIGN
  saves the architecture: heat lengthens the width = LATE = the
  measured-benign direction (≈ +24 ps ≈ −7% E_hop at 85 C, VBEND fine),
  cold shortens it = EARLY = the bad direction (≈ −14 ps at 0 C ≈ −1.8%
  VBEND). Drift 0.46 ps/K, so ±16 K between calibrations holds the
  measured-benign ±7.5 ps residual. **CORRECTED (verify round, 2026-09-27):
  the ratio reproduces to the digit (16.414/13.893; 16.09/13.91 on a refined
  0.1 ps grid) and the instance-DTA path is now controlled (a never-run GDTA=0
  control at 27 C is bit-identical to the plain shim, and all 11 compiled .so
  carry the offset), so the ratio is temperature and not a compile artifact.
  But "VBEND fine at 85 C" is WRONG: the n9 reference rows sit at +2.39%
  (27 C) and +3.77% (85 C), OUTSIDE the pre-registered ±2% band — read it as
  "VBEND high, out of band, and 75% of that −7% E_hop is the E_sup(VBEND)
  subsidy term". Widths and zeros are timer-only observables and stand. Also:
  "late stays benign" is supported only to ≈ +7.5 ps, NOT to the +66 ps
  mistiming row — that row's deck carried a SUPERSEDED 5-stage park chain
  (park 22 ps BEFORE the nMOS cut), and the corrected 7-stage re-run still
  FAILS the drained-rail gate (VA_open 0.224): at +66 ps the reverse current
  takes charge back into bank A, so the apparent cheapness is an unfinished
  transfer. And every swsweep "true zero" carries a **+1.1 ps quantisation
  bias** (first-sample-past vs interpolated extraction; 1.5× the cold shift
  being measured), harmless only because one convention is used throughout.
  Uncorrected data spread: **±3σ at N=128 is ±8 ps, not ±5.8** (the original
  8-word sample under-dispersed; 16 words and the analytic |dt/da|·σ_a agree). Consequence for the flow: calibration
  must measure the **hop** observable (SAR on the bank rail), never trust the
  line as a replica of the zero. **TRIM = FD-SOI back-gate body bias,
  DEFERRED to the GF FDX target and explicitly NOT built at SG13G2** (the
  user's call): structure/tracking/observable/SAR transfer, the fine-trim
  actuator does not.
- **Why the deferred trim is also the largest deferred upside:** the FD-SOI
  back gate is the SAME knob that moves the measured **Vt cliff**. The
  lowest-energy *and* fastest QAL operating point is dV = 0.6 V —
  **0.326 fJ/gate-settle at a 325.9 ps hop**, versus 0.429 fJ / 367.5 ps at
  dV = 0.8 — but dV = 0.6 is functionally INVALID on SG13G2: the bank rail
  reaches only 0.382 V against Vt ≈ 0.4 V, so the pMOS never turns on and
  the gate settles to 64% of the rail (97.6% at dV = 0.8) [M:
  `stat-sim/qal/qal_bodybias.py`, committed]. A device threshold, not the
  energy target, is what forces the higher swing, at 1.3× the energy and 13%
  of the speed. Lowering Vt with a back gate re-opens the dV = 0.6/0.8
  operating points on FDX — **the largest deferred QAL upside in the
  campaign** [A for the FDX magnitude: nothing on FDX has been measured
  here; the SG13G2 bulk switched-cap body-bias probe moved settling
  64% → 90–97% but its energy bookkeeping did not close and is not quoted].
- **THE OPEN DECISION, pre-stated before any recovery deck ran**
  (`stat-sim/qal/recov/PRE_REGISTERED.json`, 2026-09-27 —
  **UNCOMMITTED** as of this edit; the numbers it anchors on are committed in
  `qal/sar/RESULTS_SAR.json` and the on-disk `qal/swsweep/sw_tg15p_z.cir.mt0`
  integrators). The dominating term is the switch-gate drive itself:
  **29.0 fC of tg15p gate charge per hop** (Q_gt close 10.50 fC + Q_gtp open
  16.38 fC [M, committed integrators] + park ≈ 2.1 fC [D, width-scaled]),
  which a conventional CMOS tap driver from the 1.5 V rail burns as
  **43.5 fJ/bank/hop** — that **admits NOTHING at any chain length** — while
  the ideal-recycling floor of the same gates is **3.56 fJ** [M].
  **Re-measured (verify round, 2026-09-27): 29.88 fC → 44.82 fJ, with the park
  term now MEASURED at 2.193 fC instead of width-derived; implied C_gate
  19.92 fF. `RESULTS.json`'s "switch_gate_CV2_floor 55.3 fJ" rested on an
  ASSUMED 24.6 fF geometric estimate, 23% high — the measured floor is
  44.8 fJ.** The threshold re-derived against measurement is η ≥ 71.5%, so the
  handed-down ≥71% stands. Per-gate ideal-source decomposition: gt **−2.993 fJ
  (the ideal source REABSORBS the discharge — a topology property, reproduced
  in two independent re-runs)**, gtp +3.880, pk +2.664, sum 3.551 ≡ the
  3.56 fJ floor.
  **PRE-STATED LINE, not to be moved: the fpsat_fma min-bank-63 block flips
  EXCLUDED → ADMITTED iff E_timer ≤ 12.75 fJ/bank/hop, i.e. gate-charge
  recovery ≥ 71–74%** (line-share dependent, B ≥ 8; 63 × 0.8309 − 39.6 =
  12.747 fJ, so the line is the *arithmetic* of the N_min formula, not a
  taste). Under §3's own per-gate-scaling rider — the switch must grow with
  the bank, so the tap term moves into the DENOMINATOR — the bar rises to
  **≥ 96.7%** and gate-drive recovery becomes existential rather than a
  tuning knob [D]. Three candidate mechanisms are being measured and are not
  exclusive: **resonant LC gate drive** (architecturally the prize, because a
  resonant network is clock-like — every bank hops on the same beat, so ONE
  network could serve all B banks' switch gates and divide the tap cost by B
  exactly as the line already does — but it needs inductors, the scarcest
  component in the σ0 architecture, and loss ≈ π/Q means ≥ 71% needs
  Q ≳ 11, which is an ASSUMPTION at SG13G2, not something any deck here
  measures); **stepwise capacitive charging** (≈ 1 − 1/n recovery with
  capacitors only, no magnetics and no Q question, but the step switches have
  their own gates and they must be counted at the conventional rate — the
  exact sum-of-pieces error this campaign has already paid for); and **lower
  VGH** (CV² ∝ V² against a Vt-set overdrive floor: voltage alone would need
  VGH ≤ 1.5·√(12.75/43.5) = 0.81 V, below the 1.0 V bank + Vt the nMOS must
  pass, so it is a multiplier on the other two, not a mechanism [D]).
  **Until one of them is MEASURED at ≥ 71% with a closed ledger and the
  completeness gates intact (VBEND in band, rail drained, all 8 cells
  settled, E_hop_open still ≈ 8.109 fJ), QAL admission stays CLOSED at
  SG13G2. If none clears, that CLOSES the QAL question at this node** — a
  negative result of record, not an open item.
- **THE DECISION, MEASURED AND CLOSED FOR THE THREE MECHANISMS AS BRIEFED
  (2026-09-27, `stat-sim/qal/recov/` + `qal/recov/skeptic/`, UNCOMMITTED).
  The line is NOT cleared: best complete measured ledger = 17.911 fJ/bank/hop,
  η 58.8%, N_min 69.2 → fpsat_fma min-bank-63 stays EXCLUDED.** [M]
  - **M3 lower VGH: admits nothing and breaks first.** CV² measured ∝ V^1.86
    (not V²); the lowest completeness-passing row is VGH = 1.5 V, VBEND leaves
    its band at 1.20 V and E_hop_open leaves ±5% already at 1.35 V — far above
    the 0.81 V the arithmetic demanded. A ×0.84 multiplier bought for a +5.8%
    E_hop penalty on the same ledger, i.e. ≈ zero. It is a constraint, not a
    lever. [M]
  - **M2 stepwise: dead by 3× even idealised.** Measured n=2 → 121.98 fJ, n=4
    → 183.36 fJ (η −180% / −322%): the step switches' own gates (57 → 105 fJ)
    and their hold-switch Miller traffic (60–72 fJ) dwarf the 1 − 1/n saving.
    residual/CV² = 1/n + 2ατn²/T_edge with τ_TG = **1.884 ps MEASURED** (the
    pre-registered estimate was ~3 ps) ⇒ n_opt ≈ 2 and **no n wins**. Analytic
    best case with every measured overhead idealised away = 38.995 fJ, η 10.3%,
    N_min 94.6 — still 3× over the line. The sum-of-pieces trap, paid again. [M]
  - **M1 switched resonant (real freeze TG + clamps): dead, −69.7% measured**
    (73.79 fJ min-width, 389.73 fJ at 5/10 µm — cost linear in W). The freeze
    switch is a **B-invariant recursion**: its width tracks the load it drives,
    so its gate charge tracks too and never amortizes over B. Its analytic
    optimum (28.06 fJ, η 35.5%) needs R_opt = 1827 Ω, which **exceeds the
    cut-order limit** — the optimum is not even reachable. [M]
  - **M1 free-running resonant: the one real result, and it is a PART, not a
    timer.** A multi-harmonic (Σ_{k odd ≤5} sin kθ/k) free-running network with
    NO per-edge switch drives the gt/gtp taps for **2.974 fJ net** with the
    ledger closed to 1e−12, independently re-metered by a trapezoid path that
    never touches the 1F instrument (0.19%), the transfer intact (bank A's own
    expenditure EA_C −0.22% vs ideal) and **all five pre-registered gates PASS
    at the pre-registered checkpoint** (VBEND 0.6844, VA_open 0.0916 — better
    than the committed 0.0978 — E_hop_open 8.130 fJ = +0.26%, 8 cells settled,
    cut order pMOS +1.8 ps / park +30.8 ps). A plain sinusoid FAILS (its
    quarter-period fall leaves the nMOS conducting when the park pulls sw to 0
    and bank B drains, 0.703 → 0.527 V); the harmonic waveform was designed
    mid-round and is therefore **post-hoc, tested against pre-registered
    gates** — weaker than a pre-registered prediction. The architectural prize
    is real: Q = 1/(ωC_net R) is **B-invariant** when B banks share one network
    (R/B against B·C_net), so sharing buys a realisable L without making Q
    harder — 3 modes, **3–4 inductors chip-wide**, L₁ = 5.9 nH at B = 64 with
    shared series R ≤ 8.4 Ω. Required **Q ≥ 7**, set by the **CUT ORDER** (the
    gtp tap RC-lags, so large R makes the pMOS cut late — the v1 failure), not
    by energy (energy alone would allow Q ≈ 2.4). The inductor is IDEAL in
    every deck; **no SG13G2 metal Q is measured anywhere** [A]. Costs measured:
    **8.6% beat penalty** (580 vs 534 ps), gate–bulk stress −1.84 V on a 1.5 V
    oxide (+23%, unpriced), and a fixed phase advance of 3–9 ps on gtp that
    ±2 cells of data swing consumes 4.9 ps of.
  - **WHAT KILLS IT: the park's driver.** The round booked the park at
    Q_pk·VGH = 2.40 fJ from an IDEAL PWL step. Measured floor for a real one —
    ONE minimum sg13g2_inv_1, zero junction capacitance, free ideal input, no
    delay chain, phase assumed free — is **15.0–15.5 fJ** against a **9.77 fJ
    headroom**, and it is robust to the input edge (15.48 fJ at 0.5 ps vs
    15.02 at 130 ps) and the window (0.3% over 400 ps). It brackets correctly
    inside the campaign's own two independent per-stage figures (FO1 at 1.5 V
    9.87 fJ; as-built park tap 135.29/7 = 19.33 fJ). **Even the cheapest of
    those, 9.87 fJ, gives E = 12.843 fJ and N_min 63.12 — still past the
    line.** No park-driver figure anywhere in this campaign fits the headroom. [M]
  - **THE LEVEL ERROR, and it is in the brief's own wording.** "E_timer ≤
    12.75 fJ/bank/hop, **i.e.** recovery ≥ 71–74%" is FALSE as an equivalence.
    η is **load-referenced** (against Q_gate·VGH = 43.5 fJ of gate charge);
    E_timer is **driver-referenced** (what the timer hardware draws from its
    supplies). They coincide only if a driver costs what the charge it delivers
    costs — the campaign's own as-built ratio is **7.0×** (302.8 fJ of driver
    for 43.5 fJ of load). **η ≥ 71% was cleared (87.9%); E ≤ 12.7467 fJ was
    not.** Quote the fJ, never the percentage, in any admission statement.
  - **The per-gate rider is refuted mechanism-independently**: the ideal-PWL
    floor of 3.5627 fJ ⇒ **η_max = 91.8% at SG13G2**, and the rider needs
    96.7%. No drive scheme whatsoever clears it. That branch is CLOSED. [M]
  - **Still unbooked in BOTH ledgers** (pre-existing, not M1-D's fault): the
    VHI 1.5 V pMOS-bulk rail at **4.31–4.49 fJ/hop** = 35% of the whole budget;
    `grep` finds no EHI/VHI in any committed README or RESULTS.
  - **The one open door, and it is narrower than either round said.** Nobody
    has measured a **resonant park tap**. If the park could ride the same
    free-running network at gt/gtp-like cost (~1.5 fJ) then E = 4.474 fJ,
    N_min 53.0 and the block ADMITS — but the park must HOLD a DC level through
    the hold phase and then cut, which is the one waveform a resonator is worst
    at. Two riders [D, this report's arithmetic on their measured numbers]:
    (i) the **sustaining amplifier** break-even is **η_amp ≥ 35.1%** (zero DC
    bias) to **≥ 44.6%** (worst-case 2.71 fJ bias), NOT the round's "≥ 27.7%" —
    that figure was computed against the 5.273 fJ headline that omitted the
    park driver. (ii) **Lowering the park rail alone does not rescue it**: the
    park is an nMOS to ground and needs no 1.0 V-bank overdrive, so its gate
    could run below 1.5 V, but the measured V^1.86 law requires **V_park ≤
    1.19 V** merely to fit the headroom, and at V_park = 1.0 V with a 50% amp
    and the bias paid E = 15.7 fJ, N_min 66.6, **still EXCLUDED**. Until the
    resonant park tap is measured, **QAL admission at SG13G2 is EXCLUDED, not
    open.**

**Admit QAL iff** (i) best min-bank of the *bush* ≥ N_min under d ≤ 4;
(ii) the tail is excisable at affordable cut width (§5C); (iii) the workload
is streaming — a latency-bound serial recurrence disqualifies outright
(`qal_crossover_map.py:20-21`: the entire QAL speed win is register-tax
elimination), and QDI early completion is unbankable without an elastic
consumer.

**Burst length is the wrong variable.** A full wave pipeline accepts an op
every beat, so switch, top-up and ZCD fire per op per bank
(`qal_pulse_topup.py:31-34`); B amortizes only fill/drain. And a whole-Vortex
correction: the switch must grow with the bank to hold transfer loss fixed,
so **switch cost is per gate, not per bank** — the ALU-rung composition shows
naive per-gate energy (1.343 fJ × cells) undercounts ~3× (wp-weighted logic
17.1 pJ vs naive 5.4 pJ on the ALU), with a switch-tax band of 0.7–26 fJ/gate
depending on gate-drive recovery. This post-dates the Step-6 arithmetic below
and erodes its margins; treat every QAL total as carrying that band.

**Switch sweep (2026-09-27, `stat-sim/qal/swsweep/`, pre-registered,
skeptic-verified — all 14 rows recomputed from raw mt0s, 0 mismatches; the
tg15p re-run bit-identical):** the committed 60 µm TG is far oversized. At
the iso-current point E_hop_open falls **monotonically** with TG width —
11.31 / 10.66 / 9.6 / 8.4 / 7.5 fJ from 120 down to 7.5 µm total; there is
**no interior W-optimum in range** (conduction loss never bites, ~0.05 fJ
flat). The shrink is stopped by rail-drain completeness (VA_open 0.003 →
0.162; the committed anchor itself leaves 0.095, 7.5 µm fails it) and,
below ~30 µm, by post-open ring — a 1 µm parking nMOS with its own control
phase is REQUIRED there. Constrained optimum **tg15p** (TG 5/10 µm + 1 µm
park, 16 µm total): E_hop_open **8.38 fJ = −21.6%** vs the ring-robust
10.69 fJ anchor, and **−8.4% on the beat** (true zero 266.8 vs 291.3 ps —
the zero moves earlier as the switch shrinks, so energy AND speed improve
together; the switch is a third co-design variable beside L and dV).
Per-gate-settle at the optimum: **1.048 fJ/gate** (conservative tg30p:
1.195) — carry three qualifiers on any use: (i) delivered at VBEND 0.676,
not the committed 0.576 (a one-sided completeness reading; by the
pre-registered two-sided band the strict optimum is tg60 and **1.343
stands as the committed-swing anchor** — the iso-swing retune was NOT
measured, though the co-design direction is favorable); (ii) cells burn
1.70 fJ at that swing (swing physics, inside the total); (iii) ideal-rails
bookkeeping — tg15p imports +7.9 fJ/hop of park drive-rail energy,
excluded by the same convention that excludes the committed design's
−14.5 fJ export; without recycling drive rails the win shrinks and can
invert. nMOS-only (all widths) and 2:1 reduced-pMOS TG topologies **FAIL**
(rail never drains / feedthrough pump — their low E numbers are artifacts).
Two corrections to the committed record itself (amendment A2,
skeptic-confirmed): the committed t_zcs = 342.0 ps is the true zero
(291.3 ps) **plus a +50 ps late-open artifact** — benign only at 60 µm,
whose own ~55 fF parks the interrupted-current ring (the convention does
NOT transfer to smaller switches, though the tg15p park restores graceful
+50 ps behavior, −0.9% E_hop [M]); and the ring-robust restatement of the
committed anchor is **E_hop = 10.69 fJ** (vs 10.81 D-snapshot; 1.336
fJ/gate).

**Report QAL as a triple, never energy-at-single-op-latency:**
(E_op^sustained, Θ = 2.924 Gop/s, t_fill = D_banks × 342 ps). Retire
"136.8 fJ @ 3.42 ns" — that was logic+path only (with overheads 841–3,541 fJ
[C]) at a pipeline-fill latency compared against a combinational delay.
Also: **QAL's power clock is a clock.** It does not escape the clock floor at
low duty; it renames it.

**Hurdle rates** (calibrated from this campaign's own error record — six
standing numbers corrected): BD ≥ 1.3× sync, QDI ≥ 2×, QAL ≥ 3× (the ZCD
band is no longer assumed — E_ZCD measured ≥ 144.3 fJ, and per-hop ZCS
itself is refuted; see G2 — and its replacement, the hybrid tuned timer, is
measured at 302.8 fJ/bank of non-shareable taps, see G2b). Tie-breaks in order: (i) testability — QDI faults
deadlock (undiagnosable, no scan/ATPG, the project's own certificate
mechanism); QAL has no fault model at all; (ii) assumption discharge
(`ASYNC-PLAN.md:115, :127-134`): refuse any binding whose assumptions have no
named discharger — BD's matched-delay margin has none in this flow, so BD
must either lose here or adopt the current-sense early-out to become
self-timed (its real value: closing the signoff gap — and note the current
sensing comparator is now measured at 144.3–200.5 fJ/cycle and cannot
resolve a µA-scale zero inside a ~342 ps window; any BD early-out claim
must budget that class of detector honestly); (iii) maturity tier.

---

## 4. The dual-rail sub-decision

Dual-rail is never a free-standing optimization: a **consequence** of QDI, a
**penalty** under QAL, a **converter question** everywhere else.

- **QDI: mandatory** — it *is* the completion mechanism. Cost is a
  support-size question, not a mux question: ~1.1× cells on XOR/AND/carry
  logic (113 TH for 105 generic gates [M]); the 2:1 MUX is 8 TH cells/bit and
  that is **proven minimal** (exhaustive search over ≤2-cell networks of the
  7 characterized cells and the full 11-cell library: zero input-complete
  forms; every input-complete form must observe s, a AND b); nothing above
  support 4. Do not score "MUX-dominance": the generic MUX census is
  script-dependent (1,957 vs 947 on two synths of the same RTL) and CMOS
  tech-mapping absorbs muxes into AOI cells while dual-rail cannot — the
  penalty is real even when the mux count looks small.
- **QAL: never.** Dual-rail measured harmful (246–274 vs 136.8 fJ logic-only
  — the difference between beating CMOS on the logic term and losing). The
  data-dependent-charge argument for it rests on an N=1 ideal-cap deck; at
  bank scale modulation is 2.0–2.7%, σ follows 1/√N, worst-case endpoints
  are scale-invariant and above the cliff → amplitude stability imposes **no
  floor on bank population**. Caveats: Vt = 0.40 V and the 0.50 V cliff are
  the project's own estimates [A]; single-rail rests on K=1 discipline, not
  slack; revisit below N=8.
- **Sync/BD: single-rail by definition**; dual-rail appears only as a
  converter at a QDI boundary.

There is no block for which dual-rail is an independent optimization.

---

## 5. GALS islands — what binds between, and how big

**(A) Between islands: bundled-data handshakes over single-rail data** (or
sync-to-sync with 2-FF synchronizers). QDI lives strictly inside an island;
QAL never crosses one — it is a burst mode entered and exited through the
island's own registers. A sync island boundary already pays a register:
28.2 fJ/bit/cycle (add8 anchor) to 118.3 fJ/bit/cycle (placed ALU: (13.523 +
8.719) pJ / 188 bits) [M] — so the marginal cost of sync↔BD or sync↔QAL at an
existing boundary is ≈ 0. **Only QDI changes encoding**, and only encoding
changes cost.

**(B) Size.** QDI domains must be very large or not exist: ρ ≫ 124.7 fJ/bit
fails on both measured blocks (sha_slice 3.2, ALU 98.4 fJ/bit); under Rent
p = 0.6 [A] a <20%-converter QDI island is ~460k gates — a whole GPU core.
(Anti-correlation warning: for a crossbar p ≈ 1 and bigger never helps —
which is why G-E is a gate.) Sync/BD/QAL mix freely at functional-unit
granularity, because no encoding changes — this is what makes a per-block
rule exist at all.
**PROVENANCE WARNING:** the 52.6/72.0/**124.7 fJ/bit** converter figures have
**no deck on disk** — three independent passes failed to find one. They are
internally consistent and plausible against the measured register anchor,
but plausible is not provenance. Re-measure (a 4×4 adapter matrix, diagonal
included) before using the island-size answer for anything (§8).

**(C) The affordable within-block cut is datapath-vs-control.** ALU knee at
level 25: bush 4,452 cells (98.2%), tail 81 cells, cut width **105 nets** [M]
— both sides single-rail, so the cut costs a latch, not an encoder. Rule:
QAL banks over the datapath bush; control path stays sync.

**(D) Partitioning:** seed from the existing island partition; **merge only**
(monotone and safe); the one permitted split is (C); forbidden to repartition
anything UPF/CTS/floorplan already fixed. The block-level answer is only the
unary term of a ≥3-label multiway cut (APX-hard) — say so. Whole-Vortex
measurement strengthens coarse partitioning: the core (249k cells) meets the
chip through 1,928 bits while `execute↔issue` alone is 1,897 bits; splitting
execute into 4 units added only +0.7% cut bits (a shared broadcast bus) —
**price partitions by measured cut bits, never island count**, and check
whether a wall cuts a broadcast (cheap) or a datapath (expensive). Ack-less
sidebands (`branch_ctl_if`, 668 bits, no handshake to convert) are partition
constraints. Store per-block (busy, toggles, burst histogram) plus one global
T(binding vector) and compute duty = busy/T — never store duty; that removes
the self-inconsistency of characterize-then-rebind without iteration (busy
and toggles are invariant to ~2% under a re-binding perturbation; duty moves
13% purely through T).

---

## 6. The low-duty / SNN regime (mostly-asleep, memory-triggered nodes)

**Verdict: SYNC — clock-gated from a shared cluster clock, logic
power-gated, all retained state in the SRAM macro; the memory handshake is
matched-delay regardless. QDI is the worst option; QAL is disqualified.**

- The energy balance is not about logic: a 256×8-SRAM + ~250-cell node spends
  **95.7% of active energy in the memory** (23.71 pJ vs 1.07 pJ logic) [M:
  SRAM liberty internal_power], and below t\* = E_active/P_idle ≈ 420 µs
  (≈2.4 kHz) idle leakage is 96–99.96% of per-event energy. **Below t\* the
  rule becomes a transistor-count comparison** — QDI+CD is 3.90× the devices,
  leaks 3.90×, and "no clock" repays nothing because the clock was gated to
  zero. Above ~24 kHz per-op energy rules again; the ranking inverts inside
  the candidate duty range, and the workload's actual rate has never been
  measured — pin it before more circuit work.
- **QDI cannot be power-gated**: node X is held only by long-L keepers, no TH
  cell has a reset pin (`th22.sp:37-38`; grep = 0 hits;
  `ASYNC-PLAN.md:489-490` marks it Blocking, §10). The leakiest binding is
  denied the biggest lever. Claim the post-restore *indeterminacy*, not a
  power-up direction.
- **State in SRAM, datapath stateless**: retention 12.09 pW/bit vs a DFF's
  526.5 pW/bit — **43.6×** [M]. SG13G2 ships no retention flop and does not
  need one.
- **Design rule**: the SRAM's dynamic draw is exactly zero only with
  `!A_MEN & !A_WEN & !A_REN` (`values (0)` [M]); partial deselect costs
  0.296–0.985 pJ/edge. Drive all three low to idle.
- **The wake-up discriminant is the clock SOURCE, not the tree**: share an
  always-on cluster clock and gate distribution locally (residual async
  advantage = tree leakage ≈ 57–70 nW = 7–9% of block leakage [M]); a
  per-island PLL is unusable in both states (the ~450 µW / ~459 ns figures
  are sky130 1.8 V design defaults, not SG13G2 [A]). Gate at the true root.
- Whole-Vortex confirmation, and a reversal of the campaign's expectation:
  the deep-sleep class (`sfu_unit` duty 0.0005) was supposed to be
  async/QAL's home ground; after clock gating it sits at **2.8× its own
  leakage floor** — a 2,112× prize captured by a free gate. There is no
  remaining margin for async or QAL to compete for. And 32–62% of whole-GPU
  idle runs are exactly one cycle, so anything with a multi-cycle ring-up
  cannot even engage.
- An SNN neuron is excluded from QDI **twice over**, before any energy
  argument: its state loop is cyclic (G-A; the only stateful-async route is
  desync = BD-with-a-local-clock) and its memory boundary has no completion
  signal (G-D).

Do not quote in this regime: the "~60,000×" BD idle ratio (a 4 ns-window
artifact; the real number is a 5.38 nW leakage rate), α\* ≈ 0.51 (an ungated
high-duty artifact; against a gated opponent BD is 1.72× worse per op with
92 vs 48 cells — no crossover at any duty; the sync-vs-BD ordering at
moderate duty currently hangs on an unmeasured clock-restart term — state it
as undetermined), the 5.30 pJ/1,236× clock floor (measured: ~18 pJ/cycle
including the flop clock-pin term; floor:leakage ≈ 4,700:1 — which
*undersells* sync), any single per-cell leakage constant (58.5–155.7 pW/cell
band, state- and mix-dependent; the TH liberty has zero leakage entries and
the other models th22 as a keeper-less AND2), or any QAL standing power as
measured (the resonator has never been built at transistor level and the
model has no time axis). Everything here is bulk 130 nm; on GF FDX back-gate
bias cuts standby leakage 10–100× and would moot the leakage-dominance
argument at the device level.

---

## 7. Applied to the measured blocks

**sha_slice → SYNC** (reproduces the measurements on every axis, and for the
right reason — bank population, not abstention). QDI legal (0 cycles, all
support ≤ 4) but α\* = 2712/487 = 5.6 > 1: QDI can never win on energy for a
purely combinational block at any activity [M]. QAL fails G1+G2 at every
legal partition by 4–7×; even the best bush-excision reaches only 1.17× at
the zero-ZCD limit against a 3× hurdle. At the measured N_min ≥ 221 the QAL
arm is EXCLUDED outright (bush = 0/10 levels; best 4-span prefix bank 92
< 221) [M: `stat-sim/qal/zcd/restate_admission.py`, skeptic brute-forced],
and the hybrid timer moves it further out, not back (N_min 412–535 as built,
§3 G2b; the 4-level prefix bank 92 would need E_timer ≤ 36.84 fJ/bank/hop). Single-stream SHA is the named
latency-bound recurrence; the consumer is inelastic, so the 50.5% QDI
harvest is unbankable. Measured field: CMOS 232 fJ @ 928 ps (liberty basis —
the transistor cross-check found liberty's internal term 1.5–3.7× low, small
gates ×1.87–2.31, flop ×0.782 opposite sign, so a small-gate design corrects
~2×; the α correction moves it the other way, to 96–140 fJ); QDI direct
2,711.7 fJ @ 2,533 ps; **direct+CD 4,385.7 fJ** (whole-netlist costing — the
circulated 4,303.7 summed two separately-costed pieces and missed the CD's
input loading, −1.9%); DIMS 6,972 fJ (dominated, and never ran); BD
450–750 fJ [C, no netlist]; QAL 841–3,541 fJ with overheads [C].

**Vortex ALU → QAL burst over the datapath bush inside a sync island,
control tail sync, single-rail throughout; QDI eliminated at G-B; BD not
preferred (tie-break ii)** — as the triple (6.6–9.3 pJ/op, 2.924 Gop/s,
t_fill 3.76 ns) against measured CMOS 42.7 pJ/cycle with a 22.2 pJ (52.1%)
register+clock tax [M]. **PREDICTION, not ground truth** — and it carries
two warnings: (a) the wp-weighting band (§3) raises the bush logic term ~3×
and erodes the 3× hurdle margin; (b) **the answer is netlist-dependent** —
two synthesis runs of the same RTL disagree 2× on depth and 10× on tail mass
and give opposite QAL verdicts. Level-profile shape is a synthesis choice,
not a block property; Step 2 must therefore read: levelize the netlist you
will actually build, and if it fails the bank gates, **re-synthesize for
balanced levels before declaring QAL ineligible** (a repair step, not a
verdict). **2026-09-27 update (measured ZCD, §3 G2):** at N_min ≥ 221 the
whole-block QAL arm is EXCLUDED (best min-bank 8) and the fpsat_fma
min-bank-63 block resolves UNDECIDABLE → EXCLUDED (it would have needed
E_ZCD ≤ 12.75 fJ, an order below the measured floor of a detector that
does not even fire); the bush-excision arm still passes the bank criterion
(25/37 levels, 98.2% of gates) but now carries the refuted-ZCD rider — its
hop timing must come from a calibrated predictive timer, not per-hop ZCS.
**2026-09-27, second update (the timer is now MEASURED, §3 G2b):** that
predictive timer exists and costs 302.8 fJ/bank/hop of taps → N_min 412–535,
so **no arm of this block admits as built**; whole-block min-bank 8 and
sha's 7 would need E_timer < 0 and can never admit at any timer cost. The
fpsat_fma min-bank-63 row is the ONE live case in the campaign, and its flip
line is the pre-stated **E_timer ≤ 12.7467 fJ/bank/hop** (the "⇔ ≥ 71–74%
recovery" gloss is NOT an equivalence — see §3 G2b's level error).
**2026-09-27, third update (recovery is now MEASURED, §3 G2b): the line is
NOT cleared.** Complete measured ledger 17.911 fJ/bank/hop → N_min 69.2 →
**fpsat_fma min-bank-63 EXCLUDED**, and the per-gate rider is refuted
mechanism-independently (η_max 91.8% vs 96.7% needed). The free-running
resonant network does deliver the gt/gtp taps at 2.974 fJ with every gate
PASS; the **park's driver** (15.0–15.5 fJ measured, 9.77 fJ headroom) is what
excludes it. **QAL at SG13G2 is EXCLUDED, not open** — the one unmeasured
thing that could reopen it is a resonant park tap (~1.5 fJ ⇒ N_min 53.0).

**Whole Vortex, per-block calls on real kernels** (medium confidence;
binding choice flips across kernels for 12–38% of blocks — the rule must
name its target workload):
- Class 1, deep-sleep housekeeping (`sfu_unit`, `wctl_unit`, `dcr_data`,
  divsqrt): **clock-gated sync**, high confidence — the reversal in §6.
- Class 2, high-duty control recurrence (`issue`, `schedule`, `fetch`,
  `decode`, `commit`): **sync**, high confidence — gating buys 1.1–1.4×;
  slowing a recurrence taxes the whole chip (+16.2% runtime measured for one
  2×-slowed unit); ironically these have the best burst amortization
  (WGT-burst ≥74–447) exactly where latency is unaffordable.
- Class 3, wide feed-forward datapath (`muldiv` W_eff 879, `alu_int` 0.0%
  cyclic, `VX_multiplier` 0% MUX): **the only genuine async/QAL candidates**,
  medium confidence, currently undecidable — at real W_eff the delay-line
  term collapses to ~1.2–1.7% ("the delay line is the cost of async" was a
  small-block artifact; retract it), so the decision moved onto handshake,
  completion and register terms the model does not carry.
- Class 4, pure interconnect (`mem_arb` 99.7% MUX, `L2` 99.9%): DIMS
  structurally excluded; gated sync (or BD), high confidence on the
  exclusion.
- Class 5, `fpnew` (43.3% of all comb cells, owns the D=148 critical path):
  **unresolved and the block the answer turns on** — duty 0.000/0.032/0.235
  across kernels, no workload-stable duty; `i_divsqrt_lei` (12,493 bits)
  never activates in any kernel, so the structure that sets the design's
  timing has no measured activity; fpnew also has the *least* burst
  amortization in the design (WGT-burst 2.60/2.86, exact).

---

## 8. Confidence, non-claims, next measurements

**Strong (code or disk, run it and the answer is the answer):** G-A and G-B;
the bank DP + N_min = 48 ZCD-independent floor; only-QDI-changes-encoding;
per-bank overheads amortize over N and K, never burst length.

**Do not bet on:** any BD selection (no mapper, no netlist, no signoff, an
extrapolated width formula invalid on cycles, an undischargeable timing
assumption — the least defensible branch); any QAL verdict that needs
per-hop ZCS (measured 2026-09-27: the comparator class cannot provide it;
the former 50–400 UNDECIDABLE band is resolved — NOT ADMITTED, N_min ≥
221); **any QAL verdict that assumes the switch gates are driven for free**
(every deck before 2026-09-27 did — real drives cost 399.8 fJ/hop single-shot,
633.3 fJ/hop over a full trigger cycle, against the 3.56 fJ the ideal sources
booked, §3 G2b); **any QAL admission quoted as a recovery PERCENTAGE** (η is
load-referenced, the admission line is driver-referenced — the 2026-09-27
round cleared η 87.9% and still measured E_timer 17.9 fJ, N_min 69.2, §3 G2b);
**any park cost taken from an ideal-source booking** (2.40 fJ booked vs
15.0–15.5 fJ measured for the cheapest real driver); the island-size answer (rests on one
unsourced number); d_max = 4.3 (RC_g anchor); QDI for anything with
registers (751-cell latch bank, no scan); level-profile shape as a block
property (2×/10× synthesis spread, opposite verdicts).

**Do not claim** (beyond §6's list): the ALU triple as ground truth; any
composed number without its α-band (the RTL-net→gate-α bridge is the single
unlabelled assumption under every composed energy figure); "4,726 cells";
QDI-artifact clock savings (the as-built QDI ALU carries 188 sync-emulation
registers and a tree to feed them, `nulex/README.md:30,:46`); the
current-sense early-out as an energy win (ranges overlap: 4.7× win to 1.5×
loss — its value is converting BD from margined to self-timed).

**Next measurements, in order:**
1. **The 4×4 boundary-adapter cost matrix** over {sync, BD, QDI, QAL} as
   real netlists on the existing arc models — diagonal included. The only
   first-order input with zero provenance, and it decides whether a
   per-block rule exists at all. No Xyce needed.
2. (a) **Re-levelize the ALU under 2–3 synthesis scripts** and bound the
   (depth, knee, tail, min-bank) spread — the rule's mechanical core is not
   reproducible until then; settle the generic-vs-stdcell basis (±1.9×).
   (b) **ZCD timing-jitter sensitivity** — PARTLY DISCHARGED 2026-09-27:
   the comparator-energy half is measured (144.3–200.5 fJ, non-firing;
   per-hop ZCS refuted, §3 G2) and the mistiming-cost half has two
   measured anchors (the committed record's own +50 ps-late openings cost
   ~nothing energetically at 60 µm; the tg15p+park optimum degrades
   gracefully under +50 ps, −0.9% E_hop [M, skeptic]) — and **DISCHARGED
   2026-09-27** by the hybrid timer round (§3 G2b): the predictive timer is
   built, its energy measured (399.8 fJ/hop, 302.8 of it per-bank taps), its
   calibration costed (1.5 pJ/event, ≤0.3% amortized, calibrate-on-wake in
   the dark-silicon corner), its tracking measured (ratio 16.4, saved only by
   the late-direction sign), and the uncorrected data spread bounded
   (61.6→64.8 ps full-scale, N-invariant; 1/√N holds only for random data).
3. **SWITCH-GATE-CHARGE RECOVERY — DISCHARGED 2026-09-27 (§3 G2b), and the
   answer is NEGATIVE.** M3 lower-VGH, M2 stepwise and M1 switched-resonant
   all FAIL outright; the free-running multi-harmonic resonant network drives
   the gt/gtp taps at 2.974 fJ with every completeness gate PASS at the
   pre-registered checkpoint, but the **park's real driver measures
   15.0–15.5 fJ against a 9.77 fJ headroom** → complete ledger 17.911 fJ,
   N_min 69.2, **fpsat-63 EXCLUDED**; the per-gate rider is refuted for every
   possible mechanism (η_max 91.8%). **The successor, and the only remaining
   QAL-at-SG13G2 question: a RESONANT PARK TAP** — drive the park gate from a
   third tap on the same free-running network (fallback rows: park rail swept
   1.5/1.2/1.0 V, since the park is an nMOS to ground and needs no 1.0 V-bank
   overdrive — the measured V^1.86 law says ≤ 1.19 V would fit the headroom
   [D]; and the cheapest real two-stage conventional driver). Metered
   **driver-referenced**, at the pre-registered gates, with the park's own
   phase generation counted. ~1.5 fJ ⇒ N_min 53.0 and the block admits;
   anything above ~4 fJ and QAL is closed at this node with the sustaining
   amplifier and the DC bias still unpaid.
4. **Extract Vt and the settling-cliff rail level; measure RC_g** on a real
   SG13G2 gate — every G1 number scales with the first two; the third
   parameterizes the bank DP and could flip the ALU verdict alone. (The cliff
   half now has a measured anchor and a deferred actuator: dV = 0.6 V is the
   cheapest/fastest point at 0.326 fJ/gate but invalid at Vt ≈ 0.4 V, and the
   FD-SOI back gate that would move it is the deferred FDX trim — §3 G2b.)

Explicitly not prioritized: the in-flight CMOS transistor cross-check (both
headline verdicts are insensitive over ±30%; it moves margins, not answers).
If budget exists: per-cone support on a second large block (the memory
arbiter or warp scheduler) — G-B does the most eliminating work in the rule
and has one data point on each side of the cliff.
