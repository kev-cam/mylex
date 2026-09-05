# ldx Assessment: ARV, NCL Assets, and the Vortex Question

*2026-09-01 · companion to `ASYNC-PLAN.md` §6/§9/§10 · six-agent verified map
of `/usr/local/src/ldx` and the Vortex clone; every nontrivial fact carries a
path:line citation from the mapping agents.*

## 1. What ldx actually contains

**ARV** is a phase-clocked RV32I-subset core in VHDL whose four source files are **not in ldx and not on this machine**: every harness instantiates `entity work.e_arv_cpu(ncl_cpu)` (fpga/rtl/arv_soc.vhd:168) but the sources live at `../../../arv/RISC-V.srcs/asynchronous/cpu/` = /usr/local/src/arv, absent (fpga/quartus_arv/arv_synth.qsf:24-27); they were never committed to ldx git. Verified capability: sim-passing ADDI/ADD/SUB/logic/LUI/branches/JAL(R)/LW/SW plus a CUSTOM_0 CFU (fpga/test/tb_arv_cpu.vhdl:128-294); no CSRs, interrupts, or byte/halfword access (port list, tb_arv_cpu.vhdl:31-46). It is **not self-timed**: registration is a 2-phase `phase` clock, mem_ready tied constant; ncl_sync's own header says the phase-driven processes are what make it synthesizable (fpga/lib/ncl_sync/ncl.vhdl:21). Silicon record: 2,284 LE / 17.48 MHz standalone (commit b65241c), an 18-instruction PCIe SoC run (617c02b, 92ca0a0), then an **unresolved LW-in-loop data-corruption bug** as the final ARV commit (796379a, 2026-04-12). The 1.40x SHA CFU speedup is sim-only — funct3=5 is rotr in the testbench model but bitreverse8 in real hardware (fpga/rtl/ldx_cfu.v:92).

**Second core: closed.** A full sweep finds exactly one async CPU in ldx's orbit — ARV. The architect's memory almost certainly refers to the **NCL SHA-256d bitcoin miner** (fpga/rtl/sha256/), the only other NCL-framework design and the biggest FPGA artifact: 70,578/149,760 LE fit on the DE2i-150 with a retained .sof (fpga/quartus_arv/output_files_miner/bitcoin_miner_synth.fit.summary:1) — but it is a datapath, not a CPU, and it too built via ncl_sync. Alternatively a second core sits in the missing arv repo, whose `asynchronous/` path segment implies siblings.

**NCL library + characterization.** Two source-compatible packages: fpga/lib/ncl (behavioral dual-rail; TH gates without hysteresis; treats rails 1,1 as NULL; value rides the field named L, contradicting its header — ncl.vhdl:17-19,35-37,122-126) and fpga/lib/ncl_sync (single rail, ncl_is_null≡false — the sync-emulation binding). Separately, asic/ holds a real three-tier cell effort: Sutherland C-element SPICE for th12/22/23/33/34w2 on **IHP SG13G2 130nm** (asic/cells/th22.sp:8-38), event-driven/NN hybrid VHDL/Verilog-A sim models, a repeatable Xyce characterization pipeline (asic/chr/), and a per-cell mismatch-localizing verification methodology (asic/tb/tb_ncl_add2_assert_correct.vhd:1-127). **No Liberty, LEF, or layout anywhere**; no reset-pin variants; several THmn members exist only as Boolean functions.

**Fabric.** The mailbox many-core is mature and silicon-proven — 64 VexRiscv cores at 200 MHz on ZCU104 (fpga/zcu104/vivado/mailbox/feature_matrix.md:7) — but it is spatial BSP message-passing with private memories, the structural inverse of Vortex's shared-memory SIMT; its node wrapper is VexRiscv-bus-specific with hardwired-ready, fixed 1-cycle responses (rtl/mailbox/ldx_soc_mailbox.v:127-162), and it is SV/Verilator while ARV is VHDL/NVC.

## 2. Integration options and recommendation

Vortex has no scalar core to swap: payloads are warp-indexed and lane-vectored end to end (hw/rtl/VX_gpu_pkg.sv:1186-1192), the GPR is {warp,reg}-addressed RAM (core/VX_opc_unit.sv:242-246), and ~2.6K LOC of SIMT machinery lives outside any datapath. Options: **(a)** an ARV array replacing VX_core discards the custom0/1 SIMT ISA and hence the entire sw/ stack and KMU CTA math — a new manycore, not integration — and requires a cache-capable ARV that does not exist (dmem has no ready signal at all). **(c)** ARV-per-warp re-derives the shared fetch/GPR/LSU front end it replaces. **(d)** Vortex-plus-mailbox-array touches Vortex not at all and proves nothing about it. **(b)** Keep Vortex's microarchitecture and convert boundaries per plan §6 — the only option preserving the toolchain.

**Recommendation: (b).** Staging: P0/P1 unchanged. P2 becomes "characterize, seeded by ldx" (below). At P3, use ldx's ncl/ncl_sync pair as the precedent for the §1 dual-binding contract — but note it has zero contract machinery and the sync binding deletes the L rail. First conversion target stays VX_alu_int (ASYNC-PLAN.md §6). ARV itself is a P3-era *reference/testbed* (a small NCL design to exercise the flow), not the Vortex vehicle — and only if /usr/local/src/arv is recovered. The miner pipeline is a better mid-scale P4 dry-run candidate than ARV (bigger, no unresolved bug, pure datapath).

## 3. Changes to ASYNC-PLAN.md

**§10.1** ("prior NCL work not found in /usr/local/src", ASYNC-PLAN.md:418-419): now found, in **/usr/local/src/ldx** — form: behavioral dual-rail VHDL package + sync binding (fpga/lib/ncl, ncl_sync), SG13G2 SPICE cells + Xyce chr pipeline + multi-tier sim models (asic/), the miner, and ARV harnesses. The ARV core proper and a patched NVC with the ncl library (commit 531df77) live outside ldx and are missing.

**§10.2** (FPGA failure cause): the split is **not** "synchronizers made synchronous" — the *entire logic package* goes synchronous; ncl_sync appears fully formed as the deliberate synthesis path (commit b65241c) with **no failed true-async attempt in ldx history**. The failures actually recorded are clocked-glue races (MMIO skew, 33a25bd; the open LW bug, 796379a). The routing-delay-vs-synthesis-optimization question stays open; the post-mortem, if written, is in the missing arv repo.

**P2** (integrate vs characterize): resolve to **characterize** — topologies, the chr pipeline, and the assert-correct methodology are reusable seeds, but everything is SG13G2/1.2V vs the plan's ASAP7/cln28, a Liberty emitter must be written from scratch, th13/24/34/44/w2-variants lack transistor netlists, and no cell has reset.

**§6**: boundary map and first target unchanged — ARV alters neither. Add to §3/§4: the ack-less/level sideband family (warp_ctl pulses, sched_csr bundle, ibuf_pop credits, valid-only DCR) is broader than the single branch_ctl_if caveat; and §4's both-rails-high assertion cannot bolt onto ncl_sync (L rail deleted) — it needs a third binding variant. Also normalize the rail convention: VHDL packages carry value on L, asic SPICE on H (ncl_logic.sp:4-5).

## 4. Open questions for the architect

1. Where is the arv repo (remote/backup)? Does its tree hold the "additional core," or is your memory the bitcoin miner?
2. Where is the patched NVC (/usr/local/src/nvc, commit 531df77) that the sim flow requires?
3. The failed true-async FPGA build predating ncl_sync — what was attempted, on what tool/part, and is any post-mortem written down?
4. Was the LW-in-loop corruption ever root-caused (CPU vs port-B arbitration)?
5. Which process is authoritative for P4 (ASAP7 or cln28), and do we have Xyce-usable device models for it?
6. Is ARV intended as a reference design or as a deliverable core? That decides whether fixing its gaps (byte access, CSRs, real handshakes) is ever in scope.

## 5. Bring-up results (2026-09-01, this machine)

The full stack was revived and runs: ARV HEAD (2-stage forwarding pipeline)
→ kev-cam/nvc fork (built from source, `lib/ncl` built in) → phase-clocked
NCL simulation via `ldx/fpga/bench/sha256/sim_bench.py`.

| Test | Result |
|---|---|
| `sha256_sw.bin` | PASS — correct hash, 4,969 cycles |
| `sha256_cfu.bin` | PASS — correct hash, 3,578 cycles (**1.39× CFU speedup**, matching the 1.40× ldx recorded) |
| `lw_test.bin`, `lw_far.bin` | PASS — both LW regressions exact |
| `kload_test.bin` | PASS — all four result registers exact |
| `rotr_test.bin` | PASS — ARV correct; the source comment's expected value for R2 was itself miscalculated |

**LW-bug update (open question 4):** the LW-in-loop corruption recorded as
unresolved at ldx `796379a` does **not** reproduce on ARV HEAD under the
sim_bench testbench (simple single-reader memory model). Suspicion narrows
to the `arv_soc` dual-port BRAM port-B arbitration in ldx (PCIe/CPU port
sharing) — or the bug was fixed by the pipeline rework. Reproducing under
`arv_soc` itself is the next diagnostic.

Build notes: the fork's `sv2vhdl` library needs `python3-dev` and has a
parallel-make race on STD.STANDARD (skippable — not needed for this flow).
An uninstalled build needs `PATH=<nvc>/build/bin` and
`NVC_LIBPATH=<nvc>/build/lib`.

## 6. tgt-vhdl chain probe: VX_elastic_buffer (2026-09-01)

**The chain works end-to-end**: `VX_elastic_buffer` (+8-file closure) went
SV → iverilog `tgt-vhdl -psv2vhdl=1` → NVC `--std=2040` analyze/elaborate/
simulate, and a handshake testbench (`probes/ebtest/tb_eb.vhd`) passed 5
tokens through with a mid-stream backpressure window, order and data intact
— after three translator fixes applied by hand to the generated VHDL. The
recipe:

```
iverilog -g2012 -tvhdl -psv2vhdl=1 -I hw/rtl -I hw/rtl/libs \
  -o eb.vhd -s VX_elastic_buffer <9 libs/*.sv files>
nvc --std=2040 -a eb.vhd tb_eb.vhd -e tb_eb -r   # NVC_LIBPATH=<nvc>/build/lib
```

