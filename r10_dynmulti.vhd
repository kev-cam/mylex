-- Item 8 (catalogue): several dynamic single-bit writes to the same target in
-- one process.  (a) the LSU byte-enable decode, comb, two writes in one case
-- arm and one in another (exec.vhd:12488-12503 g_mem_req_byteen_w); (b) the
-- VX_allocator shape, clocked NBA shadow, two dynamic writes in two ifs.
-- The walker's single masked compose reads the PRE value and declines the
-- second write: `dyn-multi@case-choice` / `dyn-multi@if-cond`.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;

entity r10_dynmulti is
  port (
    clk : in logic3d;
    reset : in logic3d;
    a : in logic3d_vector(31 downto 0);
    b : in logic3d_vector(31 downto 0);
    op : in logic3d_vector(3 downto 0);
    y : out logic3d_vector(31 downto 0)
  );
end entity;

architecture from_verilog of r10_dynmulti is
  signal byteen0 : logic3d_vector(3 downto 0) := (others => L3D_X);
  signal byteen1 : logic3d_vector(3 downto 0) := (others => L3D_X);
  signal y_r : logic3d_vector(31 downto 0) := (others => L3D_0);
begin
  process (all) is

  begin
    y <= y_r;
  end process;

  -- Generated from always process in g_mem_req_byteen_w[0]
  process (a, op) is
    variable Verilog_Case_Ex : unsigned(1 downto 0);
  begin
    byteen0 <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0);
    Verilog_Case_Ex := l3d_to_unsigned(op(1 downto 0));
    case Verilog_Case_Ex is
      when "00" =>
        byteen0(l3d_index(a(0 + 1 downto 0), False)) <= L3D_1;
      when "01" =>
        byteen0(l3d_index(a(1) & L3D_0, False)) <= L3D_1;
        byteen0(l3d_index(a(1) & L3D_1, False)) <= L3D_1;
      when others =>
        byteen0 <= logic3d_vector'(L3D_1, L3D_1, L3D_1, L3D_1);
    end case;
  end process;

  -- Generated from always process (VX_allocator free_slots_n shape)
  process is
    variable v_nba_byteen1 : logic3d_vector(3 downto 0);
    variable nba_init_run : Boolean := True;
  begin
    v_nba_byteen1 := byteen1;
    if rising_edge(clk) then
      if is_one(reset) then
        v_nba_byteen1 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0);
      else
        if is_one(op(2)) then
          v_nba_byteen1(l3d_index(a(3 downto 2), False)) := L3D_1;
        end if;
        if is_one(op(3)) then
          v_nba_byteen1(l3d_index(b(1 downto 0), False)) := L3D_0;
        end if;
      end if;
    end if;
    if nba_init_run then
      nba_init_run := False;
    else
      wait for 0 ns;
    end if;
    byteen1 <= v_nba_byteen1;
    wait on clk;
  end process;

  process (clk) is
  begin
    if rising_edge(clk) then
      if is_one(reset) then
        y_r <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
      else
        y_r <= a(31 downto 8) & byteen0 & byteen1;
      end if;
    end if;
  end process;
end architecture;
