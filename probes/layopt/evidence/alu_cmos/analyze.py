#!/usr/bin/env python3
"""Combine: design liberty power (measured VCD activity) + matched single-cell
liberty + matched transistor SPICE -> per-type correction ratio -> corrected
whole-ALU energy."""
import json,re,os,collections
W='/usr/local/src/mylex/probes/layopt/evidence/alu_cmos/'
T=4.75e-9
cen=json.load(open(W+'work/type_census.json'))
lib=json.load(open(W+'libcheck/lib_matched.json'))
CYC=list(cen.values())[0]['cycles']
NOPS=2001.0
cycles_per_op=CYC/NOPS

# ---- SPICE results ----
def spice_Q(logfile, tag):
    if not os.path.exists(logfile): return None
    for line in open(logfile):
        m=re.match(r'\s*%s\s*=\s*(\S+)'%tag, line, re.I)
        if m: return abs(float(m.group(1)))
    return None
VDD=1.2
CELLS=[  # index -> (type, arc)
 (0,"sg13g2_inv_1","A->Y"),(1,"sg13g2_buf_1","A->X"),(2,"sg13g2_buf_8","A->X"),
 (3,"sg13g2_buf_16","A->X"),(4,"sg13g2_nand2_1","A->Y"),(5,"sg13g2_nor2_1","A->Y"),
 (6,"sg13g2_o21ai_1","A1->Y"),(7,"sg13g2_a21oi_1","A1->Y"),
 (8,"sg13g2_mux2_1","A0->X"),(9,"sg13g2_mux2_1","S->X")]
print("="*104)
print("MATCHED TRANSISTOR vs LIBERTY, per cell type (same C_L, same input slew, same arc)")
print("="*104)
print("%-14s %-6s %7s %7s %9s %9s %6s | %9s %9s %6s"%(
      "cell","arc","CL_fF","slew_ps","Etog_lib","Etog_spi","ratio","Eint_lib","Eint_spi","i-rat"))
print("  (Etog = energy per output toggle, fJ.  Eint = per-toggle energy MINUS the")
print("   load term 0.5*CL*V^2, which both models compute identically.)")
ratios={}; rows=[]
for i,ct,arc in CELLS:
    q=spice_Q(W+'spice/s%d.log'%i, 'QC%d'%i)
    k=f"{ct}|{arc}"
    L=lib.get(k)
    if q is None or L is None:
        print("%-16s %-7s %8s  PENDING"%(ct.replace('sg13g2_',''),arc,''))
        continue
    Ecyc_spi=q*VDD*1e15          # fJ per full rise+fall cycle
    Etog_spi=Ecyc_spi/2.0
    Etog_lib=L['E_tog_fJ']
    r=Etog_spi/Etog_lib
    Eld=0.5*L['CL_fF']*1e-15*VDD*VDD*1e15            # fJ per toggle
    Eint_lib=L['Pint']*T*1e15
    Eint_spi=Etog_spi-Eld
    ir=Eint_spi/Eint_lib if Eint_lib else float('nan')
    rows.append((ct,arc,L['CL_fF'],L['slew_ps'],Etog_lib,Etog_spi,r,Eint_lib,Eint_spi,ir))
    ratios.setdefault(ct,[]).append(r)
    print("%-14s %-6s %7.2f %7.1f %9.4f %9.4f %6.3f | %9.4f %9.4f %6.3f"%(
        ct.replace('sg13g2_',''),arc,L['CL_fF'],L['slew_ps'],Etog_lib,Etog_spi,r,Eint_lib,Eint_spi,ir))
