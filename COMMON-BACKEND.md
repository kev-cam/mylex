# COMMON-BACKEND.md — The Common-Backend IR Contract

*2026-09-26 · companion to `ASYNC-PLAN.md` (§1, §3, §5), `SELECTION-RULE.md`
(gates + bindings), and `PIPES.md` (executable channel semantics). Written from
the code and artifacts on disk — every load-bearing claim carries a file:line —
not from intent. Uncommitted; working draft.*

**The product this serves** (architect, verbatim): *"take any block and
synthesize it multiple ways, then pick the version that works best for the
workload … convert classic RTL to async (NCL) as well as convert software to
async logic for a common backend flow."* Two frontends, one backend. This
document writes down the contract of the seam: the intermediate representation
that classic-RTL and (future) software-to-async frontends both target, and that
every binding — sync SG13G2/sky130, QDI direct-threshold, DIMS, desync, and the
analysis-only BD/QAL models — already consumes or is specified against.

**Layering, stated up front so this does not fight ASYNC-PLAN.** ASYNC-PLAN §1
plans an *NCL-semantics IR with channel contracts as first-class objects*; that
contract language is milestone P1 and remains open (`ASYNC-PLAN.md:101-144`).
This document pins the layer BELOW it: the **module-interior datapath IR** that
exists and runs today — yosys generic-gate JSON — plus the boundary/handshake
shapes each binding concretely exposes. The P1 channel-contract layer attaches
at this IR's module boundary; §2.7 below is the inventory of concrete
refinements the P1 language must be able to express. Nothing here forecloses
P1; everything here is falsifiable against code on disk.

---

## 1. What ASYNC-PLAN.md already says about software-to-async (read in full)

The whole 593-line plan was read start to finish for this document. What it
contains on the software path:

- **Multiple frontends are the founding premise.** *"It accepts multiple
  frontends (SystemVerilog RTL first, C++ and neural-model paths later),
  represents designs in an NCL-semantics IR, and lowers each design boundary to
  whatever implementation that boundary actually requires"*
  (`ASYNC-PLAN.md:4-8`).
- **The C++ frontend is planned, deferred, and already constrains the contract
  layer:** *"An HLS-shaped path to the same IR. Deferred; the contract language
  must stabilize first. Noted here because it constrains §3 — the contract
  language should not assume an RTL-shaped source. The C-side channel
  representation is settled by `PIPES.md`: a network socket is the byte-pipe
  degenerate case of a channel, so C code speaks pipes of bytes from day one."*
  (`ASYNC-PLAN.md:314-321`). Also scoped out of the current repo phase:
  *"C++ frontend (planned, deferred — see §5)"* (`ASYNC-PLAN.md:98`), and
  sequenced *"Post-P6: C++ frontend, mylex IR convergence, composition-level
  liveness, FPU binding decision"* (`ASYNC-PLAN.md:501-502`).
- **The nearest thing to a software-conversion scope question is §10.3:**
  *"'LLM → async logic' scope. Whether this means large language models
  specifically (transformer inference in async), or the neural-model path
  generally that mylex already covers"* (`ASYNC-PLAN.md:536-539`) — an open
  blocking unknown, not a design.
- **"Wandering threads": ZERO occurrences.** `grep -rn -i wandering
  /usr/local/src/mylex/` returns nothing — not in ASYNC-PLAN.md, PIPES.md, or
  anywhere else in the repository. If that phrase names an intended mechanism,
  it exists only outside this repo; nothing is built on it here and this
  document does not invent content for it.
- **Where a software frontend must live:** the plugin-boundary directive
  (`ASYNC-PLAN.md:294-312`) — mylex-side `.so` over a stable C ABI, never
  in-tree in GPL nvc — applies to any new frontend the same way it applies to
  the NCL emitter.

Nothing is implemented for software-to-async. §3 below scopes it honestly,
building on the three commitments above: same IR, contract language must not
assume RTL-shaped sources, channels are pipes.

---

## 2. The IR contract

### 2.1 Container (normative, de facto today)

The IR is a **yosys `write_json` netlist file** (Yosys 0.58 on this box). A
conforming file has, for the named top module `d["modules"][top]`:

