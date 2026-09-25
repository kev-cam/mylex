#!/bin/bash
cd /usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice
while ! grep -q ALLDONE runall.progress 2>/dev/null; do sleep 10; done
while [ "$(pgrep Xyce|wc -l)" != "0" ]; do sleep 5; done
S=$(date +%s); PYMS_DIR=/usr/local/share/xyce/PyMS timeout 1200 /usr/local/src/xyce-build/src/Xyce chain.sp > chain.log 2>&1
echo "chain rc=$? $(( $(date +%s)-S ))s $(grep -iE '^ *QCHAIN' chain.log)" >> runall.progress
echo PHASE5DONE >> runall.progress
