// Replay mylex probes/alutest/vectors.txt through the gen_statemachine model of alu_top.
// Line k: inputs applied at negedge k; recorded outputs reflect the preceding posedge
// plus the new inputs (comb) -> sm_comb(state, in_k) must equal outputs_k; then sm_clock.
// Pre-history as in tb_alu.sv (`reg clk = 0; always #5 clk = ~clk`, reset = 1 from t0, row 0
// driven from t0, recorder at negedge+1 ns): the first rising edge at 5 ns precedes the row-0
// sample at 11 ns, so row k follows k+1 posedges (inputs in0, in0, in1, ..). Replay that edge
// before the row-0 compare; all rows are compared (x nibble = don't care).
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include "alu.c"

static int hexval(char c){ if(c>='0'&&c<='9')return c-'0'; if(c>='a'&&c<='f')return c-'a'+10; if(c>='A'&&c<='F')return c-'A'+10; return -1; }
// parse hex string (MSB first) into 32-bit limbs; returns 0 on X
static int parse_hex(const char*s, uint32_t*limbs, int nlimbs, uint8_t*xmask_nib){
  int n=strlen(s); memset(limbs,0,4*nlimbs); int hasx=0;
  for(int i=0;i<n;i++){ int v=hexval(s[n-1-i]); if(v<0){hasx=1; if(xmask_nib) xmask_nib[i]=1; v=0;} else if(xmask_nib) xmask_nib[i]=0;
    int bit=i*4; if(bit/32<nlimbs) limbs[bit/32] |= (uint32_t)v<<(bit%32); }
  return !hasx;
}
static int cmp_nib(uint64_t act, const char*exp){ // exp hex string; X nibble = don't care
  int n=strlen(exp); for(int i=0;i<n;i++){ int v=hexval(exp[n-1-i]); if(v<0) continue; if(((act>>(4*i))&15)!=(uint64_t)v) return 0; } return 1; }
static int cmp_limbs(const uint32_t*act,int nl,const char*exp){ int n=strlen(exp); for(int i=0;i<n;i++){int v=hexval(exp[n-1-i]); if(v<0)continue; int bit=4*i; uint32_t a=(bit/32<nl)?(act[bit/32]>>(bit%32))&15:0; if((int)a!=v) return 0;} return 1; }
int main(int argc,char**argv){
  FILE*f=fopen(argv[1],"r"); if(!f){perror("vectors");return 2;}
  state_t st; inputs_t in; outputs_t out; memset(&in,0,sizeof in); sm_reset(&st);
  char exv[8],exd[80],rsr[8],e_exr[8],e_rsv[8],e_rsd[40],e_brv[8],e_brw[8],e_brt[8],e_brd[16],e_trap[8],e_mret[8],e_cause[8];
  int cyc=0,bad=0,fires=0,brs=0;
  while(fscanf(f,"%7s %79s %7s %7s %7s %39s %7s %7s %7s %15s %7s %7s %7s",exv,exd,rsr,e_exr,e_rsv,e_rsd,e_brv,e_brw,e_brt,e_brd,e_trap,e_mret,e_cause)==13){
    in._reset = (cyc<2)?1:0;           // oracle: reset high for lines 0-1
    in._ex_valid = hexval(exv[0])>0?1:0; in._rs_ready = hexval(rsr[0])>0?1:0;
    parse_hex(exd,in._ex_data,9,NULL);
    if(cyc==0) sm_clock(&st,&in);         // the oracle's first posedge (5 ns) precedes its row-0 sample (11 ns)
    memset(&out,0,sizeof out); sm_comb(&st,&in,&out);
    {
      int ok=1;
      ok &= cmp_nib(out._ex_ready,e_exr) && cmp_nib(out._rs_valid,e_rsv) && cmp_nib(out._br_valid,e_brv);
      if(hexval(e_rsv[0])==1){ fires++; ok &= cmp_limbs(out._rs_data,4,e_rsd); }
      if(hexval(e_brv[0])==1){ brs++; ok &= cmp_nib(out._br_taken,e_brt) && cmp_nib(out._br_dest,e_brd) && cmp_nib(out._br_wid,e_brw) && cmp_nib(out._br_is_trap,e_trap) && cmp_nib(out._br_is_mret,e_mret) && cmp_nib(out._br_trap_cause,e_cause); }
      if(!ok){ bad++; if(bad<=5) printf("cycle %d: mismatch (ex_ready=%llu rs_valid=%llu br_valid=%llu rs_data=%08x%08x%08x%08x exp %s %s %s %s)\n",cyc,(unsigned long long)out._ex_ready,(unsigned long long)out._rs_valid,(unsigned long long)out._br_valid,out._rs_data[3],out._rs_data[2],out._rs_data[1],out._rs_data[0],e_exr,e_rsv,e_brv,e_rsd); }
    }
    sm_clock(&st,&in); cyc++;
  }
  printf("%s: %d cycles, %d results, %d branches, %d mismatches\n", bad?"FAIL":"PASS", cyc, fires, brs, bad);
  return bad?1:0;
}
