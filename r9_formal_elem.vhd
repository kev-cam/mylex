-- Item 9 (found by the first real RTLIL build of the ALU — invisible to the
-- census, whose null builder accepts any sigspec): an ELEMENT read of an
-- inlined function's formal, and a user body whose name carries a
-- numeric_std conversion name.
--   VX_gpu_pkg_inst_alu_is_sub(opnd) = opnd(1)   -> HEAD renders the bare
--     formal `opnd[1]` (the formal is a T_PARAM_DECL, not a T_VAR_DECL, so
--     the substitution table was never consulted): `gsm_rtlil: no wire
--     'opnd'` and the session is poisoned (api-case-assign).
--   VX_gpu_pkg_inst_alu_SIGNED(opnd) = opnd(0)   -> the name matched the
--     numeric_std `SIGNED(x)` identity pattern and the whole argument was
--     passed through (a 4-bit value into the 1-bit is_signed).
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;

entity r9_formal_elem is
  port (
    clk : in logic3d;
    reset : in logic3d;
    a : in logic3d_vector(31 downto 0);
    b : in logic3d_vector(31 downto 0);
    op : in logic3d_vector(3 downto 0);
    y : out logic3d_vector(31 downto 0)
  );
end entity;

architecture from_verilog of r9_formal_elem is
  signal is_sub_op : logic3d := L3D_X;
  signal is_signed : logic3d := L3D_X;
  signal op_class : logic3d_vector(1 downto 0) := (others => L3D_X);
  signal y_c : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal y_r : logic3d_vector(31 downto 0) := (others => L3D_0);

  impure function VX_gpu_pkg_inst_alu_is_sub (
    opnd : logic3d_vector(3 downto 0)
  )
  return logic3d;

  impure function VX_gpu_pkg_inst_alu_signed (
    opnd : logic3d_vector(3 downto 0)
  )
  return logic3d;

  impure function VX_gpu_pkg_inst_alu_class (
    opnd : logic3d_vector(3 downto 0)
  )
  return logic3d_vector;

  -- Generated from function VX_gpu_pkg_inst_alu_is_sub
  impure function VX_gpu_pkg_inst_alu_is_sub (
    opnd : logic3d_vector(3 downto 0)
  )
  return logic3d is
    variable VX_gpu_pkg_inst_alu_is_sub_Result : logic3d;
  begin
    VX_gpu_pkg_inst_alu_is_sub_Result := opnd(1);
    return VX_gpu_pkg_inst_alu_is_sub_Result;
  end function;

  -- Generated from function VX_gpu_pkg_inst_alu_signed
  impure function VX_gpu_pkg_inst_alu_signed (
    opnd : logic3d_vector(3 downto 0)
  )
  return logic3d is
    variable VX_gpu_pkg_inst_alu_signed_Result : logic3d;
  begin
    VX_gpu_pkg_inst_alu_signed_Result := opnd(0);
    return VX_gpu_pkg_inst_alu_signed_Result;
  end function;

  -- Generated from function VX_gpu_pkg_inst_alu_class
  impure function VX_gpu_pkg_inst_alu_class (
    opnd : logic3d_vector(3 downto 0)
  )
  return logic3d_vector is
    variable VX_gpu_pkg_inst_alu_class_Result : logic3d_vector(1 downto 0);
  begin
    VX_gpu_pkg_inst_alu_class_Result := opnd(2 + 1 downto 2);
    return VX_gpu_pkg_inst_alu_class_Result;
  end function;
begin
  process (all) is

  begin
    y <= y_r;
  end process;

  comb_fused_0: process (a, b, op) is
  begin
    is_sub_op := VX_gpu_pkg_inst_alu_is_sub(op);
    is_signed := VX_gpu_pkg_inst_alu_signed(op);
    op_class := VX_gpu_pkg_inst_alu_class(op);
    y_c := a(0 + 27 downto 0) & op_class & is_signed & is_sub_op;
  end process;

  process (clk) is
  begin
    if rising_edge(clk) then
      if is_one(reset) then
        y_r <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
      else
        y_r <= y_c;
      end if;
    end if;
  end process;
end architecture;
