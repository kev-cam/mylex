#!/usr/bin/env python3
"""Generate an N-bit NCL ripple-carry adder MC subckt + worst-case deck, to
independently validate the stat-sim in-context tiled mu(N) prediction. Worst-case
vector A=1..1, B=0..0, Cin=1 propagates the carry ci->c1->...->coH (coH is an
N-deep th23 carry chain). Reuses nclfa_mc/th23_mc/th34w2_mc (kvt threaded).
Usage: gen_ripple.py <N> <outdir> [Nsamp] [kvt]"""
import sys, os, json
VDD=1.2; PH=4.0e-9; EDGE=0.2e-9
HERE=os.path.dirname(os.path.abspath(__file__))
MODEL="/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
VA="/usr/local/share/xyce/verilog-a/psp103/psp103.va"

def subckt(N):
    ins=" ".join("a%dH a%dL"%(i,i) for i in range(N))
    insb=" ".join("b%dH b%dL"%(i,i) for i in range(N))
    outs=" ".join("s%dH s%dL"%(i,i) for i in range(N))
    L=["* %d-bit NCL ripple adder MC subckt (kvt threaded to each nclfa)"%N,
       ".subckt nclfa%d %s %s ciH ciL %s coH coL VDD VSS"%(N,ins,insb,outs),
       ".param kvt=1"]
    for i in range(N):
        cin = ("ciH ciL" if i==0 else "c%dH c%dL"%(i,i))
        cout= ("coH coL" if i==N-1 else "c%dH c%dL"%(i+1,i+1))
        L.append("Xfa%d a%dH a%dL b%dH b%dL %s s%dH s%dL %s VDD VSS nclfa kvt={kvt}"
                 %(i,i,i,i,i,cin,i,i,cout))
    L.append(".ends nclfa%d"%N)
    return "\n".join(L)+"\n"

def deck(N, Nsamp, kvt):
    # DATA window long enough for an N-deep ripple (~0.4ns/stage) to settle
    DATA=max(12.0e-9, N*0.5e-9+6e-9); t0=PH; t1=PH+DATA; tstop=t1+PH
    val={}
    for i in range(N):
        val["a%dH"%i]=1; val["a%dL"%i]=0    # A=1..1
        val["b%dH"%i]=0; val["b%dL"%i]=1    # B=0..0
    val["ciH"]=1; val["ciL"]=0              # Cin=1
    ins=" ".join("a%dH a%dL"%(i,i) for i in range(N))
    insb=" ".join("b%dH b%dL"%(i,i) for i in range(N))
    outs=" ".join("s%dH s%dL"%(i,i) for i in range(N))
    L=["* %d-bit ripple worst-case carry (A=1..1,B=0..0,Cin=1): coH = %d-deep th23 chain"%(N,N),
       '.hdl "%s"'%VA, '.include "%s"'%MODEL,
       '.include "%s/th23_mc.sp"'%HERE, '.include "%s/th34w2_mc.sp"'%HERE,
       '.include "%s/nclfa_mc.sp"'%HERE, '.include "%s/nclfa%d_mc.sp"'%(HERE,N),
       ".param kvt=%g"%kvt, "VVDD VDD 0 %g"%VDD,
       "Xdut %s %s ciH ciL %s coH coL VDD 0 nclfa%d kvt={kvt}"%(ins,insb,outs,N),
       "CcoH coH 0 2f"]
    for r,v in val.items():
        vv=VDD if v else 0.0
        L.append("V%s %s 0 PWL(0 0 %.4gn 0 %.4gn %.3g %.4gn %.3g %.4gn 0)"
                 %(r,r,t0*1e9,(t0+EDGE)*1e9,vv,t1*1e9,vv,(t1+EDGE)*1e9))
    L.append(".tran 20p %.4gn"%(tstop*1e9))
    tm=t1-0.4e-9
    L.append(".measure tran cout FIND V(coH) AT=%.4gn"%(tm*1e9))
    L.append(".measure tran tripple TRIG V(ciH) VAL=0.6 RISE=1 TD=%.4gn TARG V(coH) VAL=0.6 RISE=1 TD=%.4gn"
             %((t0-0.1e-9)*1e9,(t0-0.1e-9)*1e9))
    L.append(".SAMPLING useExpr=true")
    L.append(".options SAMPLES numsamples=%d SAMPLE_TYPE=MC SEED=1"%Nsamp)
    L.append("+ measures=cout,tripple OUTPUT_SAMPLE_STATS=true stdoutput=true")
    L.append(".end")
    return "\n".join(L)+"\n"

if __name__=="__main__":
    N=int(sys.argv[1]); outdir=sys.argv[2]
    Nsamp=int(sys.argv[3]) if len(sys.argv)>3 else 200
    kvt=float(sys.argv[4]) if len(sys.argv)>4 else 1
    open("%s/nclfa%d_mc.sp"%(HERE,N),"w").write(subckt(N))
    open("%s/mc_nclfa%d.cir"%(outdir,N),"w").write(deck(N,Nsamp,kvt))
    print("wrote %s/nclfa%d_mc.sp + %s/mc_nclfa%d.cir (N=%d, Nsamp=%d, kvt=%g)"
          %(HERE,N,outdir,N,N,Nsamp,kvt))
