# Self-timed static-CMOS FSM — campaign documentation (banked 2026-10-03)

> **Status: BANKED for resume with better PDKs + computing targets.** This records a
> measured + stat-sim-composed campaign on IHP SG13G2 (130 nm, PSP103, Xyce). The
> *direction and the cross-design ordering are the durable results*; the absolute
> energies are 130 nm estimates to be re-pinned on a real target PDK. See
> **§7 Resume plan**.

Companion to `ASYNC-PLAN.md`, `SELECTION-RULE.md`, `POLYSYNTH.md`. Code + measured
records live in the **stat-sim** repo (separate tree) under
`qal/synth/threeway/spice/{fsm,sha_fsm,aes_fsm,ghash_fsm}/` — paths cited per section.

---

## 1. The idea (and the pivot that got here)

Earlier async work mapped RTL to **domino** (precharge/evaluate). Measured on the
sha_slice block it cost **4.6× static-CMOS energy** — the fixed precharge→evaluate→
**reset-to-one-quiescent-state** cycle pays CV² every cycle regardless of data, plus a
dual-rail carry chain for the embedded done. The user reframe: *drop the fixed reset;
let the machine transition to a new state and hold it; get the "done" out of the logic.*

That lands on a **self-timed static-CMOS state machine**:
- **Precharge-free static** next-state logic (ordinary CMOS, NOT domino) — pays CV²
  only on nodes that actually change (data-dependent, like static CMOS).
- An **edge-triggered DFF** state register (master-slave ⇒ no transparent-latch
  feedback race — a verifier-caught correctness requirement, not an optimization).
- A **done-pulsed capture**: an in-kind replica delay (≈ the round critical path)
  fires the capture, so the state advances on completion, not on a global clock.

Consequence: it **holds state and dissipates only on transitions**, so it sheds the
**clock floor** when idle. Per-op it is **~parity** with clocked CMOS; the win is
**duty-shaped** (idle regime). Per the 2026-10-02 directive, *parity is an acceptable
result* and *stat-sim composition is preferred over SPICE transient*.

The "done" also connects to the current-sense completion work (`cscd/`): watching
supply current works as a done signal, and how sharp it is depends on the round shape
(see §5 the three-cipher arc).

---

## 2. Measured anchor — 4-bit accumulator (the one full SPICE measurement)

`stat-sim/qal/synth/threeway/spice/fsm/` (gen_fsm.py, analyze_fsm.py, FSM_NUMBERS.txt).
Static ripple-adder + edge-triggered dfrbp DFF; golden = free-running clock (idle
cycles data-gated), self-timed = done-pulsed capture. **Measured (Xyce):**

| duty (op every N cyc) | clocked fJ | self-timed fJ | ratio |
|---|---|---|---|
| 1/1 (full) | 882 | 2009 | 0.44× |
| 1/4 | 2409 | 2693 | 0.89× |
| 1/10 | 5061 | 2697 | **1.88×** |

Self-timed energy is **duty-flat**; clocked grows with the idle window (clock floor ×
cycles). **Crossover ≈ 10 % activity**; self-timed wins increasingly below it.
Functional differential vs the clocked golden **PASS** (after a warm-up-cycle fix on
the clocked reference). This is the physical proof of the mechanism; the ciphers below
scale it by stat-sim composition.

---

## 3. The ciphers (the Ethernet / MACsec GCM-AES-128 primitive)

Each built as a self-timed FSM, **functionally proven** (iverilog, against an
independent reference — never self-asserted) and **energy composed in stat-sim**
(yosys cell counts × the measured sha_slice **3.683 fJ/cell** anchor + add8 clock/
register coefficients E_clk 28.2 fJ/DFF/cyc, E_regtoggle 45 fJ).

- **SHA-256** — `sha_fsm/` (RESULT.md). round = Σ0/Σ1/Maj/Ch/T1/T2 static next-state,
  8×32b a..h + rolling W schedule. Digests `abc`/empty == hashlib (re-verified 3×).
  **2.94 nJ/512b block**, round 5.638 ns. **Register-heavy: 774 flops**,
  floor/active 0.475.
- **AES-128** — `aes_fsm/` (RESULT.md). round = SubBytes(16 S-boxes)/ShiftRows/
  MixColumns/AddRoundKey + on-the-fly key expand. Ciphertext == FIPS-197
  `69c4e0d8…c55a` (openssl + pycryptodome, +200 random). **0.475 nJ/128b block**,
  round 2.124 ns. **Logic-heavy (S-box = 87 % of round): 260 flops**,
  floor/active 0.154. S-box lever: LUT 410 cells / composite (Canright) 182 cells.
- **GHASH** — `ghash_fsm/` (RESULT.md). GF(2¹²⁸) carry-less multiply-accumulate
  `Y'=(Y⊕C)·H` mod the GCM poly, bit-reflected. GCM Test Case 4 S `698e57f7…` →
  tag `5bc94fbc…` == NIST SP 800-38D + pycryptodome (re-verified, distinct code path).
  **0.066 nJ/128b block** (Karatsuba), one GF multiply = 99 % of combinational.
  **Carry-less, register-light: 264 flops**, floor/active 0.113.
  Multiplier forms: bit-serial 259 cells/step×128 / schoolbook 32,999 cells /
  **Karatsuba 14,137 cells (primary)**.

