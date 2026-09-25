#!/bin/bash
cd /usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice
for i in 2 3 4 5 6 7 8 9; do
  while [ "$(pgrep Xyce|wc -l)" != "0" ]; do sleep 2; done
  python3 gen_comb.py /usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice/shim_full.sp s$i.sp $i >/dev/null
  S=$(date +%s)
  PYMS_DIR=/usr/local/share/xyce/PyMS timeout 900 /usr/local/src/xyce-build/src/Xyce s$i.sp > s$i.log 2>&1
  echo "cell $i rc=$? $(( $(date +%s)-S ))s  $(grep -iE '^ *Q' s$i.log|head -1)" >> runall.progress
done
echo DONE >> runall.progress
