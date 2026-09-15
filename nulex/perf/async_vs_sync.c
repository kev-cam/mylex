/* nulex/perf/async_vs_sync.c — quantify the async-vs-sync work difference on a
 * design of many units that work in PARALLEL with other (often idle) work.
 *
 * Model: K independent units, each an L-stage pipeline (a shift register of
 * {valid,data} slots). A deterministic workload injects `lambda` jobs/cycle into
 * random units. A job flows through the L stages over L cycles, then exits.
 * Different units are busy at different times -- the Vortex execute stage in
 * miniature (ALU busy while the FPU idles, etc.).
 *
 *   SYNC  (clock-driven, what stock sim does): the clock wakes every flop, so
 *         EVERY stage of EVERY unit is evaluated every cycle -- K*L per cycle,
 *         independent of activity. Also pays an O(K) per-cycle scan.
 *   ASYNC (event-driven, idle-costs-zero): a WORKLIST holds only the units that
 *         currently hold in-flight data. Each cycle it evaluates just those (plus
 *         the freshly-injected ones) and drops a unit when it drains -- no O(K)
 *         scan. Work = (active units)*L.
 *
 * Both engines produce the SAME exit stream (order-independent checksum, verified)
 * -- a pure speed difference. The async win is 1/utilization.
 *
 * cc -O2 -o async_vs_sync async_vs_sync.c && ./async_vs_sync
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

#define K   1024        /* parallel units          */
#define L   8           /* pipeline depth per unit */
#define T   200000      /* cycles simulated        */

typedef struct { uint8_t valid; uint32_t data; } slot_t;

static uint64_t rng;
static inline uint32_t xr(void){ rng^=rng<<13; rng^=rng>>7; rng^=rng<<17; return (uint32_t)rng; }
static inline uint64_t exitmix(uint64_t c,uint32_t u,uint32_t out){   /* commutative: order-independent */
    return ((c*K+u)*2654435761u) ^ ((uint64_t)out*2246822519u);
}
/* shift one unit; *oval/*out = the job leaving stage L-1; returns still-busy. */
static inline int step_unit(slot_t *st, int inject, uint32_t indata, uint32_t *out, uint8_t *oval){
    *oval = st[L-1].valid; *out = st[L-1].data;
    for (int i = L-1; i > 0; i--) st[i] = st[i-1];
    st[0].valid = inject; st[0].data = indata;
    int busy = 0; for (int i = 0; i < L; i++) busy |= st[i].valid;
    return busy;
}
static double now(void){ struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return t.tv_sec+t.tv_nsec*1e-9; }

/* SYNC: every unit every cycle. */
static uint64_t sim_sync(uint64_t seed, int lambda, uint64_t *cksum){
    static slot_t st[K][L]; static uint8_t ij[K]; static uint32_t id[K];
    memset(st,0,sizeof st); uint64_t ops=0,cks=0; rng=seed;
    for (uint64_t c=0;c<T;c++){
        memset(ij,0,sizeof ij);
        for (int j=0;j<lambda;j++){ int u=xr()%K; ij[u]=1; id[u]=xr(); }
        for (int u=0;u<K;u++){
            uint32_t out; uint8_t ov;
            step_unit(st[u], ij[u], id[u], &out, &ov);
            ops += L;
            if (ov) cks += exitmix(c,u,out);
        }
    }
    *cksum=cks; return ops;
}
/* ASYNC: worklist of active units; evaluate only those + fresh injections. */
static uint64_t sim_async(uint64_t seed, int lambda, uint64_t *cksum){
    static slot_t st[K][L]; static int list[K]; static uint8_t inl[K], ijf[K]; static uint32_t ijd[K];
    memset(st,0,sizeof st); memset(inl,0,sizeof inl); memset(ijf,0,sizeof ijf);
    int nl=0; uint64_t ops=0,cks=0; rng=seed;
    for (uint64_t c=0;c<T;c++){
        for (int j=0;j<lambda;j++){
            int u=xr()%K; uint32_t d=xr();
            ijd[u]=d; ijf[u]=1;
            if(!inl[u]){ list[nl++]=u; inl[u]=1; }
        }
        int w=0;
        for (int i=0;i<nl;i++){
            int u=list[i]; uint32_t out; uint8_t ov;
            int busy = step_unit(st[u], ijf[u], ijd[u], &out, &ov);
            ijf[u]=0; ops += L;
            if (ov) cks += exitmix(c,u,out);
            if (busy) list[w++]=u; else inl[u]=0;       /* drop drained units */
        }
        nl=w;
    }
    *cksum=cks; return ops;
}

int main(void){
    printf("K=%d units, L=%d stages, T=%d cycles (sync does K*L=%d flop-evals/cycle regardless of activity)\n\n",
           K, L, T, K*L);
    printf("%8s %14s %14s %8s %9s %9s %8s  %s\n",
           "inj/cyc","sync_ops","async_ops","active%","sync_ms","async_ms","wall_spd","equiv");
    int rates[]={1,2,4,8,16,32,64,128,256,512,1024};
    for (unsigned r=0;r<sizeof rates/sizeof*rates;r++){
        int lambda=rates[r]; uint64_t seed=0x9e3779b97f4a7c15ull, cs, ca;
        double t0=now(); uint64_t sops=sim_sync (seed,lambda,&cs); double t1=now();
        double t2=now(); uint64_t aops=sim_async(seed,lambda,&ca); double t3=now();
        printf("%8d %14llu %14llu %7.1f%% %9.1f %9.1f %7.2fx  %s\n",
               lambda,(unsigned long long)sops,(unsigned long long)aops,
               100.0*aops/sops,(t1-t0)*1e3,(t3-t2)*1e3,(t1-t0)/(t3-t2),
               cs==ca?"OK":"*** MISMATCH ***");
    }
    printf("\nasync work scales with ACTIVITY, sync with SIZE; async speed-up = 1/utilization.\n"
           "Both compute the identical exit stream. This is the 'units work in parallel with\n"
           "idle work' case -- e.g. the Vortex FPU's 10.6k flops idle while the ALU runs.\n");
    return 0;
}
