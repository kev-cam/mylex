#!/usr/bin/env python3
"""Per-net output toggle counts from the gate-level VCD, keyed by NETLIST net name."""
import re,collections,json,sys
W='/usr/local/src/mylex/probes/layopt/evidence/alu_cmos/work/'
f=open(W+'alu_phys.vcd')
scope=[]; var={}   # sym -> (width, [netnames MSB..LSB])
for line in f:
    s=line.strip()
    if s.startswith('$scope'): scope.append(s.split()[2])
    elif s.startswith('$upscope'): scope.pop()
    elif s.startswith('$var'):
        p=s.split()
        if len(scope)!=2: continue          # only tb.dut.<net>
        w=int(p[2]); sym=p[3]
        raw=' '.join(p[4:-1])
        m=re.match(r'^(.*?)\s*\[(\d+):(\d+)\]$', raw)
        if m:
            base=m.group(1); hi=int(m.group(2)); lo=int(m.group(3))
            step=-1 if hi>=lo else 1
            bits=[f"{base}[{i}]" for i in range(hi,lo+step,step)]
        else:
            bits=[raw]
        var[sym]=(w,bits)
    elif s.startswith('$enddefinitions'): break
print("design-level VCD vars: %d  (net-bits %d)"%(len(var),sum(v[0] for v in var.values())))
tog=collections.Counter(); last={}
T0=4*4750.0; t=0
for line in f:
    line=line.rstrip()
    if not line: continue
    c=line[0]
    if c=='#': t=int(line[1:]); continue
    if c in '01xzXZ': v,sym=c,line[1:]
    elif c in 'bB': v,_,sym=line[1:].partition(' '); sym=sym.strip()
    else: continue
    if sym not in var: continue
    w,bits=var[sym]
    pv=last.get(sym); last[sym]=v
    if pv is None or t<T0 or v==pv: continue
    if w==1:
        tog[bits[0]]+=1
    else:
        pad=lambda x:(x[0] if x[0] in 'xzXZ' else '0')*(w-len(x))+x
        a,b=pad(pv),pad(v)
        for i,(ca,cb) in enumerate(zip(a,b)):
            if ca!=cb: tog[bits[i]]+=1
CYC=(t-T0)/4750.0
print("window %.1f cycles; nets with toggles: %d; total transitions %d"%(CYC,len(tog),sum(tog.values())))
json.dump({'cycles':CYC,'tog':dict(tog)}, open(W+'net_toggles.json','w'))
