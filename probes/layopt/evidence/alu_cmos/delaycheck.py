#!/usr/bin/env python3
"""Does the liberty CELL MODEL (capacitances) agree with SPICE, even though its
internal_power table does not?  Compare delay-vs-load slope and intercept at the
SAME input slew (64.9 ps 20-80%)."""
import re,os
LIB=[(1.000,32.00,31.64),(2.000,35.49,34.66),(4.260,43.37,41.48),(9.340,61.09,56.82),
     (15.000,80.82,73.91),(23.400,110.11,99.28),(39.000,154.38,135.62)]  # CL fF, tp_rise ps, tp_fall ps
def fit(xs,ys):
    n=len(xs); mx=sum(xs)/n; my=sum(ys)/n
    b=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/sum((x-mx)**2 for x in xs)
    return b, my-b*mx
L=os.path.dirname(os.path.abspath(__file__))+'/spice/inv_load.log'
print("sg13g2_inv_1  delay vs load, input slew 64.9 ps (20-80%)")
print("%-10s %12s %12s | %12s %12s"%("CL(fF)","lib_tpLH","lib_tpHL","spi_tpLH","spi_tpHL"))
spi=[]
if os.path.exists(L):
    txt=open(L).read()
    cls=re.findall(r'CL\s*=\s*([\d.eE+-]+)', txt)
    q=re.findall(r'^\s*TPLH\s*=\s*(\S+)', txt, re.M|re.I)
    h=re.findall(r'^\s*TPHL\s*=\s*(\S+)', txt, re.M|re.I)
    steps=[1.0,2.0,4.26,9.34,15.0,23.4,39.0]
    for i,c in enumerate(steps):
        if i<len(q) and i<len(h): spi.append((c,float(q[i])*1e12,float(h[i])*1e12))
for i,(c,a,b) in enumerate(LIB):
    s=next((x for x in spi if abs(x[0]-c)<1e-6), None)
    print("%-10.3f %12.2f %12.2f | %12s %12s"%(c,a,b,
        ("%.2f"%s[1]) if s else "pending", ("%.2f"%s[2]) if s else "pending"))
sl,ic=fit([x[0] for x in LIB],[x[1] for x in LIB]); print("\nLIBERTY  tpLH: %.4f ps/fF, intercept %.2f ps -> effective self-load %.2f fF"%(sl,ic,ic/sl))
sl2,ic2=fit([x[0] for x in LIB],[x[2] for x in LIB]); print("LIBERTY  tpHL: %.4f ps/fF, intercept %.2f ps -> effective self-load %.2f fF"%(sl2,ic2,ic2/sl2))
if len(spi)>=4:
    sl,ic=fit([x[0] for x in spi],[x[1] for x in spi]); print("SPICE    tpLH: %.4f ps/fF, intercept %.2f ps -> effective self-load %.2f fF"%(sl,ic,ic/sl))
    sl2,ic2=fit([x[0] for x in spi],[x[2] for x in spi]); print("SPICE    tpHL: %.4f ps/fF, intercept %.2f ps -> effective self-load %.2f fF"%(sl2,ic2,ic2/sl2))
