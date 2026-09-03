#!/bin/bash
# usage: ./run_repro.sh file.v [top]   -- translate + nvc analyse + elaborate
export PATH=/usr/local/src/iverilog/_install/bin:/usr/local/src/nvc/build/bin:$PATH
export NVC_LIBPATH=/usr/local/src/nvc/build/lib
f=$1; top=${2:-top}; b=${f%.v}
d=$(dirname $(readlink -f $f)); cd $d
rm -rf work_$b; mkdir -p work_$b
iverilog -g2012 -tvhdl -psv2vhdl=1 -s $top -o work_$b/$b.vhd $f || { echo "TRANSLATE FAIL"; exit 1; }
(cd work_$b && nvc --std=2040 -a $b.vhd && nvc --std=2040 -e $top) && echo "PASS $f" || echo "FAIL $f"
