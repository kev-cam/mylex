-- tb_add4_cbc — correct-by-construction gate for the 4-bit adder:
-- structural th-gate adder vs SYNC golden AND vs the behavioral dual-rail
-- reference, rail-for-rail, over the full input space, 4-phase RTZ.
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;
library ncl;
use ncl.ncl.all;

entity tb_add4_cbc is
end entity tb_add4_cbc;

architecture test of tb_add4_cbc is
  signal a, b       : ncl_logic_vector(3 downto 0);
  signal res_struct : ncl_logic_vector(3 downto 0);
  signal res_behav  : ncl_logic_vector(3 downto 0);
  signal passes     : integer := 0;
begin
  dut_struct: entity work.ncl_add4_struct port map (a => a, b => b, result => res_struct);
  dut_behav:  entity work.ncl_add4_behav  port map (a => a, b => b, result => res_behav);

  stim: process
    variable golden : std_logic_vector(3 downto 0);
  begin
    a <= ncl_null_vector(4); b <= ncl_null_vector(4); wait for 10 ns;
    for ai in 0 to 15 loop
      for bi in 0 to 15 loop
        a <= ncl_encode(std_logic_vector(to_unsigned(ai, 4)));
        b <= ncl_encode(std_logic_vector(to_unsigned(bi, 4)));
        wait for 10 ns;
        golden := std_logic_vector(to_unsigned((ai + bi) mod 16, 4));
        assert ncl_complete(res_struct) = '1' and ncl_complete(res_behav) = '1'
          report "incomplete at " & integer'image(ai) & "+" & integer'image(bi) severity failure;
        assert ncl_decode(res_struct) = golden
          report "STRUCT != golden at " & integer'image(ai) & "+" & integer'image(bi) severity failure;
        assert ncl_decode(res_behav) = golden
          report "BEHAV != golden at " & integer'image(ai) & "+" & integer'image(bi) severity failure;
        for k in 0 to 3 loop
          assert res_struct(k).L = res_behav(k).L and res_struct(k).H = res_behav(k).H
            report "rail mismatch bit " & integer'image(k) severity failure;
        end loop;
        passes <= passes + 1;
        a <= ncl_null_vector(4); b <= ncl_null_vector(4); wait for 10 ns;
        assert ncl_complete(res_struct) = '0' and ncl_complete(res_behav) = '0'
          report "no return-to-NULL at " & integer'image(ai) & "+" & integer'image(bi) severity failure;
      end loop;
    end loop;
    report "CBC-GATE PASS: structural th-gate adder == sync golden == behavioral, 4-phase RTZ ("
         & integer'image(passes) & "/256)";
    wait;
  end process;
end architecture test;