# flop
fq={t:spice_Q(W+'spice/flop.log',t) for t in ('QA','QA2','QB')}
flop=None
if all(v is not None for v in fq.values()):
    NC=20.0
    EA=fq['QA']*VDD*1e15/NC; EA2=fq['QA2']*VDD*1e15/NC; EB=fq['QB']*VDD*1e15/NC
    a=cen['sg13g2_dfrbpq_1']['alpha']
    Espi=EA + a*(EB-EA)
    Elib_a0=1.249267370e-05*T*1e15
    Elib_a1=(1.940254333e-05+1.229305326e-06)*T*1e15
    Elib=Elib_a0 + a*(Elib_a1-Elib_a0)
    flop=dict(EA=EA,EA2=EA2,EB=EB,Espi=Espi,Elib=Elib,Elib_a0=Elib_a0,Elib_a1=Elib_a1,alpha=a,r=Espi/Elib)
    print("\nFLOP sg13g2_dfrbpq_1 (per CLOCK CYCLE, CL=8.11fF, CLK slew 20.1ps, D slew 50ps)")
    print("  SPICE  D static lo : %8.3f fJ/cyc   D static hi: %8.3f fJ/cyc"%(EA,EA2))
    print("  SPICE  Q toggles every cycle (a=1): %8.3f fJ/cyc"%EB)
    print("  SPICE  at design a=%.4f          : %8.3f fJ/cyc"%(a,Espi))
    print("  LIBERTY a=0 %.3f  a=1 %.3f  a=%.4f %.3f fJ/cyc"%(Elib_a0,Elib_a1,a,Elib))
    print("  RATIO (spice/liberty) = %.3f   <-- OPPOSITE DIRECTION to the logic cells"%flop['r'])
    print("  decomposed:  clock-only floor  spice/lib = %.3f  (liberty OVER-states it)"%(EA/Elib_a0))
    print("               data term (a=1 minus a=0) spice/lib = %.3f  (liberty UNDER-states it,"%((EB-EA)/(Elib_a1-Elib_a0)))
    print("               same direction and size as the combinational cells)")
    ratios['sg13g2_dfrbpq_1']=[flop['r']]
else:
    print("\nFLOP: PENDING")

# ---- apply to whole design ----
tot_lib=sum(v['P'] for v in cen.values())
meas=set(ratios)
cov=sum(cen[t]['P'] for t in meas if t in cen)/tot_lib if meas else 0
mean_comb=None
comb_types=[t for t in ratios if t not in ('sg13g2_dfrbpq_1',)]
if comb_types:
    num=sum(cen[t]['P']*(sum(ratios[t])/len(ratios[t])) for t in comb_types if t in cen)
    den=sum(cen[t]['P'] for t in comb_types if t in cen)
    mean_comb=num/den
print("\n"+"="*104)
print("WHOLE-ALU CORRECTION   (direct SPICE coverage: %.1f%% of design power)"%(100*cov))
print("="*104)
if mean_comb:
    # split the extrapolation: unmeasured BUFFER-like types get the measured buffer mean,
    # unmeasured small-logic types get the measured logic mean. A single buffer-weighted
    # mean would under-correct the (mostly small-logic) unmeasured pool.
    BUF=[t for t in ratios if 'buf' in t or 'dlygate' in t]
    LOG=[t for t in ratios if t not in BUF and t!='sg13g2_dfrbpq_1']
    def wmean(ts):
        num=sum(cen[t]['P']*(sum(ratios[t])/len(ratios[t])) for t in ts if t in cen)
        den=sum(cen[t]['P'] for t in ts if t in cen)
        return num/den if den else 1.0
    mb, ml = wmean(BUF), wmean(LOG)
    corr=0.0; nx=0.0
    for t,v in cen.items():
        if t in ratios: r=sum(ratios[t])/len(ratios[t])
        elif ('buf' in t or 'dlygate' in t): r=mb; nx+=v['P']
        else: r=ml; nx+=v['P']
        corr+=v['P']*r
    print("  extrapolation for the %.1f%% not directly measured: buffer-like x%.3f, logic x%.3f"%(
        100*nx/tot_lib, mb, ml))
    print("  census-weighted mean ratio for UNMEASURED types (extrapolated): %.3f"%mean_comb)
    print("  liberty  total: %.6f mW   -> %.3f pJ/cycle  -> %.3f pJ/op"%(tot_lib*1e3, tot_lib*T*1e12, tot_lib*T*1e12*cycles_per_op))
    print("  corrected total: %.6f mW  -> %.3f pJ/cycle  -> %.3f pJ/op"%(corr*1e3, corr*T*1e12, corr*T*1e12*cycles_per_op))
    print("  *** OVERALL TRANSISTOR/LIBERTY CORRECTION RATIO = %.3f ***"%(corr/tot_lib))
