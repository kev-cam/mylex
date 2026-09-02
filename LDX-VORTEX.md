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
4. Minor: `bin/fix-ivl-vhdl`'s concat-cast rule predates logic3d typing
   and *introduces* type errors on `-psv2vhdl` output — skip it there.

Toolchain state on this machine: iverilog fork built at
`/usr/local/src/iverilog/_install`; NVC fork complete in
`/usr/local/src/nvc/build` including all `lib/sv2vhdl` packages,
`libsv_math.so` and `libresolver.so` (built with explicit
`PYTHON3_CFLAGS=$(python3-config --includes)` — the Makefile's deferred
expansion misfires).
