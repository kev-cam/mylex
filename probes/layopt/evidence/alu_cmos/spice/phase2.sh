#!/bin/bash
cd /usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice
while ! grep -q DONE runall.progress 2>/dev/null; do sleep 10; done
while [ "$(pgrep Xyce|wc -l)" != "0" ]; do sleep 5; done
S=$(date +%s); PYMS_DIR=/usr/local/share/xyce/PyMS timeout 1800 /usr/local/src/xyce-build/src/Xyce inv_load.sp > inv_load.log 2>&1
echo "invload rc=$? $(( $(date +%s)-S ))s" >> runall.progress
while [ "$(pgrep Xyce|wc -l)" != "0" ]; do sleep 5; done
S=$(date +%s); PYMS_DIR=/usr/local/share/xyce/PyMS timeout 3600 /usr/local/src/xyce-build/src/Xyce flop_full.sp > flop.log 2>&1
echo "flop rc=$? $(( $(date +%s)-S ))s $(grep -iE '^ *Q[AB]' flop.log|tr '\n' ' ')" >> runall.progress
echo PHASE2DONE >> runall.progress
