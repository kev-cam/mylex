#!/usr/bin/env python3
"""Analyze th23 2-of-3-majority (NCL hysteresis) Monte-Carlo runs:
functional yield + delay stats. Reads per-sample Xyce measure files
<deck>.mt0..mtN (one sample each). Adapted from analyze_mc.py (th22).

Sequence / expected levels:
  yrst0 reset(000)->0   yset1 set(110)->1   yhld1 hold(100)->1
  yrst2 reset(000)->0   yhld0 hold(001)->0  yset2 set(011)->1
Delays: tset1 (P1 set rise), trst (P3 reset fall), tset2 (P5 set rise).
"""
import glob, os, re, sys, statistics as st, json

VDD = 1.2
HI = 0.6 * VDD   # a "high" must exceed this (0.72 V)
LO = 0.4 * VDD   # a "low"  must stay below this (0.48 V)
LEVELS = {'yrst0':'lo','yset1':'hi','yhld1':'hi','yrst2':'lo','yhld0':'lo','yset2':'hi'}
DELAYS = ['tset1','trst','tset2']

def read_mt(path):
    d = {}
    for ln in open(path):
        m = re.match(r'\s*([A-Za-z]\w*)\s*=\s*(\S+)', ln)
        if m:
            k = m.group(1).lower()
            v = m.group(2)
            try: d[k] = float(v)
            except ValueError: d[k] = v   # "FAILED" etc.
    return d

def analyze(deck, emit_json=False):
    files = sorted(glob.glob(deck + '.mt*'),
                   key=lambda p: int(re.search(r'mt(\d+)$', p).group(1)))
    if not files:
        print("  no .mt files for %s" % deck); return None
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
    print("  samples=%d  functional=%d  yield=%.1f%%" % (n, func, 100.0*func/n))
    dstats = {}
    for dn in DELAYS:
        vals = [s[dn]*1e12 for s in samples if isinstance(s.get(dn), float) and s[dn] > 0]
        nfail = n - len(vals)
        if not vals:
            print("    %-6s: no valid measurements (%d failed)" % (dn, nfail)); continue
        mean = st.mean(vals); sd = st.pstdev(vals)
        dstats[dn] = dict(mean_ps=mean, sd_ps=sd, min_ps=min(vals), max_ps=max(vals), fail=nfail)
        print("    %-6s: mean=%7.1f ps  sd=%5.1f ps  min=%7.1f  max=%7.1f  3sig=%7.1f ps  (fail=%d)"
              % (dn, mean, sd, min(vals), max(vals), mean+3*sd, nfail))
    res = dict(samples=n, functional=func, delays=dstats)
    if emit_json:
        print("JSON " + json.dumps(res))
    return res

if __name__ == '__main__':
    for deck in sys.argv[1:]:
        print("=== %s ===" % os.path.basename(deck))
        analyze(deck, emit_json=True)
