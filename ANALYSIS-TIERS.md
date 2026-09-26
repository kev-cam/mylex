# ANALYSIS-TIERS.md — The Three-Tier Analysis Architecture

*2026-09-26 · companion to `COMMON-BACKEND.md` (the IR polysynth scores over),
`ASYNC-PLAN.md`, and `SELECTION-RULE.md`. Uncommitted; the main session
commits. Every load-bearing number below is MEASURED, was independently
re-run by a skeptic pass this campaign, and lives in a machine-readable
residuals file cited by path.*

**The architecture** (architect, verbatim): *"Analysis can be transistor
level — block models are behavioral analog or stat-sim for doing full
system."*

Three tiers. Each tier is calibrated against the one below it, and the
residual of that calibration is **recorded, not remembered**.

---

## 1. The tiers and what each one scores

| Tier | Engine | Scope | What it scores in polysynth / the common backend | Status |
|---|---|---|---|---|
| **T0 — TRANSISTOR** | Xyce + PSP103 (SG13G2), sky130 | cells and **anchors** | ground truth: per-cell energy/delay anchors, hop/bank events, anything a higher tier is calibrated against | **SOLID** — every campaign anchor lives here |
| **T1 — BEHAVIORAL ANALOG** | bfit-tuned Verilog-A/AMS + B-source macromodels (Xyce today; VACASK/ngspice lanes written but that toolchain is not installed here) | **blocks**, specifically the mixed-signal ones where full-swing event models are INVALID: QAL banks/settling gates, inductor hops, ZCD, hysteretic (keeper) cells | block-level energy + delay + waveform SER for candidates that T2's event semantics cannot represent (partial swings, adiabatic recovery, keeper fights) | **BROUGHT UP THIS CAMPAIGN** — see §3 |
| **T2 — STAT-SIM** | event-driven, full system (`statsim_delay`/ssta + `stat-sim/gpu/vortex_energy` composition) | full-system digital, full logic swings (regular and async) | system-level delay distributions and composed energy for whole cores; consumes T0/T1 numbers as leaf models | **WORKING** |

The user's placement rule, verbatim: *"stat-sim works for regular and async
that do full logic swings; behavioral Verilog-A based on SPICE (nominal) is
probably what is best for QAL."* T1 exists because QAL cells settle rather
than switch, recover charge on the reverse ramp, and stall at device
thresholds — none of which an event model can carry, and none of which
transistor sim can afford at block scale.

---

## 2. THE CALIBRATION CONTRACT

Every T1 and T2 model ships with:

1. **A recorded residual vs the tier below**, at the **fitted** operating
   point AND at operating points the fit never saw (**holdouts**), in a
   machine-readable `residuals.json` next to the model — entries of the form
   `{feature, operating_point, T0_anchor, T1_value, err_pct, fitted|holdout,
   validity_window, T0_source_file}`. Prose in a README or a fit.json note
   string does not satisfy this: a T2 composition cannot parse it.
2. **A stated validity window.** Outside the window the model's number is
   not used — the quantity stays sourced from the tier below. A recorded
   FAIL is a first-class contract entry (it tells T2 what it must NOT source
   from T1), not something to delete.
3. **Provenance tags that carry the tier.** Any number quoted upward is
   labeled with the tier that produced it (T0-sourced / T1±band / T2-composed)
   and the residual band rides along. MEASURED / COMPOSED / DERIVED / ASSUMED
   labeling applies within every tier.
4. **Energy must emerge from the supply-current integral** of the model's own
   solved currents (recovery = the integral running negative), never from an
   asserted formula. A model that hard-codes `f_adia` is the spreadsheet
   again. (Verified by grep + rerun on every T1 model below.)
