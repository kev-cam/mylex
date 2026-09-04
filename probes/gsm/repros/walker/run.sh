#!/bin/bash
# Walker repro harness: for each DUT, analyse it with the shared bench
# (tb_template.vhd, @DUT@ substituted), run the plain interpreter for the
# gold Y, the RTLIL census for the walker's decline reasons, then the real
# `--accel` run with NVC_ACCEL_RTLIL=1 (walker first, text path fallback) and
# report whether the subtree installed VIA THE RTLIL BUILDER and whether its
# Y matches the gold.  Run it once against the pre-change build and once
# against the new one:
#   ./run.sh before /path/to/nvc_before r1_fcap r2_nest ...
#   ./run.sh after  /usr/local/src/nvc/build r1_fcap ...
# Extra env for the accel run (e.g. NVC_ACCEL_VERIFY=1) goes in $EXTRA.
set -u
LABEL=$1; NVCDIR=$2; shift 2
HERE="$(cd "$(dirname "$0")" && pwd)"
export PATH=$NVCDIR/bin:/usr/local/src/iverilog/_install/bin:$PATH
export NVC_LIBPATH=$NVCDIR/lib
export LD_LIBRARY_PATH=/usr/local/src/iverilog/_install/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export NVC_GSM_LIB=${NVC_GSM_LIB:-/usr/local/src/sv2ghdl/yosys/libgsm.so}
EXTRA=${EXTRA:-}
echo "== $LABEL: $(nvc --version 2>&1 | head -1); libgsm $(stat -c %y $NVC_GSM_LIB | cut -c1-19)"
for DUT in "$@"; do
  W=$HERE/work_${LABEL}_$DUT
  rm -rf "$W"; mkdir -p "$W/cache"
  sed "s/@DUT@/$DUT/g" "$HERE/tb_template.vhd" > "$W/${DUT}_tb.vhd"
  (cd "$W" && nvc --std=2040 -a "$HERE/$DUT.vhd" "$W/${DUT}_tb.vhd" > a.log 2>&1 \
     && nvc --std=2040 -e ${DUT}_tb > e.log 2>&1) \
     || { echo "$DUT [$LABEL]: ANALYSE/ELAB FAILED"; sed -n '1,8p' "$W/a.log" "$W/e.log"; continue; }
  gold=$(cd "$W" && nvc --std=2040 -r ${DUT}_tb 2>&1 | tee gold.log | grep -oE 'Y=[0-9]+' | tail -1)
  # The text-path fallback needs Verilog for the subtree: a DUT with a
  # Verilog twin ($DUT.v, named by its nvc_verilog_src attribute as in the
  # tgt-vhdl flow) synthesises that; otherwise vhdl2vlog emits the subtree
  # (NVC_ACCEL_FROM_VHDL=1).  The walker under test reads neither.
  FV=NVC_ACCEL_FROM_VHDL=1
  [ -f "$HERE/$DUT.v" ] && { cp "$HERE/$DUT.v" "$W/"; FV=NVC_ACCEL_REPRO_TWIN=1; }
  # census: every decline of the walker, module by module (null builder)
  (cd "$W" && env NVC_ACCEL=auto $FV NVC_ACCEL_CACHE_DIR=$W/cache_census NVC_ACCEL_RTLIL=1 \
      NVC_ACCEL_RTLIL_CENSUS=1 GSM_LOG=1 nvc --std=2040 -r --accel ${DUT}_tb > census.log 2>&1)
  reasons=$(grep -oE "vhdl2rtlil-census: [a-z0-9_]+ p[0-9]+ L[0-9]+: .*" "$W/census.log" \
            | sed 's/vhdl2rtlil-census: //' | grep -v " process@" | sort -u | tr '\n' ';')
  # the real run: walker first, text path fallback
  out=$(cd "$W" && env NVC_ACCEL=auto $FV NVC_ACCEL_CACHE_DIR=$W/cache NVC_ACCEL_RTLIL=1 GSM_LOG=1 $EXTRA \
        nvc --std=2040 -r --accel ${DUT}_tb 2>&1 | tee accel.log)
  acc=$(echo "$out" | grep -oE 'Y=[0-9]+' | tail -1)
  via=$(echo "$out" | grep -c "via rtlil builder")
  declined=$(echo "$out" | grep -oE "vhdl2rtlil: '[a-z0-9_]+' declined \([^)]*\)|rtlil builder (declined|failed)[^\n]*" | head -1)
  fits=$(echo "$out" | grep -c "rhs fitted")
  active=$(echo "$out" | grep -c "ACTIVE")
  textpath=$(echo "$out" | grep -c "text path")
  diverg=$(echo "$out" | grep -iE "diverg|mismatch at|verify" | head -2 | tr '\n' ' ')
  if [ -n "$gold" ] && [ "$gold" = "$acc" ]; then m=MATCH; else m=MISMATCH; fi
  if [ "$via" -gt 0 ] && [ "$textpath" -eq 0 ] && [ "$active" -gt 0 ]; then how="INSTALLED via rtlil builder"
  elif [ "$active" -gt 0 ]; then how="text path (walker: ${declined:-?})"
  else how="NOT installed (${declined:-?})"; fi
  echo "$DUT [$LABEL]: gold $gold accel $acc $m | $how | fits=$fits${diverg:+ | $diverg}"
  [ -n "$reasons" ] && echo "    census: $reasons"
done
