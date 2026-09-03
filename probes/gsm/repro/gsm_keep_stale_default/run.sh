#!/bin/sh
# Stale-default "keep" hazard in gen_statemachine's chparam loop.
# dep.v: parameter RESETW defaults to DATAW.  Actuals DATAW=4 RESETW=1
# (the VX_pipe_register #(.DATAW(N), .RESETW(1)) shape).  The keep test
# compares RESETW=1 against the default snapshot taken BEFORE chparam
# DATAW=4 (RESETW default was 1 then) and skips it; the derived module
# has RESETW = DATAW = 4, so the model resets all four bits.
# Usage: GSM=<gen_statemachine> ./run.sh <tag>
GSM=${GSM:-/usr/local/src/sv2ghdl/yosys/gen_statemachine}
tag=${1:-run}
cd "$(dirname "$0")"
"$GSM" dep.v DATAW=4 RESETW=1 dep out_$tag.c 2>&1 | grep -E "keep|chparam|Generated|ERROR"
echo "--- reset mux in out_$tag.c (correct: bit 0 only reset, bits 3:1 hold):"
grep -n "_rst ?" out_$tag.c | head -2
