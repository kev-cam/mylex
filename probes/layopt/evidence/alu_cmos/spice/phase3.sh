#!/bin/bash
cd /usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice
while ! grep -q PHASE2DONE runall.progress 2>/dev/null; do sleep 10; done
while [ "$(pgrep Xyce|wc -l)" != "0" ]; do sleep 5; done
S=$(date +%s); PYMS_DIR=/usr/local/share/xyce/PyMS timeout 1800 /usr/local/src/xyce-build/src/Xyce inv_slew.sp > inv_slew.log 2>&1
echo "invslew rc=$? $(( $(date +%s)-S ))s" >> runall.progress
echo PHASE3DONE >> runall.progress