# --- estimator 2: liberty's LOAD term is exact; correct only the INTERNAL term ---
irat={}
for r in rows: irat.setdefault(r[0],[]).append(r[9])
FLOPT='sg13g2_dfrbpq_1'
if irat:
    num=sum(cen[t]['Pint']*(sum(v)/len(v)) for t,v in irat.items() if t in cen)
    den=sum(cen[t]['Pint'] for t in irat if t in cen)
    kbar=num/den
    c2=0.0
    for t,v in cen.items():
        if t==FLOPT and flop:
            # the flop's dominant term is CLOCK-pin internal power, not a load term;
            # apply its directly measured total ratio instead of an internal-only k
            c2+=v['P']*flop['r']; continue
        k=(sum(irat[t])/len(irat[t])) if t in irat else kbar
        c2+=v['Psw']+k*v['Pint']+v['Plk']
    print("\n  ESTIMATOR 2 (load term exact, internal term x k):")
    print("    power-weighted mean internal correction k = %.3f (unmeasured types)"%kbar)
    print("    corrected total: %.6f mW -> %.3f pJ/op   (overall x%.3f)"%(
        c2*1e3, c2*T*1e12*cycles_per_op, c2/tot_lib))
print("\ncycles/op = %.4f (%.0f ops in %.1f cycles)"%(cycles_per_op,NOPS,CYC))

# ---------------- design-level accounting ----------------
P_TOT=9.146656e-3; P_SEQ=2.966605e-3; P_COMB=4.425386e-3; P_CLKTREE=1.754673e-3
P_A05=1.073604e-2; P_A10=1.746970e-2; P_SYNTH=6.518550e-3; P_SYNTH_A05=7.792591e-3
FLOP_CLKFRAC=(flop['Elib_a0']/flop['Elib']) if flop else 1.249267370e-05/1.550552588e-05
def pj(P): return P*T*1e12
print("\n"+"="*104); print("DESIGN ENERGY ACCOUNTING (physical netlist, real CTS, measured VCD activity)"); print("="*104)
print("  %-42s %10s %10s"%("","pJ/cycle","pJ/op"))
for n,P in [("Combinational",P_COMB),("Sequential (flops, incl. their CLK pin)",P_SEQ),
            ("Clock tree (CTS buffers/inverters)",P_CLKTREE),("TOTAL",P_TOT)]:
    print("  %-42s %10.3f %10.3f"%(n,pj(P),pj(P)*cycles_per_op))
print("\n  CLOCK-ATTRIBUTABLE (the term async/QAL claim to remove):")
if flop: print("    [flop clock fraction taken from liberty at the measured alpha=%.4f]"%flop['alpha'])
P_flopclk=P_SEQ*FLOP_CLKFRAC
print("    flop CLK-pin floor  = %.3f%% of Sequential = %.4f mW"%(100*FLOP_CLKFRAC,P_flopclk*1e3))
print("    + clock tree                              = %.4f mW"%(P_CLKTREE*1e3))
print("    = %.4f mW = %.1f%% of total = %.3f pJ/op"%((P_flopclk+P_CLKTREE)*1e3,
      100*(P_flopclk+P_CLKTREE)/P_TOT, pj(P_flopclk+P_CLKTREE)*cycles_per_op))
