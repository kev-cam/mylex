library ieee;
use ieee.std_logic_1164.all;
library sv2vhdl;
use sv2vhdl.logic3d_types_pkg.all;

entity tb_eb is end entity;

architecture t of tb_eb is
    signal clk, reset, valid_in, ready_in, data_in : logic3d := L3D_0;
    signal data_out, ready_out, valid_out : logic3d := L3D_0;
begin
    dut: entity work.vx_elastic_buffer
        port map (clk => clk, reset => reset,
                  valid_in => valid_in, ready_in => ready_in, data_in => data_in,
                  data_out => data_out, ready_out => ready_out, valid_out => valid_out);

    stim: process
        type seq_t is array (0 to 4) of integer;
        constant send : seq_t := (1, 0, 1, 1, 0);
        variable pushed, popped : seq_t := (others => -1);
        variable np, nq : integer := 0;
        procedure tick is
        begin
            -- sample handshakes as they stand at the coming edge
            if valid_in = L3D_1 and ready_in = L3D_1 and np <= pushed'high then
                if data_in = L3D_1 then pushed(np) := 1; else pushed(np) := 0; end if;
                np := np + 1;
            end if;
            if valid_out = L3D_1 and ready_out = L3D_1 and nq <= popped'high then
                if data_out = L3D_1 then popped(nq) := 1; else popped(nq) := 0; end if;
                nq := nq + 1;
            end if;
            clk <= L3D_1; wait for 5 ns;
            clk <= L3D_0; wait for 5 ns;
        end procedure;
        variable i : integer := 0;
    begin
        reset <= L3D_1; tick; tick; reset <= L3D_0;
        ready_out <= L3D_1;
        while nq <= popped'high loop
            -- backpressure window mid-stream
            if i = 2 then ready_out <= L3D_0; end if;
            if i = 4 then ready_out <= L3D_1; end if;
            if np <= pushed'high then
                valid_in <= L3D_1;
                if send(np) = 1 then data_in <= L3D_1; else data_in <= L3D_0; end if;
            else
                valid_in <= L3D_0;
            end if;
            wait for 1 ns;  -- let combinational ready settle
            tick;
            i := i + 1;
            assert i < 50 report "TIMEOUT" severity failure;
        end loop;
        for k in seq_t'range loop
            assert popped(k) = send(k)
                report "MISMATCH at " & integer'image(k) &
                       ": got " & integer'image(popped(k)) &
                       " want " & integer'image(send(k)) severity error;
        end loop;
        if popped = send then
            report "PASS: 5 tokens through VX_elastic_buffer with backpressure, order and data intact";
        else
            report "FAIL" severity failure;
        end if;
        wait;
    end process;
end architecture;
