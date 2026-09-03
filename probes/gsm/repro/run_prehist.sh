#!/bin/bash
# prehist repro: vvp oracle (exectest alignment) -> gen_statemachine model -> generated harness.
# Expect: the harness WITH the pre-history posedge passes; the previous generator (no pre-history
# edge, compares row 0 before any posedge) fails on `ready` at row 0 and on `cnt` at every row.
# usage: ./run_prehist.sh [gen_gsm_harness.py] [old_gen_gsm_harness.py]
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
GEN=${1:-$HERE/../gen_gsm_harness.py}
OLDGEN=${2:-}
GSM=${GSM:-/usr/local/src/sv2ghdl/yosys/gen_statemachine}
export PATH=/usr/local/src/iverilog/_install/bin:$PATH LD_LIBRARY_PATH=/usr/local/src/iverilog/_install/lib
cd $HERE
iverilog -g2012 -o prehist.vvp tb_prehist.v prehist.v || exit 1
vvp prehist.vvp > /dev/null || exit 1
echo "== oracle rows (reset a | ready cnt q junk)"; cat vectors.txt
$GSM prehist.v prehist_top prehist.c 2>&1 | tail -1
python3 $GEN ports_prehist.txt prehist.c h_prehist.c > /dev/null && gcc -O1 -w -o h_prehist h_prehist.c || exit 1
echo "== harness with the pre-history posedge:"; ./h_prehist vectors.txt; rc=$?
if [ -n "$OLDGEN" ]; then
  python3 $OLDGEN ports_prehist.txt prehist.c h_prehist_old.c > /dev/null && gcc -O1 -w -o h_prehist_old h_prehist_old.c || exit 1
  echo "== harness WITHOUT it (previous generator):"; ./h_prehist_old vectors.txt
fi
exit $rc
