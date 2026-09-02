# tgt-vhdl / iverilog fixes for the Vortex VX_elastic_buffer probe

Patches against the kev-cam iverilog fork working tree (`/usr/local/src/iverilog`,
uncommitted). With all three applied, the probe recipe in LDX-VORTEX.md section 6
(translate the 9-file `VX_elastic_buffer` closure with
`iverilog -g2012 -tvhdl -psv2vhdl=1`, analyse with `probes/ebtest/tb_eb.vhd`
under `nvc --std=2040`, elaborate, run) reports

    PASS: 5 tokens through VX_elastic_buffer with backpressure, order and data intact

with **zero hand patches** to the generated VHDL. `vortex-probe/eb.vhd` is that
translation; `vortex-probe/tb_eb.vhd` the testbench.

## Patches

| file | fixes | touches |
|---|---|---|
| `01-tgt-vhdl-reserved-words.patch` | BUG 1 - `pipe` (and every VHDL-2000/2008/2019 + NVC keyword) emitted as a bare identifier | `tgt-vhdl/scope.cc` `is_vhdl_reserved_word()` table |
| `02-ivl-packed-prefix-index.patch` | BUG 2 - `(i-1)*2+1` flat index for a variable prefix index into a packed dim with msb == lsb | `netmisc.cc` `make_prefix_var_offset()`, `collapse_array_exprs()` (iverilog core, not tgt-vhdl) |
| `03-tgt-vhdl-merge-edge-processes.patch` | BUG 3 - several always_ff blocks on one reg become several whole-signal VHDL drivers (first-source-wins under nvc STD_MX) | `tgt-vhdl/process.cc`, `state.hh`, `vhdl.cc`, `vhdl_syntax.hh` |
| `all-fixes-combined.patch` | all of the above in one file | |

Apply from the iverilog tree root, then rebuild the translator:

    cd /usr/local/src/iverilog
    git apply /usr/local/src/mylex/probes/tgt-vhdl-fixes/all-fixes-combined.patch   # or 01, 02, 03 in any order
    make -j$(nproc) && make install

`git apply --check` should be clean against the fork HEAD the working tree is
based on; the three patches touch disjoint files so they apply independently.
Patch 02 changes the core elaborator, so `ivl` is rebuilt as well as `vhdl.tgt`.

### 01 - reserved words (tgt-vhdl/scope.cc)

The reserved-word table used by `make_safe_name()` / `valid_entity_name()` was
the VHDL-93 list. NVC's fork tokenises `pipe` unconditionally (src/lexer.l:458,
plain `TOKEN()`, no `--std` gate) and upstream NVC does the same for
`reverse_range`; VHDL-2000/2008/2019 add `protected`, `context`, `force`,
`release`, `parameter`, `default`, `cover`, `view`, `private` and the PSL words.
The patch appends 23 entries, so `reg ... pipe` becomes `pipe_sig` at the
declaration and every reference (the rename is routed through
`get_renamed_signal`). Interface note: an SV *port* named after any listed word
is renamed too (`view` -> `view_sig`), so hand-written VHDL testbenches must use
the suffixed name.

### 02 - packed prefix index (netmisc.cc)

`normalize_variable_base(expr, msb, lsb, wid, is_up)` describes an indexed part
select `[base +: wid]`. The fork's `make_prefix_var_offset()` passed the element
*stride* as `wid` and `msb > lsb` as `is_up`; for a dim with `msb == lsb`
(`reg [DEPTH-1:0][DATAW-1:0]` with DEPTH=1) that takes the `-:` branch and
subtracts `stride-1`. Both call sites now normalise the prefix index as a single
element position (`wid = 1, is_up = true`), which is `idx-lsb` / `lsb-idx`
exactly like `NetNet::sb_to_idx`. Expression trees for `msb != lsb` are
unchanged. vvp was equally wrong before (data_out = xx), so this is a core fix,
verified under both vvp and nvc.

### 03 - one VHDL driver per Verilog variable (tgt-vhdl/process.cc)

A Verilog variable has one driver however many always blocks assign it; the
translator made one VHDL process per block, and `nba_defer_commits()` commits
a whole-signal shadow whenever the block's write set is not one static slice
(dynamic index, mixed slices). nvc `--std=2040` accepts several sources on an
unresolved signal but its driving value is the *first* source's
(rt/model.c calculate_driving_value, r == NULL), so the other blocks' updates
vanished silently (VX_pipe_register g_partial_reset).

The patch adds `merge_edge_processes_in_all_entities()` (called from vhdl.cc
after all processes are drawn, before comb fusion):

* always blocks in one architecture that are edge-triggered with a sensitivity
  list, whose top-level statements are all the edge guard, that have the same
  sensitivity **set**, and that assign (`<=`) a common architecture signal
  (transitively) are composed into one process in source order; the blocking
  and NBA shadow passes then run once on the union, giving one seed, one
  `wait for 0 ns`, one commit, one driver;
* a member is **not** merged when it assigns with `=` a signal another member
  assigns with `<=` (`blocking_vs_nba`, review issue 1) or when its scope holds
  something other than plain variables; after dropping members the remainder is
  re-split by shared signals (`split_by_shared_sigs`);
* an always_ff drawn in the `wait until <edge>` form because it reads a
  blocking temporary is first rewritten to the guarded, sensitised form
  (`promote_wait_until_edge_form`, review issue 2) when its only other waits are
  the `wait for 0 ns` that the blocking-shadow pass deletes anyway - so it gets
  NBA deferral and takes part in merging;
