#!/bin/bash
# Proof of concept: a structural threshold-gate (TH) netlist -> yosys JSON (TH
# cells kept OPAQUE) -> constraints.py enumerates the dual-rail async forks,
# using no LEF and no hardcoded cell map (pin dirs come from the TH submodules'
# own ports). This de-risks the async half of the nulex->layopt loop; the still-
# missing piece is emitting such a netlist FROM RTL (an instantiable TH-cell lib
# + a structural map_ncl), see ../README.md "Async note".
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
export PATH=/home/claude/.local/bin:$PATH
yosys -q -p "read_verilog $HERE/th_cells.v $HERE/ncl_struct_example.v; hierarchy -top fork_top; flatten; write_json $HERE/fork_top.json"
python3 "$HERE/../constraints.py" "$HERE/fork_top.json" fork_top "$HERE/fork_top_forks.json"
