# polysynth — synthesize a block every viable way, score it under the workload, pick

> "Take any block and synthesize it multiple ways, then pick the version that
> works best for the workload. In mylex we are looking to convert classic RTL
> to async (NCL) as well as convert software to async logic for a common
> backend flow."

Two deliverables live here:

* **A. The driver** — `polysynth.py`: (block, workload) → every viable variant
  → scored with the campaign's MEASURED cost models → comparison table + pick.
* **B. The common-backend IR contract** (§3 below): the one intermediate form
  both frontends — classic RTL today, software-to-async tomorrow — must land
  on, written down so a software frontend can target it.

Empirical selection: the `../SELECTION-RULE.md` hard gates are a **pruner**
(a structurally-illegal variant is never built), never the decider. The
decider is the score under the workload vector. Every figure is labelled
MEASURED / COMPOSED / DERIVED / ASSUMED; every variant EMITTABLE /
ANALYSIS-ONLY / INVALID-AS-EMITTED. UNDECIDABLE is a valid pick.

## 1. Usage

```
polysynth.py <rtl-or-netlist> <top>
    [--workload <module>@<kernel>[,<module>@<kernel>...]]    # permodule.json vectors
    [--duty D --alpha A [--alpha-ff F] [--burst B] [--ncyc N]]  # explicit vector
    [--out DIR] [--vcd FILE --vcd-scope tb/dut --op-ns 10]      # liberty power measurement
    [--gt sha_slice|alu_top]      # reproduce committed ground truth, ±2% gate
    [--json out.json] [--verify]  # QDI functional/delay-insensitivity checker
```

Workload vectors come from `/home/claude/vortex_energy/permodule.json`
(per-module × kernel duty2/alpha/burst from real Vortex runs) or explicitly.
Multiple vectors in one invocation → one table per vector, so pick movement is
visible in a single run.

Validation (both reproduce the committed ground truth, `--gt`, all PASS):

```
polysynth.py stat-sim/qal/synth/threeway/sha_slice.v sha_slice \
    --vcd .../threeway/work/cmos.vcd --op-ns 10 --duty 1.0 --alpha 0.476 --gt sha_slice
polysynth.py nulex/mapper/alu/work/alu.v alu_top \
    --workload alu_int@hello,alu_int@sgemm,fpu_unit@fpsat_fma --gt alu_top
```

| committed ground truth | polysynth | err |
|---|---|---|
| sha_slice sync 232 fJ/op @ 0.9281 ns (liberty+VCD) | 231.9 fJ @ 0.9281 ns | −0.03% |
| sha_slice QDI direct 2712 fJ @ 2.533 ns | 2713 fJ @ 2.533 ns | +0.02% |
| sha_slice QDI direct+CD 4385.7 fJ | 4385.8 fJ | −0.00% |
| alu_top sync 46.671 pJ/op (liberty, placed+CTS) | 46.675 (composed; instrument check) | +0.01% |
| alu_top QDI direct+CD+rings 523.7 pJ/op, 25,551 cells | 526.1 pJ, 25,555 cells | +0.45% |
| alu_top QAL band ~21–146 pJ | 20.6 (subtotal-lo) – 147.1 (total-hi) pJ | band ✓ |

## 2. Pipeline and what is reused

Nothing is re-derived; the coefficients and cost engines are imported from the
tools that measured them (the 4303.7-vs-4385.7 sum-of-pieces lesson).

1. **Frontend → shared IR.** yosys → generic-gate JSON, the exact
   `mapper/alu/synth_alu.ys` recipe; plus the word-level JSON (keeps `$add`)
   per `threeway/run_direct.sh` step 1.
2. **Prune** (`../SELECTION-RULE.md` §1, cited not restated): G-A register
   *cycles* via `map_ncl_struct.pipeline_stages()` (self-hold edges from the
   dfflegalize DFFE-fold are dropped — a self-hold is state, not a pipeline
   cycle, matching permodule.json `regs_in_cycles`); G-B cone-support census
   (word-level with `$add` cut as the Fant adder unit for comb blocks, generic
   otherwise; MAXSUP from `map_ncl_direct.py`); G-C arbitration (name-token
   heuristic, labelled); G-D `$mem`; G-E wire-dominance proxy → abstain.
3. **Emit** into `--out`:
   * **sync SG13G2** — sequential: the `alu_cmos/run_synth.sh:8-9` recipe
     (reproduces the committed `alu.cmos.v` byte-identical); combinational:
     `abc -liberty` over the shared generic IR (reproduces the committed
     `sha_slice.cmos.v` byte-identical). OpenSTA reports cells/area/critical
     path; with `--vcd`, liberty power (the committed 232 fJ basis).
   * **QDI direct-threshold (+CD tree)** — word-level `map_ncl_direct.py`
     when every cone fits, else `map_ncl_direct_gl.py --maxgates 1 --cd tree
     --cd-scope po` (census-identical to the committed `alu_direct_cdpo.v` —
     24,193 cells, same per-type counts — and cost-identical to 0.0003%
     (479,647.6 vs 479,646.3 fJ via `compose_alu.run`); net numbering differs,
     so NOT byte-identical);
     **QDI ring registers** for feed-forward blocks — the committed
     `regstage*.v` template (byte-identical), one boundary per pipeline stage,
     boundary *k* carrying the cumulative live state.
   * **DIMS for contrast** — `map_ncl_struct.py`, labelled INVALID-AS-EMITTED
     with its pinned-high hysteretic-cell count (616 on the ALU: cannot RTZ;
     the committed netlist never ran).
