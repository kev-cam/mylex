#!/bin/bash
# --accel with NVC_ACCEL_RTLIL=1 on the final build; walker tried first, text path fallback.
#   usage: ./run_rtlil.sh <dir with work lib> <bench top> <tag> [extra env assignments...]
set -u
DIR=$1; TOP=$2; TAG=$3; shift 3
OUT=/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/rtlil_catalog
export PATH=/usr/local/src/iverilog/_install/bin:/usr/local/src/nvc/build/bin:$PATH
export NVC_LIBPATH=/usr/local/src/nvc/build/lib
export NVC_GSM_LIB=/usr/local/src/sv2ghdl/yosys/libgsm.so
export NVC_ACCEL_CACHE_DIR=$OUT/cache_$TAG NVC_ACCEL=auto GSM_LOG=1 NVC_ACCEL_RTLIL=1
for kv in "$@"; do export "$kv"; done
cd $DIR || exit 2
rm -rf $OUT/cache_$TAG; mkdir -p $OUT/cache_$TAG
echo "== nvc: $(nvc --version 2>&1 | head -1); libgsm.so $(stat -c %y $NVC_GSM_LIB | cut -c1-19); extra env: $*"
/usr/bin/time -f "   wall %es" nvc --std=2040 -r --accel $TOP > $OUT/accel_$TAG.log 2>&1
echo "rc=$?"
grep -E "accel-jit: (entity|synth|ACTIVE|subtree|cached|reusing|no clk|rtlil)|vhdl2rtlil|declin|registers|PASS|FAIL|wall" $OUT/accel_$TAG.log | sed 's/â/-/g' | cut -c1-220
