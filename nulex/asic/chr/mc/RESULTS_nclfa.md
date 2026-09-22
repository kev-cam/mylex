# Monte-Carlo Vt-Mismatch Reliability of the NCL Full-Adder (nclfa)

First **composed-block** Monte-Carlo reliability study in this suite (single-cell
TH-gate results live in `RESULTS.md`). The `nclfa` is a 1-bit dual-rail NCL full
adder in Fant canonical form: **4 threshold gates** — `coH = TH23(aH,bH,ciH)`,
`coL = TH23(aL,bL,ciL)`, `sH = TH34W2(coL,aH,bH,ciH)`, `sL = TH34W2(coH,aL,bL,ciL)`
(the weight-2 input of each sum gate is the *opposite-rail* carry) — totalling
**60 transistors**, each carrying an independent per-device threshold shift.

## Methodology

Each of the four gate instances draws its own independent per-device
`AGAUSS` `DELVTO` from the `th23_mc` / `th34w2_mc` cell variants, so the composed
block presents **60 independent per-device DELVTO** (Xyce confirms
*"Number of unique random parameters = 60"* on every level), with the shift
reaching the device threshold live through the PyMS runtime-callback path.
The mismatch scale `kvt` is threaded **down** to every gate instance by the
`nclfa_mc.sp` wrapper (`kvt={kvt}` passed into each `th23`/`th34w2` — the plain
`ldx/asic/cells/nclfa.sp` does not, which would otherwise let the subckt-local
`.param kvt=1` pin the whole block at nominal). Stimulus is the dual-rail
**NULL/DATA return-to-zero** protocol: an all-rails-low NULL spacer separates
every DATA codeword (resetting TH-gate hysteresis), and the sequence walks all
**8 (A,B,Cin) input vectors**; after each DATA the four outputs must form the
correct dual-rail codeword (HIGH > 0.72 V / LOW < 0.48 V) and after the final NULL
all four must return LOW (RTZ). A sample is **functional** iff all 36 checks pass
(8 vectors × 4 output rails + 4 final-NULL RTZ). Runs use Xyce `.SAMPLING`
(`SAMPLE_TYPE=MC`, `SEED=1`), **N = 200 per level**, `kvt = 1, 2, 3, 4`
(`kvt = 4 ≈ 4×`-nominal stress). Completion latency `tvalid` is the last-DATA
`aH → sH` posedge propagation — the deepest carry→sum path through the block.

## Reliability result (N = 200 / level, SEED = 1)

| kvt | Functional | Yield | Completion latency mean ± sd (ps) | min (ps) | max (ps) |
|----:|-----------:|------:|----------------------------------:|---------:|---------:|
| 1 (nominal) | 200/200 | 100.0% | 397.00 ± 8.70  | 375.80 | 428.40 |
| 2           | 200/200 | 100.0% | 398.55 ± 17.64 | 357.32 | 466.06 |
| 3           | 200/200 | 100.0% | 400.79 ± 26.94 | 340.40 | 510.46 |
| 4 (~4×)     | 200/200 | 100.0% | 403.80 ± 36.80 | 324.90 | 564.00 |

**Aggregate: 800 / 800 samples functional.** The composed full adder computes the
correct dual-rail Sum/Cout for all 8 input vectors and returns to NULL, with zero
wrong-output events across all four mismatch scales, including ~4×-nominal
(`worst_measures` empty at every level). All standard deviations are population
stdev, matching `analyze_fa.py`; every level ran to a clean `End of Xyce(TM)
Simulation` (exit code 0), produced all 200 `.mt` files, and logged no
abort/fatal/segfault markers.

## Adversarial verification (four independent lenses — all PASS)

- **Truth-table (pass)** — independently derived the dual-rail FA truth from the
  gate thresholds (`TH23` = ≥2-of-3; `TH34W2` = 2·first+rest ≥ 3) and confirmed
  the `.expected.json` map for all 8 vectors + RTZ, with `sH = A⊕B⊕Cin`,
  `coH = maj(A,B,Cin)`, `coL = ¬coH`, `sL = ¬sH`. Every dual-rail pair is
  complementary in all 8 DATA vectors (valid codewords, no all-high state); the
  scoring map is correct.
- **Raw-data recount (pass)** — re-parsed all 200 per-sample `.mt` files with an
  independent parser (not `analyze_fa.py`), applying HIGH > 0.72 V / LOW < 0.48 V
  to each of the 36 measures: functional = 200/200, no parse gaps. Separation is
  effectively rail-to-rail — max value among LOW-expected = 6.19e-5 V, min among
  HIGH-expected = 1.199997 V, and **zero** measured values fall in the ambiguous
  [0.48, 0.72] band — so the verdict is insensitive to the exact threshold.
- **NCL protocol (pass)** — confirmed all three invariants: each rail is 0 V in
  all nine NULL windows; each DATA window asserts exactly one rail per input pair
  (one-hot, spanning D0…D7, no double-assert, no NULL leakage); a full NULL spacer
  sits between every consecutive DATA pair; and the 32 DATA + 4 final-NULL
  measures cover all 8 vectors and the RTZ return of all four outputs.
- **kvt-scaling (pass)** — confirmed the swept parameter reaches the DUT and
  scales the mismatch: per-sample `.mt` outputs differ byte-for-byte between k1 and
  k4 at every sampled index (kvt is not inert), and the `tvalid` population stdev
  is strictly monotone increasing (8.70 → 17.64 → 26.94 → 36.80 ps; k4/k1 ≈ 4.23×),
  with the mean drifting upward and the min/max envelope widening monotonically —
  consistent with real per-device mismatch, not a flat/inert sweep.

## Findings

1. **Functional robustness under mismatch.** The composed block is functionally
   robust to local Vt mismatch: **0 failures in 800 samples** through ~4×-nominal,
   with rail-to-rail output separation (zero values in the ambiguous band). This
   is the expected NCL delay-insensitivity property — per-device mismatch perturbs
   *timing*, not the dual-rail codeword or the RTZ return — and it matches the
   single-cell finding that codeword/DC levels are insensitive to mismatch.
2. **Latency sd scales ~linearly with mismatch.** Completion-latency stdev grows
   8.70 → 17.64 → 26.94 → 36.80 ps for kvt = 1→4 (≈ 9 ps per unit kvt; 4.23× over
   the sweep), consistent with the single-cell delay-σ trend but now integrated
   across the composed carry→sum path.
3. **Mean latency ALSO drifts upward — the composed-block signature.** Unlike a
   single cell, whose mean delay stays ~flat as mismatch grows, the block's mean
   `tvalid` drifts 397.0 → 403.8 ps (+6.8 ps, ≈ 1.7%) and the worst-case tail
   widens fastest (max 428.4 → 564.0 ps; min 375.8 → 324.9 ps). Completion is the
   *slowest of the parallel carry→sum paths*, so mismatch skews the max-path
   (order-statistic) latency positive — the effect to watch as composed blocks
   deepen.

## Files

- `gen_fa_deck.py` — builds the dual-rail NULL/DATA deck + `.expected.json` truth map.
- `nclfa_mc.sp` — MC wrapper threading `kvt` down to the four TH-gate instances.
- `mc_nclfa.cir` (+ `.expected.json`) — the parameterized `.SAMPLING` deck (N = 200).
- `analyze_fa.py` — functional yield + completion-latency (`tvalid`) from the `.mt` files.
