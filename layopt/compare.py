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


def internal_nodes(ex) -> set:
    """Nets that are uncontacted diffusion between exactly two S/D terminals of
    same-kind, same-L devices and carry no label: the middle nodes of series
    stacks.  Such a node has no observable identity -- a stack mirrored into a
    second finger (sky130's own nand2_2 style) has its own, separate middle
    node and is the same circuit."""
    out = set()
    for nid, net in ex.nets.items():
        if not net.name.isdigit() or len(net.devices) != 2:
            continue
        if any(t == "G" for _, t in net.devices):
            continue
        if not all(ex.shapes[i].layer.startswith("sd_") for i in net.shapes):
            continue
        dn = {d for d, _ in net.devices}
        if len(dn) != 2:
            continue
        devs = [dv for dv in ex.devices if dv.name in dn]
        if len(devs) == 2 and devs[0].kind == devs[1].kind and round(devs[0].l, 6) == round(devs[1].l, 6):
            out.add(nid)
    return out


def reduce_stacks(ex):
    """Series-parallel canonical form for the topology guard.  Returns
    (devices as (name, kind, l, w, g, s, d) tuples, net id mapping).

    Devices connected through internal nodes form a stack (an ordered gate
    sequence between two external nets).  Parallel stacks with the same end
    nets and gate sequence are the same stack drawn with more fingers: their
    middle nodes are identified so the parallel fingers then collapse in the
    signature, like combine_parallel does for single devices."""
    internal = internal_nodes(ex)
    by_name = {dv.name: dv for dv in ex.devices}
    # chains: walk from each device that touches an external net on one side
    seen = set()
    stacks = []          # (key, [device names in order], [internal node ids in order])
    for dv in ex.devices:
        if dv.name in seen:
            continue
        ends = [dv.s not in internal, dv.d not in internal]
        if not any(ends):
            continue                                 # both S and D internal: reached from a chain end
        if all(ends):
            seen.add(dv.name)
            continue                                 # not in a stack
        start_net = dv.s if ends[0] else dv.d
        chain = [dv.name]; nodes = []
        cur = dv; other = dv.d if ends[0] else dv.s
        while other in internal:
            nodes.append(other)
            nxt = [d for d, _ in ex.nets[other].devices if d != cur.name][0]
            nd = by_name[nxt]
            chain.append(nxt)
            cur = nd
            other = nd.d if nd.s == other else nd.s
        seen.update(chain)
        end_net = other
        gates = [by_name[c].g for c in chain]
        fwd = (start_net, tuple(gates), end_net)
        rev = (end_net, tuple(reversed(gates)), start_net)
        if rev < fwd:
            chain = list(reversed(chain)); nodes = list(reversed(nodes)); fwd = rev
        key = (dv.kind, round(dv.l, 6), fwd)
        stacks.append((key, chain, nodes))
    netmap = {}
    first = {}
    for key, chain, nodes in stacks:
        if key in first:
            for a, b in zip(nodes, first[key]):
                netmap[a] = b
        else:
            first[key] = nodes
    m = lambda n: netmap.get(n, n)
    return [(dv.name, dv.kind, dv.l, dv.w, dv.g, m(dv.s), m(dv.d)) for dv in ex.devices], netmap


def graph_signature(ex, with_w: bool = False, stacks: bool = True) -> str:
    """Topology signature.  Sizes are excluded by default so a resize move
    compares equal (kind and L stay; connectivity must).  With stacks=True
    (the guard's default) series stacks are put in canonical form first, so a
    stack mirrored into a second finger compares equal to the original; the
    reference-netlist isomorphism check uses stacks=False, with_w=True."""
    nodes = {}
    edges = []
    if stacks:
        devs, _ = reduce_stacks(ex)
        if not with_w:                              # parallel fingers collapse (sizes excluded)
            uniq = {}
            for t in devs:
                uniq.setdefault((t[1], round(t[2], 6), t[4], frozenset((t[5], t[6]))), t)
            devs = list(uniq.values())
    else:
        devs = [(dv.name, dv.kind, dv.l, dv.w, dv.g, dv.s, dv.d) for dv in ex.devices]
    for name, kind, l, w, g, s, d in devs:
        nodes["D" + name] = "%s:%g:%s" % (kind, round(l, 4), "%g" % round(w, 3) if with_w else "-")
        for t, n in (("G", g), ("S", s), ("D", d)):
            nodes.setdefault("N%d" % n, "net")
            edges.append(("D" + name, "N%d" % n, "SD" if t in "SD" else "G"))
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
        "isomorphic": graph_signature(ex, with_w=True, stacks=False) == ref_signature(ref),
        "area_perim_match": ap_o == ap_t,
        "ap_only_ours": ap_o - ap_t, "ap_only_ref": ap_t - ap_o,
    }
