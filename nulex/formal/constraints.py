#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""nulex/formal/constraints.py — isochronic-fork constraint extraction (ASYNC-PLAN §8).

QDI/NCL correctness rests on isochronic forks: a net that fans out to several gate
inputs must reach them with matched delay, or a transition orphans and the
handshake breaks. Formal enumerates *which* forks; layout (layopt) decides whether
the branches are matched. This is the automated form of the path set that
`probes/layopt/l3_fork_balance.py` currently takes by hand:

    - <net> ( <driver_inst> <pin> ) ( <recv_inst> <pin> ) ( <recv_inst> <pin> ) ...

Reads a yosys gate netlist (write_json) and emits, for every multi-fanout net, an
isochronic-fork path set (driver pin + receiver pins) that layopt's
`objective.fork_balance` consumes after P&R. Clock and reset distribution forks
are tagged separately (skew, not orphan). Forks are ranked by fanout (the wider
the fork, the harder to balance).

Usage: constraints.py <netlist.json> <top> [out.json]
"""
import json, sys
from collections import defaultdict

# per gate cell: (input pins, output pin). Clock/reset pins flagged for tagging.
CELLS = {
    "$_AND_": (["A", "B"], "Y"), "$_OR_": (["A", "B"], "Y"), "$_XOR_": (["A", "B"], "Y"),
    "$_NAND_": (["A", "B"], "Y"), "$_NOR_": (["A", "B"], "Y"), "$_XNOR_": (["A", "B"], "Y"),
    "$_NOT_": (["A"], "Y"), "$_BUF_": (["A"], "Y"), "$_MUX_": (["A", "B", "S"], "Y"),
    "$_DFF_P_": (["D", "C"], "Q"), "$_DFF_PN0_": (["D", "C", "R"], "Q"),
}
CTRL_PINS = {"C", "R"}     # clock / reset: distribution skew, not orphan

def main():
    jpath, top = sys.argv[1], sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else None
    m = json.load(open(jpath))["modules"][top]
    ports, cells = m["ports"], m["cells"]

    driver = {}                      # net -> (inst, pin, kind)   kind: gate|input|reg
    recv = defaultdict(list)         # net -> [(inst, pin, is_ctrl)]
    # module ports: an input port drives its net; an output port is a sink (ignored as fork receiver)
    for pn, p in ports.items():
        if p["direction"] == "input":
            for i, b in enumerate(p["bits"]):
                if isinstance(b, int):
                    driver[b] = (pn, "" if len(p["bits"]) == 1 else "[%d]" % i, "input")
    for inst, c in cells.items():
        t = c["type"]
        if t == "$scopeinfo": continue
        if t not in CELLS: continue   # $mem etc. handled separately (skip for fork sets)
        ins, outp = CELLS[t]
        k = c["connections"]
        for b in k.get(outp, []):
            if isinstance(b, int): driver[b] = (inst, outp, "reg" if outp == "Q" else "gate")
        for pin in ins:
            for b in k.get(pin, []):
                if isinstance(b, int): recv[b].append((inst, pin, pin in CTRL_PINS))

    forks = []
    for net, rcvs in recv.items():
        if len(rcvs) < 2: continue    # not a fork
        drv = driver.get(net)
        if drv is None: continue      # undriven / constant
        is_ctrl = all(r[2] for r in rcvs)
        forks.append({
            "net": net,
            "driver": {"inst": drv[0], "pin": drv[1], "kind": drv[2]},
            "receivers": [{"inst": r[0], "pin": r[1]} for r in rcvs],
            "fanout": len(rcvs),
            "kind": "clock_reset_dist" if is_ctrl else "isochronic",
            "weight": len(rcvs),      # wider fork = harder to balance = higher weight
        })
    forks.sort(key=lambda f: (f["kind"] != "isochronic", -f["fanout"]))

    iso = [f for f in forks if f["kind"] == "isochronic"]
    ctl = [f for f in forks if f["kind"] == "clock_reset_dist"]
    result = {"design": top, "source": jpath, "n_forks": len(forks),
              "n_isochronic": len(iso), "n_clock_reset": len(ctl), "forks": forks}
    if out:
        json.dump(result, open(out, "w"), indent=1)
    # human summary
    tot_recv = sum(f["fanout"] for f in iso)
    fh = defaultdict(int)
    for f in iso: fh[f["fanout"]] += 1
    print("%s: %d isochronic-fork path sets (%d branch endpoints), %d clock/reset-dist forks"
          % (top, len(iso), tot_recv, len(ctl)))
    print("  fanout distribution (isochronic): " +
          ", ".join("%d-way:%d" % (k, fh[k]) for k in sorted(fh)))
    print("  top forks (widest first):")
    for f in iso[:6]:
        d = f["driver"]
        print("    net %-6s  %s.%s -> %d receivers   [%s...]" % (
            f["net"], d["inst"].split("$")[-1][:24], d["pin"], f["fanout"],
            ", ".join("%s.%s" % (r["inst"].split("$")[-1][:12], r["pin"]) for r in f["receivers"][:3])))
    if out: print("  wrote %s (layopt consumes: net -> driver pin + receiver pins for objective.fork_balance)" % out)

if __name__ == "__main__":
    main()
