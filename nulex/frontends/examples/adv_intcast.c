/* adv_intcast -- ADVERSARIAL: the `(int)` cast on the compare path.
 *
 * REGRESSION for the second compare-path silent-miscompile (c_expr.py, the
 * `names == ["int"]` cast branch, was lines 429-430).  That branch set
 * w = 32 with the comment "value already fits" and left the result UNSIGNED
 * with neg = False, so a value provably >= 2^31 reached an ordered compare
 * believed non-negative and was compared UNSIGNED -- while C compares it as
 * a NEGATIVE int.  The recorded repro is adv_intcast_wrap() below
 * (MEASURED pre-fix: 259/259 oracle mismatches, exit 1).
 *
 * adv_intcast() is the DEFINED half and must agree bit-exact:
 *   p : (int) casts that convert NOTHING (uint8_t already promoted to int) --
 *       ordered compare of two of them, the common benign idiom;
 *   q : (int) of a value provably <= INT_MAX (masked to 7 bits) -- a
 *       value-preserving retype, still allowed, now marked signed;
 *   r : the documented FIX for the wrap case -- (uint32_t), an unsigned
 *       compare of a >= 2^31 value, which is exactly what the emission
 *       used to do silently while claiming to be C's (int) compare.  Here it
 *       is what C does too, so C == HW; r is 1 only when a == 0.
 *   s : (int) of a negative-capable int passed through ~ , then re-cast to
 *       (uint32_t) before the compare -- the neg flag must survive the
 *       (int) no-op cast (an ordered compare WITHOUT the (uint32_t) is
 *       refused; see adv_intcast_signed_cmp).
 *
 * adv_intcast_wrap() / adv_intcast_signed_cmp() are the REFUSAL half: both
 * must be rejected loudly (nonzero exit, naming the (uint32_t) fix), never
 * emitted.  They are driven by tests/run_oracle_suite.sh as named tests.
 */
#include <stdint.h>

uint8_t adv_intcast(uint8_t a, uint8_t b)
{
    uint8_t  p = (uint8_t)((int)a < (int)b);
    uint8_t  q = (uint8_t)((int)(a & 0x7F) >= 1);
    uint32_t big = (uint32_t)a | 0x80000000u;
    uint8_t  r = (uint8_t)((uint32_t)big <= 0x80000000u);
    uint8_t  s = (uint8_t)((uint32_t)(int)(~(a | 0x10u)) > 0x7FFFFFFFu);
    return (uint8_t)(p | (uint8_t)(q << 1) | (uint8_t)(r << 2)
                     | (uint8_t)(s << 3));
}

/* THE RECORDED REPRO -- must be REFUSED, not emitted.  In C the (int)
 * conversion of a value >= 2^31 is implementation-defined; gcc and clang
 * both wrap, so the value is negative and (negative < 1) is always 1.  The
 * pre-fix emission compared unsigned and said always 0. */
uint8_t adv_intcast_wrap(uint8_t a)
{
    return (uint8_t)((int)(a | 0x80000000u) < 1);
}

/* the adjacent shape: the (int) cast of an already-negative-capable int is a
 * NO-OP and must keep neg set, so this ordered compare must still hit the
 * existing signed-comparator refusal (it did before this fix too -- this
 * test pins that the fix did not open a hole by passing the node through). */
uint8_t adv_intcast_signed_cmp(uint8_t a)
{
    return (uint8_t)((int)(~a) < 1);
}
