#!/bin/bash
# usage: [GSM=<gen_statemachine binary>] ./run.sh
# Three synths of hier.v: no override, N=2 (== default), N=3 (!= default).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
GSM=${GSM:-/usr/local/src/sv2ghdl/yosys/gen_statemachine}
export LD_LIBRARY_PATH=/home/claude/tools/yosys/lib:${LD_LIBRARY_PATH:-}
cd "$HERE" || exit 2
for p in "" "N=2" "N=3"; do
  case "$p" in "") out=out_none.c;; "N=2") out=out_default.c;; *) out=out_other.c;; esac
  rm -f "$out"
  echo "== gen_statemachine hier.v $p hier $out"
  "$GSM" hier.v $p hier "$out" 2>&1 | grep -E "keep|chparam|skip|ERROR|Generated|declin" | sed 's/^/   /' | cut -c1-120
  [ -s "$out" ] && echo "   -> model written ($(wc -c < "$out") bytes)" || echo "   -> NO model"
done
