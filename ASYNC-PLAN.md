# Nulex — Project Plan

**Nulex** is an asynchronous logic synthesis stack built around NCL as a
*definition* language. It accepts multiple frontends (SystemVerilog RTL first,
C++ and neural-model paths later), represents designs in an NCL-semantics IR,
and lowers each design boundary to whatever implementation that boundary
actually requires — QDI dual-rail, bundled-data, clocked-SRAM wrapper,
Verilog-AMS analog, or synchronous emulation.

Part of the Cameron EDA stack, alongside `mylex` (ONNX/NIR → Verilog-AMS).
Currently housed in the mylex repository as `ASYNC-PLAN.md`; the final
repository relationship is an open decision (§10).

License: PolyForm Noncommercial 1.0.0 (`LICENSE-ASYNC.md`). Deliberately not
the BSD-3-Clause of the mylex frontend — the async stack sits nearer the
commercial core. Variant choice is recorded in §12.

This document is the working plan, not the spec. Decisions get refined during
implementation; this exists to keep the architecture coherent and prevent
scope drift.

> **Name is a placeholder.** `nulex` (NULL + the mylex suffix) is a proposal,
> not a decision. Everything here is trivially relocatable.

---

## 1. The central idea

**NCL is the definition layer, not necessarily the implementation.**

NCL's DATA/NULL discipline is a *protocol* with monotonic, formally clean
semantics. It states what a boundary must guarantee without dictating the
gates that implement it. Nulex uses this property as its organizing principle:

```
                NCL definition
        (per channel: DATA/NULL discipline,
         completion contract, ack discipline)
                      ▲
                      │ refines
   ┌──────────┬───────┴────┬────────────┬───────────┐
QDI dual-  bundled-   clocked SRAM   Verilog-AMS   sync
  rail       data      + wrapper       analog    emulation
```

Every boundary in a design carries an NCL-defined contract. Every boundary
gets an *implementation binding*. The proof obligation is that the binding
**refines** its definition. Different boundaries in the same design bind
differently, and that is the normal case, not a compromise.

### What this buys

- **Memory stops being a wall.** An SRAM never needed to *be* NCL; it needs to
  *satisfy* an NCL contract at its interface. A clocked SRAM behind a
  handshake wrapper is a legal binding.
- **Synchronous emulation is first-class.** Replacing handshakes with clocked
  equivalents for fast functional simulation is a legal binding of the same
  definition, with its own (weaker) obligations — not a workaround to be
  backed out later. Functional verification done against the sync binding
  transfers to the QDI binding for datapath behavior — backed by the
  per-module sync↔async equivalence check (§4) — wherever the definition is
  deterministic at the data-stream level (output streams fully determined by
  input streams). It does not transfer where the definition leaves
  interleavings open — arbitration order, memory-response ordering — which
  the QDI binding resolves differently than any clocked schedule exhibits;
  those regions (on Vortex: the arbiters throughout the memory subsystem and
  warp scheduler) need verification against the contract itself, not against
  sync-binding runs.
- **The analog path is not a separate tool.** A Verilog-AMS block is another
  binding with an AMS-flavored contract. This is the seam where the mylex
  model path joins the same flow.
- **Incremental conversion is the architecture.** Converting a large design
  one boundary at a time is the intended mode of use, not a staging tactic.

### What this costs

The contract language becomes the load-bearing design decision in the whole
stack (§3). Get it wrong and everything downstream is mush.

## 2. Scope

### In scope
- NCL-semantics internal IR with channel contracts as first-class objects
- Contract/refinement language and its checker
- SystemVerilog RTL frontend
- Implementation bindings: QDI dual-rail, bundled-data, sync emulation,
  clocked-SRAM wrapper, Verilog-AMS
- Correct-by-construction rewrite rules with per-rule proof obligations
- Sync↔async equivalence checking
- Timing/RT constraint extraction for downstream discharge
- NCL threshold-gate cell library, or integration with an existing one (§10)

### Out of scope (this repo)
- Place and route and signoff. SPEF extraction is also out of scope here —
  but not missing from the stack: stat-sim's `klayout2spef.py` produces it
  from layout (see §5 toolchain)