4. **Score** under the workload vector:
   * QDI/DIMS: `threeway/compose_alu.py` `run()`/`timing()` — the same
     measured per-arc E(C_L) and delay models as `compose_async.py`,
     whole-netlist costing; ring stages costed with the same measured arcs and
     the q-rails carrying their real downstream cloud loads. Per-op is
     activity-independent (RTZ); idle leakage band 58.5–155.7 pW/cell
     [ASSUMED band] charged over wall time.
   * sync: `vortex_energy/compose_energy.py` **imported** — its own
     instrument check runs at import and aborts on drift; `compose()` gives
     liberty + transistor-corrected columns per workload (gated floors on
     busy cycles, leakage over wall time).
   * QAL (ANALYSIS-ONLY): `compose_qal_alu.py` constants generalized to the
     emitted SG13G2 netlist — measured 1.343 fJ/gate-settle wp-weighted,
     switch-tax band 0.7–26 fJ/gate, ZCD 30–300 fJ [ASSUMED] × banks, DC-DFF
     term; admission by the §3 bank-partition DP (max-min bank, contiguous,
     span ≤ 4; bush = longest prefix whose best partition sustains
     N_min = 50; 50–400 → UNDECIDABLE; burst < 20 → fill/drain never
     amortize). Reported as the triple (E band, Θ = 2.924 Gop/s,
     t_fill = D×342 ps).
   * BD (ANALYSIS-ONLY): sync-minus-clock-tree + measured delay-line tax
     1.2–1.7%; controller ASSUMED; refused at tie-break (ii) — the
     matched-delay margin has no named discharger in this flow.
5. **Pick.** Lowest-energy EMITTABLE variant, hurdles from §3 of the rule
   (BD ≥ 1.3×, QDI ≥ 2×, QAL ≥ 3× across the full ZCD band). ANALYSIS-ONLY
   rows can only yield a printed research recommendation. A pick that never
   moves across workloads triggers an explicit red-flag check that must name
   the structural reason.

Measured on the two validation blocks: sha_slice → SYNC (QDI 11.7× worse on a
comb-only block — α\* undefined, clock-elimination buys nothing); alu_top →
SYNC under all three vectors, QDI 12.5× off, QAL verdict moving
EXCLUDED (burst 6.5, 5.5 < 20) → UNDECIDABLE (min-bank 63 in the 50–400 ZCD
band) at fpsat saturation, BD clearing its paper hurdle at saturation but
refused for the undischargeable margin.

**KNOWN DEFECT in the ALU EMITTABLE label (skeptic finding, 2026-09-26):**
the ALU QDI direct+CD netlist — polysynth-emitted AND the committed
`alu_direct_cdpo.v` identically — FAILS the campaign's own
`verify_alu_direct.py` input-completeness check (261–263/400 premature
`done`; 4-phase hazard and NULL-return checks pass). This is inherited
structure, not a polysynth regression: mux cones have no input-complete form
(`SELECTION-RULE.md:209-210`) and `--cd-scope po` completion does not observe
all inputs on a 43%-MUX block. The 523.7 pJ/op energy is unaffected, but
"EMITTABLE" for the ALU QDI row currently means *netlist exists and is
costed*, NOT *protocol-verified*. sha_slice passes the full verifier.
Until polysynth runs `--verify` on every emitted QDI variant and prints the
verdict in the row (top of the fix queue), read the ALU QDI maturity label
as EMITTABLE / CD-NOT-INPUT-COMPLETE.

**Known CLI limit:** the `<rtl-or-netlist>` JSON input path works for
comb-only blocks; for sequential blocks the sync emitter re-reads the source
with `read_verilog -sv` and crashes on `.json` input — pass RTL for
sequential blocks until the `read_json` route lands.

## 3. The common-backend IR contract (deliverable B)

**The IR is the yosys generic-gate JSON netlist** (`write_json`), and today
every binding already consumes exactly it: `map_ncl_struct.py` (DIMS +
sync-emu regs + desync), `map_ncl_direct.py` / `map_ncl_direct_gl.py`
(direct-threshold QDI), the sync flow (`dfflibmap`/`abc` → SG13G2), and the
analysis paths (`levelize_alu.py`, the census). A frontend that produces this
JSON gets every binding, the scoring stack, and the physical hand-off for
free. That is the contract a software-to-async frontend must target.

### 3.1 Form

One JSON document, `modules.<top>` containing:

