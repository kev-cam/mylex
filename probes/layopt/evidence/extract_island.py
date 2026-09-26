#!/usr/bin/env python3
"""Extract one instance-path-prefix ISLAND from the flattened Vortex netlist
(vortex_flat.json, generic gates after simplemap) into a standalone one-module
yosys JSON, so it can be synthesized to SG13G2 stdcells with the SAME recipe as
the alu_cmos anchor.

Island membership uses the IDENTICAL attribution to flat_islands.py (the script
behind consolidated_vector.txt): $flatten name path where present, else
net-name LCP fallback, else 10 rounds of neighbour majority vote. So per-island
cell/seq/mem counts must reproduce the consolidated static vector exactly.

$mem_v2 cells inside the island are EXTERNALIZED (deleted; their connections
become ports): in silicon they are SRAM macros, not clock-tree flop sinks, and
the consolidated per-island 'seq' counts exclude them too.

Usage: extract_island.py vortex_flat.json TOP PREFIX OUT.json NEWTOP
"""
import json, sys, collections
sys.path.insert(0, '/home/claude/vortex_static_char')
from flat_islands import cell_path, norm, SEQ_PREFIXES, MEM_PREFIXES

fj, top, prefix, out, newtop = sys.argv[1:6]
d = json.load(open(fj))
mod = d['modules'][top]
cells = {k: v for k, v in mod['cells'].items() if v['type'] != '$scopeinfo'}

# ---------- attribution (verbatim logic from flat_islands.py main) ----------
paths = {cn: cell_path(cn) for cn in cells}
bitpath = {}
for nname, nn in mod.get('netnames', {}).items():
    if nname.startswith('$') or '.' not in nname:
        continue
    p = norm(nname.rsplit('.', 1)[0])
    if p:
        for b in nn['bits']:
            if isinstance(b, int) and b not in bitpath:
                bitpath[b] = p

def lcp(ps):
    if not ps: return None
    sp = [q.split('.') for q in ps]; o = []
    for i in range(min(len(s) for s in sp)):
        t = sp[0][i]
        if all(s[i] == t for s in sp): o.append(t)
        else: break
    return '.'.join(o) if o else None

todo = [cn for cn, p in paths.items() if not p]
for cn in todo:
    ps = {bitpath[b] for pin, cc in cells[cn]['connections'].items() for b in cc
          if isinstance(b, int) and b in bitpath}
    a = lcp(ps)
    if a:
        paths[cn] = a
netcells = collections.defaultdict(list)
for cn, c in cells.items():
    for pin, cc in c['connections'].items():
        for b in cc:
            if isinstance(b, int):
                netcells[b].append(cn)
for _ in range(10):
    rest, prog = [], 0
    for cn in [c for c in todo if not paths[c]]:
        v = collections.Counter()
        for pin, cc in cells[cn]['connections'].items():
            for b in cc:
                if isinstance(b, int):
                    for o in netcells[b]:
                        if paths.get(o): v[paths[o]] += 1
        if v:
            paths[cn] = v.most_common(1)[0][0]; prog += 1
        else:
            rest.append(cn)
    if not prog: break
# ---------------------------------------------------------------------------

isl, mems = {}, {}
for cn, c in cells.items():
    p = paths.get(cn)
    if p is not None and p.startswith(prefix):
        if c['type'].startswith(MEM_PREFIXES):
            mems[cn] = c
        else:
            isl[cn] = c

nseq = sum(1 for c in isl.values() if c['type'].startswith(SEQ_PREFIXES))
ncomb = len(isl) - nseq
print(f"island '{prefix}': comb={ncomb} seq={nseq} mem={len(mems)} "
      f"(consolidated-vector attribution)")
for cn, c in mems.items():
    pr = c.get('parameters', {})
    def iv(x):
        v = pr.get(x, '?')
        return int(v, 2) if isinstance(v, str) and set(v) <= {'0', '1'} else v
    print(f"  mem externalized: SIZE={iv('SIZE')} WIDTH={iv('WIDTH')} "
          f"RD_PORTS={iv('RD_PORTS')} WR_PORTS={iv('WR_PORTS')} ({cn[:80]})")

def pins(c):
    dirs = c.get('port_directions', {})
    for port, bits in c['connections'].items():
        pd = dirs.get(port)
        for b in bits:
            if isinstance(b, int):
                yield port, pd, b

# driver map over the WHOLE flat module (cells + top input ports)
driver = {}
for cn, c in cells.items():
    for port, pd, b in pins(c):
        if pd == 'output':
            driver[b] = cn
TOPIN = '<topin>'
top_port_name = {}
for pn, p in mod['ports'].items():
    for b in p['bits']:
        if isinstance(b, int):
            top_port_name.setdefault(b, pn)
            if p['direction'] == 'input':
                driver.setdefault(b, TOPIN)

used_in, driven_in = set(), set()
for cn, c in isl.items():
    for port, pd, b in pins(c):
        (driven_in if pd == 'output' else used_in).add(b)
used_out = set()
for cn, c in cells.items():
    if cn in isl:
        continue
    for port, pd, b in pins(c):
        if pd != 'output':
            used_out.add(b)
for pn, p in mod['ports'].items():
    if p['direction'] == 'output':
        used_out.update(b for b in p['bits'] if isinstance(b, int))

in_bits = sorted(b for b in used_in
                 if b not in driven_in and driver.get(b) is not None)
undriven = sorted(b for b in used_in if b not in driven_in and driver.get(b) is None)
if undriven:
    print(f"  WARNING: {len(undriven)} undriven bits used by island -> made inputs")
    in_bits += undriven
out_bits = sorted(b for b in driven_in if b in used_out)

ports, netnames = {}, {}
def portname(b):
    base = top_port_name.get(b)
    if base in ('clk', 'reset'):
        return base
    return f'isl_i_{b}'
for b in in_bits:
    n = portname(b)
    ports[n] = {'direction': 'input', 'bits': [b]}
for b in out_bits:
    ports[f'isl_o_{b}'] = {'direction': 'output', 'bits': [b]}
for pn, p in ports.items():
    netnames[pn] = {'bits': p['bits'], 'hide_name': 0}

newmod = {'attributes': {'top': '00000000000000000000000000000001'},
          'ports': ports,
          'cells': isl,
          'netnames': netnames}
json.dump({'creator': 'extract_island.py', 'modules': {newtop: newmod}},
          open(out, 'w'))
print(f"wrote {out}: top={newtop} ports={len(ports)} "
      f"(in={len(in_bits)} out={len(out_bits)}) cells={len(isl)} "
      f"comb={ncomb} seq={nseq}")
print(f"  clk port present: {'clk' in ports}; reset port present: {'reset' in ports}")
