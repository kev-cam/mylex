#!/bin/bash
# Run each test through vvp (reference) and tgt-vhdl -> nvc --std=2040.
# usage: run.sh <test.sv> [<top>] [env assignments prefix via VARS]
D=${D:-$(cd "$(dirname "$0")" && pwd)}
IV=/usr/local/src/iverilog/_install/bin/iverilog
VVP=/usr/local/src/iverilog/_install/bin/vvp
export PATH=/usr/local/src/nvc/build/bin:$PATH
export NVC_LIBPATH=/usr/local/src/nvc/build/lib
export LD_LIBRARY_PATH=/usr/local/src/iverilog/_install/lib:$LD_LIBRARY_PATH
f=$1; top=${2:-$(basename $f .sv)}
tag=${TAG:-run}
w=$D/out/$top.$tag; rm -rf $w; mkdir -p $w; cd $w
echo "=== $f top=$top tag=$tag"
$IV -g2012 -o $w/a.vvp -s $top $f > $w/iv.log 2>&1 || { echo "iverilog(vvp) FAILED"; cat $w/iv.log; }
echo "--- vvp:"; $VVP -n $w/a.vvp 2>&1 | grep -v "^VCD\|\$finish" | head -20
$IV -g2012 -tvhdl -psv2vhdl=1 -o $w/d.vhd -s $top $f > $w/tr.log 2>&1; rc=$?
echo "--- translate rc=$rc:"; grep -i "warning\|error\|merged\|Renamed" $w/tr.log | head -10
nvc --std=2040 -a $w/d.vhd > $w/nvc_a.log 2>&1 || { echo "nvc -a FAILED"; grep -B2 -A6 "Error\|error" $w/nvc_a.log | head -40; exit 1; }
nvc --std=2040 -e $top > $w/nvc_e.log 2>&1 || { echo "nvc -e FAILED"; grep -B2 -A6 "Error\|error" $w/nvc_e.log | head -30; exit 1; }
echo "--- nvc -r:"; timeout 60 nvc --std=2040 -r $top 2>&1 | head -30
