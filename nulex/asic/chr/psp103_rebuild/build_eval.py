import sys, time
sys.path.insert(0, "/usr/local/share/xyce/PyMS")
from vae import preprocess, parser, codegen
VA="/usr/local/share/xyce/verilog-a/psp103/psp103.va"; INC=["/usr/local/share/xyce/verilog-a/psp103"]
t=time.time
def log(m): print("[%6.1fs] %s"%(t()-T0,m), flush=True)
T0=t()
src=preprocess.preprocess_file(VA, include_dirs=INC); log("preprocess OK %d chars"%len(src))
mod=parser.parse_verilog_a(src); log("parse OK: %s ports=%d params=%d"%(getattr(mod,'name','?'),len(getattr(mod,'ports',[])),len(getattr(mod,'params',[]))))
cpp=codegen.generate(mod); log("codegen OK %d chars (vae_eval=%s)"%(len(cpp),'void vae_eval' in cpp))
open("psp103_eval.cpp","w").write(cpp); log("wrote psp103_eval.cpp")
