#!/usr/bin/env python3
"""Generate the nclfa4 (4-bit ripple adder) MC deck: worst-case carry-ripple
vector A=1111,B=0000,Cin=1 (carry propagates ci->c1->c2->c3->coH, so coH is a
4-deep th23 chain), for validating stat-sim's [th23]*4 composition prediction.
Usage: gen_fa4_deck.py <out.cir> [N] [kvt]"""
import sys, json, os
VDD = 1.2; PH = 4.0e-9; DATA = 12.0e-9; EDGE = 0.2e-9
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = "/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
VA = "/usr/local/share/xyce/verilog-a/psp103/psp103.va"

def build(out, N=200, kvt=1):
    # A=1111 B=0000 Cin=1  -> sum=0000, cout=1 (full carry ripple)
    A=[1,1,1,1]; B=[0,0,0,0]; CIN=1
    val={}
    for i in range(4):
        val['a%dH'%i]=A[i]; val['a%dL'%i]=1-A[i]
        val['b%dH'%i]=B[i]; val['b%dL'%i]=1-B[i]
    val['ciH']=CIN; val['ciL']=1-CIN
    rails=list(val.keys())
    # phases: NULL[0,PH] DATA[PH,PH+DATA] NULL[PH+DATA, +PH]
    t0=PH; t1=PH+DATA; tstop=t1+PH
    L=[]
    L.append('* nclfa4 4-bit ripple adder MC: worst-case carry ripple (A=1111,B=0000,Cin=1)')
    L.append('* coH completion = 4-deep th23 carry chain -> validates stat-sim [th23]*4.')
    L.append('.hdl "%s"'%VA); L.append('.include "%s"'%MODEL)
    L.append('.include "%s/th23_mc.sp"'%HERE)
    L.append('.include "%s/th34w2_mc.sp"'%HERE)
    L.append('.include "%s/nclfa_mc.sp"'%HERE)
    L.append('.include "%s/nclfa4_mc.sp"'%HERE)
    L.append('.param kvt=%g'%kvt)
    L.append('VVDD VDD 0 %g'%VDD)
    ports=('a0H a0L a1H a1L a2H a2L a3H a3L b0H b0L b1H b1L b2H b2L b3H b3L '
           'ciH ciL s0H s0L s1H s1L s2H s2L s3H s3L coH coL VDD 0')
    L.append('Xdut %s nclfa4 kvt={kvt}'%ports)
    for o in ('coH','coL','s0H','s1H','s2H','s3H'):
        L.append('C%s %s 0 2f'%(o,o))
    # input PWL: 0 in NULL, val*VDD in DATA
    for r in rails:
        v=VDD if val[r] else 0.0
        pwl='0 0  %.4gn 0  %.4gn %.3g  %.4gn %.3g  %.4gn 0'%(
            t0*1e9, (t0+EDGE)*1e9, v, t1*1e9, v, (t1+EDGE)*1e9)
        L.append('V%s %s 0 PWL(%s)'%(r,r,pwl))
    L.append('.tran 20p %.4gn'%(tstop*1e9))
    tm=(t1-0.4e-9)  # measure near DATA end
    # functional levels: expected sum=0000 (s*H low), cout=1 (coH high)
    exp={}
    for nm,node,hi in [('cout','coH',1),('coutl','coL',0),
                       ('sum0','s0H',0),('sum1','s1H',0),('sum2','s2H',0),('sum3','s3H',0)]:
        L.append('.measure tran %s FIND V(%s) AT=%.4gn'%(nm,node,tm*1e9))
        exp[nm]='H' if hi else 'L'
    # carry-chain completion latency: ci rise -> coH rise (4-deep th23)
    L.append('.measure tran tripple TRIG V(ciH) VAL=0.6 RISE=1 TD=%.4gn TARG V(coH) VAL=0.6 RISE=1 TD=%.4gn'
             %((t0-0.1e-9)*1e9,(t0-0.1e-9)*1e9))
    names=','.join(exp.keys())+',tripple'
    L.append('.SAMPLING useExpr=true')
    L.append('.options SAMPLES numsamples=%d SAMPLE_TYPE=MC SEED=1'%N)
    L.append('+ measures=%s'%names)
    L.append('+ OUTPUT_SAMPLE_STATS=true stdoutput=true')
    L.append('.end')
    open(out,'w').write('\n'.join(L)+'\n')
    json.dump(exp,open(out+'.expected.json','w'),indent=0)
    print('wrote %s (tstop=%.1fns) + expected.json'%(out,tstop*1e9))

if __name__=='__main__':
    a=sys.argv
    build(a[1], int(a[2]) if len(a)>2 else 200, float(a[3]) if len(a)>3 else 1)
