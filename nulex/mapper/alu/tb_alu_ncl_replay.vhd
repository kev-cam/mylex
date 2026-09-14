-- tb_alu_ncl_replay — replay the committed vvp-oracle vectors.txt through the
-- MAPPED dual-rail NCL alu_top (combinational cones = QDI dual-rail, registers
-- = sync-emulation ncl_dff) and compare outputs to the oracle, X = don't-care.
-- Timing/pre-history mirror tb_alu_replay.vhd exactly: clk posedge at 5+10k ns,
-- inputs applied at the falling edge, outputs sampled 1 ns later, reset released
-- at the 3rd negedge (cyc=2). Inputs are ncl_encode'd; outputs ncl_decode'd.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;
library ncl;
use ncl.ncl.all;

entity tb_alu_ncl_replay is end entity;

architecture t of tb_alu_ncl_replay is
    constant EXW : integer := 274;
    constant RSW : integer := 115;
    signal clk : std_logic := '0';
    signal reset : ncl_logic := NCL_DATA1;
    signal ex_valid, rs_ready : ncl_logic := NCL_DATA0;
    signal ex_ready, rs_valid, br_valid, br_taken, br_is_trap, br_is_mret : ncl_logic;
    signal ex_data : ncl_logic_vector(EXW-1 downto 0) := (others => NCL_DATA0);
    signal rs_data : ncl_logic_vector(RSW-1 downto 0);
    signal br_wid : ncl_logic;
    signal br_dest : ncl_logic_vector(29 downto 0);
    signal br_trap_cause : ncl_logic_vector(3 downto 0);
    signal running : boolean := true;

    function matches(act, exp : std_logic_vector) return boolean is
        alias a : std_logic_vector(act'length-1 downto 0) is act;
        alias e : std_logic_vector(exp'length-1 downto 0) is exp;
    begin
        for i in a'range loop
            if e(i) /= 'X' and e(i) /= 'U' and a(i) /= e(i) then return false; end if;
        end loop;
        return true;
    end function;

    -- scalar ncl_logic -> 1-bit decoded std_logic_vector
    function sc(x : ncl_logic) return std_logic_vector is
    begin return (0 => ncl_decode(x)); end function;

    procedure rdhex(l : inout line; v : out std_logic_vector) is
        alias a : std_logic_vector(v'length-1 downto 0) is v;
        variable c : character; variable ok : boolean;
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

    -- ncl_encode a std_logic_vector input (defined bits only in this stimulus)
    function enc(s : std_logic_vector) return ncl_logic_vector is
    begin return ncl_encode(s); end function;
begin
    dut: entity work.alu_top_ncl
        port map (clk => clk, reset => reset,
                  ex_valid => ex_valid, ex_ready => ex_ready, ex_data => ex_data,
                  rs_valid => rs_valid, rs_ready => rs_ready, rs_data => rs_data,
                  br_valid => br_valid, br_wid => br_wid, br_taken => br_taken, br_dest => br_dest,
                  br_is_trap => br_is_trap, br_is_mret => br_is_mret, br_trap_cause => br_trap_cause);

    clkgen: process begin
        wait for 5 ns;
        while running loop
            clk <= '1'; wait for 5 ns;
            clk <= '0'; wait for 5 ns;
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
        readline(f, l);
        l0 := new string'(l.all);
        rdhex(l0, v4);  ex_valid <= ncl_encode(v4(0));
        rdhex(l0, exd); ex_data  <= enc(exd(EXW-1 downto 0));
        rdhex(l0, v4);  rs_ready <= ncl_encode(v4(0));
        deallocate(l0);
        first := true;
        while first or not endfile(f) loop
            if not first then readline(f, l); end if;
            first := false;
            wait until clk = '0';
            if cyc = 2 then reset <= NCL_DATA0; end if;
            rdhex(l, v4);  ex_valid <= ncl_encode(v4(0));
            rdhex(l, exd); ex_data  <= enc(exd(EXW-1 downto 0));
            rdhex(l, v4);  rs_ready <= ncl_encode(v4(0));
            rdhex(l, e_exready); rdhex(l, e_rsvalid); rdhex(l, e_rsdata);
            rdhex(l, e_brvalid); rdhex(l, e_brwid); rdhex(l, e_brtaken); rdhex(l, e_dest);
            rdhex(l, e_trap); rdhex(l, e_mret); rdhex(l, e_cause);
            wait for 1 ns;
            if not matches(sc(ex_ready), e_exready(0 downto 0))
               or not matches(sc(rs_valid), e_rsvalid(0 downto 0))
               or not matches(sc(br_valid), e_brvalid(0 downto 0)) then
                bad := bad + 1;
                report "cycle " & integer'image(cyc) & ": handshake mismatch act="
                    & to_string(ncl_decode(ex_ready)) & to_string(ncl_decode(rs_valid)) & to_string(ncl_decode(br_valid))
                    & " exp=" & to_string(e_exready(0)) & to_string(e_rsvalid(0)) & to_string(e_brvalid(0)) severity error;
            end if;
            if not matches(ncl_decode(rs_data), e_rsdata(RSW-1 downto 0)) then
                bad := bad + 1;
                report "cycle " & integer'image(cyc) & ": rs_data mismatch act=" & to_hstring(ncl_decode(rs_data))
                    & " exp=" & to_hstring(e_rsdata(RSW-1 downto 0)) severity error;
            end if;
            if rs_valid = NCL_DATA1 then fires := fires + 1; end if;
            if not matches(sc(br_taken), e_brtaken(0 downto 0))
               or not matches(ncl_decode(br_dest), e_dest(29 downto 0))
               or not matches(sc(br_wid), e_brwid(0 downto 0))
               or not matches(sc(br_is_trap), e_trap(0 downto 0))
               or not matches(sc(br_is_mret), e_mret(0 downto 0))
               or not matches(ncl_decode(br_trap_cause), e_cause) then
                bad := bad + 1;
                report "cycle " & integer'image(cyc) & ": branch mismatch taken/dest act="
                    & to_string(ncl_decode(br_taken)) & "/" & to_hstring(ncl_decode(br_dest))
                    & " exp=" & to_string(e_brtaken(0)) & "/" & to_hstring(e_dest(29 downto 0)) severity error;
            end if;
            if br_valid = NCL_DATA1 then brs := brs + 1; end if;
            cyc := cyc + 1;
        end loop;
        running <= false;
        if bad = 0 then
            report "ALU-NCL PASS: " & integer'image(cyc) & " cycles replayed vs the vvp oracle, "
                 & integer'image(fires) & " results and " & integer'image(brs) & " branches identical";
        else
            report "ALU-NCL FAIL: " & integer'image(bad) & " mismatches" severity failure;
        end if;
        wait;
    end process;
end architecture;
