-- New (Tier A census after items 1-10): VX_serial_div g_div (exec.vhd:5245-
-- 5264): `v_nba_working(64 downto 0) := Ternary_Unsigned(is_one(sub_result(32)),
-- working(63 downto 0) & L3D_0, sub_result(31 downto 0) & working(31 downto 0)
-- & L3D_1)` -- the mux's width comes from an unconstrained concatenation
-- chain that r2_width cannot size: `temp-width -1@seq-assign`.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;

entity r13_ternary is
  port (
    clk : in logic3d;
    reset : in logic3d;
    a : in logic3d_vector(31 downto 0);
    b : in logic3d_vector(31 downto 0);
    op : in logic3d_vector(3 downto 0);
    y : out logic3d_vector(31 downto 0)
  );
end entity;

architecture from_verilog of r13_ternary is
  signal working : logic3d_vector(64 downto 0) := (others => L3D_X);
  signal sub_result : logic3d_vector(32 downto 0) := (others => L3D_X);
  signal y_r : logic3d_vector(31 downto 0) := (others => L3D_0);
  function Ternary_Unsigned(T : Boolean; X, Y : logic3d_vector) return logic3d_vector is
  begin
    if T then return X; else return Y; end if;
  end function;

begin
  process (all) is

  begin
    y <= y_r;
  end process;

  process (all) is

  begin
    sub_result <= (L3D_0 & working(63 downto 32)) - (L3D_0 & a);
  end process;

  -- Generated from always process in g_div[0]
  process is
    variable v_nba_working : logic3d_vector(64 downto 0);
    variable nba_init_run : Boolean := True;
  begin
    v_nba_working := working;
    if rising_edge(clk) then
      if is_one(op(0)) then
        v_nba_working(0 + 64 downto 0) := L3D_0 & b & a;
      else
        if is_one(op(1)) then
          v_nba_working(0 + 64 downto 0) := Ternary_Unsigned(is_one(sub_result(32)), working(0 + 63 downto 0) & L3D_0, sub_result(0 + 31 downto 0) & working(0 + 31 downto 0) & L3D_1);
        end if;
      end if;
    end if;
    if nba_init_run then
      nba_init_run := False;
    else
      wait for 0 ns;
    end if;
    working <= v_nba_working;
    wait on clk;
  end process;

  process (clk) is
  begin
    if rising_edge(clk) then
      if is_one(reset) then
        y_r <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
      else
        y_r <= l3d_xor(working(31 downto 0), working(63 downto 32));
      end if;
    end if;
  end process;
end architecture;
