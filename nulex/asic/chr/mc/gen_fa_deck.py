#!/usr/bin/env python3
"""Generate an NCL full-adder (nclfa) Monte-Carlo deck + expected-output map.

nclfa is dual-rail (return-to-zero NCL): each logical input X is a rail pair
(xH=value-1 rail, xL=value-0 rail); NULL = both rails 0, DATA = exactly one rail
high. The block computes Sum=A^B^Cin and Cout=maj(A,B,Cin) via
  coH=TH23(aH,bH,ciH)  coL=TH23(aL,bL,ciL)
  sH =TH34W2(coL,aH,bH,ciH)  sL=TH34W2(coH,aL,bL,ciL)   (weight-2 input first)

The stimulus walks NULL,DATA_i,NULL,... over all 8 input vectors (A,B,Cin).
After each DATA the four outputs must equal the correct dual-rail codeword; after
each NULL all four outputs must return to 0 (RTZ). Per-device Vt mismatch comes
from th23_mc.sp / th34w2_mc.sp (each subckt instance gets independent AGAUSS
draws -> 60 independent per-device DELVTO). Usage: gen_fa_deck.py <out.cir> [N] [kvt]
"""
import sys, json, os

VDD = 1.2
PH  = 4.0e-9      # phase length
EDGE= 0.2e-9      # rail slew
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = "/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
VA    = "/usr/local/share/xyce/verilog-a/psp103/psp103.va"

def fa(a, b, ci):
    s = a ^ b ^ ci
    co = 1 if (a + b + ci) >= 2 else 0
    return s, co

# input vectors (A,B,Cin) 0..7
VECS = [(a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)]

def build(out, N=200, kvt=1):
    # phase sequence: NULL, D0, NULL, D1, ..., D7, NULL
    # rails: aH aL bH bL ciH ciL ; value V -> H=V, L=!V during DATA, both 0 in NULL
    rails = ['aH', 'aL', 'bH', 'bL', 'ciH', 'ciL']
    pts = {r: [(0.0, 0.0)] for r in rails}       # PWL point lists
    meas = []          # (name, node, t, expected 'H'/'L')
    expected = {}
    t = PH             # phase 0 = initial NULL over [0,PH]
    lat = None
    for i, (a, b, ci) in enumerate(VECS):
        s, co = fa(a, b, ci)
        val = {'aH': a, 'aL': 1 - a, 'bH': b, 'bL': 1 - b, 'ciH': ci, 'ciL': 1 - ci}
        # DATA_i over [t, t+PH]
        for r in rails:
            v = VDD if val[r] else 0.0
            pts[r] += [(t, 0.0), (t + EDGE, v)]              # rise at DATA start
            pts[r] += [(t + PH, v), (t + PH + EDGE, 0.0)]    # fall back to NULL at end
        # measure outputs just before DATA end
        tm = t + PH - 0.3e-9
        outs = {'sH': s, 'sL': 1 - s, 'coH': co, 'coL': 1 - co}
        for node, hi in outs.items():
            nm = 'd%d_%s' % (i, node.lower())
            meas.append((nm, node, tm, 'H' if hi else 'L'))
            expected[nm] = 'H' if hi else 'L'
        # forward-latency probe on the all-ones vector (deepest path: co->s)
        if (a, b, ci) == (1, 1, 1):
            lat = (t, 'sH')   # DATA assert time, slow output
        t += 2 * PH          # skip the trailing NULL phase to next DATA
    # final NULL RTZ check (after last DATA's trailing NULL)
    tnull = t - PH + PH - 0.3e-9   # mid of the final NULL
    for node in ('sH', 'sL', 'coH', 'coL'):
        nm = 'n_%s' % node.lower()
        meas.append((nm, node, tnull, 'L'))
        expected[nm] = 'L'
    tstop = t

    L = []
    L.append('* NCL full-adder (nclfa) Monte-Carlo Vt-mismatch deck (auto: gen_fa_deck.py)')
    L.append('* Dual-rail NULL/DATA over all 8 (A,B,Cin) vectors; per-device DELVTO from')
    L.append('* th23_mc.sp / th34w2_mc.sp (independent AGAUSS per subckt instance = 60 devs).')
    L.append('.hdl "%s"' % VA)
    L.append('.include "%s"' % MODEL)
    L.append('.include "%s/th23_mc.sp"' % HERE)
    L.append('.include "%s/th34w2_mc.sp"' % HERE)
    # nclfa_mc.sp (NOT the plain ldx nclfa.sp) so kvt threads down to the gates.
    L.append('.include "%s/nclfa_mc.sp"' % HERE)
    L.append('.param kvt=%g' % kvt)
    L.append('VVDD VDD 0 %g' % VDD)
    L.append('Xdut aH aL bH bL ciH ciL sH sL coH coL VDD 0 nclfa kvt={kvt}')
    for o in ('sH', 'sL', 'coH', 'coL'):
        L.append('C%s %s 0 2f' % (o, o))
    def pwl(r):
        # dedup consecutive identical-time points, keep monotone time
        seq = pts[r]
        s = []
        for (tt, vv) in seq:
            if s and abs(s[-1][0] - tt) < 1e-15:
                s[-1] = (tt, vv)
            else:
                s.append((tt, vv))
        return ' '.join('%.4gn %.3g' % (tt * 1e9, vv) for (tt, vv) in s)
    for r in rails:
        L.append('V%s %s 0 PWL(%s)' % (r, r, pwl(r)))
    L.append('.tran 20p %.4gn' % (tstop * 1e9))
    for (nm, node, tm, _hi) in meas:
        L.append('.measure tran %s FIND V(%s) AT=%.4gn' % (nm, node, tm * 1e9))
    if lat:
        t0, slow = lat
        L.append('.measure tran tvalid TRIG V(aH) VAL=0.6 RISE=1 TD=%.4gn TARG V(%s) VAL=0.6 RISE=1 TD=%.4gn'
                 % ((t0 - 0.1e-9) * 1e9, slow, (t0 - 0.1e-9) * 1e9))
    names = ','.join(nm for (nm, _n, _t, _h) in meas) + (',tvalid' if lat else '')
    L.append('.SAMPLING useExpr=true')
    L.append('.options SAMPLES numsamples=%d SAMPLE_TYPE=MC SEED=1' % N)
    L.append('+ measures=%s' % names)
    L.append('+ OUTPUT_SAMPLE_STATS=true stdoutput=true')
    L.append('.end')
    open(out, 'w').write('\n'.join(L) + '\n')
    json.dump(expected, open(out + '.expected.json', 'w'), indent=0)
    print('wrote %s (%d measures, %d vectors, tstop=%.1fns) + .expected.json'
          % (out, len(meas), len(VECS), tstop * 1e9))

if __name__ == '__main__':
    a = sys.argv
    build(a[1], int(a[2]) if len(a) > 2 else 200, float(a[3]) if len(a) > 3 else 1)
