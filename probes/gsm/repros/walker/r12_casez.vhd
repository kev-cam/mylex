-- Item 5 tail (catalogue): tgt-vhdl's casez expansion `((sel(0) = 'Z') or
-- (sel(0) = '1')) and ...` on a 2-state unsigned selector (VX_rr_arbiter
-- g_lut2, exec.vhd:4239-4275).  The metavalue literal has no sigspec:
-- `ref@if-cond`; behind it the `else` arm assigns L3D_X to a variable.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;

entity r12_casez is
  port (
    clk : in logic3d;
    reset : in logic3d;
    a : in logic3d_vector(31 downto 0);
    b : in logic3d_vector(31 downto 0);
    op : in logic3d_vector(3 downto 0);
    y : out logic3d_vector(31 downto 0)
  );
  attribute nvc_verilog_src : string;
  attribute nvc_verilog_src of r12_casez : entity is "r12_casez.v:1";
end entity;

architecture from_verilog of r12_casez is
  impure function sv2v_cast_F1C5E_signed (
    inp : logic3d
  ) 
  return logic3d;
  
  signal grant_index_w : logic3d := L3D_X;
  signal grant_onehot_w : logic3d_vector(1 downto 0) := (others => L3D_X);
  signal state : logic3d := L3D_X;
  signal requests : logic3d_vector(1 downto 0) := (others => L3D_X);
  signal y_r : logic3d_vector(31 downto 0) := (others => L3D_0);
  
  impure function sv2v_cast_F1C5E_signed (
    inp : logic3d
  ) 
  return logic3d is
    variable sv2v_cast_F1C5E_signed_Result : logic3d;
  begin
    sv2v_cast_F1C5E_signed_Result := inp;
    return sv2v_cast_F1C5E_signed_Result;
  end function;
begin
  process (all) is

  begin
    y <= y_r;
  end process;

  process (all) is

  begin
    state <= b(0);
    requests <= a(1 downto 0);
  end process;

  -- Generated from always process in g_lut2
  process (state, requests) is
    variable Verilog_Case_Ex : unsigned(2 downto 0);
    variable v_grant_index_w : logic3d;
    variable v_grant_onehot_w : logic3d_vector(1 downto 0);
  begin
    v_grant_onehot_w := grant_onehot_w;
    v_grant_index_w := grant_index_w;
    Verilog_Case_Ex := l3d_to_unsigned(state & requests);
    -- Generated from casez statement
    if ((Verilog_Case_Ex(0) = 'Z') or (Verilog_Case_Ex(0) = '1')) and ((Verilog_Case_Ex(1) = 'Z') or (Verilog_Case_Ex(1) = '0')) and ((Verilog_Case_Ex(2) = 'Z') or (Verilog_Case_Ex(2) = '0')) then
      v_grant_onehot_w := logic3d_vector'(L3D_0, L3D_1);
      v_grant_index_w := sv2v_cast_F1C5E_signed(L3D_0);
    elsif ((Verilog_Case_Ex(0) = 'Z') or (Verilog_Case_Ex(0) = '1')) and ((Verilog_Case_Ex(2) = 'Z') or (Verilog_Case_Ex(2) = '1')) then
      v_grant_onehot_w := logic3d_vector'(L3D_0, L3D_1);
      v_grant_index_w := sv2v_cast_F1C5E_signed(L3D_0);
    elsif ((Verilog_Case_Ex(1) = 'Z') or (Verilog_Case_Ex(1) = '1')) and ((Verilog_Case_Ex(2) = 'Z') or (Verilog_Case_Ex(2) = '0')) then
      v_grant_onehot_w := logic3d_vector'(L3D_1, L3D_0);
      v_grant_index_w := sv2v_cast_F1C5E_signed(L3D_1);
    elsif ((Verilog_Case_Ex(0) = 'Z') or (Verilog_Case_Ex(0) = '0')) and ((Verilog_Case_Ex(1) = 'Z') or (Verilog_Case_Ex(1) = '1')) and ((Verilog_Case_Ex(2) = 'Z') or (Verilog_Case_Ex(2) = '1')) then
      v_grant_onehot_w := logic3d_vector'(L3D_1, L3D_0);
      v_grant_index_w := sv2v_cast_F1C5E_signed(L3D_1);
    else
      v_grant_onehot_w := logic3d_vector'(L3D_0, L3D_0);
      v_grant_index_w := L3D_X;
    end if;
    grant_index_w <= v_grant_index_w;
    grant_onehot_w <= v_grant_onehot_w;
  end process;

  process (clk) is
  begin
    if rising_edge(clk) then
      if is_one(reset) then
        y_r <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
      else
        y_r <= a(31 downto 3) & grant_index_w & grant_onehot_w;
      end if;
    end if;
  end process;
end architecture;
