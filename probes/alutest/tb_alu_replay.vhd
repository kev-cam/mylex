-- NVC replay bench for alu_top (VX_alu_int): re-applies every cycle's
-- recorded inputs from vectors.txt (written by the vvp oracle tb_alu.sv) at
-- the falling clock edge and compares the outputs 1 ns later, from cycle 0.
-- Pre-history matches the oracle exactly: reset starts asserted and is
-- released at the falling edge of cycle 2 (the oracle's 3rd negedge), row 0's
-- inputs are driven from time 0 (the oracle's initial values), the first
-- rising edge is at 5 ns and row k is sampled by the edge at 5 + 10k ns.
-- Hex tokens are read with rdhex, which accepts the x/X/z/Z nibbles vvp's %h
-- prints (IEEE HREAD rejects them and leaves the line pointer mid-token);
-- an 'X' expected nibble is a don't-care.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;
library sv2vhdl;
use sv2vhdl.logic3d_types_pkg.all;

entity tb_alu_replay is end entity;

architecture t of tb_alu_replay is
    constant EXW : integer := 274;
    constant RSW : integer := 115;
    signal clk : logic3d := L3D_0;
    signal reset : logic3d := L3D_1;
    signal ex_valid, rs_ready : logic3d := L3D_0;
    signal ex_ready, rs_valid, br_valid, br_taken, br_is_trap, br_is_mret : logic3d;
    signal ex_data : logic3d_vector(EXW-1 downto 0) := (others => L3D_0);
    signal rs_data : logic3d_vector(RSW-1 downto 0);
    signal br_wid : logic3d;
    signal br_dest : logic3d_vector(29 downto 0);
    signal br_trap_cause : logic3d_vector(3 downto 0);
    signal running : boolean := true;

    -- expected bit 'X' (vvp printed x) is a don't-care
    function matches(act, exp : std_logic_vector) return boolean is
        alias a : std_logic_vector(act'length-1 downto 0) is act;
        alias e : std_logic_vector(exp'length-1 downto 0) is exp;
    begin
        for i in a'range loop
            if e(i) /= 'X' and e(i) /= 'U' and a(i) /= e(i) then return false; end if;
        end loop;
        return true;
    end function;

    -- lossless std_logic_vector -> logic3d_vector (keeps X/Z)
    function slv2l3d(s : std_logic_vector) return logic3d_vector is
        alias a : std_logic_vector(s'length-1 downto 0) is s;
        variable r : logic3d_vector(s'length-1 downto 0);
    begin
        for i in a'range loop r(i) := to_logic3d(a(i)); end loop;
        return r;
    end function;

    -- read one nibble-padded hex token as vvp's %h prints it (0-9 a-f A-F,
    -- x/X for an all- or part-unknown nibble, z/Z); v'length/4 characters
    -- are consumed after skipping blanks.
    procedure rdhex(l : inout line; v : out std_logic_vector) is
        alias a : std_logic_vector(v'length-1 downto 0) is v;
        variable c : character;
        variable ok : boolean;
        variable nib : std_logic_vector(3 downto 0);
    begin
        loop
            read(l, c, ok);
            assert ok report "vectors.txt: short line" severity failure;
            exit when c /= ' ' and c /= HT;
        end loop;
        for i in v'length/4 - 1 downto 0 loop
            case c is
                when '0' => nib := x"0"; when '1' => nib := x"1"; when '2' => nib := x"2"; when '3' => nib := x"3";
                when '4' => nib := x"4"; when '5' => nib := x"5"; when '6' => nib := x"6"; when '7' => nib := x"7";
                when '8' => nib := x"8"; when '9' => nib := x"9";
                when 'a' | 'A' => nib := x"A"; when 'b' | 'B' => nib := x"B"; when 'c' | 'C' => nib := x"C";
                when 'd' | 'D' => nib := x"D"; when 'e' | 'E' => nib := x"E"; when 'f' | 'F' => nib := x"F";
                when 'x' | 'X' => nib := "XXXX";
                when 'z' | 'Z' => nib := "ZZZZ";
                when others => assert false report "vectors.txt: bad hex char '" & c & "'" severity failure;
            end case;
            a(i*4+3 downto i*4) := nib;
            if i > 0 then
                read(l, c, ok);
                assert ok report "vectors.txt: short token" severity failure;
            end if;
        end loop;
    end procedure;
begin
    dut: entity work.alu_top
        port map (clk => clk, reset => reset,
                  ex_valid => ex_valid, ex_ready => ex_ready, ex_data => ex_data,
                  rs_valid => rs_valid, rs_ready => rs_ready, rs_data => rs_data,
                  br_valid => br_valid, br_wid => br_wid, br_taken => br_taken, br_dest => br_dest,
                  br_is_trap => br_is_trap, br_is_mret => br_is_mret, br_trap_cause => br_trap_cause);

    -- same phase as the oracle's `reg clk = 0; always #5 clk = ~clk`
    clkgen: process begin
        wait for 5 ns;
        while running loop
            clk <= L3D_1; wait for 5 ns;
            clk <= L3D_0; wait for 5 ns;
        end loop;
        wait;
    end process;

    replay: process
        file f : text open read_mode is "vectors.txt";
        variable l, l0 : line;
        variable first : boolean;
        variable v4 : std_logic_vector(3 downto 0);
        variable exd : std_logic_vector(275 downto 0);
        variable e_exready, e_rsvalid, e_brvalid, e_brwid, e_brtaken, e_trap, e_mret : std_logic_vector(3 downto 0);
        variable e_rsdata : std_logic_vector(115 downto 0);
        variable e_dest : std_logic_vector(31 downto 0);
        variable e_cause : std_logic_vector(3 downto 0);
        variable cyc, bad, fires, brs : integer := 0;
    begin
        -- pre-history: row 0's inputs are the oracle's initial values, seen by
        -- its first rising edge (5 ns) under reset
        readline(f, l);
        l0 := new string'(l.all);
        rdhex(l0, v4);  ex_valid <= to_logic3d(v4(0));
        rdhex(l0, exd); ex_data  <= slv2l3d(exd(EXW-1 downto 0));
        rdhex(l0, v4);  rs_ready <= to_logic3d(v4(0));
        deallocate(l0);
        first := true;
        while first or not endfile(f) loop
            if not first then readline(f, l); end if;
            first := false;
            -- mirror the oracle recorder: inputs applied AT the falling edge,
            -- outputs compared 1 ns later (they reflect the preceding rising edge)
            wait until clk = L3D_0;
            if cyc = 2 then reset <= L3D_0; end if;  -- oracle released reset at its 3rd negedge
            rdhex(l, v4);  ex_valid <= to_logic3d(v4(0));
            rdhex(l, exd); ex_data  <= slv2l3d(exd(EXW-1 downto 0));
            rdhex(l, v4);  rs_ready <= to_logic3d(v4(0));
            rdhex(l, e_exready); rdhex(l, e_rsvalid); rdhex(l, e_rsdata);
            rdhex(l, e_brvalid); rdhex(l, e_brwid); rdhex(l, e_brtaken); rdhex(l, e_dest);
            rdhex(l, e_trap); rdhex(l, e_mret); rdhex(l, e_cause);
            wait for 1 ns;
            if not matches(to_std_logic_vector(ex_ready), e_exready(0 downto 0))
               or not matches(to_std_logic_vector(rs_valid), e_rsvalid(0 downto 0))
               or not matches(to_std_logic_vector(br_valid), e_brvalid(0 downto 0)) then
                bad := bad + 1;
                report "cycle " & integer'image(cyc) & ": handshake mismatch ex_ready/rs_valid/br_valid act="
                    & to_string(to_std_logic_vector(ex_ready)) & to_string(to_std_logic_vector(rs_valid)) & to_string(to_std_logic_vector(br_valid))
                    & " exp=" & to_string(e_exready(0)) & to_string(e_rsvalid(0)) & to_string(e_brvalid(0)) severity error;
            end if;
            if reset = L3D_0 then
                -- the handshake expectations must be defined once reset is
                -- released, or the X-as-don't-care compare would be vacuous
                assert (e_exready(0) = '0' or e_exready(0) = '1') and (e_rsvalid(0) = '0' or e_rsvalid(0) = '1')
                       and (e_brvalid(0) = '0' or e_brvalid(0) = '1')
                    report "cycle " & integer'image(cyc) & ": undefined handshake expectation after reset" severity failure;
            end if;
            if not matches(to_std_logic_vector(rs_data), e_rsdata(RSW-1 downto 0)) then
                bad := bad + 1;
                report "cycle " & integer'image(cyc) & ": rs_data mismatch act=" & to_hstring(to_std_logic_vector(rs_data))
                    & " exp=" & to_hstring(e_rsdata(RSW-1 downto 0)) severity error;
            end if;
            if rs_valid = L3D_1 then fires := fires + 1; end if;   -- result-valid cycles (incl. stalls), as before
            if not matches(to_std_logic_vector(br_taken), e_brtaken(0 downto 0))
               or not matches(to_std_logic_vector(br_dest), e_dest(29 downto 0))
               or not matches(to_std_logic_vector(br_wid), e_brwid(0 downto 0))
               or not matches(to_std_logic_vector(br_is_trap), e_trap(0 downto 0))
               or not matches(to_std_logic_vector(br_is_mret), e_mret(0 downto 0))
               or not matches(to_std_logic_vector(br_trap_cause), e_cause) then
                bad := bad + 1;
                report "cycle " & integer'image(cyc) & ": branch mismatch taken/dest act="
                    & to_string(to_std_logic_vector(br_taken)) & "/" & to_hstring(to_std_logic_vector(br_dest))
                    & " exp=" & to_string(e_brtaken(0)) & "/" & to_hstring(e_dest(29 downto 0)) severity error;
            end if;
            if br_valid = L3D_1 then brs := brs + 1; end if;
            cyc := cyc + 1;
        end loop;
        running <= false;
        if bad = 0 then
            report "PASS: " & integer'image(cyc) & " cycles replayed and compared from cycle 0, "
                 & integer'image(fires) & " results and " & integer'image(brs)
                 & " branch resolutions identical to the vvp oracle";
        else
            report "FAIL: " & integer'image(bad) & " mismatches" severity failure;
        end if;
        wait;
    end process;
end architecture;
