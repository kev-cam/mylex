#!/bin/bash
cd /usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice
while ! grep -q PHASE5DONE runall.progress 2>/dev/null; do sleep 10; done
while [ "$(pgrep Xyce|wc -l)" != "0" ]; do sleep 5; done
S=$(date +%s); PYMS_DIR=/usr/local/share/xyce/PyMS timeout 3600 /usr/local/src/xyce-build/src/Xyce inv_pdkmodel.sp > inv_pdkmodel.log 2>&1
echo "pdkmodel rc=$? $(( $(date +%s)-S ))s $(grep -iE '^ *(QCYC|TPHL|TPLH)' inv_pdkmodel.log|tr '\n' ' ')" >> runall.progress
echo PHASE6DONE >> runall.progress
