#!/usr/bin/env python3
# r19: the VX_wallace_mul partial-product concat -- 900 SCALAR VARIABLE
#      leaves (and-terms), so the rendered chain exceeds one sigspec buffer
#      and the chunked path must know every leaf's width.
# r20: the VX_fpu_std fflags merge -- a while loop over lanes, each an `if`
#      whose arm reads-and-writes bit k of a process variable (k = 0..4).
def lit(n, w=32):
    bits = ["L3D_1" if (n >> (w - 1 - i)) & 1 else "L3D_0" for i in range(w)]
    return "logic3d_vector'(" + ", ".join(bits) + ")"

HDR = """library ieee; use ieee.std_logic_1164.all;
library sv2vhdl; use sv2vhdl.logic3d_types_pkg.all;
entity {name} is
  port (clk : in logic3d; reset : in logic3d;
        a : in logic3d_vector(31 downto 0); b : in logic3d_vector(31 downto 0);
        op : in logic3d_vector(3 downto 0); y : out logic3d_vector(31 downto 0));
end entity;
"""

N = 900
NV = 24
decl = "\n".join(f"    variable t{k} : logic3d;" for k in range(NV))
ands = "\n".join(f"      t{k} := l3d_and(a({(k * 7) % 32}), b({(k * 11 + 3) % 32}));"
                 for k in range(NV))
chain = " & ".join(f"t{k % NV}" for k in range(N))
s19 = """-- Tier B census after the concat flattening: vx_wallace_mul
-- `concat-chain@seq-assign` -- the 700-operand partial-product row is a
-- chain of SCALAR process variables (the and-terms), whose rendered specs
-- overflow one sigspec buffer: the chunked path needs each leaf's width and
-- r2_width_or_operands has none for a scalar logic3d local.
""" + HDR.format(name="r19_bigcat_vars") + """architecture from_verilog of r19_bigcat_vars is
  signal yr : logic3d_vector(31 downto 0) := (others => L3D_0);
begin
  y <= yr;
  process is
    variable pp : logic3d_vector(%d downto 0);
%s
  begin
    if rising_edge(clk) then
%s
      pp := %s;
      yr <= pp(31 downto 0) xor pp(95 downto 64) xor pp(%d downto %d);
    end if;
    wait on clk;
  end process;
end architecture;
""" % (N - 1, decl, ands, chain, N - 1, N - 32)
open("r19_bigcat_vars.vhd", "w").write(s19)

s20 = """-- Tier B census: vx_fpu_std `pvar-read-in-tree V_SIG_MERGED_FFLAGS_*` --
-- the per-lane fflags merge (exec.vhd:73880): a while loop over the lanes,
-- each iteration an `if mask(i)` whose arm does
--     v(k) := l3d_or(v(k), l3d_bit_read(lanes, i*5 + k))   for k = 0..4
-- After the first per-bit write the walker poisoned v's substitution and
-- the read of v(1) inside the arm had only the hold temp (a loop).  Now the
-- written bits keep a per-bit substitution, and each iteration's tree
-- re-roots the hold temp at the previous one's result.
""" + HDR.format(name="r20_fflags") + """architecture from_verilog of r20_fflags is
  signal mask_out : logic3d_vector(3 downto 0) := (others => L3D_X);
  signal fflags_lanes : logic3d_vector(19 downto 0) := (others => L3D_X);
  signal sig_merged : logic3d_vector(4 downto 0) := (others => L3D_X);
  signal yr : logic3d_vector(31 downto 0) := (others => L3D_0);
begin
  y <= yr;
  mask_out <= op;
  fflags_lanes <= a(19 downto 0);
  process is
    variable sig_i : logic3d_vector(31 downto 0);
    variable v_sig_merged : logic3d_vector(4 downto 0);
  begin
    v_sig_merged := sig_merged;
    loop
      v_sig_merged := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
      sig_i := %(c0)s;
      while l3d_lt_s(sig_i, %(c4)s) loop
        if is_one(l3d_bit_read(mask_out, l3d_index(sig_i, True))) then
          v_sig_merged(0) := l3d_or(v_sig_merged(0), l3d_bit_read(fflags_lanes, l3d_index(sig_i * %(c5)s, True)));
          v_sig_merged(1) := l3d_or(v_sig_merged(1), l3d_bit_read(fflags_lanes, l3d_index((sig_i * %(c5)s) + %(c1)s, True)));
          v_sig_merged(2) := l3d_or(v_sig_merged(2), l3d_bit_read(fflags_lanes, l3d_index((sig_i * %(c5)s) + %(c2)s, True)));
          v_sig_merged(3) := l3d_or(v_sig_merged(3), l3d_bit_read(fflags_lanes, l3d_index((sig_i * %(c5)s) + %(c3)s, True)));
          v_sig_merged(4) := l3d_or(v_sig_merged(4), l3d_bit_read(fflags_lanes, l3d_index((sig_i * %(c5)s) + %(c4)s, True)));
        end if;
        sig_i := sig_i + %(c1)s;
      end loop;
      sig_merged <= v_sig_merged;
      wait on mask_out, fflags_lanes;
    end loop;
  end process;
  process is
  begin
    if rising_edge(clk) then
      if is_one(reset) then
        yr <= %(c0)s;
      else
        yr <= (b(26 downto 0) & sig_merged) xor a;
      end if;
    end if;
    wait on clk;
  end process;
end architecture;
""" % dict(c0=lit(0), c1=lit(1), c2=lit(2), c3=lit(3), c4=lit(4), c5=lit(5))
open("r20_fflags.vhd", "w").write(s20)
print("wrote r19_bigcat_vars.vhd r20_fflags.vhd")
