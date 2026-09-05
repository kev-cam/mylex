-- The first real Tier B walker build with all 119 modules admitted still
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
  signal norm_mant_s4 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal align_shamt_s4 : logic3d_vector(11 downto 0) := (others => L3D_X);
  signal tmp_ivl_283 : logic3d_vector(32 downto 0) := (others => L3D_X);
  signal tmp_ivl_309 : logic3d_vector(6 downto 0) := (others => L3D_X);
  signal tmp_ivl_316 : logic3d := L3D_X;
  signal tmp_ivl_323 : logic3d_vector(6 downto 0) := (others => L3D_X);
  signal tmp_ivl_333 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal tmp_ivl_337 : logic3d_vector(6 downto 0) := (others => L3D_X);
  signal tmp_ivl_343 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal tmp_ivl_285 : logic3d_vector(64 downto 0) := (others => L3D_X);
  signal tmp_ivl_312 : logic3d_vector(6 downto 0) := (others => L3D_X);
  signal tmp_ivl_313 : logic3d_vector(6 downto 0) := (others => L3D_X);
  signal tmp_ivl_336 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal aligned_mant_full_s4 : logic3d_vector(64 downto 0) := (others => L3D_X);
  signal tmp_ivl_318 : logic3d_vector(6 downto 0) := (others => L3D_X);
  signal aligned_mant_s4 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal guard_bit_s4 : logic3d := L3D_X;
  signal round_bit_s4 : logic3d := L3D_X;
  signal tmp_ivl_296 : logic3d_vector(30 downto 0) := (others => L3D_X);
  signal fp_trunc_sh_s4 : logic3d_vector(6 downto 0) := (others => L3D_X);
  signal sticky_bit_s4 : logic3d := L3D_X;
  signal fp_trunc_s4 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal tmp_ivl_325 : logic3d_vector(6 downto 0) := (others => L3D_X);
  signal tmp_ivl_339 : logic3d_vector(6 downto 0) := (others => L3D_X);
  signal tmp_ivl_330 : logic3d_vector(4 downto 0) := (others => L3D_X);
  signal tmp_ivl_341 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal tmp_ivl_328 : logic3d_vector(4 downto 0) := (others => L3D_X);
  signal fp_sticky_mask_s4 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal fp_guard_s4 : logic3d := L3D_X;
  signal tmp_ivl_347 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal tmp_ivl_350 : logic3d := L3D_X;
  signal LPM_d0_ivl_266 : logic3d_vector(84 downto 0) := (others => L3D_X);
  signal dst_man_w_s4 : logic3d_vector(5 downto 0) := (others => L3D_X);
  signal yr : logic3d_vector(31 downto 0) := (others => L3D_0);
  impure function sv2v_cast_7_signed (
    inp : logic3d_vector(6 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_7_signed_Result : logic3d_vector(6 downto 0);
  begin
    sv2v_cast_7_signed_Result := inp;
    return sv2v_cast_7_signed_Result;
  end function;
  impure function sv2v_cast_7 (
    inp : logic3d_vector(6 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_7_Result : logic3d_vector(6 downto 0);
  begin
    sv2v_cast_7_Result := inp;
    return sv2v_cast_7_Result;
  end function;
  impure function sv2v_cast_99F89_signed (
    inp : logic3d_vector(31 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_99F89_signed_Result : logic3d_vector(31 downto 0);
  begin
    sv2v_cast_99F89_signed_Result := inp;
    return sv2v_cast_99F89_signed_Result;
  end function;
  impure function sv2v_cast_C255F (
    inp : logic3d_vector(4 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_C255F_Result : logic3d_vector(4 downto 0);
  begin
    sv2v_cast_C255F_Result := inp;
    return sv2v_cast_C255F_Result;
  end function;
  function Reduce_OR(X : logic3d_vector) return logic3d is
    variable R : logic3d := L3D_0;
  begin
    for I in X'Range loop
      R := l3d_or(X(I), R);
    end loop;
    return R;
  end function;

begin
  y <= yr;
  -- norm_mant = a, align_shamt 0..31, dst_man_w 28..31 (int32 F2I is 31)
  LPM_d0_ivl_266 <= a(20 downto 0) & a & (L3D_0 & L3D_0 & L3D_0 & L3D_0 & L3D_0 & L3D_0 & L3D_0 & op & b(0)) & b(19 downto 0);
  dst_man_w_s4 <= L3D_0 & L3D_1 & L3D_1 & L3D_1 & op(1 downto 0);
  comb_fused_5: process (LPM_d0_ivl_266, dst_man_w_s4) is
  begin
    norm_mant_s4 := LPM_d0_ivl_266(32 + 31 downto 32);
    align_shamt_s4 := LPM_d0_ivl_266(20 + 11 downto 20);
    tmp_ivl_283 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    tmp_ivl_309 := logic3d_vector'(L3D_0, L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
    tmp_ivl_316 := L3D_0;
    tmp_ivl_323 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
    tmp_ivl_333 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
    tmp_ivl_337 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
    tmp_ivl_343 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
    tmp_ivl_285 := norm_mant_s4 & tmp_ivl_283;
    tmp_ivl_312 := sv2v_cast_7_signed(tmp_ivl_309);
    tmp_ivl_313 := tmp_ivl_316 & dst_man_w_s4;
    tmp_ivl_336 := sv2v_cast_99F89_signed(tmp_ivl_333);
    aligned_mant_full_s4 := tmp_ivl_285 srl To_Integer(align_shamt_s4);
    tmp_ivl_318 := sv2v_cast_7(tmp_ivl_313);
    aligned_mant_s4 := aligned_mant_full_s4(33 + 31 downto 33);
    guard_bit_s4 := aligned_mant_full_s4(32);
    round_bit_s4 := aligned_mant_full_s4(31);
    tmp_ivl_296 := aligned_mant_full_s4(0 + 30 downto 0);
    fp_trunc_sh_s4 := tmp_ivl_312 - tmp_ivl_318;
    sticky_bit_s4 := Reduce_OR(tmp_ivl_296);
    fp_trunc_s4 := aligned_mant_s4 srl To_Integer(fp_trunc_sh_s4);
    tmp_ivl_325 := fp_trunc_sh_s4 - tmp_ivl_323;
    tmp_ivl_339 := fp_trunc_sh_s4 - tmp_ivl_337;
    tmp_ivl_330 := tmp_ivl_325(0 + 4 downto 0);
    tmp_ivl_341 := tmp_ivl_336 sll To_Integer(tmp_ivl_339);
    tmp_ivl_328 := sv2v_cast_C255F(tmp_ivl_330);
    fp_sticky_mask_s4 := tmp_ivl_341 - tmp_ivl_343;
    fp_guard_s4 := l3d_bit_read(aligned_mant_s4, l3d_index(tmp_ivl_328, False));
    tmp_ivl_347 := l3d_and(aligned_mant_s4, fp_sticky_mask_s4);
    tmp_ivl_350 := Reduce_OR(tmp_ivl_347);
  end process;
  

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
