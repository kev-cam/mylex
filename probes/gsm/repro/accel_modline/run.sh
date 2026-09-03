#!/bin/bash
# accel_verilog_module repro (nvc/src/rt/model.c): long physical lines before the
# module header + `module automatic`.  Three steps:
#   1. modline.c: the old chunk-counting scanner names the wrong module (`decoy`),
#      the new physical-line scanner names `PTop`;
#   2. the full --accel flow on the fixed nvc: `entity 'ptop' is Verilog module
#      'PTop'`, ACTIVE install, PASS;
#   3. the prefix guard: with the nvc_verilog_src attribute pointed at the decoy's
#      header (a mis-located window, simulated by editing the .vhd), the name is
#      rejected ("not its module -- ignored"), the variant name is kept, yosys
#      declines (`PTop` is case-sensitive) and the bench still PASSES interpreted.
#   usage: [NVC=<nvc binary> NVCLIB=<its lib dir>] ./run.sh [tag]
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

# expand the //LONG lines to ~5000 characters (longer than the 4096-byte fgets buffer)
python3 - <<'EOF'
long = "// " + "x" * 5000
src = open("modline.v.in").read().replace("//LONG", long)
open("modline.v", "w").write(src)
EOF
echo "== physical lines longer than 4095 characters: $(awk 'length > 4095' modline.v | wc -l)"
iverilog -g2012 -tvhdl -psv2vhdl=1 -s PTop -o modline.vhd modline.v || exit 2
LINE=$(grep 'nvc_verilog_src of PTop' modline.vhd | sed 's/.*modline.v://; s/".*//')
echo "== nvc_verilog_src of PTop: modline.v:$LINE  (line $LINE is: $(sed -n "${LINE}p" modline.v | cut -c1-40))"
gcc -O1 -o modline modline.c || exit 2
echo "== step 1: header scan at line $LINE"
./modline modline.v $LINE | sed 's/^/   /'
echo "== step 1b: lifetime.v line 2 ($(sed -n 2p lifetime.v | cut -c1-30)...) -- scanner only, yosys read_verilog rejects TOK_AUTOMATIC"
./modline lifetime.v 2 | sed 's/^/   /'

$NVC --std=2040 --work=work_$TAG -a modline.vhd tb_ptop.vhd || exit 2
$NVC --std=2040 --work=work_$TAG -e tb_ptop || exit 2
echo "== step 2: --accel (text path) on the fixed nvc"
NVC_ACCEL=auto NVC_ACCEL_CACHE_DIR=$HERE/cache_$TAG GSM_LOG=1 \
  $NVC --std=2040 --work=work_$TAG -r --accel tb_ptop > accel_$TAG.log 2>&1
grep -E "accel-jit: (entity|synth|ACTIVE|subtree|cached|reusing)|ERROR|not found|declin|PASS|FAIL" accel_$TAG.log | cut -c1-160 | sed 's/^/   /'
echo "   cache: $(ls cache_$TAG | grep -E '\.so$' | tr '\n' ' ')"

echo "== step 3: attribute pointed at the decoy header (mis-located window) -> guard"
DECOY=$(grep -n '^module decoy' modline.v | cut -d: -f1)
sed "s/\(nvc_verilog_src of PTop : entity is \"modline.v:\)$LINE\"/\1$DECOY\"/" modline.vhd > modline_decoy.vhd
grep -q "modline.v:$DECOY\"" modline_decoy.vhd || { echo "   sed failed"; exit 2; }
rm -rf work_${TAG}_decoy cache_${TAG}_decoy; mkdir -p cache_${TAG}_decoy
$NVC --std=2040 --work=work_${TAG}_decoy -a modline_decoy.vhd tb_ptop.vhd || exit 2
$NVC --std=2040 --work=work_${TAG}_decoy -e tb_ptop || exit 2
NVC_ACCEL=auto NVC_ACCEL_CACHE_DIR=$HERE/cache_${TAG}_decoy GSM_LOG=1 \
  $NVC --std=2040 --work=work_${TAG}_decoy -r --accel tb_ptop > accel_${TAG}_decoy.log 2>&1
grep -E "accel-jit: (entity|synth|ACTIVE|subtree|cached|reusing)|ERROR|not found|declin|PASS|FAIL" accel_${TAG}_decoy.log | cut -c1-160 | sed 's/^/   /'
echo "   cache: $(ls cache_${TAG}_decoy | grep -E '\.so$|\.decline$' | tr '\n' ' ')"
