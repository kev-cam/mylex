#!/bin/bash
# One validation phase after an nvc build: repros (after), ALU census/real/verify,
# Tier A census/real/verify.  usage: ./phase.sh <tag> [repros|alu|tierA ...]
set -u
TAG=$1; shift
S=/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad
R=$S/cmp/rtlil_catalog/run_rtlil.sh
what=${*:-repros alu tierA}
for w in $what; do
  case $w in
    repros)
      (cd $S/walker/repros && ./run.sh after_$TAG /usr/local/src/nvc/build r10_dynmulti r11_oob r12_casez r13_ternary r14_castsigned r1_fcap r2_nest r3_nba r4_slice_arm r5_pvar_read r6_bitread r7_sra r8_dynslice r9_formal_elem 2>&1 | tee $S/walker/repros/after_$TAG.txt)
      ;;
    alu)
      echo "== ALU census"; $R $S/alutest tb_alu_replay ${TAG}_alu_census NVC_ACCEL_RTLIL_CENSUS=1 | grep -E "decline\(s\)|PASS|FAIL|wall|rc="
      echo "== ALU real";   $R $S/alutest tb_alu_replay ${TAG}_alu_real | grep -E "synth|declin|Generated|ACTIVE|PASS|FAIL|wall|rc=|fitted" | cut -c1-200
      echo "== ALU verify"; $R $S/alutest tb_alu_replay ${TAG}_alu_verify NVC_ACCEL_VERIFY=1 | grep -E "synth|declin|VERIFY|diverg|PASS|FAIL|wall|rc=" | cut -c1-200
      ;;
    tierA)
      echo "== Tier A census"; $R $S/cmp/final/exec_tierA tb_exec_replay ${TAG}_tierA_census NVC_ACCEL_RTLIL_CENSUS=1 | grep -E "decline\(s\)|PASS|FAIL|wall|rc=" | grep -v " 0 decline"
      python3 $S/cmp/rtlil_catalog/agg.py $S/cmp/rtlil_catalog/accel_${TAG}_tierA_census.log | tail -25
      ;;
    tierAreal)
      echo "== Tier A real";   $R $S/cmp/final/exec_tierA tb_exec_replay ${TAG}_tierA_real | grep -E "synth|declin|Generated|ACTIVE|PASS|FAIL|wall|rc=|fitted" | cut -c1-200
      ;;
    tierAverify)
      echo "== Tier A verify"; $R $S/cmp/final/exec_tierA tb_exec_replay ${TAG}_tierA_verify NVC_ACCEL_VERIFY=1 | grep -E "synth|declin|VERIFY|diverg|PASS|FAIL|wall|rc=" | cut -c1-200
      ;;
  esac
done
