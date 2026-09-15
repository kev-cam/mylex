#!/bin/bash
# install_pdk.sh — sky130 PDK for the layopt flow, NO sudo (run as the user).
# Installs volare in a venv, downloads sky130A, wires layopt's expected LIB dir
# (~/tools/sky130_fd_sc_hd: tlef + LEF + per-cell GDS split from the merged lib).
set -e
T=$HOME/tools
python3 -m venv $T/layenv 2>/dev/null || true
$T/layenv/bin/pip install --quiet volare
$T/layenv/bin/volare enable --pdk sky130 --pdk-root $T/pdk \
    c6d73a35f524070e85faff4a6a9eef49553ebc2b
PDK=$T/pdk/sky130A/libs.ref/sky130_fd_sc_hd
LIB=$T/sky130_fd_sc_hd
mkdir -p $LIB
ln -sf $PDK/techlef/sky130_fd_sc_hd__nom.tlef $LIB/sky130_fd_sc_hd.tlef
ln -sf $PDK/lef/sky130_fd_sc_hd.lef           $LIB/sky130_fd_sc_hd__merged.lef
# layopt's def2flat wants per-cell <macro>.gds; split the merged GDS with layopt.gds
MYLEX=${MYLEX:-/usr/local/src/mylex}
python3 - "$PDK/gds/sky130_fd_sc_hd.gds" "$LIB" "$MYLEX" <<'PY'
import sys; sys.path.insert(0, sys.argv[3])
from layopt import gds; import os
lib = gds.read(sys.argv[1])
for c in [n for n in lib.structs if n.startswith("sky130_fd_sc_hd__")]:
    gds.write_flat(gds.flatten(lib, top=c), os.path.join(sys.argv[2], c + ".gds"), name=c)
print("wired %s (tlef + LEF + %d per-cell GDS)" % (sys.argv[2],
      len([n for n in lib.structs if n.startswith('sky130_fd_sc_hd__')])))
PY
echo "PDK ready. Verify: cd $MYLEX/probes/layopt && LAYOPT_SCRATCH=/tmp/lo python3 l3_fork_balance.py --iters 40"
