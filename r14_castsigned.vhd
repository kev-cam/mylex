-- New (Tier A census after items 1-10): VX_serial_div (exec.vhd:5293-5316):
-- `v_nba_cntr := cntr - sv2v_cast_5E5BC_signed(<const>)` -- the inlined body
-- `Result := inp; return Result` with a CONSTANT actual:
-- `var-read SV2V_CAST_5E5BC_SIGNED_RESULT@seq-assign`.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;

entity r14_castsigned is
  port (
    clk : in logic3d;
    reset : in logic3d;
    a : in logic3d_vector(31 downto 0);
    b : in logic3d_vector(31 downto 0);
    op : in logic3d_vector(3 downto 0);
    y : out logic3d_vector(31 downto 0)
  );
end entity;

architecture from_verilog of r14_castsigned is
  impure function sv2v_cast_5E5BC_signed (
    inp : logic3d_vector(4 downto 0)
  ) 
  return logic3d_vector;
  
  signal busy_r : logic3d := L3D_X;
  signal cntr : logic3d_vector(4 downto 0) := (others => L3D_X);
  signal y_r : logic3d_vector(31 downto 0) := (others => L3D_0);
  
  impure function sv2v_cast_5E5BC_signed (
    inp : logic3d_vector(4 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_5E5BC_signed_Result : logic3d_vector(4 downto 0);
  begin
    sv2v_cast_5E5BC_signed_Result := inp;
    return sv2v_cast_5E5BC_signed_Result;
  end function;
  function Boolean_To_Logic(B : Boolean) return logic3d is
  begin
    if B then
      return L3D_1;
    else
      return L3D_0;
    end if;
  end function;

begin
  process (all) is

  begin
    y <= y_r;
  end process;

  -- Generated from always process in VX_serial_div
  process is
    variable v_nba_busy_r : logic3d;
    variable v_nba_cntr : logic3d_vector(4 downto 0);
    variable nba_init_run : Boolean := True;
  begin
    v_nba_busy_r := busy_r;
    v_nba_cntr := cntr;
    if rising_edge(clk) then
      if is_one(reset) then
        v_nba_busy_r := L3D_0;
      else
        if is_one(op(0)) then
          v_nba_busy_r := L3D_1;
        end if;
        if is_one(busy_r) and is_one(Boolean_To_Logic((resize(cntr, 32) = logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0)))) then
          v_nba_busy_r := L3D_0;
        end if;
      end if;
      v_nba_cntr := cntr - sv2v_cast_5E5BC_signed(logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_1));
      if is_one(op(0)) then
        v_nba_cntr := sv2v_cast_5E5BC_signed(logic3d_vector'(L3D_1, L3D_1, L3D_1, L3D_1, L3D_1));
      end if;
    end if;
    if nba_init_run then
      nba_init_run := False;
    else
      wait for 0 ns;
    end if;
    busy_r <= v_nba_busy_r;
    cntr <= v_nba_cntr;
    wait on clk;
  end process;

  process (clk) is
  begin
    if rising_edge(clk) then
      if is_one(reset) then
        y_r <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
      else
        y_r <= a(31 downto 6) & busy_r & cntr;
      end if;
    end if;
  end process;
end architecture;
