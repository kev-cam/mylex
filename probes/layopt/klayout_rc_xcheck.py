# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""Cross-check layopt's geometry engine against KLayout: same nets (flat L2N from
kestrel's extract.py), KLayout's merged-region area/perimeter per (net, layer),
layopt's C formula. Compares per-layer totals and the sorted per-net C list."""
import sys, collections
sys.path.insert(0, '/usr/local/src/mylex')
import klayout.db as kdb
from layopt import gds, tech, extract, rc, geom
S = sys.argv[1] if len(sys.argv) > 1 else '.'   # dir holding kestrel_pll_klayout0.30.l2n (kestrel layout/extract.py output)
T = tech.SKY130
l2n = kdb.LayoutToNetlist(); l2n.read(S + '/kestrel_pll_klayout0.30.l2n')
dbu = l2n.internal_layout().dbu
layers = {n: l2n.layer_by_name(n) for n in ('poly', 'li', 'met1', 'met2', 'met3') if l2n.layer_by_name(n) is not None}
kl_total = collections.defaultdict(lambda: [0.0, 0.0]); kl_nets = []
top = l2n.netlist().top_circuit()
for net in top.each_net():
    c = 0.0
    for ln, reg in layers.items():
        r = l2n.shapes_of_net(net, reg, True).merged()
        a, p = r.area() * dbu * dbu, r.perimeter() * dbu
        kl_total[ln][0] += a; kl_total[ln][1] += p
        c += T.carea.get(ln, 0) * a + T.cfringe.get(ln, 0) * p
    kl_nets.append(c)
fl = gds.flatten(gds.read('/usr/local/src/kestrel/layout/kestrel_pll.gds')); ex = extract.extract(fl, T)
lo_total = collections.defaultdict(lambda: [0.0, 0.0]); lo_nets = []
d = fl.dbu_um
for nid, net in ex.nets.items():
    by = collections.defaultdict(list)
    for s in net.shapes: by[ex.shapes[s].layer].append(ex.shapes[s].rect)
    c = 0.0
    for ln, rects in by.items():
        if ln not in layers: continue
        a, p = geom.union_area_perimeter(rects); a, p = a * d * d, p * d
        lo_total[ln][0] += a; lo_total[ln][1] += p
        c += T.carea.get(ln, 0) * a + T.cfringe.get(ln, 0) * p
    lo_nets.append(c)
print("%-6s %14s %14s   %14s %14s" % ("layer", "kl area um2", "lo area um2", "kl perim um", "lo perim um"))
for ln in layers:
    print("%-6s %14.3f %14.3f   %14.3f %14.3f" % (ln, kl_total[ln][0], lo_total[ln][0], kl_total[ln][1], lo_total[ln][1]))
kl_nets.sort(reverse=True); lo_nets.sort(reverse=True)
print("nets: klayout %d (device-connected, purged) layopt %d (all)" % (len(kl_nets), len(lo_nets)))
print("total C fF: klayout-geometry %.2f  layopt %.2f" % (sum(kl_nets), sum(lo_nets)))
print("top-8 C fF klayout-geometry:", [round(x, 2) for x in kl_nets[:8]])
print("top-8 C fF layopt          :", [round(x, 2) for x in lo_nets[:8]])
