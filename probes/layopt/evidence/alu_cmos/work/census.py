#!/usr/bin/env python3
import re,json,collections,statistics
W='/usr/local/src/mylex/probes/layopt/evidence/alu_cmos/work/'
OUTPINS={'X','Y','Q','Q_N','L_HI','L_LO'}
def norm(n): return re.sub(r'\s+\[','[',' '.join(n.split()))
src=open(W+'alu.phys_4.75.v').read()
inst={}   # name -> (type, outnet, [innets])
for typ,name,body in re.findall(r'(sg13g2_\w+)\s+(\\?\S+?)\s*\(([^;]*?)\)\s*;', src, re.S):
    pins={}
    for pm in re.finditer(r'\.(\w+)\(\s*(.*?)\s*\)\s*(?:,|$)', body, re.S):
        pins[pm.group(1)]=norm(pm.group(2))
    outs=[v for k,v in pins.items() if k in OUTPINS]
    inst[name.lstrip('\\')]=(typ, outs[0] if outs else None, pins)
print("instances parsed:",len(inst))
# net caps
netcap={}
cur=None
for line in open(W+'netdump.txt'):
    if line.startswith('@@@N '): cur=line[5:].strip()
    elif line.strip().startswith('Total capacitance:') and cur:
        v=line.split(':')[1].strip().split('-')
        netcap[cur]=(float(v[0])+float(v[-1]))/2.0   # pF, mean of min-max
print("nets with cap:",len(netcap))
# instance power
pw={d['name']:d for d in json.load(open(W+'inst_power.json'))}
print("instances with power:",len(pw))
# VCD toggles per net
sym2name={};widths={};scope=[]
f=open(W+'alu_phys.vcd')
for line in f:
    s=line.strip()
    if s.startswith('$scope'): scope.append(s.split()[2])
    elif s.startswith('$upscope'): scope.pop()
    elif s.startswith('$var'):
        p=s.split(); sym2name[p[3]]='.'.join(scope[1:]+[p[4]]); widths[p[3]]=int(p[2])
    elif s.startswith('$enddefinitions'): break
tog=collections.Counter(); last={}
T0=4*4750.0
t=0
for line in f:
    line=line.rstrip()
    if not line: continue
    c=line[0]
    if c=='#': t=int(line[1:]); continue
    if c in '01xzXZ': v,sy=c,line[1:]
    elif c in 'bB': v,_,sy=line[1:].partition(' '); sy=sy.strip()
    else: continue
    if sy not in sym2name: continue
    pv=last.get(sy); last[sy]=v
    if pv is None or t<T0 or v==pv: continue
    if widths[sy]==1: tog[sym2name[sy]]+=1
    else:
        a=pv.rjust(widths[sy],'0' if pv[0] not in 'xz' else pv[0]); b=v.rjust(widths[sy],'0' if v[0] not in 'xz' else v[0])
        tog[sym2name[sy]]+=sum(1 for i,j in zip(a,b) if i!=j)
TEND=t; CYC=(TEND-T0)/4750.0
print("VCD window: %.1f cycles"%CYC)
# map instance -> toggles on its output net
by=collections.defaultdict(lambda: dict(n=0,P=0.0,Pint=0.0,Psw=0.0,tog=0,caps=[],names=[]))
missing=0
for name,(typ,outnet,pins) in inst.items():
    r=by[typ]; r['n']+=1
    d=pw.get(name)
    if d: r['P']+=d['total']; r['Pint']+=d['internal']; r['Psw']+=d['switching']
    else: missing+=1
    if outnet:
        r['caps'].append(netcap.get(outnet,float('nan')))
        # VCD net name: escaped names in vcd appear as-is
        cand=outnet
        r['tog']+=tog.get(cand,0)
        r['names'].append((name,outnet))
print("instances missing power:",missing)
rows=sorted(by.items(), key=lambda kv:-kv[1]['P'])
tot=sum(v['P'] for v in by.values())
print("\n%-22s %5s %10s %7s %10s %10s %9s"%("cell type","count","P(W)","%P","tog/inst/cyc","meanCL(fF)","P/inst(uW)"))
cum=0
for t_,v in rows:
    cl=[c for c in v['caps'] if c==c]
    mc=statistics.mean(cl)*1000 if cl else 0
    cum+=v['P']
    print("%-22s %5d %10.3e %6.2f%% %10.4f %10.2f %9.3f   cum %.1f%%"%(
        t_,v['n'],v['P'],100*v['P']/tot, v['tog']/v['n']/CYC if v['n'] else 0, mc, 1e6*v['P']/v['n'], 100*cum/tot))
json.dump({t_:{'n':v['n'],'P':v['P'],'Pint':v['Pint'],'Psw':v['Psw'],'tog':v['tog'],
               'meanCL_pF':statistics.mean([c for c in v['caps'] if c==c]) if any(c==c for c in v['caps']) else 0,
               'cyc':CYC}
           for t_,v in by.items()}, open(W+'type_census.json','w'), indent=1)
