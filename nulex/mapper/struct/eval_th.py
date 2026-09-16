import json, sys
J=json.load(open('add4_th.json'))['modules']['add4']
cells, ports, netnames = J['cells'], J['ports'], J.get('netnames',{})
# TH comb functions
def th(t, xs):
    n=sum(xs)
    if t=='th22': return int(xs[0] and xs[1])
    if t=='th33': return int(all(xs[:3]))
    if t=='th44': return int(all(xs[:4]))
    if t in ('th12','th13','th14'): return int(any(xs))
    if t=='th23': return int(n>=2)
    if t=='th24': return int(n>=2)
    if t=='th34': return int(n>=3)
    if t=='th23w2': return int(2*xs[0]+xs[1]+xs[2]>=2)
    if t=='th34w2': return int(2*xs[0]+xs[1]+xs[2]+xs[3]>=3)
    raise Exception('unknown '+t)
# collect port bit lists per rail
def bits(pname): return ports[pname]['bits']
def eval_add(av, bv):
    val={}  # net bit -> 0/1
    # drive input rails: a_L[i]=a[i], a_H[i]=~a[i]; same for b
    for pn,vv in (('a',av),('b',bv)):
        for i,nb in enumerate(bits(pn+'_L')): val[nb]=(vv>>i)&1
        for i,nb in enumerate(bits(pn+'_H')): val[nb]=((vv>>i)&1)^1
    # constants
    for c in (0,1): val[str(c)]=c
    # iterate cells to fixpoint (pure comb)
    order=list(cells.values())
    for _ in range(len(order)+2):
        changed=False
        for c in order:
            conn=c['connections']; pins=['a','b','c','d']
            xs=[]
            ok=True
            for p in pins:
                if p in conn:
                    b=conn[p][0]
                    if isinstance(b,str): xs.append(int(b))
                    elif b in val: xs.append(val[b])
                    else: ok=False; break
            if not ok: continue
            y=conn['y'][0]
            nv=th(c['type'],xs)
            if val.get(y)!=nv: val[y]=nv; changed=True
        if not changed: break
    # decode s: s[i]=s_L[i]
    sL=bits('s_L')
    s=0
    for i,nb in enumerate(sL):
        b=sL[i]
        v = int(b) if isinstance(b,str) else val.get(b,0)
        s |= (v<<i)
    return s
bad=0
for a in range(16):
    for b in range(16):
        got=eval_add(a,b); exp=a+b
        if got!=exp:
            bad+=1
            if bad<=5: print('  MISMATCH a=%d b=%d exp=%d got=%d'%(a,b,exp,got))
print('checked 256 combos, mismatches=%d'%bad)
