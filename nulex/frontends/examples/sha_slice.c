/* sha_slice -- the SHA-256 round's core Boolean+arith primitives, 8-bit,
 * written as NATURAL C (a software artifact, not a Verilog transliteration):
 * Maj and Ch exactly as FIPS 180-4 writes them, and the CPA that dominates
 * the round's critical path.
 *
 * This is the same function as the committed RTL validation block
 * stat-sim/qal/synth/threeway/sha_slice.v; the point of B0 is that the
 * common backend produces the same numbers whether the block arrives as
 * Verilog or as this C.
 *
 * C integer promotion applies throughout: every uint8_t operand is promoted
 * to int before the operators, so a + b is a 9-bit-significant value until
 * the store into *sum truncates it (0xFF + 0xFF -> 0x1FE -> 0xFE).  The
 * frontend models exactly that; the compiled-C oracle is the arbiter.
 */
#include <stdint.h>

void sha_slice(uint8_t a, uint8_t b, uint8_t c,
               uint8_t e, uint8_t f, uint8_t g,
               uint8_t *maj, uint8_t *ch, uint8_t *sum)
{
    *maj = (a & b) ^ (a & c) ^ (b & c);   /* Maj(a,b,c), FIPS 180-4 (4.3) */
    *ch  = (e & f) ^ (~e & g);            /* Ch(e,f,g),  FIPS 180-4 (4.2) */
    *sum = (uint8_t)(a + b);              /* the carry-chain CPA          */
}
