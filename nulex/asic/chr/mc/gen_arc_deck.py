#!/usr/bin/env python3
"""Per-arc characterization decks: isolate a specific input timing-arc of a TH
cell and MC its delay under Vt mismatch, at a realistic fanout load (2 fF). Closes
the mu gap where the single-cell MC measured a different (faster) arc than the one
a composed design exercises.

Arcs characterized (the ones the FA / nclfa4 use):
  th34w2-w1 : weight-1 arc — a(weight-2)=0, b,c,d rise together -> y (3-series B.C.D
              branch; the FA sum sH path, ~2x slower than the weight-2 arc).
  th23-cin  : carry-in arc — a=1 held, c rises last -> y (the ripple carry arc).
Usage: gen_arc_deck.py <arc> <out.cir> [N] [kvt]   arc in {th34w2-w1, th23-cin}
"""
import sys, json, os
VDD=1.2; HERE=os.path.dirname(os.path.abspath(__file__))
MODEL="/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
VA="/usr/local/share/xyce/verilog-a/psp103/psp103.va"

ARCS={
 # cell, pins(order), instline, driven-signals PWL spec, TRIG node, expected y at DATA end
 "th34w2-w1": dict(cell="th34w2", inc="th34w2_mc.sp", pins="a b c d y",
    inst="Xdut a b c d y VDD 0 th34w2 kvt={kvt}",
    src={"a":"0", "b":"pulse@5", "c":"pulse@5", "d":"pulse@5"},
    trig="b", expect_hi=True,
    note="weight-1 arc: a(w2)=0, b,c,d rise together (2*0+3>=3)"),
 "th23-cin": dict(cell="th23", inc="th23_mc.sp", pins="a b c y",
    inst="Xdut a b c y VDD 0 th23 kvt={kvt}",
    src={"a":"pulse@5", "b":"0", "c":"pulse@6"},   # a settles first, c arrives last
    trig="c", expect_hi=True,
    note="carry-in arc: a rises@5n (held), c rises@6n last (2 high -> y)"),
}

def pwl(spec):
    if spec=="0": return "0 0"
    # pulse@T : 0 until T ns, rise, hold to 9.9n, fall (single DATA over [T,10])
    T=float(spec.split("@")[1])
    return "0 0  %.4gn 0  %.4gn %g  9.9n %g  10n 0"%(T, T+0.2, VDD, VDD)

def build(arc, out, N=200, kvt=1):
    a=ARCS[arc]
    L=[]
    L.append("* per-arc characterization: %s  (%s)"%(arc, a["note"]))
    L.append('.hdl "%s"'%VA); L.append('.include "%s"'%MODEL)
    L.append('.include "%s/%s"'%(HERE, a["inc"]))
    L.append('.param kvt=%g'%kvt)
    L.append('VVDD VDD 0 %g'%VDD)
    L.append(a["inst"])
    L.append('Cy y 0 2f')
    for sig,spec in a["src"].items():
        L.append('V%s %s 0 PWL(%s)'%(sig,sig,pwl(spec)))
    L.append('.tran 10p 12n')
    L.append('.measure tran ylev FIND V(y) AT=9.7n')          # functional (expect ~VDD)
    L.append('.measure tran tarc TRIG V(%s) VAL=0.6 RISE=1 TARG V(y) VAL=0.6 RISE=1'%a["trig"])
    L.append('.SAMPLING useExpr=true')
    L.append('.options SAMPLES numsamples=%d SAMPLE_TYPE=MC SEED=1'%N)
    L.append('+ measures=ylev,tarc OUTPUT_SAMPLE_STATS=true stdoutput=true')
    L.append('.end')
    open(out,'w').write('\n'.join(L)+'\n')
    print("wrote %s (arc=%s, cell=%s)"%(out,arc,a["cell"]))

if __name__=="__main__":
    v=sys.argv
    build(v[1], v[2], int(v[3]) if len(v)>3 else 200, float(v[4]) if len(v)>4 else 1)
