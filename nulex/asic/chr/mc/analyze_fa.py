#!/usr/bin/env python3
"""Analyze nclfa full-adder Monte-Carlo runs: functional yield + completion latency.

A sample is FUNCTIONAL iff EVERY output measure is on the correct side of VDD/2:
each DATA-phase output rail must match the expected dual-rail codeword (HIGH>0.72V
/ LOW<0.48V) and every final-NULL output must return LOW (RTZ). Expected levels
come from <deck>.expected.json (written by gen_fa_deck.py). Reads per-sample
<deck>.mt0..mtN. Usage: analyze_fa.py <deck.cir> [<deck.cir> ...]"""
import glob, json, os, re, sys, statistics as st

HI, LO = 0.72, 0.48

def read_mt(path):
    d = {}
    for ln in open(path):
        m = re.match(r'\s*([A-Za-z]\w*)\s*=\s*(\S+)', ln)
        if m:
            try: d[m.group(1).lower()] = float(m.group(2))
            except ValueError: d[m.group(1).lower()] = m.group(2)
    return d

def analyze(deck):
    exp = json.load(open(deck + '.expected.json'))
    files = sorted(glob.glob(deck + '.mt*'),
                   key=lambda p: int(re.search(r'mt(\d+)$', p).group(1)))
    files = [f for f in files if not f.endswith('.json')]
    if not files:
        print("  %s: no .mt files" % os.path.basename(deck)); return
    n = len(files); func = 0
    perfail = {}          # measure -> #samples that got it wrong
    lat = []
    for f in files:
        mt = read_mt(f); ok = True
        for nm, e in exp.items():
            v = mt.get(nm)
            wrong = (not isinstance(v, float)) or (e == 'H' and v < HI) or (e == 'L' and v > LO)
            if wrong:
                ok = False; perfail[nm] = perfail.get(nm, 0) + 1
        func += ok
        tv = mt.get('tvalid')
        if isinstance(tv, float) and tv > 0: lat.append(tv * 1e12)
    print("  %-16s samples=%d  functional=%d  yield=%.1f%%"
          % (os.path.basename(deck), n, func, 100.0 * func / n))
    if perfail:
        top = sorted(perfail.items(), key=lambda kv: -kv[1])[:6]
        print("    wrong-output tallies: " + ", ".join("%s:%d" % (k, v) for k, v in top))
    if lat:
        print("    completion latency tvalid: mean=%.1f sd=%.1f min=%.1f max=%.1f ps (n=%d)"
              % (st.mean(lat), st.pstdev(lat), min(lat), max(lat), len(lat)))

if __name__ == '__main__':
    for d in sys.argv[1:]:
        analyze(d)
