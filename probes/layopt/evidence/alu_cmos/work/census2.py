#!/usr/bin/env python3
import re,json,collections,statistics
W='/usr/local/src/mylex/probes/layopt/evidence/alu_cmos/work/'
OUTPINS={'X','Y','Q','Q_N','L_HI','L_LO'}
def norm(n): return re.sub(r'\s+\[','[',' '.join(n.split())).lstrip('\\')
src=open(W+'alu.phys_4.75.v').read()
inst={}
for typ,name,body in re.findall(r'(sg13g2_\w+)\s+(\\?\S+?)\s*\(([^;]*?)\)\s*;', src, re.S):
    pins={}
    for pm in re.finditer(r'\.(\w+)\(\s*(.*?)\s*\)\s*(?:,|$)', body, re.S):
        pins[pm.group(1)]=norm(pm.group(2))
    outs=[v for k,v in pins.items() if k in OUTPINS]
    inst[name.lstrip('\\')]=(typ, outs[0] if outs else None, pins)
netcap={}
for fn in ('netdump.txt','netdump2.txt'):
    cur=None
    for line in open(W+fn):
        if line.startswith('@@@N '): cur=norm(line[5:].strip().replace('\\[','[').replace('\\]',']'))
        elif line.strip().startswith('Total capacitance:') and cur:
            v=line.split(':')[1].strip().split('-'); netcap[cur]=(float(v[0])+float(v[-1]))/2.0
pw={d['name'].lstrip('\\'):d for d in json.load(open(W+'inst_power.json'))}
J=json.load(open(W+'net_toggles.json')); CYC=J['cycles']
tog={norm(k):v for k,v in J['tog'].items()}
miss=[n for n,(t,o,p) in inst.items() if o and o not in tog and o not in netcap]
print("instances: %d ; output nets not found in VCD: %d ; not in netcap: %d"%(
    len(inst), sum(1 for n,(t,o,p) in inst.items() if o and o not in tog),
    sum(1 for n,(t,o,p) in inst.items() if o and o not in netcap)))
by=collections.defaultdict(lambda: dict(n=0,P=0.0,Pint=0.0,Psw=0.0,Plk=0.0,tog=0,caps=[],ex=[]))
for name,(typ,outnet,pins) in inst.items():
    r=by[typ]; r['n']+=1
    d=pw.get(name)
    if d: r['P']+=d['total']; r['Pint']+=d['internal']; r['Psw']+=d['switching']; r['Plk']+=d['leakage']
    if outnet:
        if outnet in netcap: r['caps'].append(netcap[outnet])
        r['tog']+=tog.get(outnet,0)
        r['ex'].append((name,outnet,netcap.get(outnet,0),tog.get(outnet,0)))
tot=sum(v['P'] for v in by.values())
rows=sorted(by.items(), key=lambda kv:-kv[1]['P'])
print("\n%-22s %5s %10s %7s %12s %10s %12s"%("cell type","count","P(W)","%P","tog/inst/cyc","meanCL(fF)","E/tog(fJ)"))
cum=0
out={}
for t_,v in rows:
    cl=[c for c in v['caps'] if c==c]
    mc=statistics.mean(cl)*1000 if cl else 0.0
    a=v['tog']/v['n']/CYC if v['n'] else 0
    # liberty energy per output toggle for this type (dynamic only: internal+switching)
    Pdyn=v['Pint']+v['Psw']
    etog=(Pdyn*4.75e-9*CYC)/v['tog']*1e15 if v['tog'] else float('nan')
    cum+=v['P']
    print("%-22s %5d %10.3e %6.2f%% %12.4f %10.2f %12.3f  cum %.1f%%"%(t_,v['n'],v['P'],100*v['P']/tot,a,mc,etog,100*cum/tot))
    out[t_]=dict(n=v['n'],P=v['P'],Pint=v['Pint'],Psw=v['Psw'],Plk=v['Plk'],tog=v['tog'],
                 meanCL_pF=statistics.mean(cl) if cl else 0.0, alpha=a, E_tog_lib_fJ=etog, cycles=CYC)
json.dump(out, open(W+'type_census.json','w'), indent=1)
print("\nTOTAL P = %.6e W ; E/cycle = %.3f pJ ; cycles=%.1f"%(tot, tot*4.75e-9*1e12, CYC))
