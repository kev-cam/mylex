/* cmp_precedence_trap -- const-vs-const compare, reached through C's real
 * precedence: `a & 0xF == 1` parses as `a & (0xF == 1)` (== binds tighter
 * than &), so the compare is 0xF == 1 -- two constants, always FALSE, and
 * the whole function is constantly 0.
 *
 * REGRESSION for the compare-emission bug (c_expr.py, compare cw): treating
 * a const comparand as width 1 masked BOTH constants to 1 bit and emitted
 * `1'h1 == 1'h1` -- always TRUE -- turning the function into `a & 1`.
 * Oracle-caught: 130/259 mismatches (every odd a) before the fix.
 * The frontend now constant-folds const-cmp-const at DAG build (mirroring
 * what the compiled-C oracle's compiler does), and the emitter's compare
 * width includes const maxbits so it cannot lie even when handed one.
 */
#include <stdint.h>

uint8_t cmp_precedence_trap(uint8_t a)
{
    return (uint8_t)(a & 0xF == 1);
}
