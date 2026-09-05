-- Self-checking bench shared by every walker repro (run.sh instantiates it
-- per DUT by substituting @DUT@).  Every DUT has the same ports: clk/reset,
-- a/b (32), op (4) in; y (32) out.  40 cycles of xorshift stimulus are
-- driven at the falling edge; the registered output is folded into a
-- rotate-xor checksum and reported as `Y=<n>` — the accel run (RTLIL
-- builder or text path) must report the same Y as the plain interpreter.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.logic3d_types_pkg.all;

entity @DUT@_tb is end entity;

architecture t of @DUT@_tb is
  signal clk : logic3d := L3D_0;
  signal reset : logic3d := L3D_1;
  signal a, b : logic3d_vector(31 downto 0) := (others => L3D_0);
  signal op : logic3d_vector(3 downto 0) := (others => L3D_0);
  signal y : logic3d_vector(31 downto 0);
  signal running : boolean := true;
begin
  dut : entity work.@DUT@
    port map (clk => clk, reset => reset, a => a, b => b, op => op, y => y);

  clkgen : process is
  begin
    wait for 5 ns;
    while running loop
      clk <= L3D_1; wait for 5 ns;
      clk <= L3D_0; wait for 5 ns;
    end loop;
    wait;
  end process;

  stim : process is
    variable x : unsigned(31 downto 0) := x"2545F491";
    variable acc : unsigned(31 downto 0) := (others => '0');
  begin
    for i in 0 to 39 loop
      wait until clk = L3D_0;             -- drive at the falling edge
      if i = 2 then reset <= L3D_0; end if;
      x := x xor (x sll 13);
      x := x xor (x srl 17);
      x := x xor (x sll 5);
      a <= unsigned_to_l3d(x);
      b <= unsigned_to_l3d(x(15 downto 0) & x(31 downto 16));
      op <= unsigned_to_l3d(x(3 downto 0));
      wait for 1 ns;                       -- registered y from the last edge
      acc := (acc(30 downto 0) & acc(31)) xor l3d_to_unsigned(y);
    end loop;
    report "Y=" & integer'image(to_integer(acc(30 downto 0)));
    report "PASSED";
    running <= false;
    wait;
  end process;
end architecture;