- Training or model authoring (mylex's domain)
- C++ frontend (planned, deferred — see §5)
- FPGA QDI implementation (see §7; sync-emulation binding on FPGA is in scope)

## 3. The contract language

The hard problem. A channel contract must be precise enough that refinement
is machine-checkable, and loose enough that a clocked SRAM and a dual-rail
adder are both legal implementations of one definition.

A channel contract carries:

| Field | Meaning | Example values |
|---|---|---|
| `encoding` | How DATA and NULL are represented | dual-rail, 1-of-N, bundled bits + req, sync valid |
| `completion` | How the receiver knows DATA has arrived | rail-OR completion tree, matched delay, clock edge |
| `ack` | How the sender learns it may proceed | explicit ack wire, ready signal, implicit by clock |
| `phase` | Handshake protocol | 4-phase RTZ (NCL standard), 2-phase |
| `assumptions` | Timing assumptions the binding introduces | isochronic forks only (QDI); matched-delay margin; setup/hold |
| `type` | Data width and interpretation | — |

**Refinement.** A binding refines a contract iff:

- **(a) ordering** — the DATA/NULL wavefront ordering observable at the
  channel is preserved;
- **(b) values** — each DATA wavefront carries the value the definition
  assigns to it: the data stream, not just the wavefront alternation, is
  preserved;
- **(c) local liveness** — an enabled wavefront is eventually produced and
  acknowledged under the environment assumptions stated in the contract;
- **(d) assumption discharge** — every timing assumption the binding
  declares is discharged by some downstream method named in the contract.

Condition (b) is what the sync↔async equivalence check (§4) actually
discharges. Condition (c) is the per-boundary liveness obligation that §4's
assume-guarantee and deadlock discussion presuppose when they speak of
individually-live boundaries. Both are mandatory content for the P1
contracts ADR. Assumptions are never silently absorbed — a binding that
needs matched delay must say so under (d), and that statement becomes a
constraint the verification stack is obliged to discharge (§4).

This section is deliberately under-specified. Pinning it down is milestone
**P1** and should produce an ADR before any mapper code is written. The
contract's *executable* counterpart is the pipe construct: `PIPES.md`
specifies it (operations, close/EOF, deterministic arbitration, signal-view
polymorphism, the byte-pipe/socket degenerate case) and maps pipe
configuration onto the fields above and pipe mechanisms onto refinement
conditions (a)–(d).

## 4. Verification architecture

Verification is **per-boundary tier selection**, not a global pipeline. Each
binding discharges its own obligations by the method appropriate to it.

| Binding | Obligation | Method | Stage |
|---|---|---|---|
| QDI dual-rail | Input-completeness, observability, orphan-freedom | Static formal | Pre-layout |
| Bundled-data | Matched-delay margin, RT constraints | SPEF + variation sim | Post-layout |
| Clocked SRAM wrapper | Protocol conformance, synchronizer MTBF | Formal + stat-sim metastability models (MTBF quantified, not linted) | Both |
| Verilog-AMS | Settling / threshold contract | AMS simulation, narrow | Post-layout |
| Sync emulation | Functional equivalence only | Sync↔async EC discharges; fast RTL sim is the *use* | Pre-layout |

### Formal role (decided)

- **Correct-by-construction rewrite rules.** Each mapping rule carries a
  *congruence lemma*: soundness over open terms in an arbitrary well-formed
  context under stated interface assumptions (the classical NCL composition
  theorems for input-completeness and observability are the model).
  Application is then trusted — but free only under three conditions:
  (1) the inter-rule glue (fork insertion, completion-tree construction,
  ack fan-in) is itself rule-governed, with its own proofs in `rules/`
  (P3); (2) no later pass restructures the mapped netlist — the don't-touch
  requirement of §5/§11 extends to nulex's own passes, which rules out NCL
  relaxation unless relaxation is itself expressed as proven rules; and
  (3) `formal/completeness.py` (§8) runs as a cheap per-design
  netlist-level completeness/observability/orphan lint — the structural
  backstop for violations of (1) and (2). Orphan-freedom retains an
  irreducible per-design component regardless: isochronic-fork enumeration,
  discharged downstream (see the SPEF notes below).
- **Sync↔async equivalence checking.** Backstops the datapath rewrite against
  the source RTL, per module, across an elastic boundary. The relation is
  **flow equivalence** (latency-insensitive stream equivalence, after
  Cortadella and Carloni): the same sequence of data values on each
  corresponding channel, ignoring timing and inserted NULL wavefronts —
  off-the-shelf cycle-accurate sequential EC cannot check this directly.
  Non-channel interface signals (reset, flush, valid-only broadcasts) need a
  stated convention: each is either lifted to a contract-bearing channel or
  excluded from the EC boundary with a documented argument; both go in the
  P1 ADR. Against a *sync-emulation* binding the check is close to vacuous —
  it validates the datapath transformation, not the handshake (those
  obligations are the static ones above) — but it is cheap and it is what
  discharges the sync-emulation row in the table, so it runs per-module
  always (settling a former §12 question).

### Composition — the known gap

Per-boundary refinement composes for safety (standard assume-guarantee).
**Deadlock does not.** Two individually-live boundaries can deadlock when
composed; it is a property of the channel graph — cyclic contract
dependencies, token-count invariants around loops — not of any boundary.
And the gap is not only liveness: functional behavior under interleavings
the sync binding never exercises (arbitration order, memory-response
ordering) is likewise uncovered by per-boundary proofs and sync simulation —
strengthening the case for the composition-level check below, and for
nondeterminism-aware contract checks at arbitrated boundaries.

Nothing else in the stack is positioned to catch this. A composition-level
liveness check (Petri-net / STG reachability over the channel graph) is
therefore **recommended and currently unscheduled**. On a design like Vortex
it would bite in the memory subsystem and the warp scheduler, where there
are real cycles. See §11.

### Existing practice this plugs into

- **Sync-emulation functional simulation.** Already in use. Cheap suggested
  addition: retain dual-rail *encoding* in the sync binding even with a
  clocked handshake, and assert both rails are never simultaneously high.
  Free illegal-state check in the fastest tier. Note from the ldx libraries
  (`LDX-VORTEX.md`): the existing `ncl_sync` binding deletes the second
  rail entirely, so this assertion needs a third binding variant
  (dual-rail-clocked), and the rail-polarity convention must be normalized
  first — the ldx VHDL packages carry the value on the L rail while the
  asic SPICE cells carry it on H.
- **SPEF back-annotation with statistical simulation — the `stat-sim`
  tool** (`/usr/local/src/stat-sim`, PolyForm NC, implementing US8478576B1
  probability waveforms + US20230334213A1 defect binning). It generates
  Verilog-AMS models carrying silicon variability — per-cell tau/T0 from
  transistor Monte-Carlo on a real PDK — so metastability is *simulated
  with a quantified MTBF*, not structurally linted; `klayout2spef.py`
  produces the SPEF from layout. Already in use.
  Discharges the RT constraints that formal extracts symbolically: formal
  enumerates which forks must be isochronic, SPEF supplies per-branch RC to
  settle each claim numerically. Two notes:
  - **For QDI RT-constraint discharge, weight variation toward local
    mismatch, not global corners.** QDI is insensitive to uniform delay
    scaling by construction; sweeping ss/tt/ff largely confirms what the
    circuit style guarantees. Within-die random mismatch and systematic
    gradients between adjacent paths are what break it. Bundled-data margin
    discharge is the opposite case: delay-line-to-datapath tracking is a
    cross-corner property — the delay line and the datapath it shadows are
    different cell topologies that do not track across ss/tt/ff — so
    matched-delay checks must still sweep global PVT corners (including
    low-voltage temperature inversion) on top of local mismatch.
  - **Use coupled extraction on dual-rail pairs.** Rails route adjacent and
    switch complementarily — near-worst-case aggressor conditions. Crosstalk
    delay on one rail relative to its partner is an orphan mechanism, and it
    is invisible above extracted parasitics.

## 5. Frontends

### SystemVerilog RTL (first)

**Proposed: Yosys.** Read SV, synthesize to a gate netlist, apply the NCL
binding pass at the point where technology mapping would otherwise happen.

Rationale: it yields a known-synthesizable subset, and the formal tooling is
in the same ecosystem. Vortex — the proving target (§6) — already ships a
working `hw/syn/yosys` flow to ASAP7, which is direct evidence the approach
survives contact with real SystemVerilog at scale.

**Open risk, must resolve first:** if the prior FPGA failure was caused by
synthesis *optimizing away* hazard-freedom structure (collapsing C-element
feedback into a latch, eliminating logic that exists purely for
hazard-freedom), then Yosys and ABC will do the same to an NCL netlist.
The mapper must mark NCL cells don't-touch and never let a generic optimizer
see inside them. See §10.

An in-house alternative path exists, and it is more complete than first
noted: the `iverilog` fork's actively developed `tgt-vhdl` backend parses
(System)Verilog and emits VHDL against the `logic3dw`/`sv2vhdl` support
packages; `sv2ghdl` orchestrates the translation; the NVC fork simulates
the result (`lib/sv2vhdl` is that runtime — building it needs
`python3-dev`), and its direct-RTLIL backend reaches Yosys:
**SV → iverilog `tgt-vhdl` → sv2ghdl → NVC → RTLIL**. That keeps the whole
frontend in tools we own and simulate with; which path the mapper trusts
(sv2v → Yosys vs iverilog/sv2ghdl → NVC → RTLIL) is an open decision for
P3.

*Evidence as of 2026-09-03 (LDX-VORTEX.md §6–§9):* the chain is proven
through Vortex's whole execute stage — with **sv2v in front**, because
Icarus cannot parse SV interface ports — and the translated VHDL is
cycle-for-cycle equivalent to Icarus on the same flattened Verilog. More
consequential for P3: the NVC fork already links **libyosys in-process**
and constructs `RTLIL::Design` directly from its elaborated tree
(`vhdl2rtlil_module`, behind `NVC_ACCEL_RTLIL=1`, first installs on VeeR
EH1a 2026-08-31; see `nvc/TODO-yosys-integration.md`). So the "Yosys
frontend" and "NVC simulation" halves of this plan are already one
process in the toolchain: the NCL mapper can be a Yosys pass invoked
in-process on NVC's own RTLIL, and NVC can then simulate the mapped
netlist — the equivalence loop closes without leaving the process.

### C++ (planned)

An HLS-shaped path to the same IR. Deferred; the contract language must
stabilize first. Noted here because it constrains §3 — the contract language
should not assume an RTL-shaped source. The C-side channel representation
is settled by `PIPES.md`: a network socket is the byte-pipe degenerate case
of a channel, so C code speaks pipes of bytes from day one.

### Neural models (via mylex)

mylex compiles ONNX/NIR to Verilog-AMS today. Under this architecture the AMS
emission is a *binding*, which is the natural seam: mylex targets the Nulex
IR, and the AMS binding is shared infrastructure rather than a parallel
implementation.

### The surrounding toolchain

The federation this plan plugs into (all kev-cam repos, restored locally):
`smak` (make replacement orchestrating the fleet), the `iverilog` fork
(`tgt-vhdl` — the Verilog parser of the translation chain), `sv2ghdl`
(SV→VHDL orchestration), the `nvc` fork (digital sim, `lib/ncl`, RTLIL backend, Xyce
cosim), the `xyce` fork (analog, auto ADC/DAC bridge insertion at
mixed-signal boundaries), `stat-sim` (variability AMS models, SPEF from
layout, MTBF), `ldx` (runtime linker + many-core fabric), `arv` (async
RISC-V testbed). PIPES.md's foreign endpoints are the intended transport
between federation members.

**License boundary — settled 2026-09-01.** All tools in the mylex
repository, `bindings/ams.py` and the mylex compiler included, are PolyForm
Noncommercial 1.0.0 (`LICENSE-ASYNC.md`). BSD-3-Clause survives only where
upstream requires it: code derived from NIR (reference models, reused
tests) keeps its origin license. mylex PLAN.md's license line is updated to
match; its §1.4 "open frontend" positioning should be re-read against the
source-available posture.

## 6. Vortex as the proving target

[Vortex](https://github.com/vortexgpgpu/vortex) is an open-source RISC-V
GPGPU in SystemVerilog. Measured from the repository:

- **84,463 lines** of RTL across **384 files** — not a toy
- **73 files carry valid+ready pairs**, with `VX_elastic_buffer`,
  `VX_pipe_buffer`, `VX_elastic_adapter`, `VX_bypass_buffer` in `hw/rtl/libs`
- Essentially one clock domain (`clk` throughout), no latches, no async reset
  outside a single DPI testbench, `tri`/`inout` in 2 files
- Existing `hw/syn/yosys` flow (sv2v → Yosys → ABC → OpenSTA, ASAP7), plus
  `hw/syn/libs/` with cln28hpc, cln28hpm, and a `no_mem` variant

**Why it fits.** The microarchitecture is already latency-insensitive at
module boundaries. A valid/ready boundary is semantically close to an NCL
channel — `valid` ≈ DATA wavefront present, `ready` ≈ acknowledge. The seams
where async wants to cut are already drawn in the source, so the elastic
interfaces become the natural contract points, and per-boundary binding
becomes the natural conversion strategy.

### Boundary map (first pass)

| Subsystem | LOC | Proposed binding |
|---|---|---|
| `core` (ALU, decode, issue) | 11.6K | QDI dual-rail |
| `libs` | 12.5K | Mixed — logic QDI, RAMs wrapped |
| `fpu` | 6.4K | Bundled-data (deep comb; completion cost concentrates here) |
| `cache` | 5.4K | Clocked SRAM + wrapper |
| `tcu` (tensor) | 10K | Deferred (includes third-party `fpnew`) |
| `mem`, `vm`, `cp`, `dxa` | ~12K | Sync at AXI/AVS protocol boundaries |
| `raster`, `om`, `tex`, `rtu` | 14.8K | Deferred — graphics, not needed for proof |

### First target

`hw/rtl/core/VX_alu_int.sv` — self-contained, no memory, real datapath,
elastic interfaces, small enough that both the binding and its equivalence
proof close end-to-end quickly. Validates the entire toolchain: SV → Yosys →
gate netlist → NCL binding → completion detection → equivalence check.

One caveat, verified in the source: of its three interfaces, `execute_if`
and `result_if` are valid/ready elastic, but `branch_ctl_if` is a valid-only
broadcast to the scheduler with no ack. The first target therefore already
contains one non-elastic boundary — the §3 contract language must express an
ack-less channel, or P4 must explicitly exclude it and treat the branch
pulse as derived from the `result_if` handshake (where `br_enable` actually
originates). The sideband family is broader than this one interface —
warp-control pulses, the scheduler CSR bundle, ibuffer credit returns,
valid-only DCR writes — so the ack-less-channel decision is load-bearing
across the whole §6 map, not a one-off.

Then `VX_alu_muldiv`, then full `VX_execute`, then reassess the FPU.

### Cost expectations

QDI dual-rail with completion detection runs ~2–4× synchronous area. The
payoff is no clock tree and genuinely event-driven power, which matters
unusually much for a GPGPU where warps spend most of their life stalled on
memory and idle lanes burn clock power for nothing. That is the same argument
as the SNN sparsity story, which is why both paths want this backend.

## 7. FPGA

QDI on FPGA is not supported and not planned. Threshold gates need
hysteresis/state-holding, LUT mapping introduces hazards, and place-and-route
will not honor isochronic fork assumptions. Prior in-house experience
confirms this.

The **sync-emulation binding on FPGA is fully supported** and is the intended
FPGA story: functional verification at speed, on real hardware, of a design
whose QDI binding targets ASIC. ASAP7 and cln28 are the silicon targets.

**Near-term: simulation only.** The FPGA is currently on loan, so the
sync-emulation binding runs in RTL simulation for now and moves back to
hardware when the board returns. Rented GPU capacity (Vast.AI) is available
for compute-heavy stages — model training on the mylex path, and any
simulation workload that can exploit it (statistical Monte-Carlo fans out
embarrassingly across seeds). `GPU-SIM.md` surveys event-driven mixed-signal
simulation on GPUs and recommends the batched architecture.

> **Note for the mylex plan.** mylex `PLAN.md` §9 M6 targets ZCU104 with
> D5005 in phase 2. Under this architecture those boards run the
> sync-emulation binding, not async silicon. Worth reconciling the two
> documents explicitly.

## 8. Repository structure (proposed)

Shown as a standalone tree. While housed inside the mylex repository this
maps to a `nulex/` subdirectory; nothing below hard-codes the repo split.

```
nulex/
├── README.md
├── LICENSE
├── pyproject.toml
├── docs/
│   ├── PLAN.md                  this document
│   ├── contracts.md             contract language spec (P1 output)
│   ├── bindings.md              per-binding obligations
│   └── decisions/               ADRs
├── nulex/
│   ├── ir/
│   │   ├── graph.py             channel graph
│   │   └── contract.py          contract objects, refinement relation
│   ├── frontend/
│   │   └── yosys_reader.py      RTLIL/netlist → IR
│   ├── bindings/
│   │   ├── qdi.py               dual-rail NCL
│   │   ├── bundled.py           bundled-data
│   │   ├── sram.py              clocked SRAM wrapper
│   │   ├── ams.py               Verilog-AMS (shared with mylex)
│   │   └── sync.py              synchronous emulation
│   ├── rules/                   rewrite rules + their proof obligations
│   ├── formal/
│   │   ├── equivalence.py       sync↔async EC
│   │   ├── completeness.py      input-completeness / observability
│   │   └── constraints.py       RT constraint extraction → SPEF flow
│   └── cli.py
├── lib/                         NCL cell library (or bindings to existing)
└── tests/
    ├── rules/                   per-rule soundness
    ├── bindings/                per-binding conformance
    └── vortex/                  VX_alu_int and successors
```

## 9. Milestones

Phase-ordered, not calendar-dated. Sequencing depends on the cell library
answer (§10) more than anything else.

- **P0 — Scaffolding.** Repo, license, package skeleton, CI.
- **P1 — Contract language.** The load-bearing decision. Produces
  `docs/contracts.md` and an ADR. No mapper code before this lands.
- **P2 — Cell library resolution: characterize, seeded by ldx.** The ldx
  assets (cell topologies, the Xyce characterization pipeline, the
  assert-correct verification methodology) are reusable seeds, but they
  target IHP SG13G2/1.2V vs this plan's ASAP7/cln28, a Liberty emitter must
  be written from scratch, several THmn members lack transistor netlists,
  and no cell has reset. Blocking; see §10 and `LDX-VORTEX.md`.
- **P3 — QDI binding + rules for a gate subset.** Enough rules to map a
  2-input gate netlist, each with its soundness proof. Establishes the
  methodology the rest follows.
- **P4 — `VX_alu_int` end-to-end.** SV → Yosys → NCL → equivalence check.
  The "this architecture is real" milestone.
- **P5 — Multi-binding.** Sync emulation and clocked-SRAM wrapper bindings,
  proving that heterogeneous binding within one design works.
- **P6 — `VX_execute`.** A full execute stage with mixed bindings, taken
  through SPEF back-annotation and statistical simulation.

**Post-P6:** C++ frontend, mylex IR convergence, composition-level liveness,
FPU binding decision.

## 10. Blocking unknowns

Recorded because they change the shape of early work, not merely its order.

1. **Prior NCL work — FOUND (2026-09-01); see `LDX-VORTEX.md`.** Lives in
   `/usr/local/src/ldx`: a behavioral dual-rail VHDL package plus its sync
   binding (`fpga/lib/ncl`, `fpga/lib/ncl_sync`), Sutherland C-element
   SPICE cells for th12/22/23/33/34w2 on IHP SG13G2 130nm with a Xyce
   characterization pipeline and Verilog-A extraction (`asic/`), an NCL
   SHA-256d miner (70,578 LE, retained bitstream), and ARV harnesses. The
   ARV core sources and the patched NVC live outside ldx and are restored
   as of 2026-09-01: NVC at `/usr/local/src/nvc` (kev-cam fork — `lib/ncl`
   built in, a Xyce co-simulation branch, a direct-RTLIL backend giving a
   native VHDL→Yosys path), and the core at
   `/usr/local/src/risc-v-cpu-asynchronous` (`arv` symlink pending), where
   ARV has advanced past the ldx snapshot: 2-stage forwarding pipeline,
   Fmax 17→45 MHz, plus sync↔async transceivers and handshake components
   in `infrastructure/`. Caution: three divergent copies of the ncl
   package exist (arv 290 / ldx 436 / nvc 451 lines) — single-sourcing on
   NVC's `lib/ncl` is a P0-level cleanup. No Liberty, LEF, or layout exists anywhere; no
   reset-pin cell variants.
2. **Cause of the FPGA failure.** If routing delay violated isochronic forks,
   the ASIC path is unaffected. If synthesis optimized away hazard-freedom
   structure, the same failure is latent in the Yosys path and the mapper
   must be designed around it from day one (§5). *Evidence from ldx
   (2026-09-01, `LDX-VORTEX.md`):* the recorded split is not "synchronizers
   made synchronous" — the entire logic package goes synchronous
   (`ncl_sync` deletes the second rail), it appears fully formed as the
   deliberate synthesis path, and ldx history holds no failed true-async
   attempt; the failures actually recorded are clocked-glue races (MMIO
   skew; an unresolved LW-in-loop corruption). The routing-vs-optimization
   question stays open; any post-mortem is in the missing arv repo.
3. **"LLM → async logic" scope.** Whether this means large language models
   specifically (transformer inference in async), or the neural-model path
   generally that mylex already covers. Determines whether mylex must reach
   operators its own PLAN.md §5 currently defers to Tier 3.
4. **Statistical simulation variation model.** LVF/POCV-style models from the
   library, or transistor-level Monte-Carlo. Determines whether completion
   trees can be characterized once and reused, or need re-simulation in
   context.
5. **Repository relationship to mylex.** Work currently lives inside the
   mylex repository (`/usr/local/src/mylex`); whether it stays as a
   sub-project or moves to a sibling repo — with IR convergence deferred
   until both paths have proven what they need — remains open. Nothing in
   §8 hard-codes either answer.

## 11. Risk register

- **Contract language is over- or under-specified.** The whole stack is
  downstream of §3. Over-specify and legitimate bindings become illegal;
  under-specify and refinement is not machine-checkable. Mitigation: write
  the SRAM wrapper and the dual-rail adder contracts *first*, as the two
  extremes the language must span, before generalizing.
- **Synthesis destroys NCL structure.** See §5 and §10.2. Mitigation: resolve
  the FPGA post-mortem before designing the mapper; treat NCL cells as opaque
  don't-touch objects throughout.
- **Composition-level deadlock ships undetected.** Per-boundary proofs will
  not find it (§4). Mitigation: schedule the liveness check before any design
  with cyclic channel dependencies reaches silicon — which on Vortex means
  before the memory subsystem.
- **Area.** 2–4× on QDI-bound regions. Mitigation: heterogeneous binding is
  itself the mitigation — bind QDI only where robustness is worth paying for.
- **AMS simulation does not scale.** It cannot be the primary async bug-finder
  (stimulus-dependent, seconds-per-cycle). Mitigation: keep it narrow —
  cell behavior and margins on critical paths — with static formal and
  SPEF-based statistical simulation carrying coverage.
- **mylex convergence pulls in two directions.** mylex has its own deadline
  pressure and its own emission path. Forcing early IR convergence could
  destabilize both. Mitigation: defer convergence to post-P6, keep the AMS
  binding as the only shared surface until then.

## 12. Open decisions

Deliberately unpinned; to be settled ADR-style in `docs/decisions/`.

- Project name (`nulex` is a placeholder).
- Which PolyForm variant. Noncommercial 1.0.0 is assumed; Small Business,
  Internal Use, or Shield would each express a different commercial posture.
- ~~Which license governs `bindings/ams.py`~~ — settled (§5): PolyForm
  Noncommercial 1.0.0 for all tools in the repository; NIR-derived code
  keeps BSD-3-Clause.
- 4-phase RTZ only, or 2-phase bindings as well?
- Does the IR model NULL wavefronts explicitly, or only DATA with NULL
  implied by the protocol field of the contract?
- Completion detection: generated per-binding, or a characterized library
  object reused across bindings? (Interacts with §10.4.)
- Where the RT constraint set is emitted — SDC, a custom `.rt` format, or
  directly into the statistical simulation flow.
- ~~Whether equivalence checking runs per-module always~~ — settled (§4):
  per-module always; EC is the discharge method for the sync-emulation row.
