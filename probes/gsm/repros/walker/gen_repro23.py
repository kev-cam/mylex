#!/usr/bin/env python3
# r23: VX_fcvt_unit's F2I align/round process (comb_fused_5) verbatim, with
# its signal declarations and identity casts, fed from the bench ports.
import re
W = "/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/walker"
fcvt = open(f"{W}/fcvt.vhd").read().splitlines()
proc = open(f"{W}/fcvt_p5.vhd").read()

names = ["norm_mant_s4", "align_shamt_s4", "tmp_ivl_283", "tmp_ivl_309", "tmp_ivl_316",
         "tmp_ivl_323", "tmp_ivl_333", "tmp_ivl_337", "tmp_ivl_343", "tmp_ivl_285",
         "tmp_ivl_312", "tmp_ivl_313", "tmp_ivl_336", "aligned_mant_full_s4", "tmp_ivl_318",
         "aligned_mant_s4", "guard_bit_s4", "round_bit_s4", "tmp_ivl_296", "fp_trunc_sh_s4",
         "sticky_bit_s4", "fp_trunc_s4", "tmp_ivl_325", "tmp_ivl_339", "tmp_ivl_330",
         "tmp_ivl_341", "tmp_ivl_328", "fp_sticky_mask_s4", "fp_guard_s4", "tmp_ivl_347",
         "tmp_ivl_350", "LPM_d0_ivl_266", "dst_man_w_s4"]
decls = []
for n in names:
    for l in fcvt:
        if re.match(rf"^\s*signal {n} :", l):
            decls.append(re.sub(r"\s*--.*", "", l)); break
assert len(decls) == len(names), len(decls)

def func(name):
    # the BODY (second occurrence: "impure function <name> (" ... "end function;")
    txt = "\n".join(fcvt)
    m = list(re.finditer(rf"  (?:impure )?function {re.escape(name)} ?\(.*?end function;\n", txt, re.S))
    assert m, name
    return m[-1].group(0)
funcs = "".join(func(n) for n in ["sv2v_cast_7_signed", "sv2v_cast_7",
                                  "sv2v_cast_99F89_signed", "sv2v_cast_C255F", "Reduce_OR"])

s = """-- The first real Tier B walker build with all 119 modules admitted still
-- mismatched the float->int results (cycles 464..528: F2I/F2U, e.g. 2.5
-- RNE -> 10 instead of 2 -- a 2-bit alignment error), everything else
-- bit-exact.  This is VX_fcvt_unit's F2I align/round process (comb_fused_5,
-- exec.vhd:72423) verbatim: `norm_mant & 33 zero bits`, a dynamic `srl`,
-- guard/round/sticky slices at 32/31/30..0, a second `srl`, a dynamic
-- bit read at a cast index, `sll`, and a mask subtraction.
library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;
entity r23_f2i is
  port (clk : in logic3d; reset : in logic3d;
        a : in logic3d_vector(31 downto 0); b : in logic3d_vector(31 downto 0);
        op : in logic3d_vector(3 downto 0); y : out logic3d_vector(31 downto 0));
end entity;
architecture from_verilog of r23_f2i is
%s
  signal yr : logic3d_vector(31 downto 0) := (others => L3D_0);
%s
begin
  y <= yr;
  -- norm_mant = a, align_shamt 0..31, dst_man_w 28..31 (int32 F2I is 31)
  LPM_d0_ivl_266 <= a(20 downto 0) & a & (L3D_0 & L3D_0 & L3D_0 & L3D_0 & L3D_0 & L3D_0 & L3D_0 & op & b(0)) & b(19 downto 0);
  dst_man_w_s4 <= L3D_0 & L3D_1 & L3D_1 & L3D_1 & op(1 downto 0);
%s
  process is
  begin
    if rising_edge(clk) then
      if is_one(reset) then
        yr <= (others => L3D_0);
      else
        yr <= fp_trunc_s4 xor aligned_mant_s4
              xor (tmp_ivl_350 & fp_guard_s4 & sticky_bit_s4 & round_bit_s4 & guard_bit_s4 & tmp_ivl_296(26 downto 0));
      end if;
    end if;
    wait on clk;
  end process;
end architecture;
""" % ("\n".join(decls), funcs, proc)
open("r23_f2i.vhd", "w").write(s)
print("wrote r23_f2i.vhd", len(s.splitlines()), "lines")
