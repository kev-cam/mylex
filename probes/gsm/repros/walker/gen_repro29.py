#!/usr/bin/env python3
# r28_<stage>: r24_fcvt with the fcvt unit's pipeline register outputs
# exposed one at a time through a 128-bit debug port (folded into y by xor
# of 32-bit words) -- bisecting the r24 mismatch by stage.
import re, sys
exec(open("gen_repro24.py").read().split("need, done, out =")[0])   # block(), txt

def closure(root):
    need, done, out = [root], [], []
    while need:
        n = need.pop(0)
        if n.lower() in [d.lower() for d in done]:
            continue
        b = block(n); done.append(n); out.append(b)
        for dep in re.findall(r"entity work\.(\w+)", b):
            if dep.lower() not in [d.lower() for d in done]:
                need.append(dep)
    return out

STAGES = {"exp": ("unpacked_exp_s0", 12), "mant": ("unpacked_mant_s0", 32),
          "fclass": ("fclass", 7), "expraw": ("src_exp_raw", 8), "safe": ("safe_dataa", 64),
          "bias": ("src_bias_s", 12), "q98": ("LPM_q_ivl_98", 62)}
blocks = closure("VX_fcvt_unit")
fcvt = blocks[0]
deps = "".join(reversed(blocks[1:]))
for tag, (sig, w) in STAGES.items():
    name = f"r29_{tag}"
    f = re.sub(r"\bVX_fcvt_unit\b", f"VX_fcvt_unit_{tag}", fcvt)
    f = f.replace("    fflags : out logic3d_vector(4 downto 0)\n  );",
                  "    fflags : out logic3d_vector(4 downto 0);\n    dbg : out logic3d_vector(127 downto 0)\n  );", 1)
    assert "dbg : out" in f, "port edit"
    # debug drive: first `begin` of the architecture body
    body = f.find("\nbegin\n", f.find(f"of VX_fcvt_unit_{tag} is"))
    assert body > 0
    f = f[:body] + f"\nbegin\n  dbg({w-1} downto 0) <= {sig};\n  dbg(127 downto {w}) <= (others => L3D_0);" + f[body + len("\nbegin"):]
    wrapper = f"""
library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;
-- r24_fcvt with the pipeline register {sig} ({w} bits) exposed: y = xor of its 32-bit words
entity {name} is
  port (clk : in logic3d; reset : in logic3d;
        a : in logic3d_vector(31 downto 0); b : in logic3d_vector(31 downto 0);
        op : in logic3d_vector(3 downto 0); y : out logic3d_vector(31 downto 0));
end entity;
architecture from_verilog of {name} is
  signal dataa : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal frm : logic3d_vector(2 downto 0) := (others => L3D_X);
  signal is_signed : logic3d := L3D_X;
  signal result : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal fflags : logic3d_vector(4 downto 0) := (others => L3D_X);
  signal dbg : logic3d_vector(127 downto 0) := (others => L3D_X);
  signal one : logic3d := L3D_1;
  signal zero : logic3d := L3D_0;
begin
  dataa <= a(31) & L3D_1 & L3D_0 & L3D_0 & L3D_0 & op & a(22 downto 0);
  frm <= b(2 downto 0) when is_one(b(3)) else L3D_0 & b(1 downto 0);
  is_signed <= b(4);
  u : entity work.VX_fcvt_unit_{tag}
    port map (clk => clk, reset => reset, enable => one, mask => one, frm => frm,
              is_itof => zero, is_ftoi => one, is_f2f => zero, is_signed => is_signed,
              is_int64 => zero, src_fmt => zero, dst_fmt => zero,
              dataa => dataa, result => result, fflags => fflags, dbg => dbg);
  y <= dbg(31 downto 0) xor dbg(63 downto 32) xor dbg(95 downto 64) xor dbg(127 downto 96);
end architecture;
"""
    open(f"{name}.vhd", "w").write(deps + f + wrapper)
    print("wrote", name)
