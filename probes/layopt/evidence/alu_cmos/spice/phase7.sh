#!/bin/bash
cd /usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice
while [ "$(pgrep Xyce|wc -l)" != "0" ]; do sleep 5; done
S=$(date +%s); PYMS_DIR=/usr/local/share/xyce/PyMS timeout 900 /usr/local/src/xyce-build/src/Xyce chain.sp > chain.log 2>&1
echo "chain2 rc=$? $(( $(date +%s)-S ))s $(grep -iE '^ *QCHAIN' chain.log)" >> runall.progress
# genuine PDK-model (PSP 103.8.2) run: FRESH cache dir so PyMS cannot reuse the
# .so built from the 103.4.0 source (cache keys on model params, not the .va file)
while [ "$(pgrep Xyce|wc -l)" != "0" ]; do sleep 5; done
rm -rf /tmp/pyms_vae_pdk && mkdir -p /tmp/pyms_vae_pdk
S=$(date +%s)
PYMS_DIR=/usr/local/share/xyce/PyMS PYMS_VAE_CACHE=/tmp/pyms_vae_pdk \
  timeout 3600 /usr/local/src/xyce-build/src/Xyce inv_pdkmodel.sp > inv_pdkmodel.log 2>&1
echo "pdkmodel2 rc=$? $(( $(date +%s)-S ))s $(grep -iE '^ *(QCYC|TPHL|TPLH)' inv_pdkmodel.log|tr '\n' ' ')" >> runall.progress
# control: SAME fresh-cache mechanism but the 103.4.0 source, to isolate the model version
while [ "$(pgrep Xyce|wc -l)" != "0" ]; do sleep 5; done
sed 's|/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.tech/verilog-a/psp103/psp103.va|/usr/local/share/xyce/verilog-a/psp103/psp103.va|' inv_pdkmodel.sp > inv_oldmodel.sp
rm -rf /tmp/pyms_vae_old && mkdir -p /tmp/pyms_vae_old
S=$(date +%s)
PYMS_DIR=/usr/local/share/xyce/PyMS PYMS_VAE_CACHE=/tmp/pyms_vae_old \
  timeout 3600 /usr/local/src/xyce-build/src/Xyce inv_oldmodel.sp > inv_oldmodel.log 2>&1
echo "oldmodel rc=$? $(( $(date +%s)-S ))s $(grep -iE '^ *(QCYC|TPHL|TPLH)' inv_oldmodel.log|tr '\n' ' ')" >> runall.progress
echo PHASE7DONE >> runall.progress
