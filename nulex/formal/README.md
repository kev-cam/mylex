# nulex/formal — the nulex → layopt hand-off (isochronic-fork constraints)

`constraints.py` is the nulex side of the async **layout hand-off** (ASYNC-PLAN §8,
LAYOUT-OPT.md §6 / L3). It closes the interface `probes/layopt/l3_fork_balance.py`
flagged as open: *"the path set is given by hand (nulex's constraint extraction
will emit it)."*

## What it produces

Reads a yosys gate netlist (`write_json`) and emits, for every multi-fanout net,
an **isochronic-fork path set** — the QDI/NCL correctness object: a net that forks
to several gate inputs must reach them with matched delay or a transition orphans
and the handshake breaks. Output (`<top>_forks.json`) per fork:

```
{ "net": <id>, "name": <net name>, "driver": {inst,pin,kind}, "receivers": [{inst,pin}...],
  "fanout": N, "kind": "isochronic"|"handshake"|"clock_reset_dist",
  "objective": "match_delay"|"skew_tolerant", "weight": N }
```

## QDI-aware fork kinds

A dual-rail NCL netlist has two structurally different fork classes, and layout
must treat them differently:

- **`isochronic`** — a fork of a dual-rail DATA rail (`<sig>_L`/`<sig>_H`). An
  orphaned (unmatched) branch breaks the handshake, so these need **matched delay**
  (`objective: match_delay`). This is the orphan-critical set.
- **`handshake`** — a fork of the single-rail request/completion control network
  (`ki*`/`ko*`/`cd*`/`acc*`, from `map_ncl_struct --reg qdi`). The completion
  detection + C-elements absorb skew by design, so these are **skew-tolerant**
  (`objective: skew_tolerant`) — a lower-bound / drive-balance objective, like clock
  distribution, not an orphan constraint.
- **`clock_reset_dist`** — a synchronous clock/reset fork (single-rail, by pin
  heuristic); also `skew_tolerant`.

Classification: dual-rail (`_L`/`_H`) is tested first, so a data signal the user
named e.g. `ack` (rails `ack_L`/`ack_H`) is still DATA; only the reserved single-rail
`ki/ko/cd/acc` control nets are tagged `handshake`. A purely combinational NCL
netlist has zero handshake forks; a pipeline has one request fork per stage.

which maps 1:1 onto layopt's path set `- <net> ( <driver_inst> <pin> ) ( <recv_inst>
<pin> ) ...` — i.e. `objective.fork_balance(ex, net, driver_shape, [receiver_shapes])`.
Clock/reset distribution forks are tagged separately (that's skew, not orphan);
isochronic forks are ranked widest-first (the wider the fork, the harder to balance
in geometry). `usage: constraints.py <netlist.json> <top> [out.json]`.

## How layopt consumes it

After P&R, layopt maps each fork's `(inst, pin)` endpoints to physical shapes and
runs `objective.fork_balance` / the `l3_fork_balance` optimizer to minimise the
Elmore-delay spread across the branches (resizing branch wires / devices) under the
topology + DRC guard — automatically, over all enumerated forks, instead of one
hand-written net. Weights (fanout, and later per-branch criticality) prioritise the
budget. Completion-tree drive balance (LAYOUT-OPT.md:1543) is the same shape with a
lower-bound objective.

## Cell pin directions: generic gates or `--lef`

Cell pin directions come from one of three sources, tried in order:
1. the built-in gate map (`CELLS`) — a generic yosys netlist (`$_AND_`, …);
2. `--lef <lef>...` — a **technology-mapped** netlist (sky130_fd_sc_hd cells, what
   actually gets placed): directions from the LEF `DIRECTION`;
3. the JSON's own **submodule ports** — a cell whose type is another module in the
   netlist (kept opaque, e.g. blackbox threshold cells in a structural NCL netlist)
   takes its input/output pins from that submodule's port directions. No LEF, no
   hardcoded map — this is what lets the same extractor run on the async TH netlist
   (see `th_struct_poc/`).

Clock/reset pins are split off by name heuristic (`CLK*`, `RESET*`, `SET_B`, …).

    constraints.py <netlist.json> <top> [out.json] [--lef LEF ...]

## Demonstrated

- **`alu_top` (`VX_alu_int`) technology-mapped to sky130 and placed+routed** — the
  full loop (`../mapper/alu/pnr/`): `constraints.py --lef` finds **1807 isochronic
  forks, 8338 branch endpoints** (fanout to 152-way) + 1 clock-distribution fork;
  the routed design's 1699 physical signal forks were measured on real geometry by
  `alu_fork_balance.py` (worst as-routed branch-delay spread ~63 ps). This is the
  first end-to-end run: enumerate → route → measure/optimise on real sky130 RC.
- `alu_top` generic gate netlist (pre-map): 1686 isochronic forks → `alu_forks.json`.
- `exec_top` Tier A: **21,557 forks**, fanout up to 732-way → `exec_forks.json`.

## Async note

Run here on the synchronous gate netlists because those are what layopt physically
places today (the NCL threshold cells still lack a LEF/GDS view — ASYNC-PLAN §10).
The extractor is netlist-agnostic: the *same* tool run on the flattened dual-rail
NCL netlist yields the QDI-critical isochronic forks (each dual-rail signal's fork,
plus the completion-tree forks). Producing that flattened dual-rail gate netlist
(the `map_ncl` output lowered past the behavioral `lib/ncl` functions to structural
threshold cells) is the next nulex step; the constraint format and layopt's
consumption path are unchanged.