* `ports`: `{name: {direction: input|output, bits: [net-id...]}}`. Net ids are
  integers; the strings `"0"/"1"/"x"` are constant bits.
* `cells`: `{name: {type, connections: {PIN: [net-id...]}}}` restricted to the
  **cell alphabet**:
  * combinational, 1-bit: `$_AND_ $_OR_ $_XOR_ $_XNOR_ $_NAND_ $_NOR_ $_NOT_
    $_MUX_` (pins A, B, S, Y) — the set `map_ncl_direct_gl.py` and
    `map_ncl_struct.py` dispatch on;
  * state: `$_DFF_P_` (C, D, Q) only — run
    `dfflegalize -cell $_DFF_P_ x; simplemap` so enables/resets are folded to
    logic (`synth_alu.ys`);
  * `$scopeinfo` is ignored; anything else is a contract violation (the
    mappers `sys.exit` on it).
* Canonical producing recipe (RTL frontend):
  `read_verilog -sv; hierarchy -check -top; proc; flatten; opt -full; techmap;
  opt -full; dfflegalize -cell $_DFF_P_ x; simplemap; opt_clean; write_json`.
* A comb-only block may additionally ship the **word-level** JSON (`proc;
  opt -nodffe -nosdff`) keeping `$add`, which the word-level QDI mapper
  expands as the proven Fant ripple adder instead of a cone.

### 3.2 Semantics the backend assumes (and checks)

* **Acyclic combinational graph** — every mapper topo-sorts and exits on comb
  loops (`compose_alu.topo`, `map_ncl_direct_gl.topo_cones`).
* **Registers define the phase structure.** `pipeline_stages()` assigns each
  `$_DFF_P_` a stage from the reg-to-reg dependency graph; cycles among
  *distinct* registers make pure 4-phase QDI illegal (hard gate G-A) and route
  the block to desync/sync. Self-hold loops (enable folds) are state, not
  cycles.
* **No memories, no arbiters in the IR.** `memory_map` lowering into the IR is
  a 43.6× retention mistake (SELECTION-RULE §0); SRAM and arbitration bind
  sync at the interface (G-C/G-D) and stay *outside* the block handed to this
  contract.
* **Boundary protocol is carried beside the IR, not inside it.** Channel
  contracts (encoding/completion/ack/phase/assumptions) are
  `../ASYNC-PLAN.md` §3; the executable counterpart is `../PIPES.md`. The IR
  is the *inside* of one contract-bounded block.

### 3.3 What a software frontend must do

`../ASYNC-PLAN.md` already reserves the seat: the C++ path is "an HLS-shaped
path to the same IR" (§5, deferred until the contract language stabilizes),
the contract language "should not assume an RTL-shaped source", and the
C-side channel representation is settled by PIPES.md — "a network socket is
the byte-pipe degenerate case of a channel, so C code speaks pipes of bytes
from day one". Nothing of it is implemented; what exists is this contract.

Concretely, a software frontend (compiled function, actor network, NN layer
via mylex) targets the backend by emitting, per contract-bounded block:

1. the generic-gate JSON of §3.1 for the block body (dataflow → gates;
   loop-carried state → `$_DFF_P_` so the phase structure is explicit);
2. a channel contract per boundary (ASYNC-PLAN §3 fields; ack-less sidebands
   must be declared — they are partition constraints);
3. optionally the word-level JSON if it wants the Fant adder treatment.

`polysynth.py` then applies unchanged: prune → emit sync/QDI/DIMS → score
sync/QDI/QAL/BD under the deployment workload vector → pick. The pick is
per-block, which is the GALS premise: different blocks of one program bind
differently, and that is the normal case.

### 3.4 Known limits of the contract (stated, not hidden)

* Single-clock `$_DFF_P_` only; multi-clock and latches are outside.
* The IR carries no placement/wire information, so G-E (wire dominance) can
  only abstain here — `stat-sim/klayout2spef.py` closes that loop post-layout.
* Level-profile shape is a synthesis choice, not a block property (2×/10×
  spread measured); QAL admission read from one netlist must re-synthesize
  for balanced levels before declaring ineligibility (SELECTION-RULE §7).
* The scoring coefficients are calibrated on the physical SG13G2 ALU anchor;
  transfer to very small or interconnect-shaped blocks is out of regime and
  the table says so where it applies.

## 4. Files

* `polysynth.py` — the driver (this directory).
* Outputs per run (`--out`): `<top>.gates.json` (the IR), `<top>.word.json`,
  `<top>.cmos.v` + stat, `<top>.qdi_direct*.v` (+ census), `regstage*.v`,
  `<top>.dims.v`, `<top>.levels.json`, OpenSTA tcl/logs,
  `compose_energy_import.log`, and `--json` results.
* Cost engines (imported, not copied): `stat-sim/qal/synth/threeway/
  {compose_alu.py, compose_qal_alu.py, cost_inputs.py, levelize_alu.py}`,
  `/home/claude/vortex_energy/compose_energy.py`.
