#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#define SM_NO_MAIN
#include "execA.c"

static int hv(char ch){ if(ch>='0'&&ch<='9')return ch-'0'; if(ch>='a'&&ch<='f')return ch-'a'+10; if(ch>='A'&&ch<='F')return ch-'A'+10; return -1; }
// hex (MSB first) -> limbs; x nibbles read as 0 (inputs never contain x by construction)
static void set_limbs(const char*s,uint32_t*l,int nl){ int n=strlen(s); memset(l,0,4*nl); for(int i=0;i<n;i++){int v=hv(s[n-1-i]); if(v<0)v=0; int b=4*i; if(b/32<nl) l[b/32]|=(uint32_t)v<<(b%32);} }
static uint64_t hex64(const char*s){ uint64_t v=0; for(const char*p=s;*p;p++){int d=hv(*p); v=(v<<4)|(d<0?0:d);} return v; }
// compare a w-bit value (limbs, LSB limb first) with a %b string (MSB first); x = dont care
static int cmp_bits(const uint32_t*l,int w,const char*s,int*firstbad){ int n=strlen(s); if(n<w) return 0; for(int i=0;i<w;i++){ char e=s[n-1-i]; if(e=='x'||e=='X'||e=='z'||e=='Z') continue; int a=(l[i/32]>>(i%32))&1; if(a!=(e=='1')){ *firstbad=i; return 0;} } return 1; }
int main(int argc,char**argv){ FILE*f=fopen(argv[1],"r"); if(!f){perror("vectors");return 2;}
  state_t st; inputs_t in; outputs_t out; memset(&in,0,sizeof in); sm_reset(&st);
  static char tok[75][2048]; int cyc=0,bad=0; char line[65536];
  while(fgets(line,sizeof line,f)){ int nt=0; char*p=strtok(line," \n"); while(p&&nt<75){ strncpy(tok[nt++],p,2047); p=strtok(NULL," \n"); } if(nt!=75){ fprintf(stderr,"line %d: %d tokens\n",cyc,nt); return 2; }
    in._reset = hex64(tok[0]);
    in._lsu_client_if_0_req_ready = hex64(tok[1]);
    in._lsu_client_if_0_rsp_valid = hex64(tok[2]);
    set_limbs(tok[3], in._lsu_client_if_0_rsp_data, 5);
    in._dispatch_if_0_valid = hex64(tok[4]);
    set_limbs(tok[5], in._dispatch_if_0_data, 9);
    in._dispatch_if_1_valid = hex64(tok[6]);
    set_limbs(tok[7], in._dispatch_if_1_data, 9);
    in._dispatch_if_2_valid = hex64(tok[8]);
    set_limbs(tok[9], in._dispatch_if_2_data, 9);
    in._commit_if_0_ready = hex64(tok[10]);
    in._commit_if_1_ready = hex64(tok[11]);
    in._commit_if_2_ready = hex64(tok[12]);
    in._sched_csr_if_cycles = hex64(tok[13]);
    in._sched_csr_if_instret = hex64(tok[14]);
    in._sched_csr_if_active_warps = hex64(tok[15]);
    in._sched_csr_if_thread_masks = hex64(tok[16]);
    in._sched_csr_if_mscratch = hex64(tok[17]);
    set_limbs(tok[18], in._sched_csr_if_cta_csrs, 11);
    in._sched_csr_if_cta_lane = hex64(tok[19]);
    in._sched_csr_if_csr_mstatus = hex64(tok[20]);
    in._sched_csr_if_csr_mtvec = hex64(tok[21]);
    in._sched_csr_if_csr_mepc = hex64(tok[22]);
    in._sched_csr_if_csr_mcause = hex64(tok[23]);
    in._sched_csr_if_csr_mtval = hex64(tok[24]);
    in._warp_ctl_if_bar_phase = hex64(tok[25]);
    in._warp_ctl_if_warp_pending_alm_empty = hex64(tok[26]);
    in._warp_ctl_if_lsu_sched_drained = hex64(tok[27]);
    in._warp_ctl_if_dvstack_ptr = hex64(tok[28]);
    in._dcr_csr_if_valid = hex64(tok[29]);
    in._dcr_csr_if_addr = hex64(tok[30]);
    in._dcr_csr_if_mpm_class = hex64(tok[31]);
    // pre-history of the exectest oracle (tb_exec.sv.in: `reg clk = 0; always #5 clk = ~clk`, reset = 1 from t0,
    // row 0 driven from t0, recorder at negedge+1 ns): the first rising edge at 5 ns precedes the row-0 sample
    // at 11 ns, so row k is compared after k+1 posedges with inputs in0, in0, in1, ..., in(k-1). Replay that edge.
    if(cyc==0) sm_clock(&st,&in);
    memset(&out,0,sizeof out); sm_comb(&st,&in,&out);
    { int fb; uint32_t tmp[64];
      tmp[0]=(uint32_t)out._lsu_client_if_0_req_valid; tmp[1]=(uint32_t)(out._lsu_client_if_0_req_valid>>32); if(!cmp_bits(tmp,1,tok[32],&fb)){ bad++; if(bad<=8) printf("cycle %d: lsu_client_if_0_req_valid mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._lsu_client_if_0_req_valid,tok[32]); }
      if(!cmp_bits(out._lsu_client_if_0_req_data,221,tok[33],&fb)){ bad++; if(bad<=8) printf("cycle %d: lsu_client_if_0_req_data mismatch (bit %d) exp=%s\n",cyc,fb,tok[33]); }
      tmp[0]=(uint32_t)out._lsu_client_if_0_rsp_ready; tmp[1]=(uint32_t)(out._lsu_client_if_0_rsp_ready>>32); if(!cmp_bits(tmp,1,tok[34],&fb)){ bad++; if(bad<=8) printf("cycle %d: lsu_client_if_0_rsp_ready mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._lsu_client_if_0_rsp_ready,tok[34]); }
      tmp[0]=(uint32_t)out._dispatch_if_0_ready; tmp[1]=(uint32_t)(out._dispatch_if_0_ready>>32); if(!cmp_bits(tmp,1,tok[35],&fb)){ bad++; if(bad<=8) printf("cycle %d: dispatch_if_0_ready mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._dispatch_if_0_ready,tok[35]); }
      tmp[0]=(uint32_t)out._dispatch_if_1_ready; tmp[1]=(uint32_t)(out._dispatch_if_1_ready>>32); if(!cmp_bits(tmp,1,tok[36],&fb)){ bad++; if(bad<=8) printf("cycle %d: dispatch_if_1_ready mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._dispatch_if_1_ready,tok[36]); }
      tmp[0]=(uint32_t)out._dispatch_if_2_ready; tmp[1]=(uint32_t)(out._dispatch_if_2_ready>>32); if(!cmp_bits(tmp,1,tok[37],&fb)){ bad++; if(bad<=8) printf("cycle %d: dispatch_if_2_ready mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._dispatch_if_2_ready,tok[37]); }
      tmp[0]=(uint32_t)out._commit_if_0_valid; tmp[1]=(uint32_t)(out._commit_if_0_valid>>32); if(!cmp_bits(tmp,1,tok[38],&fb)){ bad++; if(bad<=8) printf("cycle %d: commit_if_0_valid mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._commit_if_0_valid,tok[38]); }
      if(!cmp_bits(out._commit_if_0_data,114,tok[39],&fb)){ bad++; if(bad<=8) printf("cycle %d: commit_if_0_data mismatch (bit %d) exp=%s\n",cyc,fb,tok[39]); }
      tmp[0]=(uint32_t)out._commit_if_1_valid; tmp[1]=(uint32_t)(out._commit_if_1_valid>>32); if(!cmp_bits(tmp,1,tok[40],&fb)){ bad++; if(bad<=8) printf("cycle %d: commit_if_1_valid mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._commit_if_1_valid,tok[40]); }
      if(!cmp_bits(out._commit_if_1_data,114,tok[41],&fb)){ bad++; if(bad<=8) printf("cycle %d: commit_if_1_data mismatch (bit %d) exp=%s\n",cyc,fb,tok[41]); }
      tmp[0]=(uint32_t)out._commit_if_2_valid; tmp[1]=(uint32_t)(out._commit_if_2_valid>>32); if(!cmp_bits(tmp,1,tok[42],&fb)){ bad++; if(bad<=8) printf("cycle %d: commit_if_2_valid mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._commit_if_2_valid,tok[42]); }
      if(!cmp_bits(out._commit_if_2_data,114,tok[43],&fb)){ bad++; if(bad<=8) printf("cycle %d: commit_if_2_data mismatch (bit %d) exp=%s\n",cyc,fb,tok[43]); }
      tmp[0]=(uint32_t)out._sched_csr_if_csr_rd_wid; tmp[1]=(uint32_t)(out._sched_csr_if_csr_rd_wid>>32); if(!cmp_bits(tmp,1,tok[44],&fb)){ bad++; if(bad<=8) printf("cycle %d: sched_csr_if_csr_rd_wid mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._sched_csr_if_csr_rd_wid,tok[44]); }
      tmp[0]=(uint32_t)out._sched_csr_if_csr_rd_cta_id; tmp[1]=(uint32_t)(out._sched_csr_if_csr_rd_cta_id>>32); if(!cmp_bits(tmp,1,tok[45],&fb)){ bad++; if(bad<=8) printf("cycle %d: sched_csr_if_csr_rd_cta_id mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._sched_csr_if_csr_rd_cta_id,tok[45]); }
      tmp[0]=(uint32_t)out._sched_csr_if_csr_wr_valid; tmp[1]=(uint32_t)(out._sched_csr_if_csr_wr_valid>>32); if(!cmp_bits(tmp,1,tok[46],&fb)){ bad++; if(bad<=8) printf("cycle %d: sched_csr_if_csr_wr_valid mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._sched_csr_if_csr_wr_valid,tok[46]); }
      tmp[0]=(uint32_t)out._sched_csr_if_csr_wr_wid; tmp[1]=(uint32_t)(out._sched_csr_if_csr_wr_wid>>32); if(!cmp_bits(tmp,1,tok[47],&fb)){ bad++; if(bad<=8) printf("cycle %d: sched_csr_if_csr_wr_wid mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._sched_csr_if_csr_wr_wid,tok[47]); }
      tmp[0]=(uint32_t)out._sched_csr_if_csr_wr_data; tmp[1]=(uint32_t)(out._sched_csr_if_csr_wr_data>>32); if(!cmp_bits(tmp,32,tok[48],&fb)){ bad++; if(bad<=8) printf("cycle %d: sched_csr_if_csr_wr_data mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._sched_csr_if_csr_wr_data,tok[48]); }
      tmp[0]=(uint32_t)out._sched_csr_if_trap_csr_wr_valid; tmp[1]=(uint32_t)(out._sched_csr_if_trap_csr_wr_valid>>32); if(!cmp_bits(tmp,1,tok[49],&fb)){ bad++; if(bad<=8) printf("cycle %d: sched_csr_if_trap_csr_wr_valid mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._sched_csr_if_trap_csr_wr_valid,tok[49]); }
      tmp[0]=(uint32_t)out._sched_csr_if_trap_csr_wr_addr; tmp[1]=(uint32_t)(out._sched_csr_if_trap_csr_wr_addr>>32); if(!cmp_bits(tmp,12,tok[50],&fb)){ bad++; if(bad<=8) printf("cycle %d: sched_csr_if_trap_csr_wr_addr mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._sched_csr_if_trap_csr_wr_addr,tok[50]); }
      tmp[0]=(uint32_t)out._sched_csr_if_trap_csr_wr_data; tmp[1]=(uint32_t)(out._sched_csr_if_trap_csr_wr_data>>32); if(!cmp_bits(tmp,32,tok[51],&fb)){ bad++; if(bad<=8) printf("cycle %d: sched_csr_if_trap_csr_wr_data mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._sched_csr_if_trap_csr_wr_data,tok[51]); }
      tmp[0]=(uint32_t)out._branch_ctl_if_0_valid; tmp[1]=(uint32_t)(out._branch_ctl_if_0_valid>>32); if(!cmp_bits(tmp,1,tok[52],&fb)){ bad++; if(bad<=8) printf("cycle %d: branch_ctl_if_0_valid mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._branch_ctl_if_0_valid,tok[52]); }
      tmp[0]=(uint32_t)out._branch_ctl_if_0_wid; tmp[1]=(uint32_t)(out._branch_ctl_if_0_wid>>32); if(!cmp_bits(tmp,1,tok[53],&fb)){ bad++; if(bad<=8) printf("cycle %d: branch_ctl_if_0_wid mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._branch_ctl_if_0_wid,tok[53]); }
      tmp[0]=(uint32_t)out._branch_ctl_if_0_taken; tmp[1]=(uint32_t)(out._branch_ctl_if_0_taken>>32); if(!cmp_bits(tmp,1,tok[54],&fb)){ bad++; if(bad<=8) printf("cycle %d: branch_ctl_if_0_taken mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._branch_ctl_if_0_taken,tok[54]); }
      tmp[0]=(uint32_t)out._branch_ctl_if_0_dest; tmp[1]=(uint32_t)(out._branch_ctl_if_0_dest>>32); if(!cmp_bits(tmp,30,tok[55],&fb)){ bad++; if(bad<=8) printf("cycle %d: branch_ctl_if_0_dest mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._branch_ctl_if_0_dest,tok[55]); }
      tmp[0]=(uint32_t)out._branch_ctl_if_0_is_trap; tmp[1]=(uint32_t)(out._branch_ctl_if_0_is_trap>>32); if(!cmp_bits(tmp,1,tok[56],&fb)){ bad++; if(bad<=8) printf("cycle %d: branch_ctl_if_0_is_trap mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._branch_ctl_if_0_is_trap,tok[56]); }
      tmp[0]=(uint32_t)out._branch_ctl_if_0_is_mret; tmp[1]=(uint32_t)(out._branch_ctl_if_0_is_mret>>32); if(!cmp_bits(tmp,1,tok[57],&fb)){ bad++; if(bad<=8) printf("cycle %d: branch_ctl_if_0_is_mret mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._branch_ctl_if_0_is_mret,tok[57]); }
      tmp[0]=(uint32_t)out._branch_ctl_if_0_trap_cause; tmp[1]=(uint32_t)(out._branch_ctl_if_0_trap_cause>>32); if(!cmp_bits(tmp,4,tok[58],&fb)){ bad++; if(bad<=8) printf("cycle %d: branch_ctl_if_0_trap_cause mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._branch_ctl_if_0_trap_cause,tok[58]); }
      tmp[0]=(uint32_t)out._warp_ctl_if_wspawn_valid; tmp[1]=(uint32_t)(out._warp_ctl_if_wspawn_valid>>32); if(!cmp_bits(tmp,1,tok[59],&fb)){ bad++; if(bad<=8) printf("cycle %d: warp_ctl_if_wspawn_valid mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._warp_ctl_if_wspawn_valid,tok[59]); }
      tmp[0]=(uint32_t)out._warp_ctl_if_tmc_valid; tmp[1]=(uint32_t)(out._warp_ctl_if_tmc_valid>>32); if(!cmp_bits(tmp,1,tok[60],&fb)){ bad++; if(bad<=8) printf("cycle %d: warp_ctl_if_tmc_valid mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._warp_ctl_if_tmc_valid,tok[60]); }
      tmp[0]=(uint32_t)out._warp_ctl_if_split_valid; tmp[1]=(uint32_t)(out._warp_ctl_if_split_valid>>32); if(!cmp_bits(tmp,1,tok[61],&fb)){ bad++; if(bad<=8) printf("cycle %d: warp_ctl_if_split_valid mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._warp_ctl_if_split_valid,tok[61]); }
      tmp[0]=(uint32_t)out._warp_ctl_if_sjoin_valid; tmp[1]=(uint32_t)(out._warp_ctl_if_sjoin_valid>>32); if(!cmp_bits(tmp,1,tok[62],&fb)){ bad++; if(bad<=8) printf("cycle %d: warp_ctl_if_sjoin_valid mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._warp_ctl_if_sjoin_valid,tok[62]); }
      tmp[0]=(uint32_t)out._warp_ctl_if_bar_valid; tmp[1]=(uint32_t)(out._warp_ctl_if_bar_valid>>32); if(!cmp_bits(tmp,1,tok[63],&fb)){ bad++; if(bad<=8) printf("cycle %d: warp_ctl_if_bar_valid mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._warp_ctl_if_bar_valid,tok[63]); }
      tmp[0]=(uint32_t)out._warp_ctl_if_wsync_valid; tmp[1]=(uint32_t)(out._warp_ctl_if_wsync_valid>>32); if(!cmp_bits(tmp,1,tok[64],&fb)){ bad++; if(bad<=8) printf("cycle %d: warp_ctl_if_wsync_valid mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._warp_ctl_if_wsync_valid,tok[64]); }
      tmp[0]=(uint32_t)out._warp_ctl_if_wid; tmp[1]=(uint32_t)(out._warp_ctl_if_wid>>32); if(!cmp_bits(tmp,1,tok[65],&fb)){ bad++; if(bad<=8) printf("cycle %d: warp_ctl_if_wid mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._warp_ctl_if_wid,tok[65]); }
      tmp[0]=(uint32_t)out._warp_ctl_if_wspawn; tmp[1]=(uint32_t)(out._warp_ctl_if_wspawn>>32); if(!cmp_bits(tmp,32,tok[66],&fb)){ bad++; if(bad<=8) printf("cycle %d: warp_ctl_if_wspawn mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._warp_ctl_if_wspawn,tok[66]); }
      tmp[0]=(uint32_t)out._warp_ctl_if_tmc; tmp[1]=(uint32_t)(out._warp_ctl_if_tmc>>32); if(!cmp_bits(tmp,2,tok[67],&fb)){ bad++; if(bad<=8) printf("cycle %d: warp_ctl_if_tmc mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._warp_ctl_if_tmc,tok[67]); }
      tmp[0]=(uint32_t)out._warp_ctl_if_split; tmp[1]=(uint32_t)(out._warp_ctl_if_split>>32); if(!cmp_bits(tmp,35,tok[68],&fb)){ bad++; if(bad<=8) printf("cycle %d: warp_ctl_if_split mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._warp_ctl_if_split,tok[68]); }
      tmp[0]=(uint32_t)out._warp_ctl_if_sjoin; tmp[1]=(uint32_t)(out._warp_ctl_if_sjoin>>32); if(!cmp_bits(tmp,3,tok[69],&fb)){ bad++; if(bad<=8) printf("cycle %d: warp_ctl_if_sjoin mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._warp_ctl_if_sjoin,tok[69]); }
      tmp[0]=(uint32_t)out._warp_ctl_if_bar; tmp[1]=(uint32_t)(out._warp_ctl_if_bar>>32); if(!cmp_bits(tmp,13,tok[70],&fb)){ bad++; if(bad<=8) printf("cycle %d: warp_ctl_if_bar mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._warp_ctl_if_bar,tok[70]); }
      tmp[0]=(uint32_t)out._warp_ctl_if_bar_addr; tmp[1]=(uint32_t)(out._warp_ctl_if_bar_addr>>32); if(!cmp_bits(tmp,4,tok[71],&fb)){ bad++; if(bad<=8) printf("cycle %d: warp_ctl_if_bar_addr mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._warp_ctl_if_bar_addr,tok[71]); }
      tmp[0]=(uint32_t)out._warp_ctl_if_dvstack_wid; tmp[1]=(uint32_t)(out._warp_ctl_if_dvstack_wid>>32); if(!cmp_bits(tmp,1,tok[72],&fb)){ bad++; if(bad<=8) printf("cycle %d: warp_ctl_if_dvstack_wid mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._warp_ctl_if_dvstack_wid,tok[72]); }
      tmp[0]=(uint32_t)out._dcr_csr_if_value; tmp[1]=(uint32_t)(out._dcr_csr_if_value>>32); if(!cmp_bits(tmp,32,tok[73],&fb)){ bad++; if(bad<=8) printf("cycle %d: dcr_csr_if_value mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._dcr_csr_if_value,tok[73]); }
      tmp[0]=(uint32_t)out._dcr_csr_if_ready; tmp[1]=(uint32_t)(out._dcr_csr_if_ready>>32); if(!cmp_bits(tmp,1,tok[74],&fb)){ bad++; if(bad<=8) printf("cycle %d: dcr_csr_if_ready mismatch (bit %d) act=%016llx exp=%s\n",cyc,fb,(unsigned long long)out._dcr_csr_if_ready,tok[74]); }
    }
    sm_clock(&st,&in); cyc++; }
  printf("%s: %d cycles replayed through the gen_statemachine model, %d mismatches\n", bad?"FAIL":"PASS", cyc, bad); return bad?1:0; }
