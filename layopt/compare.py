# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""Netlist comparison: our extraction vs a reference SPICE netlist (e.g.
KLayout's), and topology signatures for LVS-preservation after a move."""
import hashlib
import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Tuple

_SUF = {"": 1.0, "U": 1e-6, "N": 1e-9, "M": 1e-3, "P": 1e-12, "F": 1e-15, "K": 1e3, "MEG": 1e6, "G": 1e9}


def _val(tok: str) -> float:
    m = re.match(r"([-+0-9.eE]+)([A-Za-z]*)", tok)
    if not m:
        return float("nan")
    v, s = m.groups()
    return float(v) * _SUF.get(s.upper(), 1.0)


@dataclass
class RefDevice:
    name: str
    d: str
    g: str
    s: str
    model: str
    params: Dict[str, float]


def parse_spice(path: str) -> List[RefDevice]:
    text = open(path).read()
    # join continuation lines
    lines: List[str] = []
    for ln in text.splitlines():
        if ln.startswith("+") and lines:
            lines[-1] += " " + ln[1:]
        else:
            lines.append(ln)
    out: List[RefDevice] = []
    for ln in lines:
        if not ln or ln[0] not in "Mm":
            continue
        toks = ln.split()
        name, d, g, s = toks[0], toks[1], toks[2], toks[3]
        i = 4
        if "=" not in toks[i]:
            i += 1                     # bulk
        model = toks[i]; i += 1
        params = {}
        for t in toks[i:]:
            if "=" in t:
                k, v = t.split("=", 1)
                params[k.upper()] = _val(v)
        out.append(RefDevice(name, d, g, s, model, params))
    return out


def _dev_tuples(devs, w_of, l_of, kind_of):
    return Counter((kind_of(d), round(l_of(d), 4), round(w_of(d), 4)) for d in devs)


def _wl_signature(nodes: Dict[str, str], edges: List[Tuple[str, str, str]], rounds: int = 6) -> str:
    """Colour refinement over a bipartite device/net graph.  nodes: id->label,
    edges: (a, b, label)."""
    col = dict(nodes)
    adj: Dict[str, List[Tuple[str, str]]] = {n: [] for n in nodes}
    for a, b, lab in edges:
        adj[a].append((b, lab)); adj[b].append((a, lab))
    for _ in range(rounds):
        new = {}
        for n in nodes:
            sig = col[n] + "|" + ",".join(sorted(lab + ":" + col[m] for m, lab in adj[n]))
            new[n] = hashlib.md5(sig.encode()).hexdigest()[:12]
        col = new
    return hashlib.md5(",".join(sorted(col.values())).encode()).hexdigest()


def graph_signature(ex, with_w: bool = False) -> str:
    """Topology signature.  Sizes are excluded by default so a resize move
    compares equal (kind and L stay; connectivity must)."""
    nodes = {}
    edges = []
    for dv in ex.devices:
        nodes["D" + dv.name] = "%s:%g:%s" % (dv.kind, round(dv.l, 4), "%g" % round(dv.w, 3) if with_w else "-")
        for t, n in (("G", dv.g), ("S", dv.s), ("D", dv.d)):
            nodes.setdefault("N%d" % n, "net")
            edges.append(("D" + dv.name, "N%d" % n, "SD" if t in "SD" else "G"))
    return _wl_signature(nodes, edges)


def ref_signature(ref: List[RefDevice]) -> str:
    nodes = {}
    edges = []
    for d in ref:
        kind = "p" if "pfet" in d.model or "pmos" in d.model else "n"
        nodes["D" + d.name] = "%s:%g:%g" % (kind, round(d.params.get("L", 0) * 1e6, 4),
                                           round(d.params.get("W", 0) * 1e6, 3))
        for t, n in (("G", d.g), ("S", d.s), ("D", d.d)):
            nodes.setdefault("N" + n, "net")
            edges.append(("D" + d.name, "N" + n, "SD" if t in "SD" else "G"))
    return _wl_signature(nodes, edges)


def compare_to_reference(ex, ref_path: str) -> Dict:
    ref = parse_spice(ref_path)
    ours = _dev_tuples(ex.devices, lambda d: d.w, lambda d: d.l, lambda d: d.kind)
    theirs = _dev_tuples(ref, lambda d: d.params["W"] * 1e6, lambda d: d.params["L"] * 1e6,
                         lambda d: "p" if ("pfet" in d.model or "pmos" in d.model) else "n")
    ref_nets = Counter()
    for d in ref:
        for n in (d.d, d.g, d.s):
            ref_nets[n] += 1
    our_nets = Counter()
    for dv in ex.devices:
        for n in (dv.d, dv.g, dv.s):
            our_nets[n] += 1
    # area/perimeter agreement (multiset of rounded tuples, S/D unordered)
    def ap_ours(d):
        return tuple(sorted([(round(d.as_, 4), round(d.ps, 3)), (round(d.ad, 4), round(d.pd, 3))]))
    def ap_theirs(d):
        p = d.params
        return tuple(sorted([(round(p.get("AS", 0) * 1e12, 4), round(p.get("PS", 0) * 1e6, 3)),
                             (round(p.get("AD", 0) * 1e12, 4), round(p.get("PD", 0) * 1e6, 3))]))
    ap_o = Counter(ap_ours(d) for d in ex.devices); ap_t = Counter(ap_theirs(d) for d in ref)
    return {
        "ref_devices": len(ref), "our_devices": len(ex.devices),
        "wl_match": ours == theirs,
        "wl_only_ours": ours - theirs, "wl_only_ref": theirs - ours,
        "ref_nets": len(ref_nets), "our_nets": len(our_nets),
        "degree_hist_match": Counter(ref_nets.values()) == Counter(our_nets.values()),
        "degree_hist_ref": sorted(Counter(ref_nets.values()).items()),
        "degree_hist_ours": sorted(Counter(our_nets.values()).items()),
        "isomorphic": graph_signature(ex, with_w=True) == ref_signature(ref),
        "area_perim_match": ap_o == ap_t,
        "ap_only_ours": ap_o - ap_t, "ap_only_ref": ap_t - ap_o,
    }
