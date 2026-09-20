#!/usr/bin/env python3
"""Analyze th14 OR4 Monte-Carlo runs: functional yield + delay stats.
Adapted from analyze_mc.py for th14's measure names."""
import glob, os, re, sys, json, statistics as st

VDD = 1.2
HI = 0.6 * VDD   # a "high" must exceed this (0.72 V)
LO = 0.4 * VDD   # a "low" must stay below this (0.48 V)
LEVELS = {'y0':'lo','y1':'hi','y2':'hi','y3':'hi','y4':'hi','y5':'hi','y6':'lo'}
DELAYS = ['tset1','trst']

def read_mt(path):
    d = {}
    for ln in open(path):
        m = re.match(r'\s*([A-Za-z]\w*)\s*=\s*(\S+)', ln)
        if m:
            k = m.group(1).lower()
            v = m.group(2)
            try: d[k] = float(v)
            except ValueError: d[k] = v
    return d

def analyze(deck):
    files = sorted(glob.glob(deck + '.mt*'),
                   key=lambda p: int(re.search(r'mt(\d+)$', p).group(1)))
    samples = [read_mt(f) for f in files]
    n = len(samples)
    func = 0
    for s in samples:
        ok = True
        for name, kind in LEVELS.items():
            v = s.get(name)
            if not isinstance(v, float): ok = False; break
            if kind == 'hi' and v < HI: ok = False; break
            if kind == 'lo' and v > LO: ok = False; break
        func += ok
    res = {'total': n, 'functional': func, 'delays': {}}
    for dn in DELAYS:
        vals = [s[dn]*1e12 for s in samples if isinstance(s.get(dn), float) and s[dn] > 0]
        if vals:
            res['delays'][dn] = {
                'mean': st.mean(vals), 'sd': st.pstdev(vals),
                'min': min(vals), 'max': max(vals), 'nfail': n - len(vals)}
        else:
            res['delays'][dn] = None
    return res

if __name__ == '__main__':
    allres = {}
    for K in [1,2,3,4]:
        deck = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mc_k%d.cir' % K)
        r = analyze(deck)
        allres[K] = r
        print("=== kvt=%d ===" % K)
        print("  samples=%d functional=%d yield=%.1f%%" % (r['total'], r['functional'], 100.0*r['functional']/r['total']))
        for dn in DELAYS:
            d = r['delays'][dn]
            if d:
                print("    %-6s mean=%7.2f sd=%6.2f min=%7.2f max=%7.2f ps (fail=%d)" %
                      (dn, d['mean'], d['sd'], d['min'], d['max'], d['nfail']))
            else:
                print("    %-6s: no valid measurements" % dn)
    print("\nJSON:")
    print(json.dumps(allres))
