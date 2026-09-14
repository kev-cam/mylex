# nulex — RTL → asynchronous NCL converter (task #60)

The async-logic-synthesis tool of this repo. Goal: an **NCL (Null Convention
Logic) asynchronous implementation, correct by construction**, handed to physical
implementation (NCL is the *definition*; the physical *binding* — QDI dual-rail,
bundled-data, clocked-SRAM wrapper, sync-emulation — is swappable). Demo vehicle:
**Vortex GP-GPU** (`VX_alu_int` first). Plan of record: `../ASYNC-PLAN.md`;
channel/handshake layer: `../PIPES.md`; physical flow: `../LAYOUT-OPT.md`.

License: PolyForm Noncommercial 1.0.0 (`../LICENSE-ASYNC.md`), like the whole repo.
This is why the emitter is a mylex `.so` dlopened by nvc/gsm over a stable C ABI
(`gsm_generate` + `gsm_rtlil_api_t`), never in-tree in GPL nvc.

## Status (2026-09-14)

- **P3 gate library — COMPLETE + GREEN.** `./run_gates.sh` (exit 0), NVC 1.19; uses
  the installed nvc NCL lib via `-L` (never copies the Apache package here).
  The full abc rewrite-rule set, each a structural dual-rail entity in
  `lib/ncl_gates.vhd`, each input-complete + observable by construction:
  - `ncl_inv` — free rail-swap (no cell).
  - `ncl_and2 / nand2 / or2 / nor2 / xor2 / xnor2` — **DIMS**: 4 shared TH22
    minterm C-elements → rail collectors (only the collector wiring differs).
  - `ncl_mux2` — 3-input DIMS (8 TH33 minterms; fully input-complete incl. the
    unselected data input — the conservative form; early-completion is a later opt).
  - `ncl_add4_struct` — Fant th23/th34w2 ripple adder (composed-rule proof).
  Verified exhaustively vs the sync golden: `tests/tb_ncl_gates` (INV+6 gates, all
  inputs), `tests/tb_ncl_mux2` (8/8), `tests/tb_ncl_and2` (4/4), `tests/tb_add4_cbc`
  (structural == golden == behavioral, 256/256). This is the #39 equivalence gate
  standing from the first artifact.
- **DFF/DFFE — deferred to a sync-emulation binding** (no sequential NCL register
  cell exists yet; §"Prior decisions"). The mapper leaves flops as clocked latches
  until a hysteresis NCL register cell lands.
- **Netlist mapper — first increment GREEN.** `map_ncl.py` reads a yosys gate
  netlist (`write_json` over `{$_AND_,$_OR_,$_XOR_,$_NAND_,$_NOR_,$_XNOR_,$_NOT_,
  $_MUX_}`) and emits a dual-rail NCL VHDL netlist instantiating the gate entities,
  one per cell (each 1-bit net → one `ncl_logic`; constants → `NCL_DATA0/1`).
  `mapper/run_map.sh` (exit 0): `small.v` (`y = sel ? a+b : a^b`) → yosys
  (`synth.ys`, `techmap; simplemap` — this build has no `abc`, a complete-basis
  subset) → 17-cell netlist → mapped → **512/512 == sync golden** in NVC.
  This is the P3→P4 spine on a small fixture; next is `alu.gates.il` +
  sequential ($_DFF_) handling.

## Prior decisions honored (from the async-docs documentation)

- **Rail convention**: value on `.L` (verified against nvc `lib/ncl` code; the field
  comments are stale). Physical QDI binding inserts a documented L→H swap for the
  SG13G2 SPICE cells (value on H). Normalize once, in the mapper. (LDX-VORTEX §3.)
- **No prior RTL→NCL mapper exists** — not re-deriving; the only NCL designs (SHA-256d
  miner, ARV) were hand-written against `ncl_sync`. `ncl_sync` = the existing
  sync-emulation binding (single-rail H). (LDX-VORTEX §1–3.)
- **TH cells (th12/22/23/33/34w2) exist as Sutherland C-element SPICE on IHP SG13G2
  only — no Liberty/LEF/layout, no reset-pin variants**; several THmn are Boolean-only.
  So physical P&R of NCL is gated on giving these cells a layout view. (LDX-VORTEX §1.)
- **Completion detection: no prior design** — nulex defines it.
- **Mapper interface + first target are ratified**: mylex `.so` over the stable C ABI,
  consuming the in-process `RTLIL::Design` the walker builds (VX_alu_int already builds
  in-process, VERIFY-clean), emitting NCL cells alongside the C model; mark NCL cells
  **don't-touch**. First target `VX_alu_int`. (ASYNC-PLAN §5–6, LDX-VORTEX §15.)
- **Frontend seam**: `probes/gsm/synth_alu.ys` → `abc -g AND,NAND,OR,NOR,XOR,XNOR,MUX`
  → `alu.gates.il`. Mapper input = exactly {those 7} + DFF/DFFE. 3-oracle differential
  (vvp+NVC+gen_statemachine) is the EC reference. (probes/gsm, SYNTH-RESULTS.md.)

## Physical hand-off (LAYOUT-OPT.md)

nulex `formal/constraints.py` emits the RT / isochronic-fork constraint set → **layopt**
(post-P&R) consumes it as path sets to balance geometry and prove timing in Xyce over
corners. Proven physical flow is **sky130** (OpenROAD + KLayout + Xyce); `VX_alu_int`
already went through the whole chain (154/188 boundaries dissolved, 0 DRC, netlist
equal). SG13G2 is where the NCL cells live (SPICE) but they lack layout → the gating
dependency for a real NCL P&R. ASAP7/cln28 are aspirational, PDK authority is OPEN.
GPU-SIM: the sync-emulation binding rides the existing gpubuild/CUDA farm path for
scale sim; raw-NCL phase-batched GPU sim has a modest ceiling.

## Ordered plan

1. ✅ **[P3 seed]** #39 equivalence gate + DIMS AND2 + structural adder — GREEN.
2. ✅ **[P3]** Combinational DIMS/NCL library {INV,AND,NAND,OR,NOR,XOR,XNOR,MUX} — each
   an entity, each verified by an exhaustive gate — GREEN. DFF deferred (sync-emulation).
3. **[P0]** mylex `.so` skeleton over the real C ABI (`gsm_generate` + `gsm_rtlil_api_t`),
   env-pinned, NULL-fallback, no mapping logic (regression-neutral added consumer).
4. **[P1]** contract ADR (`execute_if`/`commit_if` elastic pipes + ack-less `branch_ctl_if`
   as a tap per PIPES §7.1; refinement (a)-(d)).
5. ✅ **[P3→P4 seed]** netlist mapper (`map_ncl.py`) — small design → yosys gate
   netlist → dual-rail NCL netlist → NVC 512/512 == sync golden. GREEN.
6. **[P4]** scale the mapper: sequential `$_DFF_` → sync-emulation register, then
   `alu.gates.il` / `VX_alu_int`, verified via the 3-oracle differential
   (`probes/gsm`); hand the async netlist + RT constraints to the layopt pipeline.

Genuinely open / to decide: rail-polarity ADR ratification, the dual-rail-clocked third
binding variant (for the both-rails-high assertion), completion-detection circuitry,
frontend path (sv2v→Yosys vs iverilog/sv2ghdl→NVC→RTLIL), silicon PDK authority.

(Scratch origin of the bring-up: `/home/claude/nulex/`.)