# clock term re-measured at transistor level
if flop and rows:
    import re as _re
    _pw={d['name'].lstrip('\\'):d for d in json.load(open(W+'work/inst_power.json'))}
    _src=open(W+'work/alu.phys_4.75.v').read()
    _typ={n.lstrip('\\'):t for t,n in _re.findall(r'(sg13g2_\w+)\s+(\\?\S+?)\s*\(', _src)}
    _R={r[0]:r[6] for r in rows}
    _clk=[n for n in _pw if n.startswith('clkbuf') or n.startswith('clkload') or 'clkinv' in n]
    _Plib=sum(_pw[n]['total'] for n in _clk)
    _Pcor=sum(_pw[n]['total']*_R.get(_typ[n],1.0) for n in _clk)
    _Pff_lib=flop['Elib_a0']*1e-15*188/T
    _Pff_spi=flop['EA']*1e-15*188/T
    print("\n  SAME CLOCK TERM RE-MEASURED AT TRANSISTOR LEVEL:")
    print("    clock tree            liberty %.4f -> spice %.4f mW  (x%.3f)"%(_Plib*1e3,_Pcor*1e3,_Pcor/_Plib))
    print("    flop CLK-pin floor    liberty %.4f -> spice %.4f mW  (x%.3f)"%(_Pff_lib*1e3,_Pff_spi*1e3,_Pff_spi/_Pff_lib))
    print("    clock-attributable    liberty %.4f mW (%.1f%% of total) = %.3f pJ/op"%(
        (_Plib+_Pff_lib)*1e3, 100*(_Plib+_Pff_lib)/tot_lib, (_Plib+_Pff_lib)*T*1e12*cycles_per_op))
    print("    clock-attributable    spice   %.4f mW (%.1f%% of total) = %.3f pJ/op"%(
        (_Pcor+_Pff_spi)*1e3, 100*(_Pcor+_Pff_spi)/corr, (_Pcor+_Pff_spi)*T*1e12*cycles_per_op))
    print("    => the clock PRIZE shrinks from %.1f%% to %.1f%% of total. Liberty FLATTERS"%(
        100*(_Plib+_Pff_lib)/tot_lib, 100*(_Pcor+_Pff_spi)/corr))
    print("       the async/QAL case: it over-states the flop clock floor 1.8x while")
    print("       under-stating the combinational logic it would still have to pay.")
print("\n  ACTIVITY SENSITIVITY (physical netlist):")
for n,P in [("measured VCD activity",P_TOT),("alpha=0.5 global",P_A05),("alpha=1.0 global",P_A10)]:
    print("    %-26s %8.4f mW  %8.3f pJ/op"%(n,P*1e3,pj(P)*cycles_per_op))
print("\n  PHYSICAL-DESIGN OVERHEAD (why synth-only numbers are not comparable):")
print("    synth-only netlist @ measured activity : %8.4f mW  %8.3f pJ/op   (Clock group = 0, no CTS)"%(P_SYNTH*1e3,pj(P_SYNTH)*cycles_per_op))
print("    physical netlist   @ measured activity : %8.4f mW  %8.3f pJ/op"%(P_TOT*1e3,pj(P_TOT)*cycles_per_op))
print("    -> buffering + CTS + wire RC add %.1f%%"%(100*(P_TOT/P_SYNTH-1)))

# ---------------- sha_slice correction ----------------
import os
if os.path.exists('/tmp/claude-1001/-usr-local-src/4921ad0c-f17b-4b84-986a-5917c9ebd2a6/scratchpad/sha_type.json') and mean_comb:
    sha=json.load(open('/tmp/claude-1001/-usr-local-src/4921ad0c-f17b-4b84-986a-5917c9ebd2a6/scratchpad/sha_type.json'))
    stot=sum(v['P'] for v in sha.values())
    # sha_slice contains NO buffers and NO flops -- extrapolate its unmeasured types
    # with the mean over the measured SMALL LOGIC GATES only, not the buffer-weighted mean.
    LOGIC=[t for t in ratios if 'buf' not in t and t!='sg13g2_dfrbpq_1']
    lognum=sum(cen[t]['P']*(sum(ratios[t])/len(ratios[t])) for t in LOGIC if t in cen)
    logden=sum(cen[t]['P'] for t in LOGIC if t in cen)
    mean_logic=lognum/logden
    scorr=0.0; scov=0.0
    for ty,v in sha.items():
        if ty in ratios: r=sum(ratios[ty])/len(ratios[ty]); scov+=v['P']
        else: r=mean_logic
        scorr+=v['P']*r
    print("\n"+"="*104); print("CARRY-THROUGH TO THE sha_slice RUNG (232 fJ/op)"); print("="*104)
    print("  reproduced baseline (as published, NO output load) : %.3f fJ/op"%(stot*10e-9*1e15))
    print("  + EXT=2fF output load (what the ASYNC arm charged)  : 249.109 fJ/op  (+7.4%%)")
    print("  direct ratio coverage    : %.1f%% of sha_slice power"%(100*scov/stot))
    print("  logic-gate mean ratio used for the rest: %.3f"%mean_logic)
    print("  corrected                : %.3f fJ/op   (x%.3f)"%(scorr*10e-9*1e15, scorr/stot))
    print("  NOTE: ratios are measured at the ALU's loads/slews; sha_slice is synth-only")
    print("        (no wire RC, no buffering) so its loads are smaller -- transfer is approximate.")
