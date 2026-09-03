#!/bin/bash
# The parameter-loop cases of the keep-if-default review (gen_statemachine gsm_run):
#   dep.v    RESETW defaults to DATAW (VX_pipe_register shape) -- both argument orders
#   chain.v  B defaults to A, C to B -- both orders (correct constants 0x80/0x10/0x4 = d + 0x94)
#   hier.v   the motivating case (../gsm_chparam_default): N=2 == default must be KEPT
#            (chparam breaks sv2v's by-module-name hierarchical reference) and be
#            byte-identical to the no-override model
#   edge.v   parser/width edges: W=010 (decimal 10, not octal 8), BASE=2^32 on a 32-bit
#            default (not a no-op), K=18446744073709551615 and K=-1 on a signed -1 default (no-op)
# usage: [GSM=<gen_statemachine>] ./run_cases.sh [tag]      -> out_<tag>/, decisive lines on stdout
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
GSM=${GSM:-/usr/local/src/sv2ghdl/yosys/gen_statemachine}
TAG=${1:-run}
export LD_LIBRARY_PATH=/home/claude/tools/yosys/lib:${LD_LIBRARY_PATH:-}
O=$HERE/out_$TAG; rm -rf "$O"; mkdir -p "$O"; cd "$O" || exit 2
run() { local name=$1; shift
  echo "== $name: $*"
  "$GSM" "$@" 2>&1 | grep -E "^  (keep|chparam|skip)|ERROR|Can't decode|Generated .*\.c:" | sed 's/^/     /' | cut -c1-110
}
consts() { grep -o 'UINT64_C(0x[0-9a-f]*)' "$1" 2>/dev/null | sort -u | tr '\n' ' '; }
run dep_DR   $HERE/dep.v DATAW=4 RESETW=1 dep dep_DR.c
run dep_RD   $HERE/dep.v RESETW=1 DATAW=4 dep dep_RD.c
for f in dep_DR dep_RD; do echo "     $f reset mux (correct: bit 0 only): $(grep -m1 '_rst ?' $f.c 2>/dev/null | sed 's/^ *//' | cut -c1-90)"; done
run chain_ABC $HERE/chain.v A=2 B=1 C=1 chain chain_ABC.c
run chain_CBA $HERE/chain.v C=1 B=1 A=2 chain chain_CBA.c
for f in chain_ABC chain_CBA; do echo "     $f constants (correct: 0x80 0x10 0x4; stale keep: 0x80 0x20 0x8): $(consts $f.c)"; done
run hier_none $HERE/../gsm_chparam_default/hier.v hier hier_none.c
run hier_N2   $HERE/../gsm_chparam_default/hier.v N=2 hier hier_N2.c
cmp -s hier_none.c hier_N2.c && echo "     hier_none.c == hier_N2.c" || echo "     hier_none.c != hier_N2.c"
run dep_all_default $HERE/dep.v DATAW=1 RESETW=1 dep dep_def.c
run dep_none        $HERE/dep.v dep dep_none.c
cmp -s dep_def.c dep_none.c && echo "     dep_def.c == dep_none.c" || echo "     dep_def.c != dep_none.c"
run oct_010   $HERE/edge.v W=010 oct oct.c
echo "     mask (0xff = W kept at 8 WRONG, 0x3ff = W set to 10): $(consts oct.c)"
run wide_2p32 $HERE/edge.v BASE=4294967296 wide wide.c
echo "     BASE constant (0x100000000 expected): $(consts wide.c)"
run neg_u64   $HERE/edge.v K=18446744073709551615 neg neg.c
echo "     K constant (0xffffffff expected): $(consts neg.c)"
run neg_m1    $HERE/edge.v K=-1 neg neg_m1.c
echo "     K constant (0xffffffff expected): $(consts neg_m1.c)"
