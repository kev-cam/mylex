/* cmp_wide_const -- a constant comparand WIDER than the other side's
 * provable value bound: (a & 0xF) has maxbits 4, but 0x10 needs 5 bits,
 * so the compare is always FALSE in C.
 *
 * REGRESSION for the compare-emission bug (c_expr.py, compare cw): the
 * emission width ignored the constant's maxbits, so ref() masked 0x10 to
 * the 4-bit compare width -- emitting `w == 4'h0`, TRUE whenever
 * a & 0xF == 0.  Oracle-caught: 17/259 mismatches (a in {0x00,0x10,...}
 * plus the all-zero corner) before the fix.  The compare width now takes
 * max(non-const emit width, const maxbits) on each side.
 */
#include <stdint.h>

uint8_t cmp_wide_const(uint8_t a)
{
    return (uint8_t)((a & 0xF) == 0x10);
}
