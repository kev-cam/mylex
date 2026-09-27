/* adv_mixed -- ADVERSARIAL: mixed-width compares.  uint16 vs uint8 operands
 * with constants wider than either side's provable bits on both compare
 * shapes: `b == 0x100` is always FALSE (b's 8 provable bits vs a 9-bit
 * constant -- the cmp_wide_const trap at another width), `a > 0x1FF` needs
 * the constant's full 9 bits against a 16-bit operand, and the ordered
 * compare `(a & 0xFF) < (b + 1)` mixes an 8-bit-provable left side with a
 * 9-bit-provable right side.
 */
#include <stdint.h>

uint8_t adv_mixed(uint16_t a, uint8_t b)
{
    return (uint8_t)((a > 0x1FF) | (b == 0x100) | ((a & 0xFF) < (b + 1)));
}
