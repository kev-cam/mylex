library ieee;
use ieee.std_logic_1164.all;
library sv2vhdl;
use sv2vhdl.logic3d_types_pkg.all;

-- Checks merge_cases against SystemVerilog NBA semantics after every clock
-- edge. Reference (pre-edge reads):
--   posedge: cap[3:2] <= cntA (blkA's static local, pre-edge value)
--            cap[1:0] <= cntB (blkB's static local, pre-edge value)
--            cntA = reset ? 0 : cntA+1;  cntB = reset ? 3 : cntB-1  (post-edge)
--            same <= {d[3:1], 1}   (same[0]: blkE, the later block, wins the race)
--            both[3:2] <= d[3:2];  single <= reset ? 0 : en ? bitrev(d) : single
--   negedge: both[1:0] <= d[1:0]
entity tb_merge_cases is end entity;

architecture t of tb_merge_cases is
    signal clk, reset, en : logic3d := L3D_0;
    signal d : logic3d_vector(3 downto 0) := (others => L3D_0);
    signal cap, same, both, single : logic3d_vector(3 downto 0);
begin
    dut: entity work.merge_cases
        port map (clk => clk, reset => reset, en => en, d => d,
                  cap => cap, same => same, both => both, single => single);

    stim: process
        variable errors : integer := 0;
        variable cyc : integer := 0;
        -- reference values and per-bit validity masks (bit set = defined)
        variable r_cap,  m_cap  : integer := 0;
        variable r_same, m_same : integer := 0;
        variable r_both, m_both : integer := 0;
        variable r_sing, m_sing : integer := 0;
        variable cntA, cntB : integer := 0;
        variable cnt_valid : boolean := false;

        function bit_of(v : integer; i : integer) return integer is
            variable x : integer := v;
        begin
            for k in 1 to i loop x := x / 2; end loop;
            return x mod 2;
        end function;

        function b2i(v : logic3d) return integer is
        begin
            if v = L3D_1 then return 1;
            elsif v = L3D_0 then return 0;
            else return -1; end if;
        end function;

        function img(v : logic3d_vector(3 downto 0)) return string is
            variable s : string(1 to 4);
        begin
            for i in 0 to 3 loop
                if b2i(v(i)) = 1 then s(4 - i) := '1';
                elsif b2i(v(i)) = 0 then s(4 - i) := '0';
                else s(4 - i) := 'X'; end if;
            end loop;
            return s;
        end function;

        procedure check(name : string; sig : logic3d_vector(3 downto 0);
                        ref, mask : integer) is
        begin
            for i in 0 to 3 loop
                if bit_of(mask, i) = 1 and b2i(sig(i)) /= bit_of(ref, i) then
                    report "MISMATCH cycle " & integer'image(cyc) & " " & name &
                           "(" & integer'image(i) & ") = " & img(sig) &
                           " want bit " & integer'image(bit_of(ref, i))
                        severity error;
                    errors := errors + 1;
                end if;
            end loop;
        end procedure;

        -- set bits [hi:lo] of ref to the same bits of val, mark them valid
        procedure set_bits(variable ref, mask : inout integer;
                           val, lo, hi : integer) is
            variable r : integer := 0;
            variable m : integer := 0;
            variable w : integer := 1;
        begin
            for i in 0 to 3 loop
                if i >= lo and i <= hi then
                    r := r + bit_of(val, i) * w; m := m + w;
                else
                    r := r + bit_of(ref, i) * w; m := m + bit_of(mask, i) * w;
                end if;
                w := w * 2;
            end loop;
            ref := r; mask := m;
        end procedure;

        procedure tick(r, e, dval : integer) is
            variable bitrev, w : integer;
        begin
            if r = 1 then reset <= L3D_1; else reset <= L3D_0; end if;
            if e = 1 then en <= L3D_1; else en <= L3D_0; end if;
            for i in 0 to 3 loop
                if bit_of(dval, i) = 1 then d(i) <= L3D_1; else d(i) <= L3D_0; end if;
            end loop;
            wait for 1 ns;
            -- ---- posedge reference (all reads are pre-edge) ----
            if cnt_valid then
                set_bits(r_cap, m_cap, cntA * 4, 2, 3);
                set_bits(r_cap, m_cap, cntB, 0, 1);
            end if;
            if r = 1 then
                cntA := 0; cntB := 3; cnt_valid := true;
            elsif cnt_valid then
                cntA := (cntA + 1) mod 4; cntB := (cntB + 3) mod 4;
            end if;
            set_bits(r_same, m_same, dval, 1, 3);
            set_bits(r_same, m_same, 1, 0, 0);
            set_bits(r_both, m_both, dval, 2, 3);
            bitrev := 0; w := 1;
            for i in 0 to 3 loop bitrev := bitrev + bit_of(dval, 3 - i) * w; w := w * 2; end loop;
            if r = 1 then set_bits(r_sing, m_sing, 0, 0, 3);
            elsif e = 1 then set_bits(r_sing, m_sing, bitrev, 0, 3); end if;
            clk <= L3D_1; wait for 5 ns;
            cyc := cyc + 1;
            check("cap", cap, r_cap, m_cap);
            check("same", same, r_same, m_same);
            check("both", both, r_both, m_both);
            check("single", single, r_sing, m_sing);
            -- ---- negedge reference ----
            set_bits(r_both, m_both, dval, 0, 1);
            clk <= L3D_0; wait for 4 ns;
            check("both", both, r_both, m_both);
        end procedure;
    begin
        tick(1, 0, 16#0#);   -- reset
        tick(1, 0, 16#5#);   -- reset, d=0101
        tick(0, 1, 16#A#);   -- load 1010
        tick(0, 0, 16#3#);   -- hold, d=0011
        tick(0, 0, 16#C#);   -- hold
        tick(0, 1, 16#6#);   -- load 0110
        tick(0, 1, 16#9#);   -- load 1001
        tick(0, 0, 16#F#);   -- hold
        tick(1, 0, 16#F#);   -- reset with d=1111
        tick(0, 0, 16#0#);   -- hold
        tick(0, 1, 16#7#);   -- load 0111
        tick(0, 1, 16#2#);   -- load 0010
        if errors = 0 then
            report "PASS: merge_cases: distinct persistent locals, same-bit race order, opposite edges, single writer all correct";
        else
            report "FAIL: " & integer'image(errors) & " mismatches" severity failure;
        end if;
        wait;
    end process;
end architecture;
