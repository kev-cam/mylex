# frontends/c_expr.py — B0 software frontend (C → expression DAG → comb Verilog)

*2026-09-26. The first rung of the software-to-async ladder scoped in
`../../COMMON-BACKEND.md` §3.1/§3.3 (build-order step **B0**): a pure C
function of fixed-width unsigned ints becomes one combinational Verilog
module that the EXISTING producer recipes and backends consume unchanged.
Nothing downstream changed to make this work (one latent backend bug aside —
§5). Acceptance was reproducing the committed `sha_slice` ground truth from a
C source, and it holds: same numbers whether the block arrives as Verilog or
as C.*

## 1. What it does

```
c_expr.py <src.c> <func> [-o out.v] [--meta out.meta.json]
    [--check N | --exhaustive]   # software-oracle harness (gcc+clang vs iverilog)
    [--workload JSON]            # M3 passthrough into the metadata sidecar
    [--naive-widths]             # promotion-bug demonstrator -- never for real use
```

* parses the C with **pycparser** (3.00 on this box; `fake_libc/stdint.h` is
  for PARSING only — the oracle compiles the same source against the real
  system headers), after gating the source through `gcc -fsyntax-only`:
  the input artifact must be genuine C;
* builds a hash-consed **expression DAG** carrying C-semantic bookkeeping per
  node (promoted width, signedness, value bound `vmax`, may-be-negative);
* emits **one comb Verilog module** (ports = the C signature: value params →
  inputs, pointer params / return value → outputs) plus the **M1–M5 metadata
  sidecar** (`<out>.v.meta.json`, per COMMON-BACKEND.md §2.8 — M5 provenance
  carries producer+source sha256, because level-profile shape is a synthesis
  choice, not a block property).

Accepted subset (B0 exactly): `& | ^ ~ + - * << >> ! && || < > <= >= == !=
?:`, casts to `(uintN_t)`, integer constants, `uintN_t` locals with
initializers, single-assignment outputs. No loops / control flow / memory /
calls / floats — those are B1+ in the COMMON-BACKEND.md §3.3 build order, and
each is rejected by name.

## 2. The width model (where C frontends go wrong)

C promotes `uint8_t` to 32-bit signed `int` before every operator; the store
back to a narrow type truncates. The DAG models exactly that (forward pass),
then a backward **demanded-width pass** narrows emission where it is provably
semantics-preserving: truncation commutes with `& | ^ ~ + - * <<`, and the
`vmax` bound makes zero-extension exact. Result: `*sum = (uint8_t)(a + b)`
emits an 8-bit `$add` (the natural netlist), while
`((a + b) >> 4) & 0x1F` emits the 9-bit add it actually needs.

Where C semantics stop being expressible in unsigned hardware the frontend
REFUSES with the fix named, instead of guessing: possible signed overflow
(UB — e.g. `uint16*uint16`), `>>` on a possibly-negative int
(implementation-defined), ordered compares on possibly-negative ints
(needs a signed comparator; B0 gap). `--naive-widths` deliberately mis-models
promotion (every op at its storage width — the classic transliteration bug)
so the harness can demonstrate the oracle catching it.

**The compiled C is the arbiter.** `--check N`/`--exhaustive` compiles the
source with gcc AND clang (they must agree — a disagreement means the C
itself is unspecified), simulates the emitted Verilog with iverilog on
corners + N random (or the exhaustive space ≤ 2^20), and compares bit-exact.

## 3. Verified results (2026-09-26, this box)

