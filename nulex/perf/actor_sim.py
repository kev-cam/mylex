#!/usr/bin/env python3
"""nulex/perf/actor_sim.py — event-driven ("actor") vs oblivious gate simulation.

Reads a yosys gate netlist (write_json, the same one map_ncl.py consumes) and
simulates it two ways over a stimulus, counting the WORK (gate/register
evaluations) each does:

  OBLIVIOUS : every cycle, evaluate every comb gate (topological) and clock
              every register -- what a clock-driven / oblivious sim does. Work
              = (#gates + #regs) per cycle, independent of activity.
  ACTOR     : event-driven. A comb gate re-evaluates only when one of its inputs
              changed; a register is an ACTOR that fires only when its D input
              changed since it last captured (idle registers cost zero). Work =
              (changed gates + fired registers) per cycle.

Both must produce the IDENTICAL output/state sequence -- the actor form is a
pure work reduction, verified. This is the register mechanism the mapped NCL
netlists need to actually run faster than sync (their ncl_dff is clocked and
sits at the oblivious cost); here it is prototyped and measured on the real
gate netlists.

Usage: actor_sim.py <netlist.json> <top> [cycles] [activity]
  activity in (0,1]: fraction of primary inputs that toggle each cycle (default
  0.02). Low activity = the idle-heavy regime where the actor form wins.
"""
import json, sys, random
from collections import deque

BIN = {"$_AND_": lambda a,b: a & b, "$_OR_": lambda a,b: a | b,
       "$_XOR_": lambda a,b: a ^ b, "$_NAND_": lambda a,b: 1-(a & b),
       "$_NOR_": lambda a,b: 1-(a | b), "$_XNOR_": lambda a,b: 1-(a ^ b)}

def load(path, top):
    m = json.load(open(path))["modules"][top]
    ports, cells = m["ports"], m["cells"]
    gates = []    # (kind, [in_nets], out_net) ; kind in BIN | 'not' | 'mux'
    regs  = []    # (d_net, q_net)
    rst   = []    # parallel to regs: async active-low reset net, or None ($_DFF_P_)
    # (clock net C is ignored: every flop ticks each cycle = the ungated form;
    #  gated-clock power behavior is a later refinement.)
    for c in cells.values():
        t = c["type"]; k = c["connections"]
        if t == "$scopeinfo": continue
        if t in BIN:      gates.append((t, [k["A"][0], k["B"][0]], k["Y"][0]))
        elif t == "$_NOT_": gates.append(("not", [k["A"][0]], k["Y"][0]))
        elif t == "$_MUX_": gates.append(("mux", [k["A"][0], k["B"][0], k["S"][0]], k["Y"][0]))
        elif t == "$_DFF_P_":  regs.append((k["D"][0], k["Q"][0])); rst.append(None)
        elif t == "$_DFF_PN0_": regs.append((k["D"][0], k["Q"][0])); rst.append(k["R"][0])  # async reset-to-0, active low
        elif t == "$_BUF_": gates.append(("buf", [k["A"][0]], k["Y"][0]))
        else: sys.exit("unhandled cell " + t)
    in_ports  = [(n, p["bits"]) for n, p in ports.items()
                 if p["direction"] == "input" and n != "clk"]
    out_ports = [(n, p["bits"]) for n, p in ports.items() if p["direction"] == "output"]
    # sources = primary inputs + register Q + constants; topo-sort the comb gates
    src = set()
    for n, bits in in_ports:
        for b in bits:
            if isinstance(b, int): src.add(b)
    for d, q in regs: src.add(q)
    idx = {}                     # net -> the gate index that drives it
    for gi, (_, _, y) in enumerate(gates): idx[y] = gi
    order, seen = [], [False]*len(gates)
    def visit(gi):
        stack = [(gi, False)]
        while stack:
            g, done = stack.pop()
            if done: order.append(g); continue
            if seen[g]: continue
            seen[g] = True
            stack.append((g, True))
            for b in gates[g][1]:
                if isinstance(b, int) and b in idx and b not in src:
                    if not seen[idx[b]]: stack.append((idx[b], False))
    for gi in range(len(gates)): visit(gi)
    # net -> consuming gate indices (for event propagation)
    consumers = {}
    for gi, (_, ins, _) in enumerate(gates):
        for b in ins:
            if isinstance(b, int): consumers.setdefault(b, []).append(gi)
    d_regs = {}                  # net -> registers triggered when it changes (D input OR reset)
    for ri, (d, q) in enumerate(regs):
        if isinstance(d, int): d_regs.setdefault(d, []).append(ri)
        if isinstance(rst[ri], int): d_regs.setdefault(rst[ri], []).append(ri)
    return dict(gates=gates, regs=regs, rst=rst, order=order, consumers=consumers,
                d_regs=d_regs, in_ports=in_ports, out_ports=out_ports)

