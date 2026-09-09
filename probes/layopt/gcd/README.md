# gcd on sky130hd through OpenROAD — the first real place-and-route DEF for layopt

Built 2026-09-07 on this box: OpenROAD `63fe72c` compiled from source
(`~/src/OpenROAD`, deps in `~/.local`, GUI off), Yosys `bd5c524d`
(`~/tools/yosys`), platform files from OpenROAD-flow-scripts `master`
(`~/tools/orfs-sky130hd`: tech + merged cell LEF, tt liberty, merged cell GDS,
pdn/tapcell/tracks/setRC).

    ~/tools/yosys/bin/yosys -q synth.ys            # gcd.v -> gcd_synth.v (sky130_fd_sc_hd cells)
    openroad -exit flow.tcl                        # floorplan, PDN, place, CTS, route, fill -> gcd.def

`flow-summary.log` holds the OpenROAD report lines (0 DRC violations, 1650
vias, 2743 um^2 at 50 % utilization; timing not closed -- untuned synthesis,
irrelevant to the geometry). `gcd.def` is the routed result consumed by
`../l2_real_def.py` and the L4 probe on real whitespace.

## The split flow for the placer hand-off (`flow_place.tcl`, `flow_route.tcl`)

`flow_place.tcl` is `flow.tcl` up to the last `detailed_placement` before
routing (placement, `optimize_mirroring`, CTS, `repair_timing`); it writes
`gcd_placed.def` and `gcd_placed.odb`, the placement the router would see.
`flow_route.tcl` reads that database, sources the layopt hints when the env
var `HINTS` names them (`layopt/placer.py` writes them; `TAG` names the
outputs), runs `check_placement`, routes, fills and reports. Run from
`~/src/gcd-flow/hints` (paths inside are absolute):

    openroad -exit flow_place.tcl
    TAG=base  openroad -exit flow_route.tcl
    TAG=hints HINTS=$PWD/hints.tcl openroad -exit flow_route.tcl

`../l4_placer_handoff.py` does the planning, both routing runs and the
dissolve check; `../evidence/gcd_hints.tcl` is the hint script it produced.
