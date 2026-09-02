library ieee;
use ieee.std_logic_1164.all;
library sv2vhdl;
use sv2vhdl.logic3d_types_pkg.all;

-- Drives nba_slice through reset, an enable pulse, an enable-HOLD window,
-- then more enabled cycles, checking q after every edge against the
-- SystemVerilog reference semantics (q[1] <= reset ? 0 : en ? d[1] : q[1];
-- q[0] <= en ? d[0] : q[0]). Any lost update fails.
entity tb_nba_slice is end entity;

architecture t of tb_nba_slice is
    signal clk, reset, en : logic3d := L3D_0;
    signal d : logic3d_vector(1 downto 0) := (others => L3D_0);
    signal q : logic3d_vector(1 downto 0);
begin
    dut: entity work.nba_slice
        port map (clk => clk, reset => reset, en => en, d => d, q => q);

    stim: process
        variable ref1, ref0 : integer := -1;   -- -1 = don't care (X)
        variable errors : integer := 0;
        variable cyc : integer := 0;

        function b2i(v : logic3d) return integer is
        begin
            if v = L3D_1 then return 1;
            elsif v = L3D_0 then return 0;
            else return -1; end if;
        end function;

        procedure tick(r, e, d1, d0 : integer) is
        begin
            if r = 1 then reset <= L3D_1; else reset <= L3D_0; end if;
            if e = 1 then en <= L3D_1; else en <= L3D_0; end if;
            if d1 = 1 then d(1) <= L3D_1; else d(1) <= L3D_0; end if;
            if d0 = 1 then d(0) <= L3D_1; else d(0) <= L3D_0; end if;
            -- reference model (SV NBA semantics, pre-edge reads)
            if r = 1 then ref1 := 0; elsif e = 1 then ref1 := d1; end if;
            if e = 1 then ref0 := d0; end if;
            wait for 1 ns;
            clk <= L3D_1; wait for 5 ns;
            clk <= L3D_0; wait for 4 ns;
            cyc := cyc + 1;
            if (ref1 >= 0 and b2i(q(1)) /= ref1) or (ref0 >= 0 and b2i(q(0)) /= ref0) then
                report "MISMATCH cycle " & integer'image(cyc) &
                       " (reset=" & integer'image(r) & " en=" & integer'image(e) &
                       " d=" & integer'image(d1) & integer'image(d0) & ")" &
                       ": q=" & integer'image(b2i(q(1))) & integer'image(b2i(q(0))) &
                       " want " & integer'image(ref1) & integer'image(ref0)
                    severity error;
                errors := errors + 1;
            end if;
        end procedure;
    begin
        tick(1, 0, 0, 0);   -- reset
        tick(1, 0, 0, 0);   -- reset
        tick(0, 1, 1, 1);   -- load 11
        tick(0, 0, 0, 0);   -- HOLD (en=0): must keep 11
        tick(0, 0, 0, 0);   -- HOLD
        tick(0, 1, 0, 1);   -- load 01
        tick(0, 1, 1, 0);   -- load 10
        tick(0, 0, 1, 1);   -- HOLD: must keep 10
        tick(0, 1, 1, 1);   -- load 11
        tick(1, 0, 0, 0);   -- reset: q[1]=0, q[0] holds 1
        tick(0, 0, 0, 0);   -- HOLD: 01
        if errors = 0 then
            report "PASS: disjoint-slice NBA writers kept every update";
        else
            report "FAIL: " & integer'image(errors) & " lost/corrupted updates" severity failure;
        end if;
        wait;
    end process;
end architecture;
