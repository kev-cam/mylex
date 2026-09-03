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
