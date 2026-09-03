# Event-Driven Mixed-Signal Simulation on GPUs — Synthesis Memo

*2026-09-01 · companion to `ASYNC-PLAN.md` §7 · four independent research
sweeps synthesized; claims carry their originating angle (R1–R4). Sourced
but not yet adversarially verified — verify the tools table before adopting.*

*Synthesized from four research angles: R1 = GPU-accelerated SPICE, R2 = discrete-event simulation on GPUs, R3 = SNN simulators on GPUs, R4 = mixed-signal semantics on data-parallel hardware.*

## 1. What maps well to GPUs, and why

**Regular, fixed-shape numerics between events.** All four researchers converge: commercial GPU SPICE (Spectre X, PrimeSim, ALPS-GT; 5–30x) offloads only matrix solve and device evaluation, never timestep/event control (R1). Device-model evaluation and matrix stamping are embarrassingly parallel; repeated solves with fixed sparsity patterns suit cuDSS hot-start reuse (R1: Honeywell up to 200x hot-start).

**Many-instance batching is the durable 100x win.** Thousands of independent small circuits — Monte Carlo, corners, mismatch, seeds — run one-per-thread/block with state in registers: TinySPICE 138x (R1), RTLflow 40x at 65,536 stimuli (R2), MPGOS/DiffEqGPU.jl ensemble kernels (R4), GeNN batch mode (R4). This is structurally identical to an SNN array of identical leaky-integrator ODEs (R1, R3).

**Lockstep ODE integration with events demoted to data.** Every production GPU SNN simulator (GeNN, Brian2CUDA, NEST GPU) integrates all neurons each step, detects threshold crossings in parallel, and builds spike lists with atomics (R3). Crucially, LI/LIF dynamics are linear time-invariant, so the subthreshold update is *exact* via closed-form exponential (Rotter–Diesmann); dt only quantizes event times (R3). Scale: 4.13M neurons / 24.2B synapses on one GPU (GeNN, Nat. Comput. Sci. 2021).

**Threshold-cross (`@cross`) semantics survive batching.** Two mechanisms (R3, R4): per-step grid check (quantized), or batched Newton root-finding for exact crossing times (Diffrax/Eventax, MPGOS) — replacing analog step-rejection with per-trajectory root solves, paying only warp divergence.

**Statically compiled synchronous logic.** Queue-free restructurings (oblivious evaluation, 0-delay + re-simulation, emulator-style VLIW mapping) give GEM 6x over 8-thread Verilator single-instance and GL0AM 19–537x delay-annotated (R2).

## 2. What maps badly, and why

**The event queue itself.** Centralized timestamp-ordered priority queues serialize, diverge warps, and need dynamic device memory; queue-preserving GPU DES plateaued at 10–30x by 2010 and the field abandoned it (R2). No commercial fastSPICE/event-driven engine is GPU-accelerated anywhere (R1); no big-three digital simulator runs on GPU (R2).

**The Verilog-AMS analog/digital negotiation loop.** Per-instance bidirectional timestep negotiation — solver stops pinned to digital events, `@cross` step-rejection and re-solve — is serial, data-dependent, and latency-bound across PCIe. No published GPU-resident AMS engine exists as of 2026 (R4).

**Single-netlist sparse LU at small-to-mid sizes.** Circuit matrices are too sparse/irregular; CPU KLU wins below thousands of nodes (R1). Our per-island matrices are tiny — dense per-instance solves, not sparse LU, are the right shape.

**Heterogeneous per-arc delays.** Brian2CUDA measures roughly an order of magnitude penalty for per-synapse (SPEF-like) delays vs homogeneous, requiring per-delay spike queues and synapse-bundle blocking (R3).

**Small circuits, single runs.** GPU crossover sits at ~1e4–1e5 concurrent units or large batches; below that CPU wins (R3: Brian2CUDA 2–3x slower under 1e4 neurons; R1: VAJAX loses to CPU VACASK on small circuits).

**Resolved contradictions.** (a) GATSPI: R4 calls it "conservative event-driven with SDF"; R2's description (oblivious 0-delay cycle evaluation for power/glitch, PyTorch kernels) matches the paper — we adopt R2's. Both agree it is unreleased. (b) GEM speedup: R4's "64x single-stimulus" is a best case; R2's averages (6x vs Verilator-8T, 9x vs commercial, ~20x at 670k gates shrinking to 2.5x at 5.5M) are the planning numbers. (c) RTLflow license: both R2 and R4 flag MIT-vs-LGPL ambiguity — verify before forking.

