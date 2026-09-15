# nulex/perf — async vs sync simulation speed

Quantifies the core reason an async form can out-run synchronous simulation:
**sync work scales with design SIZE, async work with ACTIVITY.** A clock wakes
every flop every cycle whether or not its data changed (stock clock-driven sim
does O(#flops)/cycle); an event-driven async form advances only the state whose
data actually changed (O(active)/cycle). So on a design that is mostly idle —
many units working in parallel while others wait — async does proportionally
less work.

## The experiment (`async_vs_sync.c`)

K=1024 independent units, each an L=8-stage pipeline; a workload injects `lambda`
jobs/cycle into random units (a job flows through the 8 stages and exits). This
is the Vortex execute stage in miniature: the ALU busy while the FPU/LSU idle.
- **SYNC**: evaluates every stage of every unit every cycle (K·L = 8192
  flop-evals/cycle) — what a clock does.
- **ASYNC**: a worklist holds only units with in-flight data; it evaluates just
  those (plus fresh injections) and drops a unit when it drains — no O(K) scan.

Both engines produce the **identical** exit stream (order-independent checksum,
verified every row).

## Results (`cc -O2`, this box)

| inj/cyc | active% | sync ms | async ms | wall speed-up |
|--:|--:|--:|--:|--:|
| 1   | 0.9%  | 1144 | 19   | **58.9×** |
| 2   | 1.7%  | 1210 | 36   | **33.4×** |
| 4   | 3.5%  | 987  | 54   | **18.2×** |
| 8   | 6.8%  | 1078 | 145  | **7.5×**  |
| 16  | 13.1% | 1175 | 289  | 4.1×  |
| 32  | 24.5% | 1210 | 558  | 2.2×  |
| 64  | 43.0% | 1391 | 1104 | 1.3×  |
| 128 | 67.6% | 1583 | 1835 | 0.86× |
| 256 | 89.5% | 1392 | 2093 | 0.66× |
| 1024| 100%  | 2901 | 4038 | 0.72× |

- **async_ops / sync_ops == active%** exactly — async work is literally the
  activity fraction of sync work; the speed-up is **1/utilization**.
- **Wall-clock crossover ≈ 50% active.** Below it async wins (7–59× in the
  single-digit-% regime); above it the event-bookkeeping overhead makes async
  ~1.4× *slower*. Async is not free — it pays per active unit, so it only wins
  when enough of the design is idle. (Matches the pull-eval crossover in
  `bfit/prototypes/demand_driven_eval.md`.)

## What this means for the mapped Vortex NCL netlists

The win is real **only for an event-driven register**. The `ncl_dff` in the
current netlists is the *sync-emulation* binding — a clocked flop that fires
every cycle, so it does **not** skip idle work; the mapped netlists as-simulated
sit at the "100%" row. Realizing the speed-up needs the **event-driven actor
register**: state that advances on a DATA-change/completion token rather than a
global clock (the true QDI register, or an actor-network runtime). That is the
bridge from "mapped, verified" to "faster than sync", and the next build step
this measurement motivates.

Vortex is a good target: it is low-activity (the gpubuild `GSM_GATED` result
noted "GPU RTL is low-activity"), and its execute stage has 10.6k FPU flops that
idle while the ALU runs — squarely in the left, high-speed-up part of the table.
