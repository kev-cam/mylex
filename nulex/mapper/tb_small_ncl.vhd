-- tb_small_ncl — equivalence gate for the MAPPED dual-rail NCL netlist vs the
-- synchronous golden of small.v:  y = sel ? (a+b) mod 16 : (a xor b).
-- Sweeps a,b in [0,15] x sel in {0,1} (512 cases), DATA then NULL each,
-- asserting completion + ncl_decode(y) == golden + return-to-NULL.
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;
library ncl;
use ncl.ncl.all;

entity tb_small_ncl is
end entity tb_small_ncl;

architecture test of tb_small_ncl is
  signal a, b, y : ncl_logic_vector(3 downto 0);
  signal sel     : ncl_logic;
  signal passes  : integer := 0;
begin
  dut: entity work.small_ncl port map (a => a, b => b, sel => sel, y => y);

  stim: process
    variable golden : std_logic_vector(3 downto 0);
  begin
    a <= ncl_null_vector(4); b <= ncl_null_vector(4); sel <= NCL_NULL; wait for 10 ns;
    for vs in 0 to 1 loop
      for ia in 0 to 15 loop
        for ib in 0 to 15 loop
          a <= ncl_encode(std_logic_vector(to_unsigned(ia,4)));
          b <= ncl_encode(std_logic_vector(to_unsigned(ib,4)));
          if vs = 1 then sel <= NCL_DATA1; else sel <= NCL_DATA0; end if;
          wait for 10 ns;
          if vs = 1 then
            golden := std_logic_vector(to_unsigned((ia+ib) mod 16, 4));
          else
            golden := std_logic_vector(to_unsigned(ia,4)) xor std_logic_vector(to_unsigned(ib,4));
          end if;
          assert ncl_complete(y) = '1'
            report "incomplete sel=" & integer'image(vs) & " a=" & integer'image(ia)
                 & " b=" & integer'image(ib) severity failure;
          assert ncl_decode(y) = golden
            report "MAPPED != golden sel=" & integer'image(vs) & " a=" & integer'image(ia)
                 & " b=" & integer'image(ib)
                 & " got=" & integer'image(to_integer(unsigned(ncl_decode(y))))
                 & " exp=" & integer'image(to_integer(unsigned(golden))) severity failure;
          passes <= passes + 1;
          a <= ncl_null_vector(4); b <= ncl_null_vector(4); sel <= NCL_NULL; wait for 10 ns;
          assert ncl_complete(y) = '0' report "no return-to-NULL" severity failure;
        end loop;
      end loop;
    end loop;
    report "MAP-GATE PASS: mapped dual-rail NCL netlist == sync golden over " &
           integer'image(passes) & "/512 cases, 4-phase RTZ";
    wait;
  end process;
end architecture test;