## 3. Tools worth reusing

| Tool | Role for us | License | Runs on Vast.AI? |
|---|---|---|---|
| VAJAX (ChipFlow) | Verilog-A→OpenVAF→JAX GPU SPICE; corner/PVT batching (R1) | Apache-2.0 | Yes (CUDA 12; FP64 → rent A100/H100) |
| GeNN/PyGeNN | Codegen GPU SNN; sim-code+threshold+reset ≈ AMS primitive; batch mode (R3, R4) | LGPL-2.1 | Yes (needs nvcc) |
| Brian2CUDA | Reference design for per-delay spike queues / synapse bundles (R3) | GPL-3.0 | Yes (pip) |
| NEST GPU | Exact-integration LIF at scale, on-GPU construction (R3) | GPL-2+ | Yes |
| Diffrax + Eventax | Batched Newton root-finding for exact crossing times; differentiable (R3, R4) | Apache-2.0 | Yes (pip) |
| jaxsnn | Event-driven JAX + EventProp exact gradients, built for analog LIF hardware (R3) | LGPL | Yes |
| DiffEqGPU.jl / MPGOS | Per-thread ensemble ODE solves with event handling (R4) | MIT | Yes (MPGOS stale ~2021) |
| GEM (NVlabs) | Best open GPU logic sim; AIG→virtual VLIW (R2) | Apache-2.0 | Yes |
| GL0AM (NVlabs) | Delay-annotated GPU gate sim; single-clock only — blocks raw NCL (R2) | Open repo | Partly (proprietary compile-flow deps) |
| RTLflow | Batch-stimulus RTL→CUDA pattern (R2, R4) | MIT/LGPL unclear | Yes, research-grade |
| Verilator (+ process farms) | Honest CPU baseline; sync-emulation NCL runs (R2) | LGPL/Artistic | Yes (CPU cores) |
| cocotbext-ams + NVC | Host digital/analog sync contract (crossing-triggered sync + max interval); seam for a GPU backend (R4) | BSD-3 | Yes (CPU side) |
| ngspice + OpenVAF/OSDI; Xyce; VACASK | CPU accuracy oracles for golden traces (R1, R4) | BSD-ish/GPL-3 | Yes (CPU; no GPU benefit) |
| NVIDIA cuDSS | GPU sparse solver if parasitic networks grow >~few k nodes (R1) | Free binary | Yes (pip/conda) |
| GATSPI | Paper-only recipe (PyTorch oblivious gate eval) (R2) | Not released | No |
| Spectre X / PrimeSim GPU / ALPS-GT | Market validation only (R1) | Commercial, license servers | **No** |
| SpikingJelly | Fastest PyTorch SNN kernels (R3) | Partial non-commercial | Technically yes; legal review first |

## 4. Recommended architecture

**Principle (unanimous): never port the event queue; events become data, execution becomes fixed-shape batches. Event control stays on the host.**

- **NCL tier:** the DATA/NULL handshake alternation *is* a logical clock — exploit it as the oblivious/phase schedule GPU logic sims require. Keep single-run async simulation on the NVC-fork CPU event kernel; evaluate GEM for phase-batched GPU runs, modeling state-holding TH gates as explicit latch primitives or iterating delta-batches to fixed point per wavefront (R2). Delay-annotated async GPU sim (CMB-style) has a 10–30x ceiling — poor ROI (R2).
- **AMS/LIF ODE islands:** mylex emits primitives in the OpenVAF-compilable Verilog-A subset once; CPU path (ngspice/VACASK, NVC+islands) is the golden oracle, GPU path is a generated batched kernel (PyGeNN or JAX/Diffrax) using exact exponential subthreshold updates plus closed-form or batched-Newton crossing times. Threshold events are collected per window as arrays and returned to the host kernel — the cocotbext-ams contract generalized to ensembles: advance all N instances to the conservative window boundary (min next digital event time), return per-instance crossings, re-solve short windows from checkpoints instead of rollback (R4).
- **Monte-Carlo batching is the primary GPU payoff:** the SPEF-annotated statistical tier runs 1e4–1e6 parameter/mismatch/corner instances per GPU — the proven 70–138x regime (R1, R4). Copy Brian2CUDA's per-delay queue design for per-arc delays (R3). Use VAJAX for batched-SPICE spot checks; consider upstreaming SNN-shaped features rather than building a full engine (R1). The concrete port target is **stat-sim** (`/usr/local/src/stat-sim`): its generated models are analytical/event-driven *by construction* — metastability as a mid-rail plateau of duration Exp(tau) then resolution, probability waveforms emerging from Monte-Carlo aggregation — so `ensemble.py` is the batching seam and no solver enters the loop.
- **Vast.AI practicalities:** everything load-bearing is open-source, no license servers. Rent A100/H100 for FP64 stacks, or engineer FP32/mixed precision (consumer RTX throttles FP64 to 1/64) (R1).

