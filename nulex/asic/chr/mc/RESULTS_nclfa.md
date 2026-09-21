# Monte-Carlo Vt-Mismatch Reliability of the NCL Full-Adder (nclfa)

First **composed-block** Monte-Carlo study (single-cell results are in
`RESULTS.md`). The `nclfa` is a 1-bit dual-rail NCL full adder in Fant canonical
form — 4 threshold gates (`coH=TH23(aH,bH,ciH)`, `coL=TH23(aL,bL,ciL)`,
`sH=TH34W2(coL,aH,bH,ciH)`, `sL=TH34W2(coH,aL,bL,ciL)`; the weight-2 TH34W2 input
is the *opposite-rail* carry) totalling **60 transistors**, each carrying an
independent per-device threshold shift.

## Methodology

Per-device mismatch is `DELVTO ~ AGAUSS(0, kvt·σ_Vt, 1)` (`σ_Vt = A_Vt/√(W·L)`,
Pelgrom, `A_Vt ≈ 3.5 mV·µm`), reused from the `th23_mc.sp` / `th34w2_mc.sp` cell
variants. Because the block instantiates those gates twice each, **Xyce assigns
each subckt instance its own independent AGAUSS draws → 60 independent per-device
DELVTO** (confirmed: Xyce reports *"Number of unique random parameters = 60"*).
`DELVTO` reaches the PSP103 threshold live through the PyMS runtime-callback path,
so all samples share one `.so` per geometry.

The mismatch scale `kvt` is threaded down to every gate instance by
`nclfa_mc.sp` (a wrapper that passes `kvt={kvt}` into each `th23`/`th34w2` — the
plain `ldx/asic/cells/nclfa.sp` does **not**, which would otherwise pin the whole
block at nominal mismatch regardless of the top-level `kvt`). Verified: the
per-sample outputs differ between `kvt=1` and `kvt=4`, and the completion-latency
spread grows with `kvt` (below).

Stimulus is the dual-rail **NULL/DATA return-to-zero** protocol: NULL (all rails
0) separates every DATA codeword (required for TH-gate hysteresis to reset), and
the sequence walks all **8 (A,B,Cin) input vectors**. After each DATA the four
outputs must equal the correct dual-rail codeword (HIGH > 0.72 V / LOW < 0.48 V);
after the final NULL all four outputs must return LOW (RTZ). A sample is
**functional** iff every one of the 36 output checks (8 vectors × 4 outputs + 4
RTZ) is correct. Xyce `.SAMPLING` (`SAMPLE_TYPE=MC`, `SEED=1`), **N = 200 per
level**, `kvt = 1, 2, 3, 4` (`kvt = 4 ≈ 4×`-nominal stress). Completion latency
`tvalid` is the `aH → sH` propagation (VDD/2 crossing) on the all-ones vector —
the deepest carry→sum path.

## Reliability result (N = 200/level, SEED = 1)

| kvt | Functional | Yield | Completion latency mean ± sd (ps) | min (ps) | max (ps) |
|----:|-----------:|------:|----------------------------------:|---------:|---------:|
| 1 (nominal) | 200/200 | 100.0% | 397.0 ± 8.7  | 375.8 | 428.4 |
| 2 | 200/200 | 100.0% | 398.5 ± 17.6 | 357.3 | 466.1 |
| 3 | 200/200 | 100.0% | 400.8 ± 26.9 | 340.4 | 510.5 |
| 4 (~4×) | 200/200 | 100.0% | 403.8 ± 36.8 | 324.9 | 564.0 |

**Aggregate: 800 / 800 samples functional** — the composed full adder computes
the correct dual-rail Sum/Cout for all 8 input vectors and returns to NULL, with
zero wrong-output events across all four mismatch scales, including ~4×-nominal.

## Adversarial verification (three independent lenses, all PASS)

- **Truth-table** — independently derived the dual-rail FA truth from the
  `nclfa.sp` structure and the TH-gate thresholds; confirmed the expected-output
  map matches for all 8 vectors + RTZ, and that `sH = A⊕B⊕Cin`, `coH =
  maj(A,B,Cin)`, `coL = ¬coH`. (The opposite-rail weight-2 carry into TH34W2 is
  exactly what yields correct XOR.)
- **Raw-data recount** — re-parsed the 200 per-sample `.mt` files independently
  (no `analyze_fa.py`) with the same VDD/2 margins; functional count matched the
  sweep exactly.
- **NCL protocol** — confirmed every DATA phase asserts exactly one rail per
  input pair (valid codeword), every NULL phase is all-zero, a NULL separates
  every pair of DATA phases, and the measures cover all 8 vectors + RTZ.

## Findings

1. **The composed block is functionally robust to local Vt mismatch** — 0
   failures in 800 samples through 4× nominal, matching the single-cell result
   that DC/codeword levels are insensitive to mismatch.
2. **Completion latency σ scales ~linearly with mismatch** (8.7 → 17.6 → 26.9 →
   36.8 ps for kvt = 1→4, ≈ 9 ps per unit), consistent with the single-cell
   delay-σ trend.
3. **The mean latency drifts slightly upward** (397 → 404 ps) as mismatch grows —
   unlike the single-cell means, which stay flat. Completion is the *slowest of
   the parallel carry→sum paths*, so mismatch skews the max-path latency a little
   positive; the worst-case tail widens fastest (max 428 → 564 ps). This
   max-of-paths effect is the composed-block signature to watch as blocks deepen.

## Files

- `gen_fa_deck.py` — builds the dual-rail NULL/DATA deck + `.expected.json` truth map.
- `nclfa_mc.sp` — MC wrapper threading `kvt` down to the TH-gate instances.
- `mc_nclfa.cir` (+ `.expected.json`) — the parameterized `.SAMPLING` deck.
- `analyze_fa.py` — functional yield + completion-latency from the `.mt` files.
