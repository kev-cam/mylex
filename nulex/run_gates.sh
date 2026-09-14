#!/bin/bash
# nulex P3 gate-library equivalence gates (task #60).
# Uses the INSTALLED nvc NCL library (Apache, in the nvc tree) via -L; the
# PolyForm nulex tree never copies it. Exit 0 == all gates green.
set -e
NVC="${NVC:-/usr/local/src/nvc-build/bin/nvc}"
NVCLIB="${NVCLIB:-/usr/local/src/nvc-build/lib}"
cd "$(dirname "$0")"
A=( --std=2008 -L "$NVCLIB" --work=work )
rm -rf work
echo "=== analyze lib + tests ==="
$NVC "${A[@]}" -a lib/ncl_gates.vhd
$NVC "${A[@]}" -a tests/tb_ncl_and2.vhd
$NVC "${A[@]}" -a tests/tb_ncl_gates.vhd
$NVC "${A[@]}" -a tests/tb_ncl_mux2.vhd
$NVC "${A[@]}" -a tests/tb_add4_cbc.vhd
for TOP in tb_ncl_and2 tb_ncl_gates tb_ncl_mux2 tb_add4_cbc; do
  echo "=== $TOP ==="
  $NVC "${A[@]}" -e "$TOP"
  $NVC "${A[@]}" -r "$TOP"
done
echo "=== ALL NULEX GATES GREEN ==="
