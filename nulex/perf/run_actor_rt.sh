#!/bin/bash
# nulex compiled actor runtime: a yosys gate netlist (JSON) -> a compiled
# event-driven ("actor") C simulator; verify it against the oblivious baseline,
# cross-check the codegen against actor_sim.py, and benchmark wall-clock.
#   run_actor_rt.sh <netlist.json> <top> [cycles]
set -e
JSON=$1; TOP=$2; CYC=${3:-20000}
NULEX=/usr/local/src/mylex/nulex; D="$(dirname "$0")"
cd "$D"
name="$(basename "$JSON" .json)_${TOP}"
echo "=== codegen -> ${name}_rt.c, compile ==="
python3 "$NULEX/map_actor_c.py" "$JSON" "$TOP" "${name}_rt.c"
cc -O2 -o "${name}_rt" "${name}_rt.c"
echo "=== codegen fidelity vs actor_sim.py oblivious ==="
python3 actor_sim.py dump "$JSON" "$TOP" 200 0.03 "${name}_stim.txt"
"./${name}_rt" check "${name}_stim.txt"
echo "=== verify: actor == oblivious (activity sweep) ==="
"./${name}_rt" verify "$CYC" | tail -12
echo "=== wall-clock: actor vs oblivious ==="
"./${name}_rt" bench "$CYC"
