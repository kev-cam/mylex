#!/usr/bin/env python3
"""nulex/perf/measure_activity.py — REAL activity of the ALU under a program.

Drives the mapped ALU gate netlist with its actual vvp-oracle instruction stream
(probes/alutest/vectors.txt -- a real ADD/SUB/SLT/AND/OR/XOR/SLL/SRL/branch mix)
through the event-driven actor engine, and reports the actual per-cycle activity
(actor evals / oblivious evals) -- i.e. WHERE on the async-vs-sync speed-up curve
a real program lands, not a synthetic random-toggle rate.

Also models realistic GPU issue rates: a GPGPU spends most cycles stalled on
memory, so the execute stage sees an instruction only every 1/IPC cycles. We
replay the same real instructions with G held (idle) cycles inserted between
them (IPC = 1/(1+G)) and show activity + the implied speed-up fall/rise with IPC.

Usage: measure_activity.py <alu.json> <alu_top> <vectors.txt>
"""
import sys, actor_sim as A

def parse_hex(tok):
    v = 0
    for ch in tok:
        v = (v << 4) | (0 if ch in "xXzZ" else int(ch, 16))
    return v

def load_program(vpath):
    """Each ALU vector row: ex_valid ex_data rs_ready <outputs...>. Return the
    per-cycle (ex_valid, ex_data 274b, rs_ready) input triples."""
    prog = []
    for line in open(vpath):
        f = line.split()
        if len(f) < 3: continue
        ev = parse_hex(f[0]) & 1
        exd = parse_hex(f[1]) & ((1 << 274) - 1)
        rr = parse_hex(f[2]) & 1
        prog.append((ev, exd, rr))
    return prog

def port_nets(nl, name):
    for n, bits in nl["in_ports"]:
        if n == name: return bits
    raise SystemExit("no input port " + name)

def build_stim(nl, prog, idle_gap):
    """Per-cycle input net values -> change lists. reset asserted for 2 cycles
    (as the oracle's pre-history), then the program, with `idle_gap` hold cycles
    inserted after each instruction (inputs unchanged = the memory-stall gap)."""
    rst = port_nets(nl, "reset")[0]
    ev_n = port_nets(nl, "ex_valid")[0]
    rr_n = port_nets(nl, "rs_ready")[0]
    exd_n = port_nets(nl, "ex_data")            # 274 nets, LSB first
    cur = {}
    stim = []
    def cycle(rst_v, ev, exd, rr):
        want = {rst: rst_v, ev_n: ev, rr_n: rr}
        for i, net in enumerate(exd_n):
            if isinstance(net, int): want[net] = (exd >> i) & 1
        chg = [(n, v) for n, v in want.items() if cur.get(n, 0) != v]
        for n, v in chg: cur[n] = v
        stim.append(chg)
    cycle(1, 0, 0, 1); cycle(1, 0, 0, 1)          # reset preamble
    for k, (ev, exd, rr) in enumerate(prog):
        cycle(0, ev, exd, rr)
        for _ in range(idle_gap):
            stim.append([])                        # hold: no input changes (idle)
    return stim

def measure(nl, stim, ng, nr):
    to, wo = A.run(nl, stim, actor=False)
    ta, wa = A.run(nl, stim, actor=True)
    ok = to == ta
    obliv = (ng + nr) * len(stim)
    return wa, obliv, 100.0 * wa / obliv, obliv / max(wa, 1), ok

def main():
    jpath, top, vpath = sys.argv[1:4]
    nl = A.load(jpath, top)
    ng, nr = len(nl["gates"]), len(nl["regs"])
    prog = load_program(vpath)
    print(f"{top}: {ng} gates, {nr} regs; program = {len(prog)} real instructions "
          f"(from {vpath.split('/')[-1]})\n")
    print(f"{'IPC':>6} {'cycles':>7} {'actor_ev':>10} {'obliv_ev':>10} {'activity':>9} "
          f"{'work_spd':>9}  equiv")
    for gap in (0, 1, 3, 7, 15, 31):
        stim = build_stim(nl, prog, gap)
        wa, obliv, act, spd, ok = measure(nl, stim, ng, nr)
        ipc = 1.0 / (1 + gap)
        print(f"{ipc:>6.3f} {len(stim):>7} {wa:>10,} {obliv:>10,} {act:>8.2f}% "
              f"{spd:>8.1f}x  {'OK' if ok else '*** MISMATCH ***'}")
    print("\nIPC=1.0 is the dense stress test (an instruction almost every cycle);"
          "\nreal GPGPU workloads run memory-bound at low IPC, where the execute stage"
          "\nis idle most cycles and the actor form's activity -- and speed-up -- follow.")

if __name__ == "__main__":
    main()
