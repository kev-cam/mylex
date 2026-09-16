# th_struct_poc — async fork extraction on a structural TH netlist (de-risk)

Proves the async half of the nulex->layopt loop end to end, on a hand-written
structural example, so the extractor + hand-off are known good before the RTL->
structural emitter is built.

    ./run.sh

- `th_cells.v` — the threshold gates (th22/th12/th13/th23/th33) as `(* blackbox *)`
  modules. Kept OPAQUE so the DIMS structure survives `yosys flatten` instead of
  inlining to `$and`/`$or` (the trap: the nvc `ncl` TH primitives are behavioral
  *functions*, so any synthesis dissolves them — a real instantiable TH-cell lib
  is the missing piece).
- `ncl_struct_example.v` — one DIMS AND2 (4×TH22 minterms + rail collectors, .L =
  value-1) and a `fork_top` where a dual-rail input `a` fans out to three gates.
- Flatten keeps 12×th22 + 3×th13 as cells; `constraints.py` then enumerates the
  **dual-rail forks** (`a_L`->6, `a_H`->6, the coupled pair QDI must balance
  together) via its **third pin-direction source**: a cell whose type is another
  module in the JSON takes its input/output pins from that submodule's ports —
  no LEF, no hardcoded TH map. Same path set layopt's `objective.fork_balance`
  consumes.

Next (the real build): an instantiable, hysteretic TH-cell library + a structural
`map_ncl` that instantiates TH cells (not the behavioral `th22()` function calls),
so this runs on real RTL. Sequential designs also need a structural QDI register
(completion-tree/handshake forks don't exist until then).
