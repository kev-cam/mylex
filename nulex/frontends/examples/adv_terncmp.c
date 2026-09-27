/* adv_terncmp -- ADVERSARIAL: ternary-with-compare.  A ternary of two
 * constants of different widths (0x100 is 9-bit, 1 is 1-bit) feeds an
 * ordered compare (`a > (b ? 0x100 : 1)`: when b != 0 the compare is
 * always false -- a can't exceed 0x100 -- so the whole mux collapses to b
 * on that half-plane); one ternary arm is a const-cmp-const (`0x3 == 3`,
 * folds to 1) while the other arm is a live compare (`b >= 0xF0`), so the
 * mux mixes a folded constant with a comparator output at width 1.
 */
#include <stdint.h>

uint8_t adv_terncmp(uint8_t a, uint8_t b)
{
    return (uint8_t)((a > (b ? 0x100 : 1) ? a : b)
                     + ((a == 0xAA) ? (0x3 == 3) : (b >= 0xF0)));
}
