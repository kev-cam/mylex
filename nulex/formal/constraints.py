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

For a generic gate netlist the built-in gate map suffices; for a technology-
mapped netlist (e.g. sky130_fd_sc_hd cells) pass --lef so pin directions come
from the LEF: constraints.py <netlist.json> <top> [out.json] [--lef LEF ...]
"""
import json, os, re, sys
from collections import defaultdict

# QDI handshake/completion control nets, by the nulex naming convention
# (map_ncl_struct): request ki*, completion ko*, and the completion tree cd*/acc*.
# Checked only AFTER the dual-rail (_L/_H) data test, so a data signal the user
# happened to call e.g. "ack" (rails ack_L/ack_H) is still classed as data.
_HANDSHAKE_RE = re.compile(r"^(ki|ko|cd|acc)(_|\d|$)")
def _is_handshake(name):
    return bool(_HANDSHAKE_RE.match(name))

# per gate cell: (input pins, output pin). Clock/reset pins flagged for tagging.
CELLS = {
    "$_AND_": (["A", "B"], "Y"), "$_OR_": (["A", "B"], "Y"), "$_XOR_": (["A", "B"], "Y"),
    "$_NAND_": (["A", "B"], "Y"), "$_NOR_": (["A", "B"], "Y"), "$_XNOR_": (["A", "B"], "Y"),
    "$_NOT_": (["A"], "Y"), "$_BUF_": (["A"], "Y"), "$_MUX_": (["A", "B", "S"], "Y"),
    "$_DFF_P_": (["D", "C"], "Q"), "$_DFF_PN0_": (["D", "C", "R"], "Q"),
    # coarse RTL inverter/buffer (e.g. the single-rail handshake ack network's NOT)
    "$not": (["A"], "Y"), "$buf": (["A"], "Y"), "$_ANDNOT_": (["A", "B"], "Y"),
}
CTRL_PINS = {"C", "R"}     # generic clock / reset: distribution skew, not orphan

# sky130 (and general std-cell) pin-name heuristics for the LEF-derived path.
POWER_PINS = {"VGND", "VPWR", "VPB", "VNB", "VDD", "VSS", "VDDPE", "VDDCE", "VSSE"}
def _is_clk(p):  return "CLK" in p or "GCLK" in p
def _is_ctrl(p): return _is_clk(p) or "RESET" in p or p in ("SET_B", "SLEEP", "SLEEP_B", "SCE", "SCD", "NOTIFIER")

def lef_cell_pins(lef_paths):
    """macro -> (input_pins, output_pins) from LEF pin DIRECTION, skipping power.
    Lets constraints.py enumerate forks on a technology-mapped netlist (sky130
    cells), not just the generic gate map above."""
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.abspath(os.path.join(here, "..", "..")))  # repo root -> layopt
    from layopt import lefdef
    lef = lefdef.Lef()
    for p in lef_paths:
        lefdef.read_lef(p, lef)
    out = {}
    for name, m in lef.macros.items():
        ins, outs = [], []
        for pn, pin in m.pins.items():
            if pn in POWER_PINS:
                continue
            d = getattr(pin, "direction", "INPUT").upper()
            if d.startswith("OUTPUT"):
                outs.append(pn)
            elif d.startswith("INPUT"):
                ins.append(pn)
        if outs:
            out[name] = (ins, outs)
    return out

def main():
    argv = sys.argv[1:]
    lef_paths = []
    while "--lef" in argv:
        i = argv.index("--lef"); lef_paths.append(argv[i + 1]); del argv[i:i + 2]
    jpath, top = argv[0], argv[1]
    out = argv[2] if len(argv) > 2 else None
    modules = json.load(open(jpath))["modules"]
    m = modules[top]
    ports, cells = m["ports"], m["cells"]
    lef_cells = lef_cell_pins(lef_paths) if lef_paths else {}   # macro -> (ins, outs)
    # net-name resolution (for QDI-aware tagging): a dual-rail NCL netlist names its
    # data rails <sig>_L / <sig>_H, and its single-rail handshake/completion control
    # ki*/ko*/cd*/acc*. Dual-rail data forks are orphan-critical (match delay); the
    # single-rail control forks are skew-tolerant (drive balance) — the QDI point.
    netnames = m.get("netnames", {})
    name_of = {}
    for nm, info in netnames.items():
        for b in info.get("bits", []):
            if isinstance(b, int) and (b not in name_of or (name_of[b].startswith("$") and not nm.startswith("$"))):
                name_of[b] = nm
    dual_rail = any(nm.endswith("_L") or nm.endswith("_H") for nm in netnames)
    # third pin-direction source: a cell whose type is another module in this JSON
    # (kept opaque, e.g. blackbox TH cells in a structural NCL netlist) — take its
    # input/output pins from that submodule's own port directions. No LEF needed.
    json_cells = {}
    for mn, mm in modules.items():
        if mn == top:
            continue
        ins = [pn for pn, p in mm.get("ports", {}).items() if p.get("direction") == "input"]
        outs = [pn for pn, p in mm.get("ports", {}).items() if p.get("direction") == "output"]
        if outs:
            json_cells[mn] = (ins, outs)

    driver = {}                      # net -> (inst, pin, kind)   kind: gate|input|reg
    recv = defaultdict(list)         # net -> [(inst, pin, is_ctrl)]
    unknown = defaultdict(int)       # cell types skipped (no pin info)
    # module ports: an input port drives its net; an output port is a sink (ignored as fork receiver)
    for pn, p in ports.items():
        if p["direction"] == "input":
            for i, b in enumerate(p["bits"]):
                if isinstance(b, int):
                    driver[b] = (pn, "" if len(p["bits"]) == 1 else "[%d]" % i, "input")
    for inst, c in cells.items():
        t = c["type"]
        if t == "$scopeinfo": continue
        k = c["connections"]
        if t in CELLS:               # generic gate map
            ins, outs = CELLS[t][0], [CELLS[t][1]]
            ctrl = lambda pin: pin in CTRL_PINS
            is_reg = "$_DFF" in t
        elif t in lef_cells:         # technology-mapped cell (pins from LEF DIRECTION)
            ins, outs = lef_cells[t]
            ctrl = _is_ctrl
            is_reg = ("df" in t.split("__")[-1]) or ("dl" in t.split("__")[-1]) or any(_is_clk(p) for p in ins)
        elif t in json_cells:        # opaque submodule (e.g. structural TH cell) — pins from its ports
            ins, outs = json_cells[t]
            ctrl = _is_ctrl
            is_reg = ("df" in t.split("__")[-1]) or ("dl" in t.split("__")[-1]) or any(_is_clk(p) for p in ins)
        else:
            unknown[t] += 1; continue
        for outp in outs:
            for b in k.get(outp, []):
                if isinstance(b, int): driver[b] = (inst, outp, "reg" if is_reg else "gate")
        for pin in ins:
            for b in k.get(pin, []):
                if isinstance(b, int): recv[b].append((inst, pin, ctrl(pin)))

    forks = []
    for net, rcvs in recv.items():
        if len(rcvs) < 2: continue    # not a fork
        drv = driver.get(net)
        if drv is None: continue      # undriven / constant
        is_ctrl = all(r[2] for r in rcvs)
        name = name_of.get(net, "")
        is_rail = name.endswith("_L") or name.endswith("_H")   # dual-rail data rail
        if is_rail:
            kind = "isochronic"                 # dual-rail DATA: an orphaned branch breaks the handshake
        elif _is_handshake(name):
            kind = "handshake"                  # ki/ko/completion control: skew-tolerant, not orphan
        elif is_ctrl:
            kind = "clock_reset_dist"           # sync clock/reset distribution (skew, not orphan)
        else:
            kind = "isochronic"                 # single-rail data (minterms; or a sync data net)
        objective = "match_delay" if kind == "isochronic" else "skew_tolerant"
        forks.append({
            "net": net, "name": name,
            "driver": {"inst": drv[0], "pin": drv[1], "kind": drv[2]},
            "receivers": [{"inst": r[0], "pin": r[1]} for r in rcvs],
            "fanout": len(rcvs),
            "kind": kind, "objective": objective,
            "weight": len(rcvs),      # wider fork = harder to balance = higher weight
        })
    order = {"isochronic": 0, "handshake": 1, "clock_reset_dist": 2}
    forks.sort(key=lambda f: (order.get(f["kind"], 3), -f["fanout"]))

    iso = [f for f in forks if f["kind"] == "isochronic"]
    hsk = [f for f in forks if f["kind"] == "handshake"]
    ctl = [f for f in forks if f["kind"] == "clock_reset_dist"]
    result = {"design": top, "source": jpath, "n_forks": len(forks),
              "n_isochronic": len(iso), "n_handshake": len(hsk), "n_clock_reset": len(ctl), "forks": forks}
    if out:
        json.dump(result, open(out, "w"), indent=1)
    # human summary
    tot_recv = sum(f["fanout"] for f in iso)
    fh = defaultdict(int)
    for f in iso: fh[f["fanout"]] += 1
    print("%s: %d isochronic-fork path sets (%d branch endpoints), %d clock/reset-dist forks%s"
          % (top, len(iso), tot_recv, len(ctl),
             ("  [from LEF pin dirs: %d cell types]" % len(lef_cells)) if lef_cells else ""))
    if dual_rail:
        print("  QDI: %d isochronic (dual-rail DATA -> match delay), %d handshake/completion "
              "(single-rail ki/ko -> skew-tolerant drive balance)" % (len(iso), len(hsk)))
        for f in hsk[:4]:
            print("    handshake %-10s -> %d receivers (skew-tolerant)" % (f["name"] or f["net"], f["fanout"]))
    if unknown:
        print("  WARNING: %d cell types skipped (no pin info): %s"
              % (len(unknown), ", ".join(sorted(unknown)[:8])))
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