5. **Acceptance bar**: a T1 block model is useful iff (a) it reproduces its
   T0 anchor's energy and delay within stated tolerance INCLUDING at an
   unfitted point, and scores an SER dB on the waveform with the existing
   metric (`bfit/benchmarks/accuracy.py`); (b) it is materially faster than
   T0 at block scale (C6288's x93–200 sets the expectation); (c) its residual
   is recorded per (1). Anything less is a liability, not a model.

### First contract entries (produced and skeptic-verified this campaign)

**`/usr/local/src/sv2ghdl/bfit/library/th22/residuals.json`** — th22
C-element macromodel vs `ce_th22_{1,3,10}` PSP103 anchors (anchor law
E = 39.398 + 1.7369·C_L fJ, TD = 319.5 + 7.26·C_L ps). Fitted at CL=3 fF
only. Energy −0.3% / +0.05% / +1.4% at CL = 1 (holdout) / 3 (fit) / 10 fF
(holdout); TDrise −3.8/−1.8/+4.4%; 3-stage-chain slow-edge arrivals +2.0%;
20-cell chain (holdout, structural) arrival +3.2%, **block energy −7.3%**
(the band T2 must carry until a chain-energy feature lands); SER 18.1 dB.
Speed: x41–44 (4-cell), x14 (20-chain), Xyce wall. Skeptic re-ran every row
including bit-exact transistor reference reproduction: **SHIP**.

**`/usr/local/src/stat-sim/qal/va/residuals.json`** — QAL cells vs the A1b /
stall / cliff / iso-current T0 anchors. `qal_gate.va` settle law ±13% inside
T = 500 ps–2 ns (fit at 1 ns only; holdouts +21% @200 ps, −29% @5 ns — a
recorded SHAPE error: missing subthreshold physics); stall voltage exact at
VTP=0.50, T-independent; cliff LOCATION exact, shape step-vs-graded.
`qal_hop.va` cap-to-cap delivery loss to 0.14 pp over a 10x R span.
**Composed 8-cell bank hop: QUANTITATIVE FAIL, recorded** — E_hop −72%,
t_zcs −33.5%, root cause measured on the transistor run (silicon burns
8.9 fJ of near/sub-threshold clamping inside the gates during the 342 ps
event; the linear model cannot). Consequence, per contract rule 2: **bank-hop
energy and timing at the dV=1.0 design point stay T0-sourced**
(`qal_hop_corrected.json` / `qal_isocurrent.json`); T1 may contribute
per-gate settle terms only, inside the recorded window.

---

## 3. State of T1 after this campaign

| Model | Files | Verdict (skeptic) | Residual vs T0 | Speed vs T0 |
|---|---|---|---|---|
| **th22 C-element** (first hysteretic cell; keeper = 55% of its 44.62 fJ/op) | `bfit/library/th22/` + portable `th22.vams` | **SHIP** | energy ≤1.4% incl. both unfitted loads; delay ≤4.4%; chain energy −7.3% band recorded; SER 18.1 dB | x44 (4-cell) / x14 (20-chain) |
| **qal_gate.va** (single-ended settling INV/NAND2/NOR2; pMOS source-reference fix landed) | `stat-sim/qal/va/` | **FIX-FIRST** — per-gate settle terms only, inside 500 ps–2 ns | ±13% in-window; +21/−29% outside; genuine negative-integral recovery, closure ≤0.2% | ~26x at 8-gate scale |
| **qal_hop.va** (transfer switch) | same | **SHIP narrowly** (cap-to-cap only) | 0.14 pp over 10x R | — |
| **qal_gate_dr.va** (dual-rail ECRL) | same | **REJECT / quarantined** — eq-port defect unexplained AND its anchor never produced | none usable | — |

Toolchain gains that made this possible: bfit grew an **energy feature**
(supply-charge integral, the cross-validating `.measure tran Q INTEG I(Vsrc)`
form) and a **meas feature**, plus the objective-floor fix that had swamped
femtojoule targets; `stdcell2bfit` v2 replaced the linear conductance-divider
with regenerative thresholded-linear-overdrive conduction, W/L-scaled
strengths, and a tunable keeper (`kfb`) — the cmos_inv-v2 lesson ported, and
a measured model-form finding on top: **linear overdrive (α=1), not
square-law** — 130 nm SG13G2 is velocity-saturated; α=2 fit chain slow-edge
delay 19x worse.

**Still missing from T1** (recorded in the residuals files):
- **Subthreshold conduction** in the QAL cell — one measured root cause
  behind three quantitative failures (hop −72%, hard cliff, settle-law tail).
- TH cells beyond th22 (th33, th23, thxor…) — mechanical now that the v2
  form + energy feature exist; and a chain-energy fit feature for the −7.3%.
- The **ZCD** as a behavioral cell (hop timing is deck-owned and stays
  T0-sourced), the **recovering generator** (as-built η≈1/3 — always a
  separate explicit line in QAL totals), bank **wp-scaling** of switch
  parasitics (~1.96 fF/µm — lives in the deck-side generator/switch term).
- Nonlinear bank C(V); CIN/RON_N/VTN unfitted; ESCALE hazard past ~8 gates;
  dual-rail rebuild; VACASK/ngspice lanes (engine not installed here).

---

## 4. Highest-leverage next piece of T1 work

**Add a subthreshold exponential tail to `qal_gate.va`'s overdrive
conduction, then re-validate all of README §4.** One model-form change is
the measured root cause of the three dominant QAL residuals (−72% bank-hop
energy, step-vs-graded cliff, −29% settle-law tail at 5 ns); it is the same
class of physics fix that took th22 from 3–10x energy overcount to +0.05%,
and it is what could move bank-hop energy/timing from "stays T0-sourced" to
a T1 number with a band — the difference between a QAL tier that can only
decorate T0 rows and one that can compose new bank/topology candidates for
polysynth. Fit its one new parameter against anchors that already exist
(the graded-cliff percentages and the 5 ns settle-law point), keep 1 ns as
the fitted point, and re-score every row in
`stat-sim/qal/va/residuals.json` — the harnesses (`run_a1b_law.py`,
`run_cliff.py`, `run_bankhop.py`) and the regenerated T0 anchors are already
on disk.
