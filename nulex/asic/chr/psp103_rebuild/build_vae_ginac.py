import sys, subprocess, os
sys.path.insert(0, "/usr/local/share/xyce/PyMS")
from vae.parser import parse_file
from vae.ginac_emitter import emit_ginac_program
va, out_so = sys.argv[1], sys.argv[2]
params = {}
for a in sys.argv[3:]:
    k,v = a.split("="); params[k]=float(v)
mod = parse_file(va)
src = emit_ginac_program(mod, param_values=params)
open("_ginac.cpp","w").write(src)
subprocess.run("g++ -O2 -std=c++17 -o _ginac _ginac.cpp -lginac -lcln", shell=True, check=True)
subprocess.run("./_ginac > _eval.cpp", shell=True, check=True)
wrapper = '''#include <cmath>
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
extern "C" void vae_jacobian(VaeState* s, double* dFdV, double* dQdV){ _vae_jacobian_impl(s,dFdV,dQdV); }
''' % os.getcwd()
open("_wrapper.cpp","w").write(wrapper)
subprocess.run(f"g++ -O2 -std=c++17 -shared -fPIC -o {out_so} _wrapper.cpp -lm", shell=True, check=True)
print("built", out_so, "module=", mod.name)
