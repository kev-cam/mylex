#!/bin/bash
# usage: ./run_fusedorder.sh [ivl_install]  -- translate fusedorder.v three ways
# (relative path, absolute path, absolute path under a 4 KB environment) and
# compare the VHDL after path normalisation.  PASS when byte-identical.
IVL=${1:-/usr/local/src/iverilog/_install}
export PATH=$IVL/bin:$PATH LD_LIBRARY_PATH=$IVL/lib
d=$(dirname $(readlink -f $0)); cd $d
rm -rf work_fusedorder; mkdir -p work_fusedorder
iverilog -g2012 -tvhdl -psv2vhdl=1 -s fusedorder -o work_fusedorder/f1.vhd fusedorder.v || exit 1
iverilog -g2012 -tvhdl -psv2vhdl=1 -s fusedorder -o $d/work_fusedorder/f2.vhd $d/fusedorder.v || exit 1
BIGENV=$(head -c 4000 /dev/zero | tr '\0' 'b') iverilog -g2012 -tvhdl -psv2vhdl=1 -s fusedorder -o $d/work_fusedorder/f3.vhd $d/fusedorder.v || exit 1
cd work_fusedorder
for i in 1 2 3; do sed -E 's#(/[A-Za-z0-9_./-]*/)?fusedorder\.v#fusedorder.v#g' f$i.vhd > f${i}_n.vhd; done
echo "comb_fused processes: $(grep -c 'comb_fused_[0-9]*: process' f1_n.vhd)"
grep -o 'comb_fused_[0-9]*: process ([a-z0-9_, ]*)' f1_n.vhd | tr '\n' ' '; echo
if cmp -s f1_n.vhd f2_n.vhd && cmp -s f2_n.vhd f3_n.vhd; then echo "PASS: 3 translations byte-identical after path normalisation"
else echo "FAIL: translations differ"; diff f1_n.vhd f2_n.vhd | head -6; diff f1_n.vhd f3_n.vhd | grep -c '^<'; fi
