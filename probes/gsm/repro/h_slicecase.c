#include <stdio.h>
#include <string.h>
#include <inttypes.h>
#define SM_NO_MAIN
#include "slicecase.c"
int main(){ state_t s; inputs_t in; outputs_t o; memset(&in,0,sizeof in); sm_reset(&s);
  in._a=0x00001234F0F0F0F0ull; in._b=0x0000FFFF0FF00FF0ull;
  in._op=0; sm_comb(&s,&in,&o); sm_clock(&s,&in); sm_comb(&s,&in,&o); printf("slicecase op=0 (AND): y=%016" PRIx64 " expect 0000123400f000f0 %s\n", (uint64_t)o._y, ((uint64_t)o._y==0x0000123400f000f0ull)?"OK":"MISMATCH");
  in._op=1; sm_comb(&s,&in,&o); sm_clock(&s,&in); sm_comb(&s,&in,&o); printf("slicecase op=1 (OR):  y=%016" PRIx64 " expect 0000fffffff0fff0 %s\n", (uint64_t)o._y, ((uint64_t)o._y==0x0000fffffff0fff0ull)?"OK":"MISMATCH"); return 0; }
