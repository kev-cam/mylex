#!/bin/bash
cd /usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice
while ! grep -q PHASE3DONE runall.progress 2>/dev/null; do sleep 10; done
for pass in 1 2; do
for i in 0 1 2 3 4 5 6 7 8 9; do
  if grep -qiE "^ *QC$i *=" s$i.log 2>/dev/null; then continue; fi
  while [ "$(pgrep Xyce|wc -l)" != "0" ]; do sleep 5; done
  python3 gen_comb.py /usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice/shim_full.sp s$i.sp $i >/dev/null
  S=$(date +%s)
  PYMS_DIR=/usr/local/share/xyce/PyMS timeout 1200 /usr/local/src/xyce-build/src/Xyce s$i.sp > s$i.log 2>&1
  echo "refill p$pass cell $i rc=$? $(( $(date +%s)-S ))s $(grep -iE '^ *QC' s$i.log|head -1)" >> runall.progress
done
done
if ! grep -qiE "^ *QA *=" flop.log 2>/dev/null; then
  while [ "$(pgrep Xyce|wc -l)" != "0" ]; do sleep 5; done
  S=$(date +%s); PYMS_DIR=/usr/local/share/xyce/PyMS timeout 3600 /usr/local/src/xyce-build/src/Xyce flop_full.sp > flop.log 2>&1
  echo "refill flop rc=$? $(( $(date +%s)-S ))s $(grep -iE '^ *Q[AB]' flop.log|tr '\n' ' ')" >> runall.progress
fi
echo ALLDONE >> runall.progress
