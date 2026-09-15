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

## The COMPILED actor runtime (`map_actor_c.py`) — real wall-clock

`actor_sim.py` is Python, so it measures evaluation *count*, not time.
`map_actor_c.py` is the compiled form: it codegens a self-contained C simulator
from the same gate netlist (netlist baked in as static arrays; `gcc -O2`), with
the identical two engines — oblivious (every gate + every register each cycle)
and actor (event-driven; a register fires only when its D changed). Verified
three ways: C-oblivious == the Python oblivious (`check` mode vs a dumped
stimulus/trace — codegen fidelity), C-actor == C-oblivious (the `verify` sweep),
and the Python actor == Python oblivious (above). `run_actor_rt.sh <json> <top>`
runs all of it.

**Wall-clock, `gcc -O2` (this box):**

| design | activity | oblivious | actor | **wall speed-up** |
|---|--:|--:|--:|--:|
| `alu_top` (4.5k gates, 188 regs) | 0.002% | 930 ms | 44 ms | **20.9×** |
| `alu_top` | 1.1% | 852 ms | 63 ms | **13.5×** |
| `alu_top` | 2.2% | 964 ms | 113 ms | 8.5× |
| `alu_top` | 22% | 962 ms | 807 ms | 1.2× |
| `exec_top` Tier A (37k gates, 3.8k regs) | 0.07% | 1685 ms | 48 ms | **35×** |
| `exec_top` Tier A | 1.5% | 1234 ms | 76 ms | **16.2×** |
| `exec_top` Tier A | 4% | 1357 ms | 229 ms | 5.9× |
| `exec_top` Tier A | 20% | 1802 ms | 888 ms | 2.0× |
| `exec_top` Tier A | 42% | 1712 ms | 1771 ms | 0.97× (crossover) |

So the Python eval-count reduction **is real wall-clock**: 20–35× at the
single-fraction-of-a-percent activity typical of an idle-heavy design, and the
register-heavy exec wins *more* than the ALU (3.8k flops skipped). Honest tail:
at very high activity (every input toggling every cycle) the actor **thrashes**
— re-evaluating cones many times per settle — and is 30–100× *slower*; crossover
is ~25–42% activity. The actor form is the right engine precisely for the
low-activity regime (Vortex, GPU RTL), and the wrong one for saturated logic.

**This is the payoff step** the async work was aiming at: the mapped Vortex
netlists, run through this compiled event-driven engine instead of a clocked
`ncl_dff`, execute in time proportional to their activity — faster than sync
wherever the design is mostly idle, and provably bit-identical.

## Real activity under a program (`measure_activity.py`)

Synthetic random-toggle activity is a knob; a real program is the answer. This
drives the mapped ALU with its actual vvp-oracle instruction stream (`probes/
alutest/vectors.txt` — 42 real ADD/SUB/SLT/AND/OR/XOR/SLL/SRL/branch ops) and
measures the true activity, then replays the same instructions with idle cycles
inserted to model GPGPU issue rates (memory-bound → low IPC → execute stage idle
most cycles). The actor's work is **instruction-bound, not cycle-bound** (a
constant ~61k evals regardless of the idle gaps — idle cycles cost it nothing):

| workload | IPC | activity | work speed-up |
|---|--:|--:|--:|
| dense stress test | 1.0 | **29.5%** | 3.4× |
| moderate | 0.25 | 7.6% | 13× |
| memory-bound GPU | 0.125 | 3.8% | 26× |
| heavily stalled | 0.06 | 1.9% | 52× |

Even a *dense* instruction stream is only ~30% active (wide datapath, few bits
toggle per op); realistic memory-bound GPGPU execution lands in the **1–8%
active / 13–52× region**. All rows verified `actor == oblivious`.

## Two forms, two substrates — the `ncl_dff` form is the GPU/FPGA target

The event-driven actor and the dense `ncl_dff` are **complementary bindings of
the same mapped netlist**, and the dense one is not a dead end:

| form | substrate | wins by | regime |
|---|---|---|---|
| `ncl_dff` dense (sync-emulation) | **GPU / FPGA** | many-instance parallelism (SIMT / hardware) | throughput, any activity |
| actor (event-driven) | **CPU** | idle-skipping | single instance, low activity |

The dense form does fixed work every cycle — regular, branch-free, data-parallel
— ideal for GPU SIMT (batch thousands of instances, no divergence, exactly
`gpubuild`'s SoA farm) and for FPGA (it *is* the synchronous circuit). On SIMT
the divergence cost of the actor's dynamic worklist *exceeds* the idle-skip
benefit — which is why `GPU-SIM.md` recommends "events become data, fixed-shape
batches", not a ported event queue. The actor form is the CPU single-/few-
instance low-activity engine. Same netlist; pick the engine for the substrate.
