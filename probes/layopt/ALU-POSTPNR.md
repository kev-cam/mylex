# ALU-POSTPNR — layopt as the post-P&R stage, on the campaign anchor block

**Flow position** (the point being demonstrated): frontends → IR → binding
(polysynth) → gates → P&R (OpenROAD) → **LAYOPT geometry optimization** → analysis
tiers. "After P&R we use the mylex layout optimizer to fix timing and minimize
power" — this file records that stage run on the SG13G2 ALU anchor
(5,164 instances, 59,106 µm² @55% util, closed at 4.75 ns), measured, and then
independently re-derived by a skeptic pass. Everything below was re-checked
from the raw logs/JSONs on disk; the guard chains and headline STA numbers were
**re-executed from scratch** (OpenROAD re-runs + full geometry re-apply), not
transcribed.

Labels: **MEASURED** (tool output on the unmodified basis) / **ELMORE-BASIS**
(layopt's calibrated Elmore pricing; Liberty is never claimed for a moved cell)
/ **DERIVED** (arithmetic from measured anchors) / **ASSUMED** (named
assumption, T0-checkable).

Evidence root: `probes/layopt/evidence/` and `evidence/alu_cmos/work/` (all
paths below relative to those). Working tree uncommitted; modified
`layopt/{extract,lefdef,tech}.py`, new `probes/layopt/{l2_real_def_ihp,
elmore_calibrate_ihp,ihp_alu_common,l6_*}.py`.

---

## 1. What layopt delivered on this block (re-derived numbers)

### Demo B — minimize power at 4.75 ns (the 894-buffer pain point)

Baseline **MEASURED**: 9.146656 mW = sum of `work/inst_power_raw.txt`
(OpenSTA `report_power -instances`, VCD-annotated 17,981 pin activities;
re-summed independently: 5,164 instances, groups comb 4.4254 / seq 2.9666 /
clock 1.7547 mW — the anchor's numbers exactly). OpenROAD's timing-repair
buffers, re-counted from the 4.75 DEF: fanout 690 + rebuffer 123 + hold 81 =
**894 = 17.3 % of instances** (not 21 % — that convention was already corrected
in the bridge phase), **MEASURED** 1.7296 mW total / 0.5824 mW internal.

Harvest, re-summed from the per-instance records in
`work/demoB_final_numbers.json` (match exact):

| term | mW | label |
|---|---|---|
| internal | 0.1761 | DERIVED = MEASURED per-inst internal × as-built ΔW·L ratio; **~W·L scaling ASSUMED** |
| switching | 0.0522 | DERIVED = MEASURED per-net VCD toggle rate × Liberty ΔCin × ½V², V=1.2 |
| leakage | 0.000042 | DERIVED |
| **total** | **0.2284** | **= 2.50 % of block, 13.2 % of buffer power** |

750 instances shrunk (638 fanout / 0.1943 mW + 112 rebuffer / 0.0341 mW;
743 buf_1 + 7 buf_2), −160.3 µm² W·L, 0 cells added/removed/moved. Timing
after: **byte-identical endpoint dump** to baseline STA — WNS +0.009114 ns,
TNS 0, hold +0.05103, re-run this pass (§3).

Rejection ledger, re-counted from `demoB_final_plan.json` (authoritative;
sums to 894 exactly): 96 geometry-engine limitation (81 dlygate4sd3 long-L
stacks + 15 fingered buf_4/8/16 — internal power foregone re-summed
0.1354 + 0.0662 = **0.2016 mW**, exact), 16 slack-below-margin, 7 timing-guard
reverts, 4 slew-ceiling, 20 budget-too-small, 1 W-audit fragment (fanout322).

### Demo A — fix timing at 4.5 ns (the −0.124 ns pain point)

Baseline **MEASURED**, reproduced by an independent OpenROAD re-run this pass:
WNS −0.124127 / TNS −0.462236 ns, placement-parasitics basis (the anchor's own
convention; `sta45_demoA.log:5`). Result of 48 in-place W-stretches
(**ELMORE-BASIS** per-edge deltas propagated on the measured STA graph as
rise/fall late+early derates), re-run independently:

- WNS −0.1241 → **−0.0923** (25.6 % of deficit recovered; my rerun −0.092275
  vs recorded −0.092284 — 0.01 ps numeric noise)
- TNS −0.4622 → **−0.3154** (31.8 % recovered)
- hold WNS +0.0510 **unchanged** (early derates applied too)
- cost: +4.74 µm² W·L, +55.17 fF input load (charged to upstream drivers),
  +5 grown contact cuts, 0 new cells, 0 placement changes

**NOT CLOSED — honest residual −92.3 ps.** The recovered 31.8 ps would close
the anchor's 4.6 ns attempt (−0.0076, `phys_4.6.log:435`) with 4× margin.
Comparison at the same period: OpenROAD's discrete-cell repair spent 906
buffers (re-counted from the 4.5 DEF: 692+133+81) and still failed at the
identical −0.1241 (`phys_4.5.log:437`, RSZ-0062 at :148,:284).

Wire widening (pain point 2's second lever): **measurably worthless on this
min-pitch-routed block** — 23 nets ×1.5, only isolated spans survive delta-DRC
(481/650 rects), ≤0.01 ps kept, WNS unchanged (`demoA_wire_numbers.json`:
BEFORE==AFTER to the ps). Honest negative result; un-gated pricing (−2..−5
ps/net) shows what router-coordinated widening could buy.

### Corrections found by this skeptic pass

1. **"8 violating endpoints, 8 → 8"** in the demo A log is **wrong**. Per-endpoint
   dump with TNS cross-check (sums match TNS exactly on both sides):
   **6 violating flop-D endpoints before → 5 after**, all shallower, one
   (_7989_/D, −0.0054) fully recovered:
   `_8022_ −0.1241→−0.0923, _8052_ −0.1111→−0.0846, _8054_ −0.1059→−0.0800,
   _8053_ −0.0804→−0.0545, _7990_ −0.0354→−0.0040, _7989_ −0.0054→positive`.
2. **"39 % of the shrunk buffers' internal power"** in the demo B log is
   mis-captioned. 0.2284/0.5824 = 39.2 % of **all 894 buffers'** internal
   power; the internal-only saving is 0.1761/0.3525 = **50.0 % of the shrunk
   750's** internal power. (Both denominators re-summed from
   `inst_power_raw.txt`.)
3. The prose split "22 slack-below-margin, ~19 budget" is stale; the final-plan
   ledger says 16 + 20 (totals consistent either way).
4. Task framing said "894 = 21 % of placed cells"; it is 17.3 % (894/5164).

---

## 2. Guards on the FINAL layouts — independently re-executed

Both demos' apply pipelines were **re-run end-to-end from the plan JSONs this
pass** (geometry rebuilt from DEF+GDS, moves re-applied, re-extracted, guards
re-checked). Both result JSONs came out **byte-identical** to the recorded
ones. Pasted output:

Demo B (`l6_power_harvest_apply.py`, rerun 2026-09-26):

```
plan: 750 instances
build 15.1s: 744020 rects, 23579 nets, 35876 devices
applied 750 instances (3000 device resizes, 7468 rects touched, 757 orphan cols), failed 0 {}
re-extract 12.1s: 23579 nets, 35876 devices (baseline 23579/35876)
GUARD topology signature: UNCHANGED (24.3s)
GUARD delta-DRC: baseline flags 0, after 0, NEW 0 (7.5s)
```

Demo A (`l6_close_timing_apply.py`, rerun 2026-09-26) — including the
attempt-0 auto-revert drama, reproduced exactly:

```
attempt 0: build 15.6s, 60 picked, 0 excluded
applied 60 instances, 305 rects touched (+14 grown cuts)
GUARD topology signature: ***CHANGED***
GUARD delta-DRC: baseline 0, after 2, NEW 2
   NEW min_width poly: rect 293940 0.110 < 0.130 um | alu_top/_7695_/sg13g2_nand3b_1
   NEW min_width poly: rect 299320 0.110 < 0.130 um | alu_top/_7767_/sg13g2_nand3b_1
reverting offenders: {... 10 'net merge' + 2 'delta-DRC (min_width poly)' = 12 ...}
attempt 1: build 15.6s, 48 picked, 12 excluded
re-extract 12.7s: nets 23624->23624 devs 35916->35916
GUARD topology signature: UNCHANGED
GUARD delta-DRC: baseline 0, after 0, NEW 0
all geometry guards GREEN
```

The 10 attempt-0 net merges are the **silent signal-to-rail shorts** the
spacing DRC cannot see (outer-side gate-bar extension landing on rail
contacts; touching-rects merge by convention) — only the topology-signature
guard catches them. That is the framework's strongest single credential on
this block.

Timing guard, re-executed: demo B final derate STA reproduces
WNS/TNS/hold and a **byte-identical** 1,440-line endpoint dump; among the 376
degraded endpoints the minimum after-slack is **+94.5 ps** (guard band 50 ps),
0 offenders under the `after < min(before−0.1ps, 0.05ns)` rule; the block WNS
path (_8053_/D +9.1 ps) is untouched. Demo A rerun reproduces −0.0923/−0.3154
with hold unchanged.

**Guard scope, honestly stated**: "zero new DRC" means zero new violations of
layopt's modeled rule subset (min_width / min_space / enclosure on the SG13G2
table) checked for every touched rect against a full-layout index — there are
no nwell/implant/poly-diff rules in the table, so those margins live in the
room model as ASSUMED values (0.10 µm diff-poly, licon, psdm keep-in). The
topology signature is a W-blind graph signature over the full extraction
(35,876 / 35,916 devices — the extraction itself CDL-exact per-instance and
KLayout-isomorphic on all three layouts, bridge phase). Routed-DEF DRT
convergence to 0 violations is the router's own full-rule check on the
baselines, not on the moved geometry.

---

## 3. The Elmore attack — how big, and can it flip anything?

Calibration (both re-read from the logs; method: layopt re-prices each OpenSTA
worst-path stage as `t0(arc,slew) + ln2·R·C_total` with LEF-basis wire RC):

| layout | unique stages | stage-total r | mean offset | rms | sum ratio | per-path totals |
|---|---|---|---|---|---|---|
| 4.75 routed (reg2reg) | 37 | 0.9886 | −3.0 ps | 20.4 ps | 0.981 | −5.3 … −7.1 % |
| 4.5 routed (reg2reg) | 44 | 0.9715 | −5.1 ps | 34.5 ps | 0.973 | −7.0 … −9.0 % |

Gate part alone: sum ratio 0.941 / 0.931 (mean −9.6 / −12.7 ps per stage) —
layopt systematically **under** OpenSTA. Wire part: the two bases disagree
structurally (layopt LEF-physics vs the flow's `setRC.tcl`, whose Metal1/2 cap
feeds area-cap numbers as per-length — 5.14× low; Metal3-5 ~2.3× above LEF).
Neither wire basis is trustworthy until the Xyce arbitration; wire absolutes
are small (≤ ~20 ps/stage) on these paths.

**What cannot flip:**

- Demo A "NOT CLOSED": residual −92.3 ps ≈ 3× the entire priced recovery.
  Pricing would need to be wrong by ~300 % in the favorable direction.
- Demo A "recovers ≈ ¼ of the deficit": the deltas ride on R~1/W (ASSUMED);
  ±20 % on that puts the recovery at 20-31 % of deficit. Direction is
  physically robust (wider W ⇒ lower R).
- Demo A "would close the 4.6 ns attempt": needs only 7.6 of the 31.8 ps —
  survives a 4× overpricing.
- Demo B's **power arithmetic**: rides on measured activity, Liberty ΔCin,
  measured internal power and geometry ratios — Elmore appears nowhere in the
  saving itself.

**What could flip — the one genuinely soft spot:** demo B's "no path made
critical" on the most heavily shrunk paths. Sensitivity, computed this pass
from the endpoint dump (systematic underpricing fraction of the accumulated
priced slowdown that breaches each threshold):

```
endpoint   accum. slowdown  after-slack  breach 50ps band  below baseline WNS  slack<0
_8030_/D        1.580 ns      +115.2 ps        4.1 %             6.7 %          7.3 %
_8032_/D        1.661 ns      +156.8 ps        6.4 %             8.9 %          9.4 %
_8036_/D        1.346 ns      +140.4 ps        6.7 %             9.7 %         10.4 %
```

A systematic ~7 % underpricing of the shrink deltas would make _8030_/D the
critical path — and the observed calibration bias on *absolute* stage totals
is −2…−9 %. The defense is real but must be stated precisely: the derate
mechanism prices only the **ratio** (OpenSTA's own d_old is what gets scaled),
so the absolute-basis bias divides out; the ratio's error rides on **R~1/W and
slew~R (both ASSUMED)**, which the calibration does not bound. Nothing
measured on this box bounds it. Until T0 check #1 below runs, the demo B
timing guard on the heavy-shrink paths is **ELMORE-BASIS, with ≈4-7 %
systematic-error headroom** — defensible for a demo, not for signoff.

**Solid (MEASURED, reproduced):** both baselines, both final STA states, the
buffer census, the 894/906-buffer comparison, all geometry costs (as-built
re-extraction), the endpoint guard margins, the negative wire-widening result,
and both guard chains.

---

## 4. The power attack — answers

**Is α per-net or flat?** Per-net (per-pin), **MEASURED**: `sta475_pins.txt`
carries VCD-annotated toggle rates per pin (`act={7.23425e+07 0.240 vcd}` for
fanout1/A), and the planner uses each instance's own input-pin rate
(`l6_power_harvest_plan.py:126-129`). Hand-check this pass: fanout1
dp_sw = ½·1.44·7.234e7·(1−0.4353)·2.263 fF = 6.6579e-08 W — matches the JSON
record exactly. (The **flat** α appears only in demo A's *cost* estimate
(~1e8/s, no VCD exists for the 4.5 netlist) — order 10 µW, labeled
DERIVED-ASSUMED there.)

**Is the buffer internal term measured or assumed?** The per-instance internal
power is **MEASURED** (report_power, VCD activity, Liberty basis); the
reduction is that number × the as-built ΔW·L ratio, with **~W·L scaling
ASSUMED** (T0 check #3). Known bias, from the anchor's own transistor
measurements (`alu_cmos_results.log`): Liberty *understates* buf_1 internal
energy ×1.96, so at transistor level the absolute mW saving is likely larger —
but so is the block total (corrected 12.5 mW), leaving the ~2.5 % figure
roughly stable. Quote the saving as Liberty-basis mW, as done.

**Double-count with the +40.3 % physical overhead?** No — they are the same
ledger read twice, not two savings. The +40.3 % is descriptive
(synth 6.5185 → phys 9.1467 mW, `alu_cmos_results.log:76`); demo B's
0.2284 mW comes off the 9.1467 baseline, i.e. it recovers **8.7 % of the
2.628 mW physical-design overhead** (equivalently drops the overhead to
+36.8 %). Do not quote both an "overhead reduced by X" and "0.2284 mW saved"
as separate achievements.

**Caption bug**: the "39 % of the shrunk buffers' internal power" line —
see correction 2 in §1.

---

## 5. Flow-position verdict

As the post-P&R stage of the common backend, on this block layopt
demonstrably:

1. **Minimized power**: −0.2284 mW (2.50 % of block; 13.2 % of the
   timing-repair-buffer power that P&R itself added) by pure geometry, with
   the final STA endpoint-for-endpoint identical to the closed baseline and
   both geometry guards green under independent re-execution. The saving
   arithmetic stands on measured anchors; only the ~W internal scaling and the
   guard's ratio pricing are assumptions, both named and T0-checkable.
2. **Fixed timing partially, honestly**: a quarter of a −124 ps deficit for
   4.74 µm² and zero new cells, where OpenROAD's own discrete-cell repair
   (906 buffers, 7,664 µm² of buffer area) had already saturated at the same
   WNS. Geometry closes 4.6 ns; 4.5 ns needs the placement-level move class
   (l4_ whitespace/pad displacement). That boundary — where in-place W runs
   out on a 55 %-utilization block — is itself a measured deliverable.
3. **Proved the guard architecture**: the LVS-identity signature caught 10
   silent signal-to-rail shorts that spacing DRC structurally cannot see, and
   the closed verify loop (demote → revert) turned a WNS-negative naive plan
   into an exactly-baseline final. This is the difference between a geometry
   *editor* and a geometry *optimizer*.
4. **Killed a lever with numbers**: wire widening on a min-pitch-routed block
   buys ≤0.01 ps. Post-route W-stretch is the workhorse; widening needs router
   cooperation (a polysynth/route-stage hook, not a layopt fix).

**Elmore-soft** (label stays until T0 runs): demo B's timing guard on the
heavy-shrink paths (§3 table), demo A's recovery magnitude, every wire-RC
absolute. **Solid**: everything else in §1-§2.

## 6. T0 spot-checks that would make this signoff-defensible (NOT run — Xyce owned elsewhere)

1. **The guard's weakest path**: Xyce transient of the shrunk buf_1 chain on
   the `ex_data[215] → … → _8030_/D` path — specifically **fanout159,
   fanout158, fanout157 (s=0.35, as-built N 0.53/0.305, P 0.39/0.30, priced
   slowdown ≈2.0×) and fanout156 (s=0.5)** — each driving its extracted RC net
   and real receivers (`alu_4.75_routed_mt.layopt.{cir,spef}` already
   written). Bounds R~1/W + slew~R at exactly the point where 4-7 % of
   systematic error flips the guard.
2. **Demo A's credit side**: transient of stretched **_4545_
   (sg13g2_a221oi_1, k_p 1.054 / k_n 1.216, priced ratios 0.982↑/0.953↓)** vs
   its derated arc — bounds the pull-network series/parallel W-credit that the
   31.8 ps recovery is made of.
3. **Internal-power-vs-W** on one buf_1 at as-built widths (e.g. fanout1) —
   bounds the ~W·L internal scaling AND reconciles with the anchor's measured
   Liberty×1.96 internal factor; decides whether 0.1761 mW is conservative.
4. **The Metal2 RC arbitration** (standing finding): drive a ~2 kΩ widened
   fanout net before/after ×1.5 — arbitrates layopt's LEF-basis 0.0930 fF/µm
   vs setRC's 0.0181 fF/µm and retires the wire-basis asterisk on every wire
   number in the flow, the anchor's own closure included.
5. **High-C gate stage**: dfrbpq CLK→Q at ~100 fF (stage _8141_, the largest
   single calibration miss: STA 486.7 vs layopt 354.7 ps gate part on the 4.5
   layout) — bounds the edge-fit linearization where the −6 % gate bias
   concentrates.

---

*Skeptic pass 2026-09-26: all numbers above re-derived from
`demoB_final_numbers.json` / `demoA_final_numbers.json` / `inst_power_raw.txt`
/ `demoB_final_plan.json` / the endpoint dumps / the DEFs / `phys_4.*.log`;
guard chains and final STA re-executed (result JSONs byte-identical); three
prose corrections and one caption bug recorded in §1. Uncommitted — the main
session commits.*