def gval(kind, ins):
    if kind in BIN: return BIN[kind](ins[0], ins[1])
    if kind == "not": return 1 - ins[0]
    if kind == "buf": return ins[0]
    if kind == "mux": return ins[1] if ins[2] else ins[0]     # Y = S ? B : A

def netval(v, b):
    if isinstance(b, int): return v.get(b, 0)
    return 1 if b == "1" else 0

def outputs(v, out_ports):
    return tuple(tuple(netval(v, b) for b in bits) for _, bits in out_ports)

def run(nl, stim, actor, snaps=None):
    """Simulate; return (output-trace, work-count). actor=False -> oblivious.
    If snaps is a list, a copy of the net-value map is appended each cycle."""
    gates, regs, order = nl["gates"], nl["regs"], nl["order"]
    consumers, d_regs, rst = nl["consumers"], nl["d_regs"], nl["rst"]
    def nextq(ri):   # reset-aware captured value: async active-low reset forces 0
        r = rst[ri]
        return 0 if (r is not None and netval(v, r) == 0) else netval(v, regs[ri][0])
    v = {}
    for _, q in regs: v[q] = 0
    trace, work = [], 0
    if actor:
        dirty_reg = set()
        # prime: full comb evaluation once so all nets are defined
        for gi in order:
            k, ins, y = gates[gi]
            v[y] = gval(k, [netval(v, b) for b in ins])
        for ri, (d, q) in enumerate(regs):
            if nextq(ri) != v[q]: dirty_reg.add(ri)
        for cyc, inbits in enumerate(stim):
            # 1. apply input changes, propagate through comb (event-driven)
            q = deque()
            for net, val in inbits:
                if v.get(net, 0) != val:
                    v[net] = val
                    for gi in consumers.get(net, ()): q.append(gi)
                    for r in d_regs.get(net, ()): dirty_reg.add(r)   # D fed directly by an input
            inq = set(q)
            while q:
                gi = q.popleft(); inq.discard(gi)
                k, ins, y = gates[gi]
                work += 1
                nv = gval(k, [netval(v, b) for b in ins])
                if nv != v.get(y, 0):
                    v[y] = nv
                    for r in d_regs.get(y, ()): dirty_reg.add(r)
                    for c in consumers.get(y, ()):
                        if c not in inq: q.append(c); inq.add(c)
            trace.append(outputs(v, nl["out_ports"]))
            # 2. clock tick: fire only registers whose D changed (actors).
            # Two-phase: capture ALL D (pre-edge) first, THEN apply Q -- else a
            # shift path R2.D=R1.Q would read R1's new Q (simultaneous-update bug).
            nq = deque(); nqs = set(); upd = []
            for ri in list(dirty_reg):
                d, qn = regs[ri]
                work += 1
                nv = nextq(ri)
                if nv != v[qn]: upd.append((qn, nv))
            dirty_reg.clear()
            for qn, nv in upd:
                v[qn] = nv
                for c in consumers.get(qn, ()):
                    if c not in nqs: nq.append(c); nqs.add(c)
                for r in d_regs.get(qn, ()): dirty_reg.add(r)   # D fed directly by a reg Q (shift)
            # propagate register-output changes into this settle (same cycle image)
            while nq:
                gi = nq.popleft(); nqs.discard(gi)
                k, ins, y = gates[gi]
                work += 1
                nv = gval(k, [netval(v, b) for b in ins])
                if nv != v.get(y, 0):
                    v[y] = nv
                    for r in d_regs.get(y, ()): dirty_reg.add(r)
                    for c in consumers.get(y, ()):
                        if c not in nqs: nq.append(c); nqs.add(c)
            if snaps is not None: snaps.append(dict(v))
    else:
        for cyc, inbits in enumerate(stim):
            for net, val in inbits: v[net] = val
            for gi in order:                         # every comb gate, every cycle
                k, ins, y = gates[gi]
                work += 1
                v[y] = gval(k, [netval(v, b) for b in ins])
            trace.append(outputs(v, nl["out_ports"]))
            nd = [nextq(ri) for ri in range(len(regs))]  # every register, every cycle
            for ri, (_, qn) in enumerate(regs):
                work += 1; v[qn] = nd[ri]
            if snaps is not None: snaps.append(dict(v))
    return trace, work

