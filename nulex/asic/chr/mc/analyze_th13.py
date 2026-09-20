#!/usr/bin/env python3
"""Analyze th13 OR3 Monte-Carlo runs: functional yield + delay stats.
Reads the per-sample Xyce measure files <deck>.mt0..mtN (one sample each).
Emits a JSON blob per deck for the workflow to consume."""
import glob, os, re, sys, json, statistics as st

VDD = 1.2
HI = 0.6 * VDD   # a "high" must exceed this (0.72 V)
LO = 0.4 * VDD   # a "low" must stay below this (0.48 V)
# functional level measures and their expected side
LEVELS = {'y0lo':'lo','y1hi':'hi','y2lo':'lo','y3hi':'hi','y4lo':'lo',
          'y5hi':'hi','y6lo':'lo','y7hi':'hi','y8lo':'lo'}
DELAYS = ['tr_a','tf_a','tr_b','tf_b','tr_c','tf_c','tr_all','tf_all']

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
    if not files:
        return None
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
    res = {'deck': os.path.basename(deck), 'n': n, 'functional': func, 'delays': {}}
    for dn in DELAYS:
        vals = [s[dn]*1e12 for s in samples
                if isinstance(s.get(dn), float) and s[dn] > 0]
        if not vals:
            res['delays'][dn] = None
            continue
        res['delays'][dn] = {
            'mean': st.mean(vals), 'sd': st.pstdev(vals),
            'min': min(vals), 'max': max(vals), 'nvalid': len(vals)}
    return res

if __name__ == '__main__':
    out = {}
    for deck in sys.argv[1:]:
        r = analyze(deck)
        if r is None:
            print("  no .mt files for %s" % deck, file=sys.stderr); continue
        out[r['deck']] = r
        print("=== %s ===" % r['deck'])
        print("  samples=%d functional=%d yield=%.1f%%"
              % (r['n'], r['functional'], 100.0*r['functional']/r['n']))
        for dn in DELAYS:
            v = r['delays'][dn]
            if v is None:
                print("    %-7s: no valid measurements" % dn); continue
            print("    %-7s: mean=%7.1f ps sd=%5.1f ps min=%7.1f max=%7.1f (n=%d)"
                  % (dn, v['mean'], v['sd'], v['min'], v['max'], v['nvalid']))
    print("JSON " + json.dumps(out))
