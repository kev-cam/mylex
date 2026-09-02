library ieee;
use ieee.std_logic_1164.all;
library sv2vhdl;
use sv2vhdl.logic3d_types_pkg.all;

entity tb_repro is end entity;

architecture t of tb_repro is
    signal clk, reset : logic3d := L3D_0;
    signal data_in, data_out : logic3d_vector(1 downto 0) := (others => L3D_0);
begin
    dut: entity work.repro
        port map (clk => clk, reset => reset, data_in => data_in, data_out => data_out);

    stim: process
        procedure tick is
        begin
            clk <= L3D_1; wait for 5 ns;
            clk <= L3D_0; wait for 5 ns;
        end procedure;
        variable ok : boolean := true;
    begin
        -- let the translated process pass its initial `wait for 0 ns` and
        -- park on `wait on clk` before the first edge (time-0 edge race)
        reset <= L3D_1; wait for 1 ns; tick;
        -- pipe[0][1:1] <= 1'b1 under reset: data_out(1) must be 1
        if data_out(1) /= L3D_1 then
            report "FAIL after reset: data_out(1) = " & logic3d'image(data_out(1)) & " want L3D_1" severity error;
            ok := false;
        end if;
        reset <= L3D_0; data_in <= (L3D_0, L3D_1); tick;
        -- pipe[0][1:1] <= data_in[1]; pipe[i][0:0] <= data_in[0]: data_out must be "01"
        if data_out(1) /= L3D_0 or data_out(0) /= L3D_1 then
            report "FAIL after load: data_out = " & logic3d'image(data_out(1)) & logic3d'image(data_out(0)) & " want 01" severity error;
            ok := false;
        end if;
        if ok then report "PASS"; else report "FAIL" severity failure; end if;
        wait;
    end process;
end architecture;
