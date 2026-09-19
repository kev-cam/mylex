#!/usr/bin/env python3
"""Build a vae_eval .so from a .va via the GiNaC pipeline, probe it, report.
Usage: repro_tool.py <va> <workdir> [--params k=v ...] [--bias v0 v1 ...]"""
import sys, subprocess, os, re
sys.path.insert(0, "/usr/local/share/xyce/PyMS")
from vae.parser import parse_file
from vae.ginac_emitter import emit_ginac_program

def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)

va = os.path.abspath(sys.argv[1]); wd = sys.argv[2]
params={}; bias=[]
i=3
while i < len(sys.argv):
    if sys.argv[i]=="--params":
        i+=1
        while i<len(sys.argv) and "=" in sys.argv[i]:
            k,v=sys.argv[i].split("="); params[k]=float(v); i+=1
    elif sys.argv[i]=="--bias":
        i+=1
        while i<len(sys.argv) and re.match(r'^-?[0-9.eE+-]+$',sys.argv[i]):
            bias.append(float(sys.argv[i])); i+=1
    else: i+=1
os.makedirs(wd, exist_ok=True); os.chdir(wd)
mod = parse_file(va)
src = emit_ginac_program(mod, param_values=params)
src = "#define CONSTCtoK 273.15\n" + src
open("_g.cpp","w").write(src)
r=sh("g++ -O1 -std=c++17 -o _g _g.cpp -lginac -lcln")
if r.returncode: print("GINAC_COMPILE_FAIL\n"+r.stderr[:2000]); sys.exit(1)
r=sh("./_g > _eval.cpp", timeout=600)
if r.returncode: print("GINAC_RUN_FAIL\n"+r.stderr[:1000]); sys.exit(1)
evalsrc=open("_eval.cpp").read()
wrapper='''#include <cmath>
#include <cstdio>
#include <cstring>
struct VaeState { double V[16]; double Vt; };
inline double conjugate(double x){ return x; }
#define vae_eval _vae_eval_impl
#define vae_jacobian _vae_jacobian_impl
static const double temperature = 300.15;
#include "%s/_eval.cpp"
#undef vae_eval
#undef vae_jacobian
extern "C" void vae_eval(VaeState* s, double* F, double* Q){ _vae_eval_impl(s,F,Q); }
'''%os.getcwd()
open("_w.cpp","w").write(wrapper)
r=sh("g++ -O1 -std=c++17 -shared -fPIC -o _m.so _w.cpp -lm")
if r.returncode: print("WRAP_COMPILE_FAIL\n"+r.stderr[:2000]); sys.exit(1)
# analysis
nb = int(re.search(r'vae_n_branches\(\)\s*\{\s*return\s*(\d+)', evalsrc).group(1)) if re.search(r'vae_n_branches',evalsrc) else 0
# does the FINAL current (F[...]) depend on node voltage V_*? check the F[] assignment lines
flines=[l for l in evalsrc.splitlines() if re.match(r'\s*F\[\d+\]\s*=',l)]
volt_syms=set(re.findall(r'\bV_[A-Za-z0-9]+\b','\n'.join(flines)))
# transitively: gather vars used in F lines, then see if any trace to V_ (simple: check whole eval for V_ presence in non-decl lines)
compute_lines=[l for l in evalsrc.splitlines() if re.search(r'=\s',l) and 's->V[' not in l]
uses_voltage_in_compute = any(re.search(r'\bV_[A-Za-z0-9]+\b',l) for l in compute_lines)
print("N_BRANCHES=%d"%nb)
print("F_LINES=%s"%flines[:6])
print("USES_VOLTAGE_IN_COMPUTE=%s"%uses_voltage_in_compute)
print("EVAL_CPP_BYTES=%d"%len(evalsrc))
# probe
if bias:
    probe='''#include <cstdio>
#include <cmath>
struct VaeState{double V[16];double Vt;};
extern "C" void vae_eval(VaeState*,double*,double*);
extern "C" int vae_n_branches();
int main(int c,char**v){VaeState s={};s.Vt=0.02585;
 for(int i=0;i<16&&i+1<c;i++)s.V[i]=atof(v[i+1]);
 int nb=vae_n_branches();double F[32]={},Q[32]={};vae_eval(&s,F,Q);
 for(int i=0;i<nb;i++)printf("F[%d]=%.6e\\n",i,F[i]);return 0;}'''
    open("_p.cpp","w").write(probe)
    sh("g++ -O1 _p.cpp _m.so -o _p -Wl,-rpath,.")
    r=sh("./_p "+" ".join(str(b) for b in bias))
    print("PROBE@bias="+",".join(str(b) for b in bias)+":\n"+r.stdout)
