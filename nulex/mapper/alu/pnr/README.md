# VX_alu_int through P&R → layopt isochronic-fork balancing

The full nulex→layout loop on a **real placed-and-routed** design: take
`VX_alu_int` (via the `alu_top` flat-port wrapper) through OpenROAD P&R on
sky130hd, enumerate its isochronic forks with `nulex/formal/constraints.py`, and
measure/optimize each fork's branch-delay spread on the real routed geometry with
layopt. This is the `probes/layopt/l3_fork_balance.py` path (which used a
hand-built DEF) applied to a real OpenROAD DEF.

## Pipeline

    # 1. synthesize alu_top -> sky130_fd_sc_hd cells   (needs yosys w/ abc in ~/.local)
    yosys -q synth_sky130.ys                 # -> alu_top.sky130.{v,json}   (3867 cells, 37 FF)

    # 2. place & route on sky130hd            (needs openroad + ~/tools/orfs-sky130hd)
    openroad -exit flow_alu.tcl              # floorplan/PDN/place/CTS/route/fill -> alu_top.def (0 DRC)

    # 3a. LOGICAL fork census (which forks) — constraints.py, now LEF-aware
    python3 ../../../formal/constraints.py alu_top.sky130.json alu_top alu_forks_logical.json \
        --lef /home/claude/tools/orfs-sky130hd/sky130_fd_sc_hd_merged.lef

    # 3b. PHYSICAL fork set (same forks, with placed pin coordinates) from the routed DB
    openroad -exit dump_forks.tcl            # -> alu_forks_phys.json

    # 4. measure (+optionally balance) each fork's spread on the real routed RC
    python3 alu_fork_balance.py --top 15 [--balance]

    # 5. PLACEMENT hand-off: close the wide (placement-limited) forks by moving
    #    each one's driver buffer to its receivers' centroid, then re-place+route
    python3 gen_fork_hints.py --span-um 100 --top 30   # -> fork_targets.tcl
    openroad -exit flow_hinted.tcl                     # setLocation+legalize+CTS+route -> alu_top_hinted.def
    ODB=$PWD/alu_top_hinted.odb OUT=$PWD/alu_forks_phys_hinted.json openroad -exit dump_forks.tcl
    python3 compare_forks.py                            # before/after spread per moved fork

## Files (this dir)

| file | role |
|---|---|
| `synth_sky130.ys` | yosys: alu_top → sky130 cells (mirrors `gcd/synth.ys`) |
| `constraint.sdc` | relaxed 10 ns clock (geometry run, not timing closure) |
| `flow_alu.tcl` | OpenROAD floorplan→route (from `probes/layopt/gcd/flow.tcl`; 35% util, `unithd`) |
| `dump_forks.tcl` | routed `.odb` → physical fork set (driver+receiver pins, placed xy), signal nets only; env `ODB`/`OUT` |
| `alu_fork_balance.py` | `def2flat`→`extract`→`objective.fork_balance` per fork; `--balance` runs the width-resize optimizer; `--def`/`--forks` |
| `gen_fork_hints.py` | wide forks → `fork_targets.tcl` (driver → receiver-centroid target) |
| `flow_hinted.tcl` | re-place+route from `alu_placed.odb` with the driver moves (`setLocation`+legalize+CTS+route) → `alu_top_hinted.def` |
| `compare_forks.py` | per-fork branch-delay spread, baseline vs hinted routed DEF |
| `*.def / *.odb / *.v / *.json` | P&R outputs (gitignored — regenerable) |

## Why constraints.py gained `--lef`

`constraints.py` originally knew only the generic yosys gate map (`$_AND_` …),
so it saw zero cells in a technology-mapped netlist. It now takes `--lef` and
derives each cell's input/output pins from the LEF `DIRECTION`, so it enumerates
forks on any placed design. On `alu_top.sky130.json` it finds **1807 isochronic
forks** (fanout to 152-way) + 1 clock-distribution fork. The physical dump finds
**1699** signal forks (max 50-way): the difference is `repair_design`/CTS
buffer-splitting the widest logical nets to honor max-fanout — real physical
behavior, not a mismatch.

## Results (2026-09-15, sky130hd, 35% util, 0 DRC)

- **P&R:** `alu_top` 3867 sky130 cells → 244×244 µm die, detailed-routed to **0 DRC
  violations**, 35537 vias, 29221 µm² design area. (Setup timing not closed — untuned
  synthesis, irrelevant to geometry.)
- **Fork census:** `constraints.py --lef` = 1807 logical isochronic forks;
  `dump_forks.tcl` = 1699 physical signal forks (max 50-way after `repair_design`
  buffer-splitting).
- **Measured on real routed RC (912 forks resolved):** branch-delay spread
  median **0.03 ps**, mean 1.28 ps, **max 63.1 ps**. The router balances the vast
  majority; the tail is what matters.
- **Key finding — worst imbalance is placement-limited.** The 44 forks with
  spread > 5 ps have mean receiver span **170 µm** (die is 244 µm): their imbalance
  comes from *scattered receivers* (unequal branch lengths), not resizable wire.
  Windowed `layopt` width-resize on the *local* forks converges to scale 1.0 (no
  gain) — their branches are short and capacitance-dominated, so R-resize can't
  move the spread. The effective lever for the wide forks is **placement**
  (layopt's placer hand-off, `probes/layopt/l4_placer_handoff.py`), not post-route
  wire width. This is exactly the signal nulex→layopt exists to surface.

### Placement hand-off closes the wide forks (the fix)

`l4_placer_handoff.py` proper is a flip-and-abut *compaction* planner (no fork
awareness), but its `setLocation`+FIRM hint→re-place→re-route→re-measure loop is
the right vehicle. Each wide fork's driver is a `repair_design` **buffer** that
serves only that net, so `gen_fork_hints.py` moves it to the receivers' centroid
and `flow_hinted.tcl` re-legalizes + re-routes (`--span-um 155 --top 80`: 45 of 64
relocated, **0 DRC**, 29236 µm² — no area penalty). Result on the moved forks
(`compare_forks.py`):

    35 forks matched, summed branch-delay spread 826.7 -> 349.0 ps  (-57.8%)
    _3074_ 63.10 -> 0.58 ps (-99%)   _3070_ -92%   net11 61.8 -> 12.6 (-80%)
    net59 -80%   net50/46/60/62 ~ -72%

Moving one dedicated driver buffer toward its sinks' centroid closes the tail
imbalance: the single worst fork (`_3074_`) drops **63 → 0.58 ps (−99%)** and the
summed spread across the 35 wide forks more than halves, at zero DRC/area cost.
A few forks regress (one driver can't centre every fork, and re-routing perturbs
neighbours — e.g. net20 +45%), but the aggregate is decisive. Whole-design over
all ~920 measured forks: **max spread 63.1 → 34.6 ps (−45%), mean 1.28 → 0.79 ps
(−38%)**, median unchanged (most forks were already balanced). (An earlier
narrower run, `--span-um 100 --top 30`, gave −49.9% but left `_3074_` untouched;
widening to catch the 155–202 µm band closed it.) This is the placement lever the
measurement predicted, and the full nulex→layout loop closed: enumerate forks →
route → measure → **fix by placement** → re-measure.

## Platform

`~/tools/orfs-sky130hd` (reconstructed by `../../../setup`, see that README):
sky130hd tech+merged LEF, tt liberty, merged GDS, and the ORFS
`make_tracks/tapcell/pdn/setRC` tcls. Same platform layopt's existing
`probes/layopt/gcd` and `l2_real_def` probes use.
