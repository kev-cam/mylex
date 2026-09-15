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

## The event-driven actor register on the REAL netlists (`actor_sim.py`)

`async_vs_sync.c` proves the principle abstractly; `actor_sim.py` realizes it on
the actual mapped Vortex gate netlists (the same `write_json` `map_ncl.py`
consumes) and verifies it. Two engines over the netlist:

- **oblivious**: every cycle, evaluate every comb gate (topological) and clock
  every register — (#gates + #regs)/cycle, the sync/`ncl_dff` cost.
- **actor**: event-driven. A comb gate re-evaluates only when an input changed;
  **a register is an ACTOR that fires only when its D input changed since it last
  captured** — idle registers cost zero. Work = (changed gates + fired regs).

Both produce the **identical** output trace (verified every cycle) — a pure work
reduction. Two correctness subtleties the verification caught and fixed: (1) the
clock tick must be **two-phase** (capture all D pre-edge, then apply all Q) or a
shift path `R2.D=R1.Q` reads R1's new Q; (2) a register must be dirtied when its
D net changes for **any** reason — a D fed directly by a primary input or another
register's Q, not just by a gate output.

**Measured (work = evaluations, the fundamental activity metric):**

| design | activity | oblivious | actor | fewer evals |
|---|--:|--:|--:|--:|
| `alu_top` (4.5k gates, 188 regs) | 1.8% | 4.72M | 34k | **54.8×** |
| `alu_top` | 9.6% | 4.72M | 222k | 10.4× |
| `exec_top` Tier A (37k gates, 3.8k regs) | 2.1% | 8.18M | 176k | **46.5×** |
| `exec_top` Tier A | 8.5% | 8.18M | 696k | 11.7× |
| `exec_top` Tier A | 27% | 8.18M | 2.23M | 3.7× |

On real Vortex logic the actor form does **work proportional to activity** while
staying bit-exact — the **event-driven actor register, realized and verified**.
The mapped netlists' `ncl_dff` is still the clocked sync-emulation form (the
oblivious cost); the production step is to run the netlist through an actor
runtime like this (compiled — the C/GPU form, cf. gpubuild) instead of clocked
`ncl_dff`, turning "mapped + verified" into "faster than sync". `actor_sim.py`
is the correctness-proving prototype of that runtime.

Usage: `actor_sim.py <netlist.json> <top> [cycles] [activity]`.