def make_stim(nl, cycles, activity, seed=1):
    rnd = random.Random(seed)
    in_nets = []
    for _, bits in nl["in_ports"]:
        for b in bits:
            if isinstance(b, int): in_nets.append(b)
    cur = {n: 0 for n in in_nets}
    stim = []
    for _ in range(cycles):
        changes = []
        for n in in_nets:
            if rnd.random() < activity:
                nv = rnd.getrandbits(1)
                if nv != cur[n]: cur[n] = nv; changes.append((n, nv))
        stim.append(changes)
    return stim, in_nets

def dump(path, top, cycles, activity, outfile):
    """Write stimulus + oblivious output trace for map_actor_c.py's `check` mode.
    Format: '<cycles> <nin> <nout>' then per cycle '<nchg> <pos> <val>...' and a
    line of NOUT output bits. Positions index the flattened input-net list and
    the bit string the flattened output-bit list -- the same order the C builds."""
    nl = load(path, top)
    in_nets = [b for _, bits in nl["in_ports"] for b in bits if isinstance(b, int)]
    pos = {n: i for i, n in enumerate(in_nets)}
    out_bits = [b for _, bits in nl["out_ports"] for b in bits]
    stim, _ = make_stim(nl, cycles, activity)
    trace, _ = run(nl, stim, actor=False)          # pre-clock outputs, same as C check
    with open(outfile, "w") as f:
        f.write(f"{cycles} {len(in_nets)} {len(out_bits)}\n")
        for c in range(cycles):
            items = [(pos[n], v) for n, v in stim[c] if n in pos]
            f.write(str(len(items)) + "".join(f" {p} {v}" for p, v in items) + "\n")
            f.write("".join(str(b) for row in trace[c] for b in row) + "\n")
    print(f"dumped {cycles} cycles ({len(in_nets)} in / {len(out_bits)} out) to {outfile}")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "dump":
        _, _, path, top, cyc, act, out = sys.argv
        dump(path, top, int(cyc), float(act), out); return
    path, top = sys.argv[1], sys.argv[2]
    cycles   = int(sys.argv[3]) if len(sys.argv) > 3 else 500
    activity = float(sys.argv[4]) if len(sys.argv) > 4 else 0.02
    nl = load(path, top)
    ng, nr = len(nl["gates"]), len(nl["regs"])
    print(f"{top}: {ng} comb gates, {nr} registers, {len(nl['in_ports'])} in-ports; "
          f"{cycles} cycles @ activity={activity}")
    stim, in_nets = make_stim(nl, cycles, activity)
    to, wo = run(nl, stim, actor=False)
    ta, wa = run(nl, stim, actor=True)
    ok = to == ta
    obliv_per_cyc = ng + nr
    print(f"  oblivious work = {wo:>12,}  ({obliv_per_cyc}/cyc = every gate+reg)")
    print(f"  actor     work = {wa:>12,}  ({wa/cycles:.0f}/cyc avg)")
    print(f"  work ratio     = {wo/max(wa,1):.1f}x fewer evals   (activity {100*wa/max(wo,1):.1f}%)")
    print(f"  equivalence    = {'OK -- identical output trace' if ok else '*** MISMATCH ***'}")
    if not ok: sys.exit(1)

if __name__ == "__main__":
    main()
