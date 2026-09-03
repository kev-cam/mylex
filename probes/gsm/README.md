# Vortex through Yosys and sv2ghdl's gen_statemachine (2026-09-03)

Two more legs of the chain exercised on the sv2v-flattened Vortex designs
(`probes/alutest/alu.v` recipe, `probes/exectest` Tier A `exec.v`):

1. **Baseline Yosys synthesis** (`synth_alu.ys`, `synth_exec.ys`, results in
   `SYNTH-RESULTS.md`): ALU 4,582 two-input gates / 188 flops; execute stage
   26,181 gates / 3,696 flops. RTLIL and gate-level Verilog are what the P3
   NCL mapper would consume.
2. **gen_statemachine** (sv2ghdl/yosys, the single-cycle C model that
   `gpubuild` ships to GPU farms): ALU 189 cells / 2 registers in 0.5 s,
   execute stage 1,092 cells / 66 registers in 3.1 s.

`harness_alu.c` replays `probes/alutest/vectors.txt` through the ALU model
(`sm_comb` then `sm_clock` per recorded cycle, X = don't-care) as a THIRD
oracle next to vvp and NVC:

    gen_statemachine alu.v alu_top alu.c
    gcc -O1 -w -DSM_NO_MAIN -o harness_alu harness_alu.c && ./harness_alu vectors.txt
    -> PASS: 42 cycles, 27 results, 7 branches, 0 mismatches

## Bug found and fixed: partial-slice store in emit_wide_cell

Before the fix the replay failed on AND/OR/SLL with lane 1 = 0: a per-lane
`always @* case` writing `r[i]` becomes a `$pmux` whose B port is a >64-bit
concatenation, so the cell takes the WIDE emitter, which stored a single-chunk
Y with `wire = wslice64(_wy,0,yw,ng)` -- dropping the chunk's offset and
clobbering the other lane. The scalar emitter already routed partial slices
through its scatter; the wide emitter only did so for multi-chunk Y.
`01-gen_statemachine-partial-slice-store.patch` extends `y_scatter` to a
single partial chunk (the scatter branch performs the correct RMW at the
chunk offset). Minimal repro `repro/slicecase.v` + `repro/h_slicecase.c`:
`slicecase` (two case writers) failed, `sliceplain` (no case) and
`slicesingle` (one writer) passed; all pass after the patch.

Yosys/gsm/nvc all agree with vvp on the ALU vectors after the fix. The
execute-stage model was regenerated but not yet replayed (its vector
format is the Tier A `%b` layout; a generated harness is the next step).

## Toolchain notes (no sudo)

Yosys must be the pre-"log: convert all to sinks" API for gen_statemachine
to build: pinned at bd5c524d (master 2026-08-13; the sinks refactor cbbd8c0d
landed 2026-08-14). Built with CMake 4.4.3 (static release binary) into
~/tools/yosys with readline/editline/Tcl/Slang disabled, libyosys shared;
`YOSYS_DIR=~/tools/src/yosys YOSYS_BUILD=~/tools/src/yosys-build make
yosys/gen_statemachine yosys/libgsm.so` in sv2ghdl. The sv2ghdl
`docker/build_stack.sh` recipe (`make config-gcc`) is stale against
current Yosys master, which is CMake-only.

## Execute stage through the C model (generated harness)

`gen_gsm_harness.py ports_tierA.txt exec.c harness_exec.c` generates a replay
harness for any wrapper from its port manifest (the exectest vector layout:
inputs as nibble-padded hex, outputs as nibble-padded `%b`, inputs then
outputs in manifest order, `reset` recorded as an input). Against the
committed Tier A vectors (`probes/exectest/vectors.txt`, 210 cycles):

    FAIL: 210 cycles replayed through the gen_statemachine model, 10 mismatches

The model matches the vvp/NVC oracle on 200 of 210 cycles including every
LSU, SFU, MULDIV and warp-control event. The residual, open:

- cycle 0 (reset asserted, before the first rising edge): `lsu rsp_ready`,
  `dispatch_if_1/2_ready`, `branch trap_cause` differ -- time-0 initialisation
  semantics (`sm_reset` state vs vvp's declaration-initialised registers).
- cycles 12-13 (the two taken-branch commits): `branch_ctl_if_0_dest` reads 0
  and `commit_if_0_data` lane 1 differs. The dest output is driven from the
  `alu_int` `branch_reg` pipe register (`exec.c:4322`), so the value fed into
  that register (`cbr_dest_r` out of the `rsp_buf` elastic buffer) is wrong
  in the model; the ALU-only model (`alu.c`) passes the same branch shapes,
  so the defect is in the flattened `VX_alu_unit`/`pe_switch`/elastic-buffer
  path as gen_statemachine emits it. Needs the same minimal-repro treatment
  as the slice-store bug.
