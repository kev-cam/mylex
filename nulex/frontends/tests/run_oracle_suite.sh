#!/bin/sh
# run_oracle_suite.sh -- the three-legged (gcc==clang==iverilog) oracle
# regression suite for c_expr.py, one NAMED test per line.
#
#   cd frontends && sh tests/run_oracle_suite.sh
#
# Every test must exit 0 EXCEPT promo_trap_naive_catch, whose pass condition
# is the oracle CATCHING the planted --naive-widths bug (nonzero exit), and
# the two *_refuse tests, whose pass condition is c_expr REFUSING the source
# with the NAMED message (nonzero exit + the message matched, so an unrelated
# crash cannot pass them).
# sha_byte_identity additionally requires the emitted sha_slice_c.v to stay
# byte-identical run-to-run and the C-origin QDI netlists (when present in
# work/polysynth_sha_c) to stay byte-identical to the committed threeway
# ground truth -- the B0 acceptance property.
set -e
cd "$(dirname "$0")/.."
FRONT=$(pwd)
mkdir -p work
cd work

run() { name=$1; shift; echo "== $name"; python3 "$FRONT/c_expr.py" "$@"; }

# refuse NAME PATTERN ARGS... : the frontend must REJECT with PATTERN in the
# message (a refusal is a feature only if it is the RIGHT refusal).
refuse() {
    name=$1; pat=$2; shift 2
    echo "== $name (frontend MUST refuse)"
    if out=$(python3 "$FRONT/c_expr.py" "$@" 2>&1); then
        echo "$name: FRONTEND ACCEPTED IT (expected a refusal)"; echo "$out"
        exit 1
    fi
    case "$out" in
        *"$pat"*) echo "$name: refused with the named message -- PASS" ;;
        *) echo "$name: wrong failure (expected '$pat'):"; echo "$out"; exit 1 ;;
    esac
}

# ---- the B0 acceptance set ----
run sha_slice   "$FRONT/examples/sha_slice.c"  sha_slice  -o sha_slice_c.v  --check 200000
run popcount4   "$FRONT/examples/popcount4.c"  popcount4  -o popcount4_c.v  --exhaustive
run promo_trap  "$FRONT/examples/promo_trap.c" promo_trap -o promo_trap.v   --exhaustive

echo "== promo_trap_naive_catch (oracle MUST catch the planted bug)"
if python3 "$FRONT/c_expr.py" "$FRONT/examples/promo_trap.c" promo_trap \
        -o promo_trap_naive.v --naive-widths --exhaustive >/dev/null 2>&1; then
    echo "promo_trap_naive_catch: oracle FAILED TO CATCH --naive-widths"; exit 1
fi
echo "promo_trap_naive_catch: caught (nonzero exit) -- PASS"

# ---- compare-emission regressions (const comparand width; both repro
#      shapes of the B1-gating miscompile) ----
run cmp_precedence_trap "$FRONT/examples/cmp_precedence_trap.c" cmp_precedence_trap \
    -o cmp_precedence_trap.v --exhaustive
run cmp_wide_const      "$FRONT/examples/cmp_wide_const.c"      cmp_wide_const \
    -o cmp_wide_const.v --exhaustive

# ---- adversarial compare shapes ----
run adv_mixed   "$FRONT/examples/adv_mixed.c"   adv_mixed   -o adv_mixed.v   --check 200000
run adv_cmpcmp  "$FRONT/examples/adv_cmpcmp.c"  adv_cmpcmp  -o adv_cmpcmp.v  --exhaustive
run adv_terncmp "$FRONT/examples/adv_terncmp.c" adv_terncmp -o adv_terncmp.v --exhaustive

# ---- (int)-cast on the compare path: the DEFINED half must agree, and the
#      two implementation-defined shapes must be refused by name ----
run adv_intcast "$FRONT/examples/adv_intcast.c" adv_intcast -o adv_intcast.v \
    --exhaustive
refuse adv_intcast_wrap_refuse \
    "implementation-defined out-of-range conversion" \
    "$FRONT/examples/adv_intcast.c" adv_intcast_wrap -o adv_intcast_wrap.v \
    --exhaustive
refuse adv_intcast_signed_cmp_refuse \
    "ordered compare on a possibly-negative int" \
    "$FRONT/examples/adv_intcast.c" adv_intcast_signed_cmp \
    -o adv_intcast_signed_cmp.v --exhaustive

# ---- sha_byte_identity: C-origin QDI netlists vs the committed threeway GT
#      (skipped with a notice if the polysynth outputs are not in work/) ----
echo "== sha_byte_identity"
GT=/usr/local/src/stat-sim/qal/synth/threeway/work
if [ -f polysynth_sha_c/sha_slice.qdi_direct.v ] && [ -d "$GT" ]; then
    cmp polysynth_sha_c/sha_slice.qdi_direct.v    "$GT/sha_slice_direct_spice.v"
    cmp polysynth_sha_c/sha_slice.qdi_direct_cd.v "$GT/sha_slice_direct_cd.v"
    echo "sha_byte_identity: QDI netlists byte-identical to committed GT -- PASS"
else
    echo "sha_byte_identity: SKIPPED (no work/polysynth_sha_c outputs or no $GT)"
fi

echo "ALL ORACLE SUITE TESTS PASS"
