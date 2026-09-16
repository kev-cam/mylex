#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Fork-driven placement hints: for each WIDE isochronic fork (receivers scattered
far apart -> unequal branch lengths = the placement-limited imbalance the routed
measurement flagged), relocate its driver BUFFER toward the receivers' centroid.
The driver of a high-fanout net is a repair_design buffer that serves only that
net, so moving it shortens the worst branch without disturbing the receivers'
own logic. Emits fork_targets.tcl (net -> target xy) consumed by flow_hinted.tcl.

Usage: gen_fork_hints.py [--span-um U] [--top N]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPAN = float(sys.argv[sys.argv.index("--span-um") + 1]) if "--span-um" in sys.argv else 100.0
TOP = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 30

phys = json.load(open(os.path.join(HERE, "alu_forks_phys.json")))
picks = []
for f in phys["forks"]:
    xs = [r["x"] for r in f["receivers"]]
    ys = [r["y"] for r in f["receivers"]]
    span = max(max(xs) - min(xs), max(ys) - min(ys)) / 1000.0
    if span < SPAN:
        continue
    cx = sum(xs) // len(xs)      # receiver centroid (DBU) — driver goes here
    cy = sum(ys) // len(ys)
    picks.append((f["net"], cx, cy, span, f["fanout"]))
picks.sort(key=lambda p: -p[3])          # widest span first
picks = picks[:TOP]

with open(os.path.join(HERE, "fork_targets.tcl"), "w") as fh:
    fh.write("# net -> driver target (receiver centroid, DBU); from gen_fork_hints.py\n")
    fh.write("set FORK_TARGETS {\n")
    for net, cx, cy, span, fo in picks:
        fh.write("  {%s %d %d}\n" % (net, cx, cy))
    fh.write("}\n")
print("wrote fork_targets.tcl: %d wide forks (span>=%.0fum), fanout %d..%d, span %.0f..%.0f um" % (
    len(picks), SPAN, min(p[4] for p in picks), max(p[4] for p in picks),
    min(p[3] for p in picks), max(p[3] for p in picks)))
