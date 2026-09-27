/* popcount4 -- population count of the low 4 bits of a byte.  The second
 * B0 end-to-end function (NOT in the polysynth ground-truth set): shifts,
 * masks, and an adder tree -- a shape sha_slice does not have, so it shows
 * the frontend is not sha_slice-shaped.  The adds keep their word form in
 * the IR-WORD profile ($add -> Fant ripple adder). */
#include <stdint.h>

uint8_t popcount4(uint8_t x)
{
    return (uint8_t)(((x >> 0) & 1) + ((x >> 1) & 1)
                   + ((x >> 2) & 1) + ((x >> 3) & 1));
}
