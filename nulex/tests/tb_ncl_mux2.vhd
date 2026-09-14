-- tb_ncl_mux2 — exhaustive equivalence gate for the 3-input DIMS MUX rule.
-- Y = s ? b : a (yosys $mux). Over all 8 (s,a,b): DATA then NULL, assert
-- complete + ncl_decode(y) == golden + return-to-NULL.
library IEEE;
use IEEE.std_logic_1164.all;
library ncl;
use ncl.ncl.all;

entity tb_ncl_mux2 is
end entity tb_ncl_mux2;

architecture test of tb_ncl_mux2 is
  signal s, a, b, y : ncl_logic;
  signal passes : integer := 0;
begin
  dut: entity work.ncl_mux2 port map (s => s, a => a, b => b, y => y);

  stim: process
    type sl2 is array (0 to 1) of std_logic;
    constant v : sl2 := ('0', '1');
    variable vs, va, vb, g : std_logic;
  begin
    s <= NCL_NULL; a <= NCL_NULL; b <= NCL_NULL; wait for 10 ns;
    for isel in 0 to 1 loop
      for ia in 0 to 1 loop
        for ib in 0 to 1 loop
          vs := v(isel); va := v(ia); vb := v(ib);
          if vs = '1' then g := vb; else g := va; end if;
          s <= ncl_encode(vs); a <= ncl_encode(va); b <= ncl_encode(vb); wait for 10 ns;
          assert ncl_is_data(y) report "MUX incomplete" severity failure;
          assert ncl_decode(y) = g
            report "MUX WRONG s=" & std_logic'image(vs) & " a=" & std_logic'image(va)
                 & " b=" & std_logic'image(vb) & " got=" & std_logic'image(ncl_decode(y))
                 & " exp=" & std_logic'image(g)
            severity failure;
          passes <= passes + 1;
          s <= NCL_NULL; a <= NCL_NULL; b <= NCL_NULL; wait for 10 ns;
          assert ncl_is_null(y) report "MUX no return-to-NULL" severity failure;
        end loop;
      end loop;
    end loop;
    report "MUX2-GATE PASS: DIMS 3-input MUX == sync golden over all 8 inputs, 4-phase RTZ ("
         & integer'image(passes) & "/8)";
    wait;
  end process;
end architecture test;