- `ports`: `{name: {"direction": "input"|"output", "bits": [net|"0"|"1", ...]}}`
- `cells`: `{name: {"type": <cell>, "connections": {PIN: [net|"0"|"1", ...]}}}`
- nets are integers; constant bits are the strings `"0"` and `"1"` only
  (`map_ncl_struct.py:111-121` exits on any other constant; the sync flow runs
  `setundef -zero`, `alu/pnr/synth_sky130.ys:8` — **no x/z in the IR**)
- `$scopeinfo` cells are permitted and every consumer skips them
  (`map_ncl_struct.py:96-97`, `map_ncl.py:117`, `map_ncl_direct.py:365-366`).
  They are never counted as logic — the circulated "4,726 cells" for alu_top
  counted 5 of them; the real number is 4,721 (`SELECTION-RULE.md:11-13`).

Every consumer in the flow reads exactly this: `map_ncl.py:38-42`,
`map_ncl_struct.py:80-84`, `map_ncl_direct.py:350-354`, `map_actor_c.py:36-38`,
`map_plain.py`, `map_ncl_direct_gl.py`.

### 2.2 Two profiles

| profile | cell vocabulary | producer recipe on disk | consumers |
|---|---|---|---|
| **IR-BIT** (base) | `$_AND_ $_OR_ $_XOR_ $_XNOR_ $_NAND_ $_NOR_ $_NOT_ $_MUX_` + `$_DFF_P_` (`$_BUF_` tolerated but deprecated: `map_ncl_direct_gl.py` exits on it — its handled set is `$_NOT_`/`$_MUX_`/GATE2 only, `:223`; the canonical recipe's `opt_clean` strips buffers, so producers must not rely on `$_BUF_` surviving) | `proc; flatten; opt -full; techmap; opt -full; dfflegalize -cell $_DFF_P_ x; simplemap; opt_clean; write_json` (`nulex/mapper/synth.ys`, `synth_seq.ys`, `alu/synth_alu.ys`) | `map_ncl.py`, `map_ncl_struct.py`, `map_ncl_direct_gl.py` (no `$_BUF_`), `map_actor_c.py`, `map_plain.py` |
| **IR-WORD** (direct-threshold) | word-level `$and $or $xor $xnor $not $mux` + **`$add`** (kept), plus the IR-BIT comb set | `proc; opt -nodffe -nosdff; write_json` (`stat-sim/qal/synth/threeway/run_direct.sh:16-17` — "keeps $add for the Fant adder") | `map_ncl_direct.py` (BITOPS at `:358-362`, `$add` at `:367-370`) |

IR-WORD exists because decomposing to 2-input gates first *destroys the natural
threshold form* — a 3-input majority that IS one TH23/rail becomes 12 TH22 + 3
collectors (`map_ncl_direct.py:4-11`); `$add` maps to the proven Fant ripple
adder, cout=TH23 / sum=TH34W2 (`map_ncl_direct.py:36-38`,
`lib/ncl_gates.vhd:197-200`). IR-WORD is combinational-only today
(`map_ncl_direct.py:371` exits on any cell outside BITOPS/$add).

A frontend MUST emit only the profile vocabulary. Consumers MAY accept
supersets (one does — §4), but a frontend that leans on a superset is
non-conformant.

### 2.3 What `$_DFF_P_` means — the re-bindable register semantic

`$_DFF_P_` in this IR is **not a flip-flop cell commitment**. It denotes the
synchronous-register *semantic*: "capture D into Q at each successive wavefront
of the module's single time base." Bindings re-bind it; that is the proven core
of the common backend:

| `--reg` / flow | what `$_DFF_P_` becomes | where |
|---|---|---|
| sync (liberty) | edge-triggered stdcell flop via `dfflibmap`/`abc` | `alu/pnr/synth_sky130.ys:4-6` |
| sync-emulation NCL | `ncl_dff` clocked dual-rail latch | `map_ncl.py:32`, `map_ncl_struct.py:213` |
| `--reg qdi` | per-stage 4-phase RTZ TH22 latch bank + balanced C-element completion tree, stage = register-to-register depth | `map_ncl_struct.py:242-284` |
| `--reg desync` | `ncl_reg_desync` bank captured by a matched-delay completion clock | `map_ncl_struct.py:228-241` |
| actor (software sim) | firing rule: register fires only when D changed since last capture | `map_actor_c.py:1-11` |

Constraints that travel with the semantic:

- **Exactly one DFF type.** Reset, enable, and sync-set/reset are folded into D
  logic by the producer (`dfflegalize -cell $_DFF_P_ x`); `map_ncl.py:126-128`
  rejects every other variant with exactly that instruction. Initial value is
  undefined (`x` in the dfflegalize call) — no binding promises a power-up
  value (QDI cells have no reset pin at all: `SELECTION-RULE.md:294-296`).
- **Re-binding to QDI is legal only for feed-forward register graphs.**
  `pipeline_stages()` raises on any register cycle
  (`map_ncl_struct.py:342-343`) — this is hard gate G-A
  (`SELECTION-RULE.md:45-55`). The IR may *contain* cycles; the pruner then
  restricts the binding set to sync/desync.

### 2.4 Clock intent (single time base)

Clock nets are **inferred, not declared**: any net feeding a DFF `C` pin is a
clock and stays single-rail (`map_ncl_struct.py:87-91`, `map_ncl.py:44-47`).
The contract makes the discipline explicit:

- A conforming module has **zero clocks** (pure comb) **or one clock domain**.
  A frontend must guarantee the clock net drives only `C` pins and appears as a
  1-bit input port. (The inference rule is what all consumers implement; an
  explicit `clk` port-name convention is advisory, not load-bearing.)
- **Multi-clock is forbidden inside one IR module.** No async binding defines
  semantics for two time bases in one module; the proving target is essentially
  one clock domain anyway (`ASYNC-PLAN.md:364-365`). Multi-domain designs split
  at module boundaries, and the boundary binds per `SELECTION-RULE.md` §5A
  (sync↔sync with 2-FF synchronizers, or BD handshake) — noting the arbiter/
  synchronizer cell gap (G-C, `SELECTION-RULE.md:67-71`).

### 2.5 Memory: `$mem` stays `$mem` — `memory_map` is forbidden

**A frontend or producer script MUST NOT lower memories to flops.** Memories
stay `$mem`/`$memrd`/`$memwr` (or an instantiated macro blackbox) in the IR,
and the block binds per hard gate G-D: **sync at the memory interface,
unconditionally** (`SELECTION-RULE.md:73-79`).

The measured reason (`SELECTION-RULE.md:38`): the current exec flow runs
`memory_map` (`nulex/mapper/exec/synth_exec.ys:4`), *"turning a 256×8 into
2048 DFFs — 43.6× the macro's retention leakage plus a clock floor where the
macro's is exactly zero."* The 43.6× is MEASURED: SRAM retention 12.09 pW/bit
vs a DFF's 526.5 pW/bit (`SELECTION-RULE.md:297-298` [M]). A netlist produced
with `memory_map` is labeled **NON-CONFORMANT (memory-expanded)** and any
energy figure computed from it carries that label. (Consequence for the
existing exec artifact: §4.)

The `$mem` island is *opaque to bindings today* — `bindings/sram.py` does not
exist (T2, `SELECTION-RULE.md:38`), and the SRAM has no completion signal
(`SELECTION-RULE.md:77-79`), so the memory boundary is forced to matched-delay
or a clocked domain regardless of what surrounds it.

### 2.6 Everything else forbidden in the IR

1. **Latches** (`$_DLATCH*`): every consumer rejects them
   (`map_ncl.py:126-128`; `map_ncl_struct.py:215-217` "unhandled cell types …
   fold with dfflegalize/simplemap first").
2. **DFF variants** other than `$_DFF_P_` (§2.3). `map_actor_c.py:58-60`
   tolerates `$_DFF_PN0_` as a consumer extension; frontends must not emit it —
   every other consumer exits on it.
3. **`memory_map`** (§2.5).
4. **Multi-clock** within a module (§2.4).
5. **Tri-state / `inout` / multi-driver nets**: no consumer models resolution;
   Vortex confines `tri`/`inout` to 2 files (`ASYNC-PLAN.md:364-365`) and they
   stay outside converted regions.
6. **x/z constants** (§2.1).
7. **Unlowered behavioral content** (`$proc`, `$dff` word-level, `$pmux`,
   `$shift`, …): producers run `proc/techmap/simplemap` (IR-BIT) or
   `proc/opt` with the IR-WORD whitelist; consumers exit by name on anything
   else (`map_ncl_struct.py:215-217`, `map_ncl_direct.py:371`).

### 2.7 Boundary and handshake semantics per binding

The rail convention, single-sourced (it is a known divergence trap — the ldx
VHDL packages carry the value on the L rail while the asic SPICE cells carry it
on H, `ASYNC-PLAN.md:216-219`): **as emitted by both NCL mappers, `.L` is the
value-1 (t) rail and `.H` the value-0 (f) rail; DATA0=(L0,H1), DATA1=(L1,H0),
NULL=(0,0)** (`map_ncl_struct.py:26-27`; SPICE identically,
`map_ncl_struct.py:395-397,413-414`).

| binding | maturity (`SELECTION-RULE.md` §0) | port shape at the module boundary | handshake obligation on the environment |
|---|---|---|---|
| SYNC | T0 | ports as declared; 1-bit clock input | clocked; source RTL's own valid/ready |
| QDI direct-threshold comb | T0 (cone support ≤ 4) | each data bit → rail pair `p_L`/`p_H` (Verilog) or `ncl_logic` (VHDL); optional `done` output with `--cd chain|tree` | 4-phase RTZ: environment presents NULL between DATA wavefronts; consume outputs on `done` (or per-bit is-DATA). Input-completeness is proven+repaired per netlist (`map_ncl_direct.py:43-49` and the repair pass `:495-513`) |
| QDI pipeline registers | T1 | adds `ki_in` (in), `ko_out`, `ko_in` (out) (`map_ncl_struct.py:248-249`); stage request `ki_s = NOT(ko_{s+1})` (`:256`) | environment drives `ki_in` as the downstream ack and observes `ko_out/ko_in` completions; 3W+(W−1) TH cells/stage cost, no scan (`SELECTION-RULE.md:35`) |
| DESYNC | T1/T2 | adds `done` output = the local matched-delay clock (`map_ncl_struct.py:235`) | **this is bundled-data with a local clock**, not QDI (`SELECTION-RULE.md:36`, `ncl_reg_desync.vhd:25`); matched-delay margin must be discharged (`ASYNC-PLAN.md:151-157`) |
| SPICE phys | T0 comb-only | node pairs `n*_L/_H` + `VDD/VSS`; sequential rejected (`map_ncl_struct.py:178-180,207-209`) | as QDI comb, at transistor level |
| DIMS | emitted but **INVALID-AS-EMITTED** | as QDI comb | never ran: 616 constant-pinned hysteretic cells on alu (`SELECTION-RULE.md:59-64`); polysynth may emit for cost contrast only, so labeled |
| BD / QAL | T2 — **no toolchain** | none exists | ANALYSIS-ONLY from measured models (`SELECTION-RULE.md:37,40`) |

**Ack-less sidebands are first-class and must be declared** (§2.8 M4): a
valid-only broadcast with no ack (Vortex `branch_ctl_if`, and the whole family:
warp-control pulses, CSR bundles, credit returns, `ASYNC-PLAN.md:394-401`)
cannot be converted to a handshake and acts as a partition constraint
(`SELECTION-RULE.md:266-268`, 668 bits on Vortex). The P1 contract language
must express an ack-less channel; until it lands, the IR carries the
declaration as metadata and the pruner treats such boundaries as sync.

### 2.8 Metadata a frontend must supply

M1 and M2 live in the JSON itself; M3–M5 ride alongside (a sidecar JSON today;
the polysynth driver defines the exact filename).

- **M1 — top + ports.** Module name; every port with direction and bit width
  (the `bits` arrays). Boundary widths come from here — they price partitions
  (`SELECTION-RULE.md:262-266`: *"price partitions by measured cut bits, never
  island count"*).
- **M2 — clock intent** per §2.4: zero or one clock, clock net drives only `C`
  pins.
- **M3 — workload vector.** Either a module name resolving into
  `/home/claude/vortex_energy/permodule.json` (verified shape: 25 modules;
  `modules[name].dynamic[kernel]` carries `nbits, toggles, alpha,
  alpha_on_busy2, duty2, busy2_cycles, duty1, nbursts2, mean_burst2,
  work_weighted_burst2, max_burst2`; `modules[name].static` carries `comb, seq,
  mem, mux_pct, depth_D, W_eff, cyc_frac_pct, max_reg_stage, bank_profile, mix,
  cut_bits, …`) or an explicit `{duty, alpha, alpha_ff, burst}` vector. The
  durable store is **(busy, toggles, burst histogram) plus one global T —
  never duty** (`SELECTION-RULE.md:269-273`: duty self-invalidates under
  re-binding; busy and toggles are invariant to ~2%). This is exactly what the
  scoring engine consumes: `compose(name, k, static, alpha, busy, nbits, ncyc,
  alpha_ff, mix, etree)` (`stat-sim/gpu/vortex_energy/compose_energy.py:216-217`),
  and the async side costs whole netlists per-instance/per-arc
  (`stat-sim/qal/synth/threeway/compose_async.py:1-22` — never sum-of-pieces;
  the 4,303.7-vs-4,385.7 fJ lesson, `SELECTION-RULE.md:350-352`).
- **M4 — sideband declaration**: which output ports are ack-less broadcasts
  (§2.7).
- **M5 — producer provenance**: the synthesis script identity (name + hash)
  that produced the JSON. Mandatory because **level-profile shape is a
  synthesis choice, not a block property** — two synths of the same RTL
  disagree 2× on depth, 10× on tail mass, and give *opposite* QAL verdicts
  (`SELECTION-RULE.md:362-367`); a scored result is meaningless without naming
  the netlist it was scored on.

### 2.9 What is deliberately NOT in this contract

The channel-contract language (encoding/completion/ack/phase/assumptions,
`ASYNC-PLAN.md:107-136`) and its refinement checker: that is P1 and must not be
pre-empted by a datapath document. Likewise pipe semantics (PIPES.md is the
executable counterpart, `ASYNC-PLAN.md:140-144`). This contract only inventories
the concrete boundary shapes (§2.7) that P1 must be able to describe.

---

## 3. The software frontend, scoped honestly

**What it is.** Converting software to async logic = compiling a
dataflow/CFG into the §2 IR, then letting the SAME backends and the SAME
polysynth scoring drive it. Nothing about the backend changes; the entire
deliverable is a producer.

**What exists on this box that helps (checked 2026-09-26):**

- **Yosys 0.58 cannot do this** — it has no C/software frontend. Its role stays
  producer-from-Verilog.
- **CIRCT / Calyx / futil / Bambu / Vitis-HLS / XLS: NOT PRESENT.** `which`
  finds none of them and `/usr/local/src` has no checkout. If one were adopted,
  Calyx/CIRCT emit Verilog anyway — it would re-enter the flow through the same
  §2.2 producer scripts, so **the IR contract is unaffected by that choice**.
  Adoption would drag MLIR/Rust into a deliberately self-owned federation
  (`ASYNC-PLAN.md:329-343`); a tiny in-house compiler is smaller than the
  integration for the demo scope below.
- **`PIPES.md` settles the channel model for software** — quoted in §1: C code
  speaks pipes; a pipe is the executable channel contract, and
  `pipe#(T)(capacity=>N)` IS the sync-emulation binding of a channel
  (`PIPES.md` §1.3). Function-boundary handshakes have defined semantics before
  a line of the frontend exists.
- **`nulex/map_actor_c.py` is the reverse direction already built** — the IR
  walked into event-driven C with register firing rules
  (`map_actor_c.py:1-11`). It is the semantic bridge: the forward compiler's
  job is to produce an IR whose actor semantics match the source function.
- **The plugin boundary** (`ASYNC-PLAN.md:294-312`): a software frontend is
  mylex-side, PolyForm-licensed, never in-tree in GPL tools.

### 3.1 The smallest viable demo (B0)

**A pure function → dataflow DAG → comb Verilog → existing producer → both
emittable backends → polysynth table.** Concretely:

1. Write the SHA slice (Maj + Ch + 8-bit CPA) as a plain C or Python function —
   the *same function* as the committed validation block `sha_slice`
   (`SELECTION-RULE.md:339-353`).
2. New code: an expression-DAG compiler over the language's own AST (Python
   `ast` is stdlib; pure expressions, fixed-width integers) emitting one
   combinational Verilog module. ~200–400 lines. **This is the only new code
   in B0.**
3. Existing producer: `run_direct.sh`-style word-level synth (IR-WORD, keeps
   `$add`) and `synth.ys` (IR-BIT).
4. Existing backends: sync liberty flow + `map_ncl_direct.py --cd tree`.
5. Acceptance test, and the reason this demo is the right one: **the
   software-origin netlist must reproduce the committed RTL-origin ground truth
   within stated tolerance** — CMOS 232 fJ @ 0.928 ns liberty-basis, QDI-direct
   2,712 fJ @ 2.533 ns, +CD 4,385.7 fJ @ 4.021 ns (`SELECTION-RULE.md:346-352`
   [M/C]). Same numbers from a C source and a Verilog source = the
   frontend-independence of the backend, demonstrated, not asserted.

Effort: **S (days).** Everything except step 2 exists and is green on disk.

### 3.2 The hard parts (named, with the honest gate each hits)

1. **Control flow → handshake.**
   - `if/else` on data: if-conversion to `$_MUX_` — free, already in the
     vocabulary.
   - Fixed-bound loops: unroll (pure dataflow), or pipeline with `$_DFF_P_`
     stages — legal feed-forward, G-A green by construction.
   - **Data-dependent `while`: a token-recirculating loop = a register cycle.**
     G-A then correctly forbids pure QDI (`map_ncl_struct.py:342-343`); the
     only stateful-async route is desync, which IS bundled-data with a local
     clock (`SELECTION-RULE.md:36`). The IR *expresses* it; the pruner
     *restricts* it — that is the system working, not a frontend failure. A
     feed-forward-only frontend still covers the north-star streaming/GPU-lane
     workloads, which is where the throughput win lands anyway.
2. **Memory.** Arrays → `$mem` + G-D sync interface (§2.5). `bindings/sram.py`
   does not exist (T2), so memory-bearing functions are **ANALYSIS-ONLY today**
   and say so in their scorecard.
3. **Recursion.** Unbounded recursion has no representation (no stack in the
   IR). Bounded recursion = inlining, a compiler transform. Not promised.
4. **Shared functions / re-entrancy.** Two callers of one hardware instance =
   arbitration = G-C sync, unconditionally (`SELECTION-RULE.md:67-71` — no
   mutex cell exists). Default: inline per call site.
5. **The workload vector for software.** M3 must come from *profiling the
   function* (call rate → duty/busy, operand toggle profile → alpha) — new
   instrumentation with no RTL analogue. Without it polysynth can only score
   the structural gates, and a workload-independent pick is a red flag by
   doctrine.

### 3.3 Build order (labels, not promises)

| step | content | effort | gate |
|---|---|---|---|
| B0 | pure-expression compiler → comb Verilog → IR-WORD/IR-BIT; reproduce the committed `sha_slice` table from a C source | **S** (days) | none — all pieces exist |
| B1 | fixed-bound loops (unroll), width inference, optional pipelining directive → `$_DFF_P_` stages; `pipeline_stages()` green = feed-forward proof | **M** (~week) | none structural |
| B2 | function boundary = channel: valid/ready wrapper (sync binding) and `ki/ko` (QDI reg binding, ports already emitted `map_ncl_struct.py:248-249`); PIPES token semantics; software profiling → M3 vector | **M** | P1 contract ADR shapes the boundary metadata |
| B3 | data-dependent `while` via token recirculation; desync/sync bindings only | **L** | gated on the desync register bank actually running (`--reg desync` is VHDL-only, `map_ncl_struct.py:233`; cyclic logic currently `SystemExit`s the QDI path `:342-343`) |
| B4 | arrays → `$mem` + G-D sync memory interface | **L** | **blocked** on `bindings/sram.py` (T2, `SELECTION-RULE.md:38`) — ANALYSIS-ONLY until then |
| — | recursion, pointers-as-data, dynamic allocation, concurrency primitives | not promised | out of scope by construction |

---

## 4. Cost of this contract to the existing RTL flow — verified consumer by consumer

**Code changes required: ZERO.** The contract was written FROM the mappers, not
at them. Verified against §2:

| component | verdict | evidence |
|---|---|---|
| `nulex/map_ncl.py` | conforms (IR-BIT + `$_DFF_P_`); rejects everything else with the dfflegalize instruction | `:25-32,126-128` |
| `nulex/map_ncl_struct.py` | conforms; all three `--reg` bindings are §2.3 re-bindings; exits by name on vocabulary violations | `:42-49,206-217,228-284` |
| `nulex/map_ncl_direct.py` | conforms (IR-WORD); enforces MAXSUP=4 = hard gate G-B | `:81,358-370,483-486` |
| `nulex/map_ncl_direct_gl.py` | conforms (IR-BIT + `$_DFF_P_`, cone tiling) **minus `$_BUF_`** — exits "unhandled cell type" on it (`:223`; own header `:11-12` omits it). §2.2 marks `$_BUF_` deprecated accordingly | `:10-12,223` |
| `nulex/map_plain.py` | conforms (IR-BIT reference emitter) | `:72` |
| `nulex/map_actor_c.py` | conforms, **plus a superset**: accepts `$_DFF_PN0_` | `:58-60` — legal for a consumer; frontends must not emit it (§2.6.2) |
| producers `synth.ys`, `synth_seq.ys`, `alu/synth_alu.ys`, `threeway/run_direct.sh` | conform (IR-BIT / IR-WORD recipes of §2.2) | cited in §2.2 |
| sync liberty flow `alu/pnr/synth_sky130.ys` | conforms; note its `write_json` output is a *mapped-netlist artifact*, not the shared IR — the shared IR is the generic-gate JSON upstream of `dfflibmap`/`abc` | `:4-6` |
| **`exec/synth_exec.ys:4` and `exec/synth_exec_tierB.ys:4`** | **VIOLATION** — `memory_collect; memory_map` breaks §2.5. This is not incidental: it is the exact machine that produced the measured 43.6× finding (`SELECTION-RULE.md:38,297-298`) | flagged |

**Disposition of the one violation:** the exec-derived netlists (37,058-gate
Tier A artifact, `nulex/README.md`) remain valid *functional* artifacts but
carry the **NON-CONFORMANT (memory-expanded)** label for any energy/binding
scoring — their flop counts and clock floor are artifacts of `memory_map`, not
of the design. The conforming fix (keep `$mem`, bind the macro per G-D) is
blocked on `bindings/sram.py` (T2). Until it lands, memory-expanded netlists
must not be scored as if their flops were design flops. NOTE (skeptic,
2026-09-26): polysynth cannot yet *detect* memory expansion from the netlist
alone — expanded memories look like ordinary flops, and polysynth reads no
M5 provenance sidecar. So today this rule is enforced by the producer side
(do not run `memory_map`; carry M5 provenance) and by the human; the driver
gains an automatic refusal only once M5 sidecars exist and polysynth consumes
them (§5).

---

## 5. Open items this document hands to P1 / polysynth

- The ack-less-channel expression (§2.7) — load-bearing across the whole Vortex
  boundary map (`ASYNC-PLAN.md:394-401`).
- The M3 sidecar filename/schema — polysynth defines it; the fields and the
  busy/toggles-not-duty rule are fixed here.
- Whether the IR grows an explicit `$mem` → macro-blackbox normalization pass
  when `bindings/sram.py` lands (T2).
- The P1 contract ADR itself (`ASYNC-PLAN.md:137-144`) — this document's §2.7
  table is input inventory for it, nothing more.
