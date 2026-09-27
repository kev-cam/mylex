/* promo_trap -- the C-integer-promotion trap, distilled.
 *
 * In C, a and b promote to int, so (a + b) is the FULL 9-bit sum: at
 * a = b = 0xFF, (0x1FE >> 4) & 0x1F = 0x1F = 31.  An emitter that models
 * uint8_t arithmetic at 8 bits (masking the sum before the shift -- the
 * classic transliteration bug) computes (0xFE >> 4) & 0x1F = 15 instead.
 * The compiled-C oracle catches exactly this; c_expr.py --naive-widths
 * reproduces the bug on purpose so the harness can demonstrate the catch.
 */
#include <stdint.h>

uint8_t promo_trap(uint8_t a, uint8_t b)
{
    return (uint8_t)(((a + b) >> 4) & 0x1F);
}