* every non-initial process that still assigns architecture signals (real
  waits, non-edge always) enters a census (`extra_writer_t`); any signal with
  >= 2 surviving writers where one drives the whole signal (or a dynamically
  indexed element) gets a `sv2vhdl: warning:` naming the signal and the blocks;
* the edge process's `wait for 0 ns` is skipped on the initialisation run
  (`nba_init_run` flag) so the process is parked on its clock/reset within
  delta 0 and sees a time-0 `X -> 1` posedge from an initial block's deposit,
  as the Verilog block does;
* kill switch: `SV2VHDL_NO_MERGE=1` restores one process per block.

Process-local variables of merged members are renamed (`i` -> `i_2`) when they
would rebind; the legacy `-t vhdl` output is unaffected (every new pass is gated
on `-psv2vhdl=1`).

## Repros (`repros/`)

Environment for all commands:

    export PATH=/usr/local/src/iverilog/_install/bin:/usr/local/src/nvc/build/bin:$PATH
    export NVC_LIBPATH=/usr/local/src/nvc/build/lib LD_LIBRARY_PATH=/usr/local/src/iverilog/_install/lib

* `bug1-reserved-words/pipe_repro.sv` - `iverilog -g2012 -tvhdl -psv2vhdl=1 -o pipe_repro.vhd -s pipe_repro pipe_repro.sv && nvc --std=2040 -a pipe_repro.vhd && nvc --std=2040 -e pipe_repro`. Before: `unexpected pipe while parsing signal declaration`. After: analyses and elaborates, `pipe_sig` at all 7 sites. `words_repro.sv` covers module/port/reg names for the whole new list (top `pipe` -> entity `pipe_module`); `control.sv` checks that `pipeline`, `my_pipe`, `piped` etc. are left alone.
* `bug2-packed-index/repro.sv` + `tb_repro.vhd` (nvc) and `tb.sv` (vvp) - before: `Fatal: index -1 outside of INTEGER range 1 downto 0` / vvp `data_out=xx`; after: `PASS` / `data_out=01`. `cases.sv` (7-case matrix incl. 3-D middle `[0:0]`, variable final bit, read side), `structcase.sv` (packed struct array, the upstream `collapse_array_exprs` sibling), `nzlsb.sv` (non-zero lsb, both directions), `partsel.sv` (30 constant/variable part-select non-regression cases) are self-checking and print `PASSED` under vvp and under tgt-vhdl+nvc.
* `bug3-multi-driver/nba_slice.sv` + `tb_nba_slice.vhd` - two always_ff blocks writing disjoint dynamic slices of one reg. Before (or with `SV2VHDL_NO_MERGE=1`): 9 `MISMATCH` lines, bit 0 stuck at X. After: `PASS: disjoint-slice NBA writers kept every update`. `merge_cases.sv` + `tb_merge_cases.vhd` check distinct persistent block-locals, same-bit race order, opposite edges on one clock, single dynamic writer; `shapes.sv` exercises the async-reset template, colliding locals and the different-clock warning.
* `review/t1..t10*.sv` + `run.sh` - the reviewer's cases: `t3_mixed.sv` (blocking-in-one/NBA-in-other, must not merge, now warned twice), `t8_gap.sv` (two wait-until-form blocks on dynamic indices of one reg, now promoted + merged, q=0101/1111 as vvp), `t10_promote.sv` (six promotion shapes incl. async reset, `#1` delay, non-top event control, negedge, held temp, loop). `run.sh <abs path>.sv` runs vvp and tgt-vhdl+nvc side by side.

## Verification summary (2026-09-02, installed build vhdl.tgt 16:05)

* Vortex probe: PASS, zero hand patches, one merge (VX_pipe_register.sv:51 + :63).
* All repros above: pass under vvp and nvc.
* ivtest `vhdl_nvc_reg.pl` (legacy `-t vhdl`, 294 tests): 285 pass, the same 9 pre-existing failures as the baseline.
* ivtest `vvp_reg.pl` (core, 3020 tests, with patch 02): 3006 pass, 9 failures all pre-existing implicit int->enum `CE (no error reported)` cases from fork commit 8c6158c.
* 197 ivltests with edge-triggered always blocks translated in sv2vhdl mode with and without the merge pass (`evidence/sweep.log`): 4 merges, 0 exit-code differences, 3 new (correct) multi-writer warnings. All 149 outputs that differ from the pre-review translation were simulated old vs new under nvc (`evidence/simcmp.log`): 131 identical; 15 differ only in the source line quoted inside a pre-existing nvc error; edge.v is the same pre-existing infinite loop; dffsynth11 (`xxx` -> `010`) and specify4 (`q=x` -> `q=0`) changed to the vvp values thanks to the time-0 fix.
* vvp subset before/after patch 02 (`evidence/vvp_subset.*.txt`): the 9 enum `CE` failures are identical with netmisc.cc reverted; `cases.sv` goes FAILED(6) -> PASSED.

## Still open

* Blocking-in-X / NBA-in-Y on one signal is refused (warned), not fixed: the
  proper fix is to rename only reads that follow the first blocking write in
  program order inside `shadow_blocking_targets()`.
* Blocks sharing a signal with different sensitivity sets stay two drivers
  (warned).
* `always begin #5 clk = 1; #5 clk = 0; end`: the blocking-shadow commit is
  placed once at the end of the loop body, so `clk` never goes high in VHDL
  (ivltests/case5.v). Pre-existing, unrelated to these patches.
* Function, task and named-block names bypass the reserved-word table.
