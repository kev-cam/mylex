#!/bin/bash
# --accel text-path repro: parameterisation-suffixed entity names and a
# >256-byte nvc_verilog_params attribute (see params.v).
#   usage: [NVC=<nvc binary> NVCLIB=<its lib dir>] ./run.sh [tag]
# Translates params.v with the iverilog fork's tgt-vhdl, runs tb_ptop plain
# and with --accel (text path: NVC_ACCEL_RTLIL unset), and prints the accel
# log lines that matter: the synth top/params, yosys errors, the install
# line and the bench verdict.  A fresh cache dir every run.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
TAG=${1:-run}
IVL=${IVL:-/usr/local/src/iverilog/_install}
NVC=${NVC:-/usr/local/src/nvc/build/bin/nvc}
NVCLIB=${NVCLIB:-/usr/local/src/nvc/build/lib}
export PATH=$IVL/bin:$PATH LD_LIBRARY_PATH=$IVL/lib NVC_LIBPATH=$NVCLIB
export NVC_GSM_LIB=${NVC_GSM_LIB:-/usr/local/src/sv2ghdl/yosys/libgsm.so}
unset NVC_ACCEL_RTLIL
cd "$HERE" || exit 2
rm -rf work_$TAG cache_$TAG; mkdir -p cache_$TAG
W="--work=work_$TAG"

iverilog -g2012 -tvhdl -psv2vhdl=1 -s ptop -o ptop.vhd params.v || exit 2
echo "== entities and attributes (tgt-vhdl)"
grep -n "^entity\|nvc_verilog_src of\|nvc_verilog_params of" ptop.vhd | cut -c1-120
echo "params attribute length: $(grep 'nvc_verilog_params of ptop' ptop.vhd | sed 's/.*is "//; s/";//' | wc -c)"

$NVC --std=2040 $W -a ptop.vhd tb_ptop.vhd || exit 2
$NVC --std=2040 $W -e tb_ptop || exit 2
echo "== plain"
$NVC --std=2040 $W -r tb_ptop 2>&1 | grep -E "PASS|FAIL"
echo "== --accel (text path)"
NVC_ACCEL=auto NVC_ACCEL_CACHE_DIR=$HERE/cache_$TAG GSM_LOG=1 \
  $NVC --std=2040 $W -r --accel tb_ptop > accel_$TAG.log 2>&1
grep -E "accel-jit: (entity|params|synth|ACTIVE|subtree|cached|reusing)|chparam|ERROR|not found|declin|PASS|FAIL" accel_$TAG.log | cut -c1-160
echo "== cache_$TAG"; ls cache_$TAG | grep -E "\.so$|\.decline$|\.c$" | sed 's/^/   /'
