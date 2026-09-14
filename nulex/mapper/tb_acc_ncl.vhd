-- tb_acc_ncl — equivalence gate for the MAPPED SEQUENTIAL netlist (acc.v:
--   always @(posedge clk) r <= rst ? 0 : r + din).
-- Combinational cone = QDI dual-rail; the register = sync-emulation (ncl_dff).
-- Clock it, reset for 2 cycles, then stream din and compare decode(q) to the
-- running-sum model each cycle.
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;
library ncl;
use ncl.ncl.all;

entity tb_acc_ncl is
end entity tb_acc_ncl;

architecture test of tb_acc_ncl is
  signal clk  : std_logic := '0';
  signal rst  : ncl_logic;
  signal din  : ncl_logic_vector(3 downto 0);
  signal q    : ncl_logic_vector(3 downto 0);
  signal done : boolean := false;
begin
  dut: entity work.acc_ncl port map (clk => clk, rst => rst, din => din, q => q);

  clkgen: process begin
    while not done loop
      clk <= '0'; wait for 5 ns;
      clk <= '1'; wait for 5 ns;
    end loop;
    wait;
  end process;

  stim: process
    type iarr is array (natural range <>) of integer;
    constant seq : iarr := (3,1,7,15,4,8,2,9,0,5,13,6,11,1,14,10);
    variable gold, passes : integer := 0;
  begin
    -- reset preamble (2 edges) -> r = 0
    rst <= NCL_DATA1;
    din <= ncl_encode(std_logic_vector(to_unsigned(0,4)));
    wait until rising_edge(clk); wait for 1 ns;
    wait until rising_edge(clk); wait for 1 ns;
    gold := 0;
    assert ncl_complete(q) = '1' and to_integer(unsigned(ncl_decode(q))) = 0
      report "reset did not zero the accumulator" severity failure;

    rst <= NCL_DATA0;
    for i in seq'range loop
      din <= ncl_encode(std_logic_vector(to_unsigned(seq(i),4)));
      wait until rising_edge(clk); wait for 1 ns;
      gold := (gold + seq(i)) mod 16;
      assert ncl_complete(q) = '1'
        report "incomplete at cycle " & integer'image(i) severity failure;
      assert to_integer(unsigned(ncl_decode(q))) = gold
        report "ACC WRONG cycle " & integer'image(i)
             & " din=" & integer'image(seq(i))
             & " got=" & integer'image(to_integer(unsigned(ncl_decode(q))))
             & " exp=" & integer'image(gold) severity failure;
      passes := passes + 1;
    end loop;
    report "ACC-GATE PASS: mapped sequential dual-rail NCL (sync-emulation regs) == running sum over "
         & integer'image(passes) & " cycles";
    done <= true;
    wait;
  end process;
end architecture test;
