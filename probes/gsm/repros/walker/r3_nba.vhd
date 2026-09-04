-- Item 3: the tgt-vhdl NBA idiom tail and a merged same-edge always block.
-- Every clocked process with an NBA shadow variable ends in
--   if nba_init_run then nba_init_run := False; else wait for 0 ns; end if;
-- between the edge-if and the commit `pipe_sig <= v_nba_pipe_sig`, and a
-- second `if rising_edge(clk)` carries a merged always block (VX_pipe_register
-- g_partial_reset, alu.vhd:457-512).  HEAD's pre/post scan of the clocked
-- shape declines both: `proc-extra-stmt`.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;

entity r3_nba is
  port (
    clk : in logic3d;
    reset : in logic3d;
    a : in logic3d_vector(31 downto 0);
    b : in logic3d_vector(31 downto 0);
    op : in logic3d_vector(3 downto 0);
    y : out logic3d_vector(31 downto 0)
  );
  attribute nvc_verilog_src : string;
  attribute nvc_verilog_src of r3_nba : entity is "r3_nba.v:1";
end entity;

architecture from_verilog of r3_nba is
  signal pipe_sig : logic3d_vector(31 downto 0) := (others => L3D_0);
begin
  process (all) is

  begin
    y <= pipe_sig;
  end process;

  -- Generated from always process in g_partial_reset [+ merged same-edge always block(s)]
  process is
    variable v_nba_pipe_sig : logic3d_vector(31 downto 0);
    variable nba_init_run : Boolean := True;
  begin
    v_nba_pipe_sig := pipe_sig;
    if rising_edge(clk) then
      if is_one(reset) then
        v_nba_pipe_sig(31) := L3D_0;
      else
        if is_one(op(0)) then
          v_nba_pipe_sig(31) := a(31);
        end if;
      end if;
    end if;
    if rising_edge(clk) then
      if is_one(op(0)) then
        v_nba_pipe_sig(0 + 30 downto 0) := l3d_xor(a(0 + 30 downto 0), b(0 + 30 downto 0));
      end if;
    end if;
    if nba_init_run then
      nba_init_run := False;
    else
      wait for 0 ns;
    end if;
    pipe_sig <= v_nba_pipe_sig;
    wait on clk;
  end process;
end architecture;
