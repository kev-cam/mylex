#!/usr/bin/env python3
"""Toggle/activity statistics from a gate-level VCD.
alpha = mean transitions per net per clock cycle (same statistic the sha_slice
rung quoted as alpha=0.476)."""
import re, sys, collections

vcd, period_ps, t_start_ps = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
sym2name, widths = {}, {}
scope=[]
tog=collections.Counter(); xcnt=collections.Counter()
last={}
tmax=0; tmin=None
f=open(vcd)
# header
for line in f:
    line=line.strip()
    if line.startswith('$scope'): scope.append(line.split()[2])
    elif line.startswith('$upscope'): scope.pop()
    elif line.startswith('$var'):
        p=line.split()
        w=int(p[2]); s=p[3]; nm='.'.join(scope+[p[4]])
        sym2name[s]=nm; widths[s]=w
    elif line.startswith('$enddefinitions'): break
print("nets in VCD: %d" % len(sym2name))
t=0
for line in f:
    line=line.rstrip()
    if not line: continue
    c=line[0]
    if c=='#':
        t=int(line[1:]); tmax=max(tmax,t)
        continue
    if t < t_start_ps: 
        # still record values so transitions after t_start are correct
        pass
    if c in '01xzXZ':
        s=line[1:]; v=c
    elif c in 'bB':
        v,_,s=line[1:].partition(' '); s=s.strip()
    elif c in 'rR':
        continue
    else:
        continue
    if s not in sym2name: continue
    pv=last.get(s)
    last[s]=v
    if t < t_start_ps or pv is None: continue
    if v!=pv:
        if widths[s]==1:
            tog[s]+=1
            if v.lower() in 'xz': xcnt[s]+=1
        else:
            # count per-bit transitions
            a=pv.rjust(widths[s],pv[0] if pv[0] in 'xz' else '0')
            b=v.rjust(widths[s],v[0] if v[0] in 'xz' else '0')
            n=sum(1 for i,j in zip(a,b) if i!=j)
            tog[s]+=n
            if any(ch in 'xzXZ' for ch in v): xcnt[s]+=1
dur=tmax-t_start_ps
cycles=dur/period_ps
totbits=sum(widths[s] for s in sym2name)
tot=sum(tog.values())
print("window: %.0f ps -> %.0f ps = %.1f clock cycles @ %.0f ps" % (t_start_ps,tmax,cycles,period_ps))
print("total net bits: %d   total bit-transitions: %d" % (totbits,tot))
print("ALPHA (transitions per net-bit per cycle) = %.4f" % (tot/totbits/cycles))
nz=sum(1 for s in sym2name if tog[s]>0)
print("nets that ever toggled: %d / %d (%.1f%%)" % (nz,len(sym2name),100*nz/len(sym2name)))
print("nets with any X/Z after t_start: %d" % len(xcnt))
# clock net
for s,n in sym2name.items():
    if n.endswith('.clk') or n.endswith('clk'):
        print("  clockish %-30s toggles=%d (=%.3f/cycle)" % (n,tog[s],tog[s]/cycles))
print("top 10 toggling nets:")
for s,c in tog.most_common(10):
    print("   %-40s %6d  (%.3f/cyc)" % (sym2name[s],c,c/cycles))