**Findings (all in the iverilog fork's tgt-vhdl, none in Vortex or NVC):**

1. **Reserved-word collision.** `pipe` is a keyword in the fork's
   `--std=2040` grammar (the PIPES.md construct is already staked out in
   the parser). Vortex's `VX_pipe_register` names a signal `pipe` → parse
   error. tgt-vhdl must escape identifiers that collide with
   extended-standard keywords (VHDL extended identifiers, or rename).
2. **2-D packed-array part-select flat-index mis-lowering.** For
   `pipe[i][DATAW-1 : DATAW-RESETW]` (variable outer index, constant inner
   part-select; DATAW=2, RESETW=1) the flat index came out `(i-1)*2+1`
   instead of `i*2+1` — runtime index -1 at the first reset. This idiom
   (valid-bit-only reset) is everywhere in Vortex; the bug is load-bearing.
3. **Disjoint-slice NBA shadow lost-update.** Two `always_ff` blocks write
   disjoint bit ranges of one reg. Each translated process snapshots the
   WHOLE signal, updates its own bits, and drives the WHOLE signal back —
   two drivers each asserting stale copies of the other's bits; resolution
   then loses an update (token data corrupted after an enable-hold window;
   scoreboard caught it). The multi-UDN encoding has undriven-with-value
   states (L3D_0Z/L3D_1Z) that exist for exactly this: the shadow should
   weaken unowned bits so driven-beats-undriven resolution merges slices.
   Confirmed by merging the two writers into one process → PASS.
4. Not a flow bug after all: `bin/fix-ivl-vhdl` is a legacy post-processor
   that the `iverilog-sv2ghdl` wrapper never runs on `-psv2vhdl` output;
   applying it by hand during the probe is what introduced the cast
   errors. Don't.

Toolchain state on this machine: iverilog fork built at
`/usr/local/src/iverilog/_install`; NVC fork complete in
`/usr/local/src/nvc/build` including all `lib/sv2vhdl` packages,
`libsv_math.so` and `libresolver.so` (built with explicit
`PYTHON3_CFLAGS=$(python3-config --includes)` — the Makefile's deferred
expansion misfires).

## 7. tgt-vhdl fixes, review follow-up and verification (2026-09-02)

All three probe findings are fixed and committed in the iverilog fork (three commits, one per bug; the same changes are exported as patches in `probes/tgt-vhdl-fixes/`). The probe recipe now reports `PASS: 5 tokens through VX_elastic_buffer with backpressure, order and data intact` from a fresh translation with **zero hand patches** (`probes/tgt-vhdl-fixes/vortex-probe/eb.vhd`).

### What was fixed

1. **Reserved words** (`tgt-vhdl/scope.cc:496-539`, patch 01). `is_vhdl_reserved_word()` held only the VHDL-93 list; the fork's `pipe` is tokenised unconditionally (`nvc/src/lexer.l:458`, plain `TOKEN()`), as is upstream's `reverse_range` (`lexer.l:481`). 23 words added (2000/2008/2019 keywords + PSL + `reverse_range` + `pipe`); `reg pipe` -> `pipe_sig` at declaration and every use via the existing rename path (`state.cc:106`, `expr.cc:117`). Ports named after these words are renamed too (`view` -> `view_sig`); function/task/block names still bypass the table (open).
2. **Packed prefix index** (`netmisc.cc:409` and `:1660`, patch 02 — iverilog **core**, not tgt-vhdl). `make_prefix_var_offset()` called `normalize_variable_base(idx, msb, lsb, stride, msb > lsb)`, whose `wid/is_up` describe an indexed part select; for a dim with `msb == lsb` (`[DEPTH-1:0]` with DEPTH=1) the `-:` branch (`netmisc.cc:342-343`) subtracts `stride-1`, giving `(i-1)*2+1`. Both call sites now pass `(…, 1, true)` = element position `idx-lsb`/`lsb-idx`, matching `NetNet::sb_to_idx` (`netlist.cc:767-800`). Trees for `msb != lsb` are unchanged; vvp was equally wrong before (`data_out=xx`).
3. **One VHDL driver per Verilog variable** (`tgt-vhdl/process.cc`, `state.hh:50`, `vhdl.cc:125`, `vhdl_syntax.hh:546,737,994`, patch 03). nvc `--std=2040` admits several sources on an unresolved signal (`rt/model.c:13029-13036`) but the driving value is the FIRST source's (`rt/model.c:14146-14153`), so the second always_ff's whole-signal NBA shadow never reached the signal. `merge_edge_processes_in_all_entities()` (`process.cc:1068`) composes edge-triggered always blocks of one architecture that have the same sensitivity set, edge-guarded bodies, and assign a common signal (transitively) into one process before the shadow passes run; kill switch `SV2VHDL_NO_MERGE=1`.

### Review issues fixed in this pass

- **Medium 1 — blocking-in-X / NBA-in-Y merge (t3_mixed):** `blocking_vs_nba()` (`process.cc:873`) refuses a member whose blocking target is another member's NBA-only target; the remainder is re-split by shared signals (`split_by_shared_sigs`, `process.cc:890`; cluster loop `process.cc:1128-1155`) and a warning names the signal and both blocks. Long-term fix (rename only reads after the first blocking write, in `shadow_blocking_targets`) remains open.
- **Medium 2 — wait-until form outside census/merge (t8_gap):** `promote_wait_until_edge_form()` (`process.cc:753`) rewrites an edge process drawn as `wait until <edge>` (only because it reads a blocking temp — `stmt.cc:1107` wait-for-0 -> `stmt.cc:2008` form D) into the guarded sensitised form when every other wait is a `wait for 0 ns`; it then gets NBA deferral and merges (t8_gap: q=0101/1111 == vvp). Every remaining non-initial process that assigns arch signals enters the census (`extra_writer_t`, `process.cc:803`, recorded at `process.cc:1440`); a signal with >=2 writers where any drives the whole signal / a dynamic element is warned (`process.cc:1173-1200`). New: `vhdl_wait_stmt::get_expr()`, `vhdl_procedural::clear_wait_stmts()`.
- **Time-0 edge miss (found while verifying the promotion):** the guarded form ran its body once at time 0 and sat in `wait for 0 ns` when the initial block's deposits (`clr := 1`) fired at delta 1, losing the X->1 posedge Verilog sees (case5 async reset). `nba_defer_commits` now skips the `wait for 0 ns` on the initialisation run (`nba_init_run` flag, `process.cc:402`), parking the process within delta 0. dffsynth11 and specify4 now match vvp where they printed X before.
- **Low 3 (accel pin names for renamed ports):** not changed; noted as open (needs an `nvc_verilog_ports` map or a `_sig` fallback in `model.c:8797/6584`).

### Verification

- Probe: PASS, zero hand patches (translate/analyse/elaborate/run rc 0), one merge (`VX_pipe_register.sv:51+:63`).
- Repros (`probes/tgt-vhdl-fixes/repros/`): BUG1 pipe_repro/words_repro/control analyse+elaborate; BUG2 repro PASS (nvc) and `data_out=01` (vvp), cases/structcase/nzlsb/partsel PASSED under both; BUG3 nba_slice PASS (9 MISMATCH with NO_MERGE), merge_cases PASS; reviewer's t1-t10: t3 not merged + 2 warnings, t8 promoted+merged == vvp, t10 (6 promotion shapes) == vvp, others byte-identical output.
- Legacy `ivtest/vhdl_nvc_reg.pl`: 285/294, identical non-pass set to baseline (twice).
- vvp core `vvp_reg.pl`: 3006/3020 with patch 02; before/after subset with netmisc.cc reverted shows the 9 failures are pre-existing (`CE (no error reported)`, fork commit 8c6158c) and cases.sv FAILED(6) -> PASSED.
- 197-file sv2vhdl sweep: 4 merges, 0 exit diffs, 3 genuine new multi-writer warnings; 149 changed outputs simulated old vs new: 131 identical, 15 line-number-only in pre-existing nvc errors, edge.v same loop, dffsynth11/specify4 now correct.

### Still open

- Blocking-vs-NBA on one signal across blocks is refused+warned, not merged (correct fix: program-order read renaming in `shadow_blocking_targets`).
- Blocks sharing a signal with different sensitivity sets remain two drivers (warned).
- Pre-existing, unrelated: `always begin #5 clk = 1; #5 clk = 0; end` gets one blocking-shadow commit at the end of the loop body (`process.cc` shadow_blocking_targets commit placement), so `clk` never goes high in VHDL (ivltests/case5.v); function/task/named-block names bypass the reserved-word table; `|PORT:` analog metadata uses the pre-rename name.
- Not committed anywhere (per rules); the iverilog tree also carries an unrelated pre-existing `configure` diff, excluded from the patches. No ivtest case was added for the msb==lsb shape (cases.sv/structcase.sv/nzlsb.sv/partsel.sv in the export are ready to adapt).

## 8. VX_alu_int through the chain — cycle-accurate vs Icarus (2026-09-03)

`VX_alu_int` is the P4 target and the first module with real SystemVerilog:
interface ports (`VX_execute_if`, `VX_result_if`, `VX_branch_ctl_if`),
`import VX_gpu_pkg::*`, macro-declared packed structs, a string parameter.

**Finding: Icarus cannot parse SV interface ports at all** (`bus_if.slave x`
is a syntax error even for `-tnull`), and sv2ghdl's normalizer has no
interface rules. The working chain is therefore
**sv2v → iverilog `tgt-vhdl` → NVC** — sv2v is what Vortex's own Yosys flow
uses for the same reason. sv2v inlines an interface-port module into its
instantiator as a named generate block, so a flat-port wrapper is the top.

**Result: PASS — 42 cycles replayed, 27 results and 7 branch resolutions
identical to the vvp oracle.** The differential test records every cycle's
inputs and outputs from Icarus/vvp on the flattened Verilog and replays
them under NVC, comparing all outputs every cycle: ADD/ADDI/SUB/SLT/SLTU/
AND/OR/XOR/SLL/SRL/SRA/LUI/AUIPC and BEQ (taken/not), BNE, BLT, BGE, BLTU,
JAL on two lanes with periodic `rs_ready` backpressure. Recipe, wrapper,
both testbenches and the oracle vectors: `probes/alutest/`.

Translator gaps found and fixed (iverilog fork commits, one each):

1. String parameter in a generate scope aborted translation — the inlined
   `alu` block carries `INSTANCE_ID = "alu0"`. Skipped in the suffix.
2. Identifier explosion: every numeric parameter of every generate scope
   was folded into every identifier; with the inlined scope's ~40
   localparams that made 1.5 KB names and a 2.1 MB VHDL file. Only
   loop-iteration scopes (`name[idx]`) contribute now — 163 KB.
3. Block-local regs (sv2v's `sv2v_tmp_cast` temporaries) leaked into `@*`
   sensitivity lists while being declared as process variables. Stripped
   after the body is drawn.

Regression: `ivtest/vhdl_nvc_reg.pl` 285/294, failure set identical to
baseline. The elastic-buffer probe still passes on the same build.

Practical notes: sv2v v0.0.13 release binary (no Haskell toolchain
needed); Vortex build axes (`VX_CFG_XLEN`, `FLEN`, `FPU_TYPE`) are `-D`s
not header defines; `vvp` needs `LD_LIBRARY_PATH=<ivl>/_install/lib` and
the ivtest scripts need `<ivl>/_install/bin` first on `PATH`.

## 9. VX_execute through the chain — cycle-accurate vs Icarus (2026-09-03)

The whole execute stage (`hw/rtl/core/VX_execute.sv`, Tier A: ALU+MULDIV, LSU, SFU with `-DVX_CFG_EXT_F_DISABLE`) now replays under NVC cycle-for-cycle against the vvp oracle on the same flattened Verilog, with the translator output taken as generated:

    PASS: 210 cycles replayed and compared from cycle 0 (outputs bit-exact, x = don't-care);
    DUT commits alu/lsu/sfu=39/27/68, lsu req/rsp=27/20, branches=13, csr_wr=2, trap_csr_wr=5, warp_ctl=17
    -- all outputs identical to the vvp oracle every cycle

Recipe, wrapper, both benches, oracle vectors, repros and patches: `probes/exectest/` (README has the full account).

**Chain.** Same as section 8: sv2v (v0.0.13) flattens interfaces/packages/structs, `iverilog -g2012 -tvhdl -psv2vhdl=1` translates, `nvc --std=2040` simulates; vvp on the same `exec.v` is the oracle. VX_execute has seven interface ports (`lsu_client_if[1]`, `dispatch_if[3]`, `commit_if[3]`, `sched_csr_if`, `branch_ctl_if[1]`, `warp_ctl_if`, `dcr_csr_if`), so the top is a generated flat-port wrapper (`gen_wrapper.py` -> `exec_top.sv`, 74 ports + clk/reset): every interface is instantiated in the wrapper, each field becomes a packed port `<if>_<idx>_<field>` with the direction execute's modport gives it (`dcr_csr_if` is the slave side, `VX_csr_unit.sv:34`), struct inputs are cast, nothing is tied off; array sizes stay symbolic with a generate-time `$error` guard on the numeric counts. `mk_ports.py` extracts the resolved widths from sv2v's `exec.v`, and `gen_tb.py` derives the oracle's port map + recorder and the entire VHDL replay bench from that one list, so the vector layout is identical on both sides by construction. Tier B (F enabled with the soft FPU via `-DASIC`, NUM_EX_UNITS=4) translates, analyses, elaborates and runs 100 ns cleanly from the same script; it has no differential test yet.

**Differential test.** Three concurrent deterministic dispatch streams (ALU arithmetic/Zicond/MULDIV incl. /0 and INT_MIN/-1, branches, ECALL/EBREAK/MRET; LSU byte/half/word loads and stores at all alignments, lane masks, IO range, fences against a word-RAM model with 3-cycle in-order responses and `req_ready` 3-of-4; SFU: 42 CSR reads of distinctive `sched_csr_if` constants, CSRRW/S/C incl. trap CSRs, WSPAWN/TMC/PRED/SPLIT/JOIN/BAR/WSYNC with the drain gates exercised), per-unit periodic commit backpressure, DCR reads. All 43 outputs are compared every cycle from cycle 0; inputs are recorded as hex, outputs bit-exact (`%b`), X = don't-care per bit; every `*_valid`/`*_ready` expectation must be defined once reset is released (vacuity guard); the PASS tallies are counted from the NVC DUT's outputs and equal the oracle's sent/commit counts. Single-bit mutants of `vectors.txt` at rows 0, 1 and 13 each fail with exactly one mismatch.

**Translator gaps fixed** (iverilog fork `tgt-vhdl`, 9 files +368/-87, committed as an 11-commit series — patch 07 kept as a separate *defensive* commit after the audit found no failing input for it — and exported as patches, each with a repro under `probes/exectest/repros/`):

1. Entity emission order — a module reused under two parents was emitted after an entity instantiating it (`state.cc`: post-order over instantiation targets).
2. Same-named functions in different modules (sv2v's per-module `sv2v_cast_<hash>`) collapsed to one scope instance (`state.cc same_scope_type_name`: type must match; FUNCTION/TASK/BEGIN/FORK recurse into the parent).
3. Duplicate labels after flattening sibling generate scopes (`scope.cc genvar_unique_suffix`: suffix = path of generate-block names).
4. False "2 always blocks cannot be merged" warning for per-lane `always @*` slice writers (`process.cc has_whole_or_dynamic_write`; dead `drives_whole` removed, dynamic trailing selects counted).
5. Block-local variable with a VHDL-illegal name declared under its safe name but never renamed (`stmt.cc draw_block`; the two `assert(decl)` became diagnostics).
6. Bit/part-select of an unpacked-array word in continuous logic replaced the word index with the bit offset; a 1-bit word (`m[2][idx]`) then got `m(2)(idx)` (`lpm.cc` + `vhdl_var_ref::slice_element`; a scalar word is the word for index 0 and a bounds-safe `l3d_bit_read` on the lifted bit otherwise).
7. Continuous function call with an actual of a different width than the formal (`lpm.cc ufunc_lpm_to_expr`: cast to the formal's type as the procedural path does).
8. Function declared in a generate loop with iteration-dependent formal width de-duplicated by bare name (`scope.cc vhdl_function_name`).
9. Runtime-base bit-select in continuous logic was a bare VHDL index (`Fatal: index 2147483647 outside of NATURAL range` with an x base) and a signed narrow index lost its sign (`lpm.cc`: `l3d_bit_read`/`l3d_part_read` with `l3d_index(off, signed-from-nexus)`).
10. 1-bit Verilog add/sub/mul on two scalar `logic3d` operands added the 3-bit ENCODINGS (0+0 = Z) — found by the differential test: every unit's commit `sid`/LSU tag `pid` was X from the first instruction (`vhdl_syntax.cc`: package vector operator on the lifted bits, bit 0).
11. Constant driver on any word but word 0 of an unpacked array was dropped (upstream TODO in `scope.cc draw_constant_drivers`; not sv2vhdl-specific).

**Review issues closed.** Translator: the medium `slice_element`-on-scalar case (gap 6, repro `scalarword`), signed LPM part-select base (gap 9, `signedidx`), `drives_whole` dead code and the dynamic trailing-select blind spot, `ufunc` cast instead of resize, and the `scope_nexus_t` pin plumbing that could never trigger was dropped (arrayword still passes without it). Testbench: replay pre-history aligned with the oracle (reset asserted at t0, row 0 driven from t0, first rising edge at 5 ns) and comparison from cycle 0 instead of 4; `%b` outputs instead of nibble-granular `%h` (had hidden 695 defined bits, e.g. store-commit sop/eop/bytesel); DUT-side tallies; defined-handshake guard. The same alignment/`rdhex` fix was applied to `probes/alutest/tb_alu_replay.vhd` (PASS from cycle 0; row-0 mutant fails).

**Regressions.** `ivtest/vhdl_nvc_reg.pl` 285/294 with the report byte-identical to baseline; no core file changed (vvp_reg.pl not rerun). `probes/alutest` PASS (vectors identical to the probe's), `probes/ebtest` PASS (eb.vhd identical to the previous build's), Tier B clean, all 13 repros pass. The iverilog tree still carries the unrelated pre-existing `configure` regeneration diff (excluded from the patches; `git checkout -- configure` before committing, but note `make` would then re-run `config.status --recheck`).

**Open items.** `warp_ctl_if.bar_addr`/`dvstack_wid` are combinational from `execute_if` (`VX_wctl_unit.sv:176-177`) while `bar_valid` is registered, so the address sits on the row before each `bar_valid` row and is x on the expect_tx bar row (`txbar_bus_if.data = 'x`, `VX_sfu_unit.sv:223-224`) — compared correctly one cycle early, but a question for Vortex. `l3d_index` reads an all-x index by its value plane (address 0) by package design where Verilog reads x. `nexus_to_var_ref` uses the 0-based nexus pin for arrays with non-zero Verilog bounds (pre-existing, not hit by Vortex). Fused `comb_fused_N` process order is not byte-reproducible between translations (equivalent VHDL). Tier B differential test, `lane_dispatch`'s packet iterator, WGATHER, AMO and XLEN=64 remain uncovered. Committed: the 11 tgt-vhdl fixes in the iverilog fork; `probes/exectest/` and the alutest bench alignment change in mylex.

**Tier B (F enabled, soft FPU via `-DASIC`, NUM_EX_UNITS=4):** translates with zero warnings, analyses, elaborates and runs 100 ns cleanly from the same script — 55 modules including `VX_fpu_std`, `VX_fma_unit_rtl`, `VX_fdivsqrt_unit`, `VX_fcvt_unit`, `VX_wallace_mul`, `VX_csa_*`. No differential test yet, and that is the only detector for the gap-10 class (1-bit arithmetic inside `VX_fma_unit_rtl`/`VX_csa_*`, runtime-indexed selects in `VX_fdivsqrt_unit`). Also found by the audit: translator output is not byte-reproducible run to run (`comb_fused_N` labels and `tmp_ivl_N` temporaries are numbered from pointer-keyed iteration) — equivalent VHDL, but it blocks byte-for-byte regression of generated files.

## 10. Tier B (FPU) differential test PASSES; NVC eval-arena bug found and fixed; translator made byte-reproducible (2026-09-03)

**Result.** The full execute stage with the soft FPU (`-DASIC`, `VX_CFG_FPU_TYPE` = STD, NUM_EX_UNITS = 4) replays under NVC cycle-for-cycle against the vvp oracle, translator output as generated, default NVC settings (5 threads, eval arena on):

    PASS: 641 cycles replayed and compared from cycle 0 (outputs bit-exact, x = don't-care);
    DUT commits alu/lsu/sfu/fpu=39/27/74/106, lsu req/rsp=27/20, branches=13, csr_wr=2,
    trap_csr_wr=5, warp_ctl=17 -- all outputs identical to the vvp oracle every cycle

All 46 wrapper outputs compared every cycle; the oracle's `ORACLE_DONE cycles=641 sent=39/27/74/106 commits=39/27/74/106` matches the DUT-side tallies. Recipe: `probes/exectest/run.sh tierB && run_tb.sh tierB all` (README has the full account; vectors in `vectors_tierB.txt`, generated benches `tb_exec_tierB.sv` / `tb_exec_replay_tierB.vhd`, logs `evidence_*_tierB.log`).

**Tier B coverage** (`coverage.py --tier tierB`, `decode_tierB.py`): 106 FPU instructions dispatched and committed on `dispatch_if[3]`/`commit_if[3]` (495 stall cycles under the 2-entry tag store, 54 backpressure cycles from two 12-cycle `commit_ready` windows), 4 results returned out of dispatch order; ops FADD 13, FSUB 4, FMUL 10, FMADD 7, FMSUB 2, FNMADD 2, FNMSUB 1, FDIV 11, FSQRT 9, F2I 9, F2U 5, I2F 6, U2F 3, FMIN 3, FMAX 2, FSGNJ/N/X 4, FCLASS 5 (all ten classes), FMV 2, FEQ/FLT/FLE 8; rounding modes RNE 56, RTZ 8, RDN 5, RUP 6, RMM 3, DYN 4 (DYN resolves to RDN on warp 1 after the SFU stream's CSRRW of FRM, RNE on warp 0 -- results 0xBF800001 / 0x4F7FFFFF prove it); operands +0 31, -0 14, +inf 13, -inf 10, qNaN 17, sNaN 6, subnormal 25; latencies FMA 10-12, FDIV/FSQRT 19-21, FCVT 7-8, NCP 4-6; last FDIV/FSQRT commits at cycles 456/457 of 641. **206/206 lane results equal an exact IEEE-754 binary32 reference** computed independently by the decoder, 0 x bits in any valid FPU commit; fflags read-back through the SFU: FFLAGS(w0) = 0x1F, FCSR(w1) = 0x5D (RDN | NV DZ OF NX), FRM(w1) = 2, FCSR(w0) = 0 after CSRRC. The Tier A tallies are unchanged in the same run (SFU 74 = 68 + 6 F-CSR ops). **No translator gap in the FPU**: the gap-10 class (1-bit arithmetic on scalar `logic3d`) does not recur in `VX_fma_unit_rtl`/`VX_wallace_mul`/`VX_csa_*`/`VX_fdivsqrt_unit`/`VX_fcvt_unit`.

**Review issues closed (testbench, all high/medium and the low one).** `FMT_S`/`FMT_SUB` were declared as `S`/`SS` (oracle did not compile); `tx_fpu` never initialised (x on `dispatch_if_3_data/ready` in rows 0-2 tripped the replay's vacuity guard at cycle 2 -- now `'0` from row 0 under the F guard); `run_tb.sh` was Tier A only and wrote into the probe directory -- now `run_tb.sh [tierA|tierB] [oracle|replay|rerun|all] [outdir]`, everything under the out directory, port list checked against `ports_<tier>.txt`; the end-of-test wait and both `ORACLE_*` lines include the FPU port; `coverage.py`/`decode_commits.py` take `--tier` (commit/dispatch layout shifts by one bit with NUM_REGS_BITS = 6, LSU request offsets derived from the port width; Tier A output byte-identical), `decode_tierB.py` exported; `FR+32..61` wrapped past rd = 63 -> `FR+0..29` (f-register destinations now 32..63). Tier A vectors are byte-identical to the committed file after all of this (every change is under `` `ifndef VX_CFG_EXT_F_DISABLE ``).

**The Tier B crash was an NVC runtime bug, not a translator or DUT divergence.** On the unfixed fork the replay died at row 87 with `SEGV_MAPERR address=0x200000002` in `STD.TEXTIO.GET_CHAR`. Characterisation: 100% reproducible; 1/2/4 NVC threads pass, 3/5 crash; `NVC_JIT_THRESHOLD` 1/10/10^8 pass, default 100 crashes; `NVC_JIT_ASYNC=0` still crashes; `--jit` moves it to row 91; `-H` has no effect; gdb passes unless `LINES`/`COLUMNS` are unset (heap-layout dependence). `NVC_MAX_THREADS=1` and `NVC_NO_EVAL_ARENA=1` each let the **full 641-row replay pass bit-exact** on the unfixed build, localising the fault to the simulator's memory management. Root cause (hardware watchpoint under gdb + `jit-exits.c`/`jit-llvm.c`/`rt/model.c`): the fork's eval-lifetime arena (commit `28f14fcee`, default on since the gate flipped to `NVC_NO_EVAL_ARENA`) routes every `__nvc_mspace_alloc` from LLVM-compiled code into a per-thread bump arena reset at each process evaluation; that exit is not only the TLAB-overflow path for escaping unconstrained results but also `MACRO_GALLOC` -- VHDL `new` and protected-type state -- while the interpreter's `new` goes to the collected heap. So once textio's `readline`/`grow`/`shrink`/`consume` tier up to native code (after 100 calls; any bench that reads vectors), the `line` descriptor lives in memory the next evaluation's transients overwrite -- `0x200000002` is two `L3D_0` (= 2) elements of a `logic3d_vector` over the line's data pointer. The fork's own commit message states the assumption ("no access types / pointer-bearing results stored across a wait"). Fix (patch 13, +56/-13): `__nvc_mspace_alloc` is the heap again; new `__nvc_eval_alloc` serves only the TLAB slow path (`cgen_tlab_alloc_body` in jit-llvm.c, the `tlab stub` in jit-x86.c) from the arena when enabled; declared by name with the same signature because the `llvm_fn_t` table is full (`STATIC_ASSERT(LLVM_LAST_FN <= 64)`, code-cache `helper_mask`), exported in `symbols.txt` and registered in `jit-code.c`. Minimal repro `repros/arena_new.vhd` (a `line` kept across a wait while another `readline` reuses the arena; `NVC_JIT_THRESHOLD=1`): unfixed fork `iteration 195: line corrupted at 1 ('b' expected 'a')`, fixed `PASS: 200 lines kept across waits` (verified by stash/rebuild both ways); with the default threshold the small file happens to pass on the unfixed build, so the exec replay remains the primary evidence. The NVC change is exported as `patches/13-nvc-jit-eval-alloc.patch` and left **uncommitted** in `/usr/local/src/nvc` (that repository is not in the commit grant); the build in `/usr/local/src/nvc/build` is the fixed one, so every result above was produced with it.

**Determinism fix (translator gap 12, patch 12).** Two translations of the same Tier B `exec.v` differed in 4520 lines (`comb_fused_0`/`_1` of `VX_csa_tree` swapped, `tmp_ivl_N` renumbered) when invoked with an absolute vs a relative path: `process.cc fuse_comb_cones` iterated a `std::map<member_t*, ...>` keyed by member pointer, so the order followed the heap layout. Components are now visited in order of first appearance in the Kahn order (`comp_order`; the map is a lookup only). Verification: three translations each of `VX_elastic_buffer`, `alu.v`, Tier A `exec.v`, Tier B `exec.v` -- relative path, absolute path, absolute path under a 4 KB environment variable -- byte-identical after path normalisation and identical to the fresh runs' files. `repros/fusedorder.v` + `run_fusedorder.sh` (eight cones, three argv/env layouts) passes; it does not reorder on the unfixed translator (monotonic allocations -- the permutation needs a large design's allocator churn), the Tier B diff is exported as `evidence_fusedorder_tierB.diff`.

**Regressions on the final builds** (iverilog `c157cf9` + patch 12, NVC `ed2e52793` + patch 13): `ivtest/vhdl_nvc_reg.pl` 285/294 with the report byte-identical to the baseline (same 9 failures), run twice on the final binaries; no iverilog core file changed, `vvp_reg.pl` not rerun. Fresh runs: ebtest PASS 5 tokens (`eb.vhd` differs from the section-7 export only in gap-3 generate suffixes), alutest PASS 42 cycles with identical vectors, exectest Tier A PASS 210 with byte-identical `vectors.txt`, Tier B PASS 641; all 13 previous repros plus the three new ones pass. Exported into `probes/exectest/` (stray build outputs removed first): the bench template/generator/script changes, `ports_tierB.txt`, `vectors_tierB.txt`, Tier B generated benches and evidence logs, `decode_tierB.py`, `repros/{fusedorder.v,run_fusedorder.sh,arena_new.vhd,arena_line.vhd,run_arena_*.sh}`, `patches/12-*.patch`, `patches/13-*.patch`, README (Tier B section, gaps table row 12, Simulator fix, Determinism, verification). Patch 12 is committed in the iverilog fork; the NVC patch is exported only.

**Open items.** (1) NVC eval arena: TLAB-overflow objects of a process that keeps its own TLAB across a wait (`proc->tlab`, waiting procedures with large locals) still go to the shared arena that the next evaluation of any process resets -- the fork's pre-existing hazard, untouched by patch 13; the interpreter's overflow path still churns the GC. (2) `arena_line.vhd` (one `read` per character with a signal assignment in between) passes on both builds -- kept as a regression check, not a demonstration. (3) `fusedorder.v` does not reproduce the old reordering by itself (see above). (4) Unchanged from section 9: `warp_ctl_if.bar_addr` one cycle early / x on the expect_tx row (question for Vortex), `l3d_index` on an all-x index, `nexus_to_var_ref` with non-zero array bounds, and the uncovered `lane_dispatch` packet iterator, WGATHER, AMO, XLEN=64, FLEN=64/F2F and hard-FPU paths. (5) The iverilog tree still carries the unrelated pre-existing `configure` diff (not exported).

*Provenance note.* In this run the Tier B, determinism and translator-review agents were all lost to API 529 errors (three retries each); the verify agent carried the whole task and produced the report above. The translator change (patch 12) was therefore reviewed by hand before commit: it only replaces pointer-order iteration with first-appearance order over the existing Kahn ordering.

## 11. Execute stage bit-exact through gen_statemachine's C model; NVC `--accel` installs the compiled Vortex DUT; review closed (2026-09-03)

The single-cycle C model that sv2ghdl's `gen_statemachine` emits from Yosys RTLIL (the `gpubuild`/`--accel` engine) replays the committed oracle vectors bit-exact for all three Vortex designs, and NVC's `--accel` text path now compiles and installs that model for the whole translated DUT and still passes the replays. Everything below was re-run fresh on the final builds (sv2ghdl `ad031b1` + `probes/gsm/02-*.patch`, NVC `54aa09179` + `03-*.patch`, iverilog `86eba14`; every `alu.v`/`exec.v`/`.vhd`/vector file regenerated from the recipes, no hand patches); details, repros and logs in `probes/gsm/README.md`, `probes/gsm/repro/`, `probes/gsm/evidence/`.

    C model:   ALU     PASS: 42 cycles, 27 results, 7 branches, 0 mismatches            (189 cells / 2 registers)
               Tier A  PASS: 210 cycles replayed through the gen_statemachine model, 0 mismatches   (1,092 cells / 66 registers)
               Tier B  PASS: 641 cycles replayed through the gen_statemachine model, 0 mismatches   (13,977 cells / 168 registers, soft FPU)
    --accel:   alu_top  ACTIVE -- 'alu_top' subtree rerouted to native model (accel installed);  PASS 42 cycles   (plain 0.37 s, cold 3.6 s, warm 0.20 s)
               exec_top ACTIVE -- 'exec_top' subtree rerouted to native model (accel installed); PASS 210 cycles  (plain 2.5 s, cold 83 s = gcc -O3 of 5 MB, warm 1.3 s)

**Verdict on the "execute residual"** (10 mismatches in the first C-model replay): closed, no emitter defect. Cycles 12/13/15 were the partial-slice-store bug of section 10's follow-up (`ad031b1`) replayed against a model generated before the fixed binary -- bisected per cycle on every internal comb signal to `alu_int.msc_result` at the AND of PC 0x105 (lane 1 stored at lane 0), the AND/ORI/SLL commits, with `branch_ctl_if_0_dest` only echoing `from_fullPC(alu_result_r[last_tid])` under `valid = 0`. Cycle 0 was the harness: the oracle bench's first rising edge (5 ns) precedes its row-0 sample (11 ns), so row k follows k+1 posedges; the generated harness and `harness_alu.c` now replay that edge and compare every row from 0 (`repro/prehist.v` shows `sm_reset` already honours `init` attributes and `$adff` values; the only time-0 difference -- un-reset registers x in vvp, 0 in the model -- is never sampled). The three single-bit vector mutants each fail with exactly one mismatch, so the compare is not vacuous.

**`--accel` gaps closed** (the previous pass installed nothing on Vortex). In `nvc/src/rt/model.c`: the synth top is the Verilog module named at the `nvc_verilog_src` line rather than the lowered, parameterisation-suffixed entity name (`vx_pipe_register1` -> `VX_pipe_register`); the `nvc_verilog_params` attribute is no longer truncated at 256 bytes (the "mangled chparam target" was this truncation, not a tokenizer bug: exec_top's attribute is 1.5 KB / 58 tokens), the argv/command are sized by contents and the actuals are in the cache key; and the STD_MX "port with no real driver" walks in `source_value`/`calculate_driving_value` count a `SOURCE_DEPOSIT`/`SOURCE_FORCING` pseudo-source as a value source -- without that the bridge's NBA-region publication onto the ports tgt-vhdl writes with the fork's blocking `:=` never reached their readers (the installed ALU FAILed 60 rows on the branch outputs while `NVC_ACCEL_VERIFY=1` saw every net agree). In `sv2ghdl/yosys/gen_statemachine.cpp`: an override equal to the module's default is kept instead of `chparam`ed, because `chparam` re-derives the module and sv2v's by-module-name hierarchical reference inside a function argument (`sv2v_cast_4(alu_top.execute_if.data[..])`) does not survive the derivation; localparams are filtered whenever the top is found. The installed scopes are the whole DUT subtrees (`aj_alu_top_*.so`, `aj_exec_top_*.so` in the cache); a VCD comparison of the plain and accelerated ALU runs agrees on all 434 tb-level signals at every compare instant (row-0 `br_*` excepted, where the oracle expects x).

**Review issues closed.** (high, both reviews) the keep-if-default test compared against a snapshot of `parameter_default_values` taken before any `chparam`, while a default may derive from another parameter (`parameter RESETW = DATAW` -- the `VX_pipe_register` shape, 15 such headers under `hw/rtl/libs`) and each `chparam` re-derives the module: an actual coinciding with the stale default was dropped silently (`dep.v DATAW=4 RESETW=1` reset all four bits). Fixed: the default is read from the live module on every test, kept overrides are re-tested after the loop and any whose default drifted is applied, sweeping until none drifts. (medium) the parsed value was `strtoll(,0)` (octal for `010`) truncated to the default's width (`BASE=4294967296` on a 32-bit default matched 0): now base 10 with overflow rejected, compared at >= 64 bits with the default sign-extended per its own signedness (nvc's `18446744073709551615` and a CLI `-1` both keep a signed -1 default; HEAD aborted on `-1`). `repro/gsm_keep_stale_default/run_cases.sh`: `dep.v`/`chain.v` in both argument orders are semantically identical to HEAD's chparam-everything models, the all-default and `hier.v N=2` cases are byte-identical to the no-override models, the edge cases take the `chparam` leg. (low, nvc) the module-header scan counted 4096-byte `fgets` chunks as lines and took `automatic` for a name: `repro/accel_modline` (`modline.c` old vs new scanner: `decoy` vs `PTop`), plus a guard that rejects a name that is not a prefix of the entity name (declines instead of synthesizing a different module). (low, report) the sv2ghdl tree does carry an uncommitted `gen_statemachine.cpp` change -- it is `02-gen_statemachine-chparam-default.patch`, and the installed `gen_statemachine`/`libgsm.so` and all evidence here are built from it. Not addressed: tgt-vhdl records only numeric actuals in `nvc_verilog_params` (string/real-parameter variants would synthesize the default one; Vortex's string parameters are trace-only) -- an `iverilog/tgt-vhdl/scope.cc` change, out of scope here.

**Regression on the final builds.** `probes/ebtest` PASS 5 tokens; `probes/alutest` vvp vectors and `alu.v` byte-identical to the committed/previous files, NVC replay PASS; `probes/exectest` fresh Tier A and Tier B: PASS 210 / 641 cycles, `vectors.txt`/`vectors_tierB.txt` byte-identical to the committed files; `ivtest/vhdl_nvc_reg.pl` 285/294, report byte-identical to the baseline (failure set always3.1.4G basicstate basicstate2 contrib8.2 dff1 function1 inout port-test2 pr142); NVC `test/accel` 8/8 MATCH and `bin/run_regr` over the full 1,265-test `test/regress` list: 1,147 ok / 112 failed / 4 skipped with an identical failure set on the pre-fix binary (the fork's pre-existing `vlog*`/`mixed*`/`vhpi*`/`wave*`/`issue*` failures); gen_statemachine `repro/slicecase.v`, `repro/run_prehist.sh`, sv2ghdl `yosys/rtlil-selftest` PASS; sv2ghdl's VeeR-era `regress/accel` suite is not runnable here (needs Verilator).

Open: the RTLIL walker (`NVC_ACCEL_RTLIL=1`) still declines on `T_FCALL`; yosys' `chparam` on the sv2v function-argument hierarchical-reference shape fails for a genuinely non-default value (`repro/gsm_chparam_default` N=3); `gen_statemachine` declines comb-only modules; Tier B was not run under `--accel` (the 56 MB model's gcc time adds nothing to the install evidence). Nothing committed: sv2ghdl (`gen_statemachine.cpp`), nvc (`model.c`) and mylex (this file, `probes/gsm/`) are working-tree changes for review.

*Commit status for §11:* sv2ghdl `10e0aaa` (chparam default), nvc `9f228411e` (accel text path); iverilog unchanged (`86eba14`).

## 12. What the direct-RTLIL walker needs for Vortex — measured catalogue (2026-09-03)

CATALOGUE OF WHAT THE DIRECT-RTLIL WALKER (NVC_ACCEL_RTLIL=1, nvc/src/vhdl2vlog.c vhdl2rtlil_module) NEEDS FOR THE TRANSLATED VORTEX DESIGNS — measured, nothing implemented.

Baseline (final builds: NVC 54aa09179 + 03 patch, sv2ghdl ad031b1 + 02 patch, iverilog 86eba14; fresh alu.vhd/exec.vhd of cmp/final/): with NVC_ACCEL_RTLIL=1 the walker is tried first and declines the whole DUT at the TOP module, then the text path installs exactly the same scopes as without the flag and the replays PASS — ALU: `vhdl2rtlil: 'alu_top' declined (function VX_GPU_PKG_TO_FULLPC_ALU @?)` -> text path -> 189 comb cells / 2 registers -> `ACTIVE 'alu_top' subtree rerouted` -> PASS 42 cycles (wall 3.8 s); Tier A: `'exec_top' declined (function VX_GPU_PKG_TO_FULLPC_EXECUTE_ALU_UNIT_G_BLOCKS_0_ALU_INT @?)` -> 1092 cells / 66 registers -> ACTIVE exec_top -> PASS 210 cycles (wall 78.8 s). Logs: cmp/rtlil_catalog/alu_base.summary, tierA_base.summary, accel_alu_base.log, accel_tierA_base.log (all under /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/rtlil_catalog/). The `@?` breadcrumb means the decline happened before any statement was walked: it is NOT a T_FCALL/expression decline at all — it is the walker's 8-entry cap on inlinable function bodies (item 1); the previous README's 'declines on T_FCALL' reading was wrong, and the message printed an uninitialised buffer (`fw`) after the function name.

Method: the walker stops at the first decline per module and the whole subtree at the first declining module, so the catalogue needed a diagnostic-only 'census' mode (04-nvc-rtlil-census.patch, +424/-81 in vhdl2vlog.c + 2 hunks in rt/model.c, env NVC_ACCEL_RTLIL_CENSUS=1): the child walks EVERY module of the subtree against a null builder, never stops at a decline, streams `module pN L<vhd line>: reason@site`, tags bare `return false` paths (`silent-stmt`), catches a walker crash per process (`CRASH(sigN)`), raises the function cap to 64 only in census mode, and always exits 3 (text path as before). In normal mode the patch changes nothing but messages (`function X cap8`, `fcall:<name> d<depth>`, `expr-kind N`, `binop <op>`, `conc-kind N`) and the array size g_r2_funcs[64] (cap still 8). It is applied in the NVC working tree and installed in /usr/local/src/nvc/build (revert: `git checkout src/vhdl2vlog.c` and `patch -R -p1 < 04-nvc-rtlil-census.model.diff`, then rebuild; the 03 patch hunks in model.c are untouched). Runs: accel_alu_census3.log, accel_tierA_census3.log, accel_tierB_census4.log (Tier B with NVC_ACCEL_CC=false + NVC_ACCEL_EXCLUDE=replay.dut. so the 56 MB model is never compiled and children are not re-walked); aggregation agg.py / procsum.py, static census census.py -> census_static.txt, tierB_agg.txt. All three census runs still install via the text path (ALU/Tier A PASS again; Tier B compile deliberately failed).

Coverage after the census (first walk of the DUT, modules deduplicated by variant name): ALU 9 modules / 105 processes, 6 modules clean, 13 processes fail (13 leaf declines); Tier A 51 modules / 613 processes, 34 clean (elastic/pipe buffers, stream arb/switch, generic/priority encoders, csa_32, multiplier, popcount, lsu_agu, sv_and/or/xor gate variants), 65 processes fail, 76 leaf declines; Tier B 119 modules / 6093 processes, 64 clean (adds fp_classifier, lzc, pe_serializer, fma_unit, csa_42/counter_5to3, index_buffer), 1810 processes fail, of which 1741 are one family (unpacked signal arrays used as wire arrays in VX_ks_adder 1409/1602, VX_find_first x3 253, VX_fdivsqrt_unit 33/622), plus one walker CRASH (VX_wallace_mul). Leaf totals — Tier A: proc-extra-stmt 41, var-assign(slice in branch) 8, fcall depth-1 8, bitread-width 6, dyn-multi 4, var-elem 4, for-range 3, var-read 2. Tier B: array-ref@cont-rhs 1397, cont-assign-target 152, comb-empty 115, slice-base 98, array-ref 68, proc-extra-stmt 78, var-assign k22 20, var-assign k23 8, bitread-width 8, fcall d1 8, var-read 7, var-elem 6, for-range 5, dyn-multi 5, function(non-straight) 6 + 1 call, mem-usage 2, CRASH 1.

Static census of the idioms (census_static.txt, grep counts): function bodies emitted per design ALU 26 / Tier A 61 / Tier B 151, of which VX_gpu_pkg_* 9/20/20 and sv2v_cast_* 14/26/86 are ALL straight-line (`Result := expr; return Result`), Reduce_OR/Reduce_AND/Boolean_To_Logic/Ternary_* (3/15/40) are already builtins of vlog_l3d_op/fn_is_builtin, and only 4 VX_csa_tree/csa_block constant-evaluation functions are non-straight (Tier B). l3d_*/is_one/sv_and family calls are handled (l3d_and/or/xor/not, l3d_lt_s family, l3d_bit_read/part_read/index/resize_s, to_l3d/resize/to_unsigned identities, ternary_*; sv_and/sv_or/sv_xor are sv2vhdl gate ENTITIES instantiated as components and walk clean). Per-design idiom counts: nba_init_run guard 2/41/78 (= every NBA-shadow clocked process), merged same-edge always 2/5/10, OOB_WriteV dynamic part-write 4/22/75, casez/casex 0/1/2, Verilog_Case_Ex selectors 12/24/37, dynamic-index writes 4/14/24, unpacked array-of-vector signal types 0/0/9 with 1567 word-indexed accesses in Tier B, statements with >=64 `&` operands 0/0/1 (max 32/32/623).

Ordering by payoff: items 1+2+6 (trivial) admit every package/sv2v function; 3 (small) admits all 41 Tier A / 78 Tier B NBA clocked processes and makes VX_pipe_register*, VX_stream_buffer*, VX_shift_register, VX_elastic_adapter, VX_priority_arbiter, VX_serial_div, VX_allocator, VX_fcvt/fncp_unit walk clean; 4+5+7+8 (small/medium) close the remaining 29 Tier A leaf declines so ALU and Tier A walk with ZERO declines; Tier B additionally needs 9 (wire arrays, medium, 1741 processes), 10 (concat-chain crash, small), 11+12 (csa_tree constant functions / mem-usage, small). Estimated total ~3-4 engineer-days for Tier B, ~1.5 for ALU+Tier A. The prior README/LDX-VORTEX 'still declines on T_FCALL' statement should be corrected to 'declines on the 8-function cap'.

| Construct | Where | Plan | Effort |
|---|---|---|---|
| Cap of 8 inlinable user-function bodies per module (the actual `(function VX_GPU_PKG_TO_FULLPC @?)` decline; `fw` printed uninitialised) | /usr/local/src/nvc/src/vhdl2vlog.c vhdl2rtlil_module function scan: HEAD 54aa09179 L5693-5708 (`r2_func_inlinable(d, fw, sizeof fw) && g_r2_nfuncs < 8`, `g_r2_funcs[8]` L3079); patched tree L5851 (`g_r2_census ? 64 : 8`). Idiom: tgt-vhdl emits every VX_gpu_pkg_* function (to_fullPC, from_fullPC, inst_alu_class, inst_br_*, inst_lsu_*, inst_m_*, wis_to_wid, inst_sfu_is_csr) and every sv2v_cast_<N\|hash>[_signed] helper as an `impure function` body in the architecture that uses it; alu_top has 21 straight-line bodies (9 pkg + 12 sv2v), exec_top 30 (Tier A and Tier B); the 9th body in declaration order (to_fullPC) trips the cap. Counts: bodies 26 / 61 / 151 (ALU / A / B); pkg+sv2v bodies 23 / 46 / 106, 100% straight-line (`Result := expr; return Result`) so the existing inliner takes all of them once the cap is gone. | Make g_r2_funcs a growable array (or 64) with no functional cap; initialise `fw` (done in the census patch: message `function <name> cap8`). No new lowering needed. | trivial (10 lines) |
| Nested function call inside an inlined body (inline depth limited to 0) | r2_expr T_FCALL user-function inliner: HEAD L4366 `if (g_r2_inline_depth == 0)`, decline HEAD L4504 (`fcall`; census message `fcall:SV2V_CAST_32 d1 np1@seq-assign`). Idiom: package bodies call sv2v casts — to_fullPC = `sv2v_cast_32(pc & "00")`, from_fullPC = `sv2v_cast_30(resize(pc srl l3d_shcount(2), 30))`, inst_* return `sv2v_cast_1/2(...)`. Sites: ALU 5 (alu.vhd:2794, 2902, 2944, 2945, 2964), Tier A 8 (exec.vhd:13492, 13538, 13614, 13615, 13635, 13858, 12852 …), Tier B 8. | Allow g_r2_inline_depth <= 4: the per-call substitution snapshot/restore (r2_subst_save/restore) already scopes bindings, so recursion is safe; the sv2v_cast bodies are identity assigns. | trivial (5 lines) |
| tgt-vhdl NBA idiom tail: `if nba_init_run then nba_init_run := False; else wait for 0 ns; end if;` between the edge-if and the commit (and, rarer, a second `if rising_edge(clk)` from merged same-edge always blocks) | r2_process pre/post scan of the clocked shape: HEAD L5494-5551, decline `proc-extra-stmt` HEAD L5543 (any statement after the edge-if that is not the `r <= v_nba_r` commit). Text path keeps it (emit_process HEAD L2053-2086 emits pre/post statements verbatim, T_WAIT emits nothing, yosys drops the dead variable). Occurrence: every clocked process with an NBA shadow variable: ALU 2 of 4 clocked processes (VX_pipe_register/1), Tier A 41 of 47 (exec.vhd:6787, 6373, 6303, 6078, 5977, 1794, 5484/5508/5532/5552 per VX_stream_buffer, 5245/5293, 4270, 12372/12452/12678 in exec_top …), Tier B 78 of 89; it is the FIRST and only decline of VX_pipe_register*, VX_stream_buffer*, VX_shift_register, VX_elastic_adapter, VX_priority_arbiter, VX_serial_div, VX_allocator, VX_fcvt_unit, VX_fncp_unit. Merged same-edge second edge-if: ALU 2, Tier A 5, Tier B 10 processes (`-- [+ merged same-edge always block(s)]`, e.g. alu.vhd:457-512). | In the post-if scan accept and skip a T_IF whose condition is a T_REF to a process-local Boolean variable that is only ever written (nba_init_run) and whose arms hold only that var-assign and T_WAIT; accept several edge-ifs with the same edge by walking each body under the single sync (same targets/hold temps) in statement order. | small (30-60 lines) |
| Slice / element write to a process variable inside a case arm or if branch (comb pre-copy variable) | r2_seq_one T_VAR_ASSIGN: per-bit build requires g_r2_case_depth == 0 (HEAD L4765), promotion requires a whole T_REF target (HEAD L4879); decline `var-assign k23 d1` (T_ARRAY_SLICE) / `k22 d1` (T_ARRAY_REF) at HEAD L4809. Idiom: comb `always @* case` per lane — `v_shr_zic_result_alu := shr_zic_result_alu; Verilog_Case_Ex := ...; case ... when "10" => v_shr_zic_result_alu(31 downto 0) := l3d_and(...)` (VX_alu_int msc/shr/vote/shfl results; alu.vhd:2348, 2366, 2384, 2415, 2446, 2468; exec.vhd Tier A 12086, 12104, 12122, 12153, 12184, 12206 +2; Tier B 8) and the FPU fflags merge loop `v_sig_merged_fflags_g_fma(0) := l3d_or(v_sig_merged_fflags_g_fma(0), l3d_bit_read(...))` inside a while/if (Tier B VX_fpu_std 20 sites, exec.vhd:73892-73916). Counts: ALU 6, Tier A 8, Tier B 28. | Promote the variable to a pvar (r2_pvar_promote already creates hold temp g0 rooted at the pre-copy value) and case_assign onto the sigspec slice `g0[hi:lo]` / `g0[i]` (RTLIL case actions take any sigspec LHS, exactly what the signal-slice path at HEAD L4993-5018 does); reads then come from the hold temp (next item). | small-medium (~80 lines) |
| Reads of a branch-written (promoted) process variable and element reads of a substituted variable — case selectors, OOB temporaries, casez expansion | r2_expr T_REF `var-read <var>` HEAD L3839 (no pvar read path; only the flat substitution and NBA alias are consulted) and T_ARRAY_REF `var-elem <var>` HEAD L4072 (an indexed read of a whole-substituted or promoted variable). Idioms: `Verilog_Case_Ex := l3d_to_unsigned(op(3 downto 2)); case Verilog_Case_Ex is` where the assign sits inside an `if` (alu.vhd:2556, 2601; exec.vhd Tier A 12290, 12335; Tier B 7 incl. VX_fma_unit_rtl 56181, VX_fp_rounding 70400/57331); `OOB_WriteV_Tmp_N(OOB_P)` element reads (Tier A 12413, 12627, 12946; Tier B 4); tgt-vhdl's casez expansion `((Verilog_Case_Ex(0) = 'Z') or (Verilog_Case_Ex(0) = '1')) and ...` on a variable of type unsigned (VX_rr_arbiter exec.vhd:4249; Tier B 74478, 4929). Counts: ALU 2, Tier A 6, Tier B 13. | In r2_expr resolve a T_REF to a pvar as its hold temp g0 (value-so-far: RTLIL case actions are ordered, so a read after the write inside the tree sees the new value); resolve T_ARRAY_REF/SLICE on a substituted spec by indexing the spec (`spec[i]`, or the per-bit table); fold `= 'Z'` on a 2-state operand to 1'b0 so the casez chain reduces to plain equality tests. | small (~40 lines) |
| l3d_bit_read on an unconstrained operator-result operand (width unknown) | r2_expr l3d_bit_read lowering HEAD L4214-4236: `aw = r2_width(ea); if (aw <= 0) R2_DECLINE("bitread-width")` (HEAD L4223). Idiom: VX_lane_dispatch issue-index arithmetic `issue_indices := l3d_bit_read(unsigned_to_l3d(l3d_to_unsigned(a)) + unsigned_to_l3d(l3d_to_unsigned(b)), 0)` (exec.vhd Tier A 13060, 13121, 13176, 13237, 13292, 13353; Tier B 8 sites at 84050-84343). | Use r2_width_or_operands(ea) (already used by the binop path for the same unconstrained `+` chains) instead of r2_width. | trivial (2 lines) |
| OOB_WriteV guarded dynamic part-select write idiom (`target[idx*W +: W] = val`): `Tmp := val; Idx := l3d_index(e); if Idx in range then for OOB_P in 0 to W-1 loop if Idx+OOB_P in range then target(Idx+OOB_P) <= Tmp(OOB_P); end if; end loop; end if;` | r2_seq_one T_FOR HEAD L5207-5244: `g_r2_case_depth != 0` -> `for-range` (HEAD L5217) because the loop sits inside the range-guard if; the Tmp reads hit `var-elem` (previous item). Idiom sites: VX_lane_gather result_out_data (exec.vhd Tier A 12425, 12639, 12958), VX_pipe_register partial-reset loops (alu.vhd:470-500), VX_fpu_std per_core_data_out (Tier B 73990), LSU/FPU lane packing. Occurrence by `variable OOB_WriteV_Tmp` decls: ALU 4, Tier A 22, Tier B 75 (walker leaf hits 3 / 5 because earlier declines mask the rest of each process). | Pattern-match the whole idiom (Tmp assign, Idx := l3d_index(e), the two range guards, the W-iteration loop with the single bit copy) into ONE W-bit masked compose on the target's hold temp: g0 = (g0 & ~(M << idx)) \| ((val & M) << idx) with $shl/$and/$or cells — the W-bit generalisation of the existing dynamic single-bit compose (HEAD L5019-5100); the range guards fold because shifted-out bits vanish. Alternative (larger): general for-loop unrolling inside branches with scoped substitutions, which then needs the multi-dyn-write item too. | medium (~150 lines) |
| Several dynamic single-bit writes to the same target in one process | r2_seq_one dynamic single-bit write HEAD L5019-5050: the compose reads the PRE value (the signal), so a second dynamic write to the same target declines `dyn-multi` (HEAD L5043). Idiom: LSU byte-enable decode in case arms `mem_req_byteen_w(l3d_index(req_align(1) & L3D_0)) <= L3D_1; mem_req_byteen_w(l3d_index(req_align(1) & L3D_1)) <= L3D_1;` (exec.vhd Tier A 12497/12498, 12514/12515; Tier B 83294/83295, 83311/83312) and VX_allocator `free_slots_n(To_Integer(release_addr)) <= '1'; ... free_slots_n(To_Integer(acquire_addr_r)) <= '0'` in two ifs (Tier B 4304). Counts: Tier A 4, Tier B 5. | Chain the composes: the second compose reads the previous compose's result temp (or the hold temp g0 when the writes are in different arms) instead of the signal; drop the dynwr[] one-shot table. | small (~30 lines) |
| Unpacked signal arrays of vectors used as WIRE arrays (constant / generate indices), not memories: word reads with bit/slice selects, continuous and comb writes of single words | Module level: mem_shape qualification HEAD L5738-5796 admits them as memories; then the lone-assign continuous path excludes memory bases (`cont-assign-target` HEAD L5399), the comb collector skips memory words (`comb-empty` HEAD L5420), a slice of an indexed word `srt_stage(13)(106 downto 76)` hits `slice-base` (HEAD L3941), a bit of an indexed word `P_g_KS(0)(0)` / `srt_stage(13)(19)` hits `array-ref` (HEAD L4052), and `mem-usage` (HEAD L5779) declines VX_csa_block (Ct/St 3x56) and VX_dp_ram (2x51) outright. Idiom (Tier B only): VX_ks_adder `G_g_KS/P_g_KS : array (6 downto 0) of logic3d_vector(47 downto 0)` per-level prefix trees (1395 array-ref@cont-rhs + 14 cont-assign-target, 1409 of its 1602 processes), VX_find_first x3 `d_n/s_n` reduction trees (`d_n(0) <= d_n(1)` in comb ifs: 138 cont-assign-target + 115 comb-empty), VX_fdivsqrt_unit `srt_stage` stage array (98 slice-base + 68 array-ref). Counts: 9 array types, 1567 `X(i)(` accesses, 1828 leaf declines, 1741 failing processes (96% of Tier B's failures); 0 in ALU / Tier A. | At module level classify a memory-shaped signal whose every index is a compile-time constant after elaboration (generate/loop indices are folded) as a wire array: create one wire per word (`name__w<i>`) and rewrite `name(i)` refs, targets and their slices/bits to that wire so the normal paths apply (the text path gets the same effect from yosys mem2reg on its bare reg array). Keep the memory classification only for runtime-indexed arrays (the NBA-shadow RAM idiom). | medium (~200 lines) |
| Walker CRASH (SIGSEGV) on a 623-operand `&` concatenation chain — VX_wallace_mul comb_fused_0 `pp := tmp_ivl_0_g_pp_loop_23 & tmp_ivl_2_... & ...` (1152 bits) | exec.vhd (Tier B) L53516; census `vx_wallace_mul p1153 L53516: CRASH(sig11)@seq-assign`; without the guard the fork child dies: `accel-jit: rtlil builder failed for 'exec_top' (status 139) — text path` (accel_tierB_census.log:1634, accel_tierB_census3.log:3850), i.e. the whole Tier B subtree falls to the text path before any decline reason. The concat is handled recursively — r2_expr `"&"` path HEAD L4299-4307 recurses per operand with a 5.5 KB frame (`sub $0x1000; sub $0x5b8` in r2_expr.constprop.0) after r2_eval_int/r2_const also recurse — a stack overflow (confirm with gdb on the child). Only statement with >= 64 operands in the three designs (max 32 in ALU / Tier A). Also latent: R2_SPEC=4096 (HEAD L3074) bounds every sigspec string, so after the crash fix this 1152-bit concat of 45-char names (~28 KB) declines `concat-size` (HEAD L3873). | Flatten left-associative `"&"` chains iteratively into the concat element list (worklist, no recursion per operand) and either size sigspec buffers dynamically or land long concats on intermediate temp wires in chunks; also worth a generic recursion-depth guard so a deep expression declines instead of killing the child. | small-medium (~60 lines) |
| Non-straight-line constant-evaluation functions of VX_csa_tree / VX_csa_block (while loops, early returns) and one call with constant actuals | Module-level function scan HEAD L5693-5708: `function CALC_DEPTH k31@2`, `CALC_4TO2_LEVELS k31@2`, `GET_CNT_AT_LEV k31@2`, `GET_NEXT_SZ k25@0`, `NEXT_LEV_BALANCED k25@2`, `NEXT_LEV_RAGGED k25@1` (k31 = T_WHILE, k25 = T_IF) decline the two modules outright; only ONE is ever called from a statement: `tmp_ivl_97 <= get_cnt_at_lev(tmp_ivl_92, tmp_ivl_94)` (exec.vhd:21622, both actuals constants; census `fcall:GET_CNT_AT_LEV d0@cont-rhs`), the others are called only from each other. Tier B only (Wallace multiplier tree, 6 bodies in 2 modules); ALU / Tier A have no non-builtin non-straight body. | (a) Declare function bodies lazily — decline only when a non-inlinable function is actually called (removes 5 of 6 declines, trivial); (b) evaluate a call whose actuals fold to constants through the walker's const interpreter (r2_eval_int already unrolls while loops under substitutions) and render the result as a literal. | trivial for (a), small-medium (~80 lines) for (b) |
| Diagnostics of the decline path itself (so the next attempt is measurable) | vhdl2vlog.c: `fw` uninitialised when r2_func_inlinable returns true and the cap is hit (HEAD L5696-5704: the message `function X @?` carried stack garbage); g_r2_site breadcrumb never reset between concurrent statements (HEAD L3063 — `proc-extra-stmt@cont-rhs` in the old logs was really `@?`); `fcall`/`expr-kind`/`binop`/`unop`/`conc-kind` messages carried no name/kind; several `return false` paths carry no reason; a crash in the fork child gives only `status 139`. | Keep the census patch (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/rtlil_catalog/04-nvc-rtlil-census.patch, env NVC_ACCEL_RTLIL_CENSUS=1, null builder, per-statement stream + per-module tally, silent-path tagging, per-process crash guard) as the measuring tool for the implementation; rerun `run_rtlil.sh <workdir> <bench> <tag> NVC_ACCEL_RTLIL_CENSUS=1` and `agg.py`/`procsum.py` after each item to watch the leaf totals go to zero (ALU 13 -> 0, Tier A 76 -> 0, Tier B 1841 -> 0). Correct README/LDX-VORTEX: the walker declines on the 8-function cap, not on T_FCALL. | done (diagnostic patch in the NVC working tree, review/revert as noted in the summary) |

The census mode used to produce this is nvc commit `vhdl2rtlil: census mode` (patch 04 in `probes/gsm/`); it changes nothing in normal operation but the decline messages.

## 13. The direct VHDL→RTLIL walker admits and installs translated Vortex (2026-09-04)

`NVC_ACCEL_RTLIL=1 nvc -r --accel` now builds the translated Vortex ALU and
the Tier A execute stage **in-process**, VHDL → `RTLIL::Design` through the
walker (`nvc/src/vhdl2vlog.c`, `vhdl2rtlil_module`) and the builder facade
(`sv2ghdl/yosys/gen_statemachine.cpp`, `gsm_rtlil_*`), with no text-path
fallback, and the compiled model is hot-swapped in:

    alu_top   via rtlil builder: 183 comb cells / 2 registers   → ACTIVE (installed) → PASS 42 cycles;  NVC_ACCEL_VERIFY=1 clean
    exec_top  via rtlil builder: 1102 comb cells / 66 registers → ACTIVE (installed) → PASS 210 cycles; NVC_ACCEL_VERIFY=1 clean
    census:   ALU 9/9 modules and Tier A 51/51 modules walk with 0 declines

This is the leg ASYNC-PLAN §5 turns on: NVC now holds Vortex's RTLIL in its
own process, so an NCL mapper can be a Yosys pass over that design with NVC
simulating the result without leaving the process.

**How it got there.** §12's catalogue was worked in order (items 1–6), then
the census exposed two more (`l3d_sra`, dynamic part-select reads), and the
first *real* builds — which the null-builder census cannot see — exposed
four more: bare-name leaks of inlined formals, a user function mistaken for
a numeric_std conversion, RTLIL's equal-width rule on assignments (a
builder-facade gap: `rtlil_fit`, logged, sv2ghdl `ddcad3b`), and, caught
only by `NVC_ACCEL_VERIFY=1` on the first Tier A install, `l3d_resize_s`
treated as an unsigned pass-through (LSU LB/LH sign extension, multiplier
operands) — the case for keeping the passive verifier in the loop. Fifteen
minimal repros (`probes/gsm/repros/walker/r1`…`r15`) each decline on the
previous binary and install with Y = gold on the new one. Design rules in
the walker: arm-scoped substitutions poisoned on arm exit (read_verilog's
`subst_rvalue_map` without the `$1` merge), dynamic-index writes lowered to
case actions per reachable position (read_verilog's own lowering), and a
decline wherever the walker cannot be exact.

**Verification on the final build (nvc HEAD + patch 05, sv2ghdl `ddcad3b`,
iverilog `86eba14`).** All 15 repros MATCH; ALU and Tier A census/real/VERIFY
as above; the genuine text path (variable unset) still installs both designs
and passes; `rtlil-selftest` PASS; NVC `test/accel` 8/8 (six MATCH, one
DECLINED-SAFE, one OK); ivtest `vhdl_nvc_reg.pl` 285/294 with the baseline
failure set; NVC full `run_regr`: 1,147 ok / 112 failed / 4 skipped with the failure set identical to the pre-walker binary (`probes/gsm/evidence/walker/nvc_run_regr_w8.txt`). Committed: nvc walker commit on top of `112bc4b3a`, sv2ghdl `ddcad3b`.

*Provenance.* The workflow's ALU agent completed; the execute, review and
verify agents were lost to the account's spend limit after the execute
agent had implemented items 10–15 and rebuilt once. The final edit (r15)
was unbuilt; I rebuilt, re-ran every check above by hand, and reviewed the
diff at the level of its design comments and the r15 lowering. Tier B
(soft FPU) was only censused through the walker, with model compilation
disabled: **109 of 119 modules walk with zero declines** and the
interpreted run still passes 641 cycles. The declines sit in ten modules
and two reasons — `array-ref@cont-rhs` / `process@cont-rhs` (unpacked
signal arrays of vectors used as wire arrays in continuous assignments,
§12 item 9: `vx_ks_adder` 2,818, the three `vx_find_first` variants,
`vx_fdivsqrt_unit` 200, `vx_fpu_std` 20) and the `VX_csa_tree` constant
function `get_cnt_at_lev` (item 11) — plus one walker crash (`SIGSEGV` in
`vx_wallace_mul`, the long `&` concatenation chain). Evidence:
`probes/gsm/evidence/walker/tierB_census_w8.summary.log`.

## 14. Tier B (soft FPU) through the walker — inline (2026-09-04)

Continuation of §13, done by hand after the agents ran out of budget. The
Tier B census started at 109/119 modules clean with the declines in ten
modules; the walker now walks **119 of 119 with zero declines**, and the
whole Tier B execute stage builds through the RTLIL builder as one subtree:

    exec_top (Tier B) via rtlil builder: 14,170 comb cells / 168 registers → ACTIVE (installed)
        → PASS 641 cycles bit-exact vs the vvp oracle, 0 mismatches (106 FPU results);
        NVC_ACCEL_VERIFY=1: PASS, 0 divergences on the wrapper's 46 outputs

Every construct on the way has a minimal repro (`r16`…`r30`) that declines,
crashes or mis-simulates on the §13 binary and installs with Y = gold,
VERIFY clean, on this one. Twenty-six repros in all (plus the r28/r29 stage-exposure diagnostics); ALU and Tier A are
baseline-identical (census 0 declines, real builds ACTIVE, PASS, VERIFY
clean).

**What was added to the walker** (`nvc/src/vhdl2vlog.c`; the accel driver
`nvc/src/rt/model.c` for the gate):

1. *The `vx_wallace_mul` crash* (`r16_bigcat`) was a stack overflow: the
   700-operand partial-product `&` chain is left-nested, and one `r2_expr`
   frame per operand — each carrying tens of KB of sigspec buffers — blew
   the 8 MB stack. Concatenation chains (and elaboration's folded
   concat-aggregates) are now flattened iteratively; a rendered chain wider
   than one sigspec buffer lands in temp wires chunk by chunk
   (`r19_bigcat_vars`, 900 scalar-variable leaves). A depth guard
   (`expr-depth`) declines instead of crashing on any other pathological
   nesting.

2. *Unpacked signal arrays of vectors used as wire arrays* (§12 item 9;
   `r17_warr`; 2,818 of the ~4,000 Tier B declines: `vx_ks_adder`
   `G_g_KS`/`P_g_KS`, the `vx_find_first` variants, `vx_fdivsqrt_unit`
   `srt_stage`). A memory-shaped signal whose every index is a constant is
   kept as ONE flat wire (NVC's flattening: leftmost element highest) and a
   selection chain `s(i)(j downto k)` / `s(i)(b)` resolves to a bit range
   of it — in reads, continuous-assign targets and process targets. A
   dynamic outermost select over a constant word materialises the word
   and reuses the plain-vector lowerings (`shr` + `[0]` / `[k:0]`). The
   `(others => (others => L3D_X))` power-on fill folds like the flat one.

3. *Constant-evaluable design functions* (§12 item 11; `r18_cfn`;
   `VX_csa_tree`'s `get_cnt_at_lev`). A body the inliner rejects — a
   `while` loop, `if`/`else`, `l3d_mod_s`/`l3d_div_s` — is admitted as a
   constant function and evaluated at build time when every actual is a
   constant. Two supporting rules: `r2_eval_int` follows integer/vector
   constant declarations (generate indices) and *constant-driven signals*
   — a signal whose only writer is a `s <= <constant>` continuous assign
   is that constant (tgt-vhdl passes the function's actuals through such
   temps: `tmp_ivl_92 <= "..0010"; tmp_ivl_97 <= get_cnt_at_lev(tmp_ivl_92,
   tmp_ivl_94)`). The interpreter runs the body on the substitution table
   under the same snapshot discipline as the inliner.

   This one also needed the *accel driver*: a subtree the text emitter
   cannot express was never a candidate (`not fully translatable` → descend
   into children), so the walker never saw it. With `NVC_ACCEL_RTLIL=1` the
   driver now dry-walks such a subtree through the walker's null builder in
   a fork child and, if every module is admitted, carries it on the walker
   alone — no text fallback from the partial emission (`walker-only … not
   built — leaving in nvc` if the real build declines). The probe child
   is silent (`NVC_ACCEL_RTLIL_PROBE`), so the repro harness's report is
   not fooled by the testbench subtree's expected decline.

4. *Promoted variables read inside a tree* (`r20_fflags`; `vx_fpu_std`'s
   per-lane fflags merge `v(k) := v(k) or lane(i*5+k)` under `if
   mask(i)`, k = 0..4, in a `while` over the lanes). Two changes, both in
   the direction of read_verilog's `$N\v` renaming: a per-bit write inside
   an arm now keeps a per-bit *substitution* (seeded by landing the value
   so far) instead of poisoning the variable, so the next bit's read in the
   same arm sees the value so far; and each top-level switch re-roots every
   promoted variable in a fresh hold temp whose default — the previous
   value — is the **first action of every arm** (a synthesized default arm
   for a `case` without `others`). The first version of this rooted the new
   temp with a process-root action; that is wrong by construction — root
   actions run before all switches (`gsm_rtlil_case_assign_root`:
   "actions-first however they interleave"), so the chain read each
   previous temp before its own switch assigned it (`r15` mismatched,
   `r4` failed to build). A second bug hid behind it: a value seeded in an
   `if`'s implicit default arm survived to depth 0, because only explicit
   arms were poisoned on exit. Both are repro-covered now.

5. *`VX_dp_ram`* (`r21_dpram`), two bugs. The memory-usage census counted
   the comb read process's sensitivity-list reference (`process (raddr,
   ram)` is lowered to a trailing `wait on raddr, ram`) as an access, so
   the NBA-shadow idiom failed its census (`mem-usage`). Once admitted, the
   write port was **silently dropped**: a clocked process with no register
   target returned success before emitting its sync, and the pending memory
   write with it — a pre-existing silent-wrong-answer path, now closed
   (a process with memory writes proceeds to the sync).

6. *Comb processes that write one element of a wire array* (`r22_ffirst`;
   found by the first real Tier B build: the FPU commit data was wrong from
   cycle 13 on — a normalisation count). `VX_find_first` is a reduction
   tree over `d_n : array (62 downto 0) of logic3d_vector(4 downto 0)`, one
   comb process per node writing ONE element from its two children. The
   flat-wire lowering gave every node a hold temp for the whole array,
   rooted at the array itself, and committed the whole wire — 31 processes
   contending for one wire through self-rooted temps. A comb process that
   writes only a constant sub-range now drives exactly that range (hold
   temp and `always` commit over `[shi:slo]`). The census cannot see this
   class of error; the repro set and VERIFY can.

7. *Two guards the text path had and the walker did not*, exposed by the
   walker-only admission in (3) through NVC's `test/accel` suite run with
   `NVC_ACCEL_RTLIL=1` (`l3did`, `l3dwrap`, `l3dmv` gave silent wrong
   answers): a concatenation *element* now takes its declared width — an
   identity conversion (`to_l3d(x, 8)`, `unsigned_to_l3d_bit(u)`) renders
   its operand verbatim, so inside `{}` it is landed at the width its
   declaration says; and a std_logic *character* metavalue (`'U'` `'X'`
   `'W'` `'-'` `'Z'`) has no value-plane form and declines (the named
   `L3D_X` keeps its 0; `folded_int` would otherwise have supplied the enum
   *position*). `test/accel` is 8/8 in both modes now, and `l3did` installs
   through the walker where the text path has to decline. One more of my
   own errors is worth recording: `type_is_logic3d` is true of a *vector's*
   element type too, so a declared-width test that took it for "scalar"
   landed every slice in a concat as one bit and 17 repros mismatched at
   once — the repro set is what makes this kind of inline work safe.

8. *A scalar logic3d literal's encoding* (`r24_fcvt`, `r30_G`; found by
   the second real Tier B build, which was bit-exact except the float→int
   results — 2.5 → 10 instead of 2). Bisected stage by stage through the
   fcvt unit (`r28`/`r29` expose each pipeline register and stage-0
   signal through a debug port) to one statement, then construct by
   construct (`r30_A`…`G`) to `cast12(resize((L3D_0 & fclass(4)), 12))`.
   logic3d is `natural 0..7` with bit 0 the value plane; elaboration folds
   the package constant `L3D_0` into the integer literal 2, and
   `r2_const`'s integer-literal path rendered it as `1'd2` — so the
   exponent gained 2 wherever that concat fed it. A scalar logic3d literal
   now renders as its value-plane bit. (Also found on the way and fixed:
   an inlined identity cast bound to a `resize` actual inherits the
   operand's width, which is what the concat-element rule in 7 is for.)

**Verification on the final build.** Twenty-six repros MATCH + INSTALLED
via the RTLIL builder, `r17`–`r24` VERIFY clean (0 divergences); ALU census
0/9 declines, real 183 cells ACTIVE PASS, VERIFY clean; Tier A census 0/51,
real 1102 cells / 66 registers ACTIVE PASS, VERIFY clean; Tier B census
119/119 clean, real 14,170 cells / 168 registers ACTIVE PASS 641 cycles,
VERIFY clean (0 divergences);
`rtlil-selftest` PASS (sv2ghdl untouched); NVC `test/accel` 8/8 text and
8/8 walker; NVC full `run_regr` 1,147 ok / 112 failed / 4 skipped, failure
set identical to the §13 baseline by name. iverilog was
not touched in this leg, so ivtest was not re-run. Committed: nvc `428cd6948` (on top of `340ce5cba`); mylex: this commit.
Evidence: `probes/gsm/evidence/walker/*tb1[12]*`, patch
`probes/gsm/07-nvc-rtlil-walker-tierB.patch`.

**Still open.** (a) VERIFY reports only the first divergence per net and
only the candidate's ports, so localising the two Tier B failures took
hand-built stage exposure (`r28`/`r29`); a probe-port facility in the
accel driver (`NVC_ACCEL_PIN_COMPLETE` exists for census records, not for
arbitrary internal nets) would make that a one-line knob. (b) The driver's
oversized-subtree descend (`NVC_ACCEL_DESCEND_BIG`) keys on the text
emission's size, which is a stub for a walker-only subtree — it cannot
split one. (c) `r2_eval_int` still returns the logic3d *encoding* for a
scalar literal (`L3D_0` = 2); only `r2_const` renders the value plane. It
is consistent with the comparisons it feeds today (`l3d_eq1` on encodings)
but is a trap for the next person. (d) The per-slice comb targets cover
constant sub-ranges; a comb process writing a *dynamic* element of a wire
array still takes the whole array (conservative, declines nothing). (e)
The walker builds Tier B in ~10 min of yosys time on this laptop VM
(text-path synth of the same design is comparable); nothing was done for
speed.