## 4a. Already in practice: `sv2ghdl/gpubuild`

*Added 2026-09-03.* The many-instance batching this memo recommends is not
hypothetical in the stack: `sv2ghdl/gpubuild/` compiles `gen_statemachine`
single-cycle models into CUDA "farm" fat binaries in a pinned container (no
CUDA install on the build host), ships only binaries to any GPU host or a
Vast.AI session (`build_farm.sh`, `ship_run.sh`, `vast_run.sh`), and
certifies results by checksum. That is the compiled-synchronous-model
member of the §4 architecture; the analytical stat-sim engine and the NCL
phase-batched tier are the two members still to build.

## 5. Analyticity of the primitive set (verified)

*Added 2026-09-01, verified against github.com/neuromorphs/NIR @ f5372ae
(`nir/ir/*.py`), with an empirical FP32 measurement.*

The architect's claim — Verilog-AMS needs a solver only for certain model
classes; the stat-sim models can be analytical/event-driven — is **verified
against the code**. All 19 serializable NIR primitives classify as:

| Class | Count | Primitives | Inter-event treatment |
|---|---|---|---|
| Closed-form (LTI) | 6 | LI, LIF, CubaLI, CubaLIF, I, IF | exact (matrix) exponential propagator; threshold/reset only re-initializes state at events — piecewise-exact |
| Event-only | 9 | Threshold, Delay, Linear, Affine, Scale, Conv1d/2d, SumPool2d, AvgPool2d | memoryless maps or pure event retiming |
| Structural | 4 | Input, Output, Flatten, NIRGraph | index remapping; Input/Output are the natural pipe endpoints (`PIPES.md`) |

**None requires a numerical ODE integrator.** The GPU stat-sim tier is
expression evaluation plus event scheduling — the §2 negotiation-loop
blocker does not apply to it. What breaks analyticity (and stays on the CPU
oracle path): AdEx, Izhikevich, conductance-based synapses, NMDA/HH gating,
multiplicative adaptive thresholds. Additive OU noise on an LTI membrane
keeps an exact update.

**FP32 verdict (measured):** single-update relative error 1e-8..1e-7;
because the leak is a contraction, error does **not** accumulate —
|v32 − v64| holds at ~3e-8 after 10^6 chained updates. One guard: clamp
decay factors to 0 below the subnormal range (dt/tau ≳ 87) rather than
trusting subnormals, which also avoids vendor-divergent FTZ behavior.
Question 5 below is thereby answered: consumer GPUs suffice for LI/LIF
islands.

## 6. Open questions

1. TH-gate latch modeling in an AIG flow: how many fixed-point iterations per DATA/NULL wavefront in practice, and does GEM's scheduler tolerate them?
2. How badly do SPEF per-arc delay distributions hit the batched engine — is Brian2CUDA's order-of-magnitude penalty representative of our fan-out topology?
3. Spike-time quantization vs `@cross` tolerance: what dt (or root-find tolerance) makes GPU tier-0 traces equivalence-checkable against NVC/ngspice golden runs?
4. Diffrax events are terminating — is solve-per-event looping acceptable at our event rates, or do we need a custom multi-event kernel (MPGOS-style)?
5. ~~Is FP32 sufficient for LI/LIF islands?~~ Answered in §5: yes, with the subnormal clamp guard.
6. Where do typical mylex netlists sit vs the ~1e4-unit GPU crossover — i.e., which designs ever leave the CPU tier for single runs?
7. Build vs contribute: VAJAX (127 open issues, small community) upstream investment vs an in-house JAX kernel; and RTLflow's license ambiguity if we fork its batching pattern.