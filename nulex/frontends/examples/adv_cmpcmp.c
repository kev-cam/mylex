/* adv_cmpcmp -- ADVERSARIAL: compare-of-compare.  Compare results are
 * 1-bit-provable ints in C (0 or 1), so `(a < b) == 2` is always FALSE --
 * the wide-const trap where the narrow side is itself a comparator output;
 * `(a == b) == (a != 0)` compares two compare results against each other;
 * and `(!(a > b)) != (a <= b)` is identically 0 (! of a compare vs its
 * complement) -- any emission-width slip on either leg flips it to 1.
 */
#include <stdint.h>

uint8_t adv_cmpcmp(uint8_t a, uint8_t b)
{
    return (uint8_t)((((a == b) == (a != 0)) | ((a < b) == 2))
                     | ((!(a > b)) != (a <= b)));
}
