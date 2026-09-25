#!/bin/bash
cd /usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice
while ! grep -q PHASE7DONE runall.progress 2>/dev/null; do sleep 10; done
for pair in pdk:inv_pdk_nojunc old:inv_old_nojunc; do
  tag=${pair%%:*}; f=${pair##*:}
  while [ "$(pgrep Xyce|wc -l)" != "0" ]; do sleep 5; done
  rm -rf /tmp/pyms_vae_nj_$tag && mkdir -p /tmp/pyms_vae_nj_$tag
  S=$(date +%s)
  PYMS_DIR=/usr/local/share/xyce/PyMS PYMS_VAE_CACHE=/tmp/pyms_vae_nj_$tag \
    timeout 3600 /usr/local/src/xyce-build/src/Xyce $f.sp > $f.log 2>&1
  echo "nojunc-$tag rc=$? $(( $(date +%s)-S ))s $(grep -iE '^ *(QCYC|TPHL)' $f.log|tr '\n' ' ')" >> runall.progress
done
echo PHASE8DONE >> runall.progress
