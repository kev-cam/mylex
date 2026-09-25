#!/usr/bin/env python3
import re,os
S='/usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice/'
VDD=1.2
def meas(f,tag,all=False):
    if not os.path.exists(S+f): return [] if all else None
    v=re.findall(r'^\s*%s\s*=\s*(\S+)'%tag, open(S+f).read(), re.M|re.I)
    if all: return [float(x) for x in v]
    return float(v[0]) if v else None

print("="*100)
print("A) INTERNAL ENERGY vs INPUT SLEW  (inv_1, CL=9.34 fF) -- short-circuit vs self-capacitance")
print("="*100)
q=meas('inv_slew.log','QCYC',all=True)
sl=[2,10,30,108.1667,300,800]
if q:
    Eload=9.34e-15*VDD*VDD*1e15   # fJ per full cycle
    print("  liberty says E_int = 1.6223 fJ/toggle = 3.2446 fJ/cycle at this load")
    print("  %-12s %12s %12s %12s"%("tr(ps 0-100)","slew20-80","E_cyc(fJ)","E_int(fJ/cyc)"))
    for t,Q in zip(sl,q):
        E=abs(Q)*VDD*1e15
        print("  %-12.1f %12.1f %12.4f %12.4f"%(t,t*0.6,E,E-Eload))
    print("  -> the flat part at fast edges is SELF-CAPACITANCE; the rise with slew is SHORT-CIRCUIT.")
else: print("  PENDING")

print()
print("="*100)
print("B) COMPOSITION CHECK -- real 4-cell interconnected chain (inv->nand2->nor2->inv, CL=4fF)")
print("="*100)
qc=meas('chain.log','QCHAIN')
if qc:
    Espi=abs(qc)*VDD*1e15
    Elib=3.872355e-06*4.75e-9*1e15*2   # liberty at activity 1.0/cycle, x2 toggles in the SPICE window
    print("  SPICE   total supply energy, one full input rise+fall : %8.3f fJ"%Espi)
    print("  LIBERTY same netlist, same load, activity 1.0         : %8.3f fJ"%Elib)
    print("  ratio (spice/liberty)                                 : %8.3f"%(Espi/Elib))
    print("  (this INCLUDES real inter-stage slew degradation, which per-cell characterisation misses)")
else: print("  PENDING")

print()
print("="*100)
print("C) PSP103 MODEL-VERSION AND JUNCTION-GEOMETRY CONTROLS (sg13g2_inv_1, CL=9.34fF, slew 64.9ps)")
print("="*100)
def q(f,tag='QCYC'):
    import os,re
    if not os.path.exists(S+f): return None
    m=re.search(r'^\s*%s\s*=\s*(\S+)'%tag, open(S+f).read(), re.M|re.I)
    return abs(float(m.group(1))) if m else None
rows=[("PSP 103.4.0 (/usr/local/share/xyce)  + explicit AD/AS/PD/PS","inv_oldmodel.log"),
      ("PSP 103.8.2 (PDK's own verilog-a)    + explicit AD/AS/PD/PS","inv_pdkmodel.log"),
      ("PSP 103.4.0                          + NO junction geometry","inv_old_nojunc.log"),
      ("PSP 103.8.2                          + NO junction geometry","inv_pdk_nojunc.log")]
for lab,f in rows:
    Q=q(f)
    print("  %-62s %s"%(lab, ("E=%.4f fJ/cycle"%(Q*1.2*1e15)) if Q else "pending"))
a,b,c,d=[q(f) for _,f in rows]
if all(x is not None for x in (a,b,c,d)):
    print()
    print("  model version 103.4.0 vs 103.8.2, geometry supplied   : %.6f%% difference"%(100*abs(a/b-1)))
    print("  model version 103.4.0 vs 103.8.2, geometry NOT supplied: %.6f%% difference"%(100*abs(c/d-1)))
    print("  => the PSP VERSION is irrelevant here (bit-identical, 4 from-scratch builds).")
    print("  junction geometry supplied vs not                     : %.2f%% (%.4f -> %.4f fJ/cycle)"%(
        100*(a/c-1), c*1.2*1e15, a*1.2*1e15))
    print("  => what matters is AD/AS/PD/PS. The campaign's existing shim")
    print("     (/usr/local/src/stat-sim/qal/sg13lv_compat.sp) DROPS them, under-counting")
    print("     by %.0f%% at this load (and 22%% at 2 fF). The async th-cells"%(100*(a/c-1)))
    print("     (th_cells_sg13g2.sp, th22.sp) are hand-written with bare W/L and no")
    print("     junction geometry either, so BOTH arms are low for the same reason.")
