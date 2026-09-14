-- tb_ncl_and2 — equivalence gate for the DIMS AND2 rewrite rule.
-- Exhaustive over the 2-input space, DATA then NULL each case:
--   DATA: assert z is DATA (complete) and ncl_decode(z) = (a AND b) [sync golden]
--   NULL: assert z returns to NULL (spacer)  [4-phase RTZ, input-completeness]
library IEEE;
use IEEE.std_logic_1164.all;
library ncl;
use ncl.ncl.all;

entity tb_ncl_and2 is
end entity tb_ncl_and2;

architecture test of tb_ncl_and2 is
  signal a, b, z : ncl_logic;
  signal passes  : integer := 0;
begin
  dut: entity work.ncl_and2 port map (a => a, b => b, z => z);

  stim: process
    type slv_t is array (0 to 1) of std_logic;
    constant vals : slv_t := ('0', '1');
    variable golden : std_logic;
  begin
    a <= NCL_NULL; b <= NCL_NULL; wait for 10 ns;
    for ia in 0 to 1 loop
      for ib in 0 to 1 loop
        -- DATA
        a <= ncl_encode(vals(ia)); b <= ncl_encode(vals(ib)); wait for 10 ns;
        assert ncl_is_data(z)
          report "AND2 incomplete for a=" & std_logic'image(vals(ia)) & " b=" & std_logic'image(vals(ib))
          severity failure;
        golden := vals(ia) and vals(ib);
        assert ncl_decode(z) = golden
          report "AND2 wrong: a=" & std_logic'image(vals(ia)) & " b=" & std_logic'image(vals(ib))
               & " got=" & std_logic'image(ncl_decode(z)) & " exp=" & std_logic'image(golden)
          severity failure;
        passes <= passes + 1;
        -- NULL
        a <= NCL_NULL; b <= NCL_NULL; wait for 10 ns;
        assert ncl_is_null(z)
          report "AND2 no return-to-NULL" severity failure;
      end loop;
    end loop;
    report "AND2-GATE PASS: DIMS AND2 == sync golden over all 4 inputs, 4-phase RTZ ("
         & integer'image(passes) & "/4)";
    wait;
  end process;
end architecture test;
