#!/usr/bin/env python3
"""Generate a C replay harness for a gen_statemachine model from the wrapper port
manifest (dir width name) and the exectest vector layout (inputs as nibble-padded
hex, outputs as %b bit strings, inputs-then-outputs in manifest order, clk excluded).
usage: gen_gsm_harness.py ports.txt model.c out_harness.c"""
import sys
ports = [l.split() for l in open(sys.argv[1]) if l.strip()]
ins  = [(w, n) for d, w, n in [(p[0], int(p[1]), p[2]) for p in ports] if d == 'input' and n != 'clk']
outs = [(w, n) for d, w, n in [(p[0], int(p[1]), p[2]) for p in ports] if d == 'output']
def limbs(w): return (w + 31) // 32
c = ['#include <stdio.h>', '#include <stdint.h>', '#include <string.h>', '#include <stdlib.h>',
     '#define SM_NO_MAIN', '#include "%s"' % sys.argv[2], '',
     'static int hv(char ch){ if(ch>=\'0\'&&ch<=\'9\')return ch-\'0\'; if(ch>=\'a\'&&ch<=\'f\')return ch-\'a\'+10; if(ch>=\'A\'&&ch<=\'F\')return ch-\'A\'+10; return -1; }',
     '// hex (MSB first) -> limbs; x nibbles read as 0 (inputs never contain x by construction)',
     'static void set_limbs(const char*s,uint32_t*l,int nl){ int n=strlen(s); memset(l,0,4*nl); for(int i=0;i<n;i++){int v=hv(s[n-1-i]); if(v<0)v=0; int b=4*i; if(b/32<nl) l[b/32]|=(uint32_t)v<<(b%32);} }',
     'static uint64_t hex64(const char*s){ uint64_t v=0; for(const char*p=s;*p;p++){int d=hv(*p); v=(v<<4)|(d<0?0:d);} return v; }',
     '// compare a w-bit value (limbs, LSB limb first) with a %b string (MSB first); x = dont care',
     'static int cmp_bits(const uint32_t*l,int w,const char*s,int*firstbad){ int n=strlen(s); if(n<w) return 0; for(int i=0;i<w;i++){ char e=s[n-1-i]; if(e==\'x\'||e==\'X\'||e==\'z\'||e==\'Z\') continue; int a=(l[i/32]>>(i%32))&1; if(a!=(e==\'1\')){ *firstbad=i; return 0;} } return 1; }',
     'int main(int argc,char**argv){ FILE*f=fopen(argv[1],"r"); if(!f){perror("vectors");return 2;}',
     '  state_t st; inputs_t in; outputs_t out; memset(&in,0,sizeof in); sm_reset(&st);',
     '  static char tok[%d][2048]; int cyc=0,bad=0; char line[65536];' % (len(ins) + len(outs)),
     '  while(fgets(line,sizeof line,f)){ int nt=0; char*p=strtok(line," \\n"); while(p&&nt<%d){ strncpy(tok[nt++],p,2047); p=strtok(NULL," \\n"); } if(nt!=%d){ fprintf(stderr,"line %%d: %%d tokens\\n",cyc,nt); return 2; }' % (len(ins)+len(outs), len(ins)+len(outs))]
for i, (w, n) in enumerate(ins):
    if w <= 64: c.append('    in._%s = hex64(tok[%d]);' % (n, i))
    else:       c.append('    set_limbs(tok[%d], in._%s, %d);' % (i, n, limbs(w)))
c.append('    memset(&out,0,sizeof out); sm_comb(&st,&in,&out);')
c.append('    { int fb; uint32_t tmp[64];')
for j, (w, n) in enumerate(outs):
    t = len(ins) + j
    if w <= 64:
        c.append('      tmp[0]=(uint32_t)out._%s; tmp[1]=(uint32_t)(out._%s>>32); if(!cmp_bits(tmp,%d,tok[%d],&fb)){ bad++; if(bad<=8) printf("cycle %%d: %s mismatch (bit %%d) act=%%016llx exp=%%s\\n",cyc,fb,(unsigned long long)out._%s,tok[%d]); }' % (n, n, w, t, n, n, t))
    else:
        c.append('      if(!cmp_bits(out._%s,%d,tok[%d],&fb)){ bad++; if(bad<=8) printf("cycle %%d: %s mismatch (bit %%d) exp=%%s\\n",cyc,fb,tok[%d]); }' % (n, w, t, n, t))
c.append('    }')
c.append('    sm_clock(&st,&in); cyc++; }')
c.append('  printf("%s: %d cycles replayed through the gen_statemachine model, %d mismatches\\n", bad?"FAIL":"PASS", cyc, bad); return bad?1:0; }')
open(sys.argv[3], 'w').write('\n'.join(c) + '\n')
print('harness: %d inputs, %d outputs' % (len(ins), len(outs)))
