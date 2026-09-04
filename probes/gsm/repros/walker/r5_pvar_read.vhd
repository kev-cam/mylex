-- Item 5: reading a process variable that was written inside a branch.
-- `Verilog_Case_Ex := l3d_to_unsigned(...)` sits in an if arm and the case
-- selector reads it right after (VX_alu_int g_alu_result, alu.vhd:2548-2610).
-- HEAD promotes the branch-written variable to a hold temp but has no read
-- path for it: `var-read VERILOG_CASE_EX@case-value`.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;

entity r5_pvar_read is
  port (
    clk : in logic3d;
    reset : in logic3d;
    a : in logic3d_vector(31 downto 0);
    b : in logic3d_vector(31 downto 0);
    op : in logic3d_vector(3 downto 0);
    y : out logic3d_vector(31 downto 0)
  );
end entity;

architecture from_verilog of r5_pvar_read is
  signal alu_result : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal is_alu_w : logic3d := L3D_X;
  signal op_class : logic3d_vector(1 downto 0) := (others => L3D_X);
  signal y_r : logic3d_vector(31 downto 0) := (others => L3D_0);
begin
  process (all) is

  begin
    y <= y_r;
  end process;

  comb_fused_0: process (op) is
  begin
    is_alu_w := op(3);
    op_class := op(0 + 1 downto 0);
  end process;

  -- Generated from always process in g_alu_result[0]
  process (op, a, b, is_alu_w, op_class) is
    variable Verilog_Case_Ex : unsigned(1 downto 0);
    variable Verilog_Case_Ex_1 : unsigned(2 downto 0);
    variable v_alu_result : logic3d_vector(31 downto 0);
  begin
    v_alu_result := alu_result;
    if resize(op(2 + 1 downto 2), 32) = logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_1) then
      Verilog_Case_Ex := l3d_to_unsigned(op(0 + 1 downto 0));
      case Verilog_Case_Ex is
        when "00" =>
          v_alu_result(0 + 31 downto 0) := a;
        when "01" =>
          v_alu_result(0 + 31 downto 0) := b;
        when "10" =>
          v_alu_result(0 + 31 downto 0) := l3d_xor(a, b);
        when others =>
          v_alu_result(0 + 31 downto 0) := a;
      end case;
    else
      Verilog_Case_Ex_1 := l3d_to_unsigned(is_alu_w & op_class);
      case Verilog_Case_Ex_1 is
        when "000" =>
          v_alu_result(0 + 31 downto 0) := l3d_and(a, b);
        when "001" =>
          v_alu_result(0 + 31 downto 0) := l3d_or(a, b);
        when "010" =>
          v_alu_result(0 + 31 downto 0) := a + b;
        when "011" =>
          v_alu_result(0 + 31 downto 0) := a - b;
        when "100" =>
          v_alu_result(0 + 31 downto 0) := l3d_not(a);
        when "101" =>
          v_alu_result(0 + 31 downto 0) := b;
        when "110" =>
          v_alu_result(0 + 31 downto 0) := a(0 + 15 downto 0) & b(0 + 15 downto 0);
        when "111" =>
          v_alu_result(0 + 31 downto 0) := l3d_xor(a, b);
        when others =>
          null;
      end case;
    end if;
    alu_result(0 + 31 downto 0) <= v_alu_result(0 + 31 downto 0);
  end process;

  process (clk) is
  begin
    if rising_edge(clk) then
      if is_one(reset) then
        y_r <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
      else
        y_r <= alu_result;
      end if;
    end if;
  end process;
end architecture;
