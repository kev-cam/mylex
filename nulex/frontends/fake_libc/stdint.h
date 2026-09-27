/* Minimal stdint.h for pycparser PARSING ONLY (the pycparser wheel ships no
 * fake libc headers).  The software oracle compiles the SAME source against
 * the REAL system headers with gcc/clang -- this file never affects semantics,
 * it only lets pycparser see the typedefs. */
#ifndef _CEXPR_FAKE_STDINT_H
#define _CEXPR_FAKE_STDINT_H
typedef signed char        int8_t;
typedef short              int16_t;
typedef int                int32_t;
typedef long long          int64_t;
typedef unsigned char      uint8_t;
typedef unsigned short     uint16_t;
typedef unsigned int       uint32_t;
typedef unsigned long long uint64_t;
#endif