| check | result |
|---|---|
| `sha_slice.c` oracle (gcc==clang==iverilog) | 200,008/200,008 agree; corner 0xFF+0xFF → sum 0xFE |
| formal equivalence C-emitted vs reference `threeway/sha_slice.v` | yosys miter+SAT: **UNSAT = SUCCESS** (1039 vars, 2660 clauses) |
| iverilog differential vs reference | 200,001 vectors, 0 errors |
| shared-IR word census | identical to RTL-origin: `$add`×1 (8-wide) `$and`×5 `$xor`×3 `$not`×1 |
| mapped SG13G2 netlist | **byte-identical** to the RTL-origin `threeway/work/sha_slice.cmos.v` (on disk, UNTRACKED in stat-sim git — as is `cmos.vcd`; the GT *numbers* are what is committed, in POLYSYNTH.md and polysynth's GT table), so that VCD annotates the C-origin netlist legitimately |
| QDI netlists | **byte-identical** to the git-committed `sha_slice_direct_spice.v` / `_cd.v` (match HEAD); `verify_direct.py` PASS |
| polysynth `--gt sha_slice` from the C source | **ALL PASS**: sync 231.9 fJ (−0.03%), 0.9281 ns (+0.00%), QDI 2713 fJ (+0.02%) @ 2.533 ns, QDI+CD 4385.8 fJ (−0.00%) |
| `popcount4.c` (2nd function, not in the GT set) | exhaustive 256/256 oracle; yosys SAT SUCCESS vs behavioral ref; polysynth end-to-end (pick SYNC; QDI 46 TH cells) ; QDI netlist 256/256 exhaustive functional+well-formed via `verify_direct.Net` |
| `promo_trap.c` promotion trap | correct mode 65,540/65,540; `--naive-widths` caught: 32,641 mismatches (65,536 exhaustive: the 32,640 pairs with a+b ≥ 256, + the duplicated ff/ff corner), first at a=b=0xFF (C 31 vs buggy 15) |

Reproduce: `frontends/work/` holds the runs; the polysynth invocation is the
documented one (`../POLYSYNTH.md` §1) with `sha_slice_c.v` as the source.

## 4. Files

* `c_expr.py` — the frontend (the only new code in B0).
* `fake_libc/stdint.h` — pycparser parse shim (never affects semantics).
* `examples/sha_slice.c` — the natural-C SHA slice (Maj/Ch/CPA, FIPS 180-4
  shapes); the B0 acceptance block.
* `examples/popcount4.c` — second end-to-end function (shift/mask/adder-tree
  shape sha_slice doesn't have).
* `examples/promo_trap.c` — the distilled integer-promotion trap.
* `tests/` — the formal-check fixtures: `equiv_sha.ys` / `equiv_pc4.ys`
  (yosys miter+SAT; run from `work/` after emitting), `pc4_ref.v`
  (behavioral popcount reference), `diff_tb.v` (200k iverilog differential;
  needs `gold_ref.v`/`gate_c.v` module-renamed copies in cwd),
  `check_pc4_qdi.py` (exhaustive QDI functional check via
  `verify_direct.Net`).
* `work/` — emitted Verilog, sidecars, oracle harnesses, polysynth outputs;
  NOT committed (`nulex/.gitignore` excludes all `work/`), regenerable:
  `cd work && python3 ../c_expr.py ../examples/sha_slice.c sha_slice -o
  sha_slice_c.v --check 200000`.

## 5. Findings & open gaps (stated, not hidden)

1. **FIXED (backend, this campaign): `map_ncl_direct.py` `$add` ragged
   widths.** yosys `$add` semantics extend A/B to `Y_WIDTH`; every RTL-origin
   block happened to emit equal widths, so the Fant expansion indexed `A[i]`
   off the end on the C-origin popcount (`1+1 → 2-bit Y`) and crashed. Fixed
   by zero-padding unsigned operands with constant rails (the same treatment
   the bitwise ops already had; signed extension still refuses loudly).
   Regression-guarded: both C-origin and RTL-origin `--gt sha_slice` ALL PASS
   after the fix, and all three sha netlists remain byte-identical.
2. **OPEN (backend): `verify_direct.py` is sha_slice-specific.** Its TH-cell
   netlist simulator (`Net`) is generic, but `main()` hardwires ports a–g and
   the sha reference. polysynth `--verify` on any other word-route block
   prints the header line and dies. popcount4's QDI netlists were checked
   exhaustively (functional + rail well-formedness) by reusing `Net`
   (`tests/check_pc4_qdi.py`); the full 4-phase hazard/NULL-return machinery
   generalization is the backend's own fix-queue item (POLYSYNTH.md flags it).
3. **OPEN (frontend, skeptic-found): compare-with-constant emission bug**
   (`c_expr.py:541-542`). The emit-side context width for
   `== != < <= > >=` treats a `const` operand as width 1
   (`emit_w(a) if a.op != "const" else 1`), then `ref()` masks the constant
   to that width. Two silent-miscompile manifestations, both repro'd and both
   caught by the shipped oracle (exit 1): (i) const-vs-const —
   `a & 0xF == 1` (C precedence: `a & (0xF==1)`) emits
   `1'h1 == 1'h1` → always-true, 130/259 oracle mismatches; (ii) const wider
   than the other side's provable maxbits — `(a & 0xF) == 0x10` (always false
   in C) emits `w2 == 4'h0` → true on low-nibble zero, 17/259 mismatches.
   The demanded-width pass (`c_expr.py:464-468`) is sound; only the emit-side
   `cw` is wrong. Fix is local (include const `maxbits()` in `cw`; ideally
   constant-fold const-cmp-const). **No GT deliverable contains a compare**,
   so B0 results are unaffected — but until fixed, compare-bearing C is
   trustworthy only WITH the oracle gate, and this MUST be fixed before B1
   (if-conversion routes compares into `$_MUX_` selects).
4. **B0 refusals are features**: signed-overflow UB, signed `>>`, ordered
   signed compares — each rejected with the cast that fixes it. The oracle
   (real compilers) stays the arbiter of everything accepted.
5. M3 workload profiling of software (call rate → duty/busy, operand toggles
   → alpha) is B2; `--workload` is passthrough only today.