**Combined GCM-AES-128 per 128-bit block = AES 0.475 + GHASH 0.066 = 0.541 nJ**
(GHASH ≈ 12 % of total): AES carries the energy, GHASH is the cheap auth tail.

---

## 4. Energy/throughput scatter (normalized pJ/bit vs Gbit/s)

Throughput = block bits / (rounds × round critical path), single-engine. Down-and-right
is better.

| design | pJ/bit | Gbit/s |
|---|---|---|
| GHASH · Karatsuba | 0.52 | 32.8 |
| GHASH · schoolbook | 1.05 | 79.3 |
| AES-128 · composite S-box (derived) | 2.14 | 2.86 |
| AES-128 · LUT S-box | 3.71 | 6.03 |
| SHA-256 | 5.74 | 1.42 |
| GHASH · bit-serial | 13.9 | 7.94 |

Artifacts (private, claude.ai/code):
- Cipher FSM energy–throughput scatter: `artifact/2783624d-ac58-4533-b236-71c319093f4d`
- Earlier 130 nm energy–delay map (sha_slice block: CMOS/BD/domino/QDI/QAL):
  `artifact/e4dff3b3-2ca4-428c-b4e0-2ca7694a564f`

---

## 5. ★ The three-cipher arc (the load-bearing finding)

Two **independent** axes predict the two kinds of win:

- **Register weight → clock-floor-shed win.** SHA (774 flops, register-heavy) →
  biggest duty win (**1.43×/5.70×** vs good clock-gating at duty 0.1/0.01). AES
  (260) → **1.14×/2.5×**. GHASH (264, most logic-heavy) → **1.10×/2.12×**.
- **Round regularity → current-sense "done" sharpness.** SHA's deep carry ripple
  *blurs* power-settle completion (safe-but-late); AES's shallow round is *sharp*;
  GHASH's carry-less XOR tree is the *sharpest + most data-independent*.

GHASH sits at the far logic / regular corner: the **weakest clock-floor vehicle, the
best current-sense-done / GALS vehicle**. The whole arc: register weight is one axis,
round shape is the other, and a design lands somewhere on both.

**Honest scope (all three):** within a hash/encrypt/frame, duty ≈ 1 ⇒ **parity**
(line-rate MACsec); the win is **between** frames/blocks (bursty, event-driven,
wake-hash-sleep). Parity at line rate is accepted (directive).

---

## 6. Method, caveats, trust

- **Verified against real references, never self-asserted:** hashlib (SHA), openssl +
  pycryptodome + FIPS-197 (AES), NIST SP 800-38D + pycryptodome (GHASH, incl. the GCM
  bit-reflection — the #1 GHASH bug). Each re-verified independently by adversarial
  agents and by hand.
- **Absolute energy is stat-sim composed, not fully measured.** The 3.683 fJ/cell
  anchor was measured on the *shallow sha_slice adder/logic* cells; transplanted onto
  deep XOR reduction trees (GHASH) it **understates** (deep trees glitch more) → GHASH
  absolute pJ/bit is a **lower bound**. **Ratios, shape, and the 3-cipher ordering are
  robust; absolute pJ is a 130 nm estimate.**
- **The self-timed "done" is modeled, not transistor-simulated** here (directive: no
  Xyce). Logic correctness transfers from the synchronous proof (identical cone + DFF,
  only capture timing differs); the replica-done timing is an in-file narrative.
- Parity per-op is the expected and accepted outcome; the deliverable is the
  duty-shaped win + the functional scaling proof + the design-space map.

---

## 7. ★ Resume plan — "come back with better PDKs and computing targets"

When resuming on a better PDK / target:

1. **Re-pin absolute energy on the target PDK.** Replace the single 3.683 fJ/cell
   anchor with **per-cell-type** energy (XOR-tree cells vs adder vs substitution ROM),
   including deep-XOR glitch/activity — this most affects GHASH and the AES S-box. The
   ratios should hold; the absolute pJ/bit will move.
2. **A real current-sense-done SPICE anchor** on the carry-less GHASH round (the
   "sharpest settle" claim is currently a static-structure argument, §6).
3. **Composite-S-box AES** recompose (the derived point in §4 → measured); it is the
   low-power AES form.
4. **A real bursty-MACsec duty trace** (frame-size distribution, inter-frame idle)
   instead of the parametric duty sweep, to place the real operating point on §5.
5. **Better node / computing target.** The north star is NVIDIA-grade GP-GPU on an
   older node by dropping power (see memory `gpgpu_older_node_target`); FD-SOI (FDX)
   back-gate is the named device lever. On FD-SOI the self-timed FSM's duty win and the
   current-sense-done both change — re-run the arc there. Vortex is the test vehicle.
6. **Possible next cipher:** ChaCha20-Poly1305 (the other MACsec-adjacent AEAD) is a
   contrasting ARX datapath — would add a fourth point to the §5 arc.

**One-line resume:** the self-timed static-CMOS FSM computes real crypto correctly
(accumulator, SHA-256, AES-128, GHASH = full GCM-AES), is ~parity per-op, wins
duty-shaped at idle, and the (register-weight, round-regularity) arc tells you which
design wins which way — now re-measure on a real target PDK.
