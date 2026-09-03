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
    signal reset, ex_valid, rs_ready : logic3d := L3D_0;
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
begin
    dut: entity work.alu_top
        port map (clk => clk, reset => reset,
                  ex_valid => ex_valid, ex_ready => ex_ready, ex_data => ex_data,
                  rs_valid => rs_valid, rs_ready => rs_ready, rs_data => rs_data,
                  br_valid => br_valid, br_wid => br_wid, br_taken => br_taken, br_dest => br_dest,
                  br_is_trap => br_is_trap, br_is_mret => br_is_mret, br_trap_cause => br_trap_cause);

    clkgen: process begin
        while running loop
            clk <= L3D_1; wait for 5 ns;
            clk <= L3D_0; wait for 5 ns;
        end loop;
        wait;
    end process;

    replay: process
        file f : text open read_mode is "vectors.txt";
        variable l : line;
        variable v4 : std_logic_vector(3 downto 0);
        variable exd : std_logic_vector(275 downto 0);
        variable rsd : std_logic_vector(115 downto 0);
        variable dst : std_logic_vector(31 downto 0);
        variable e_exready, e_rsvalid, e_brvalid, e_brwid, e_brtaken, e_trap, e_mret : std_logic_vector(3 downto 0);
        variable e_rsdata : std_logic_vector(115 downto 0);
        variable e_dest : std_logic_vector(31 downto 0);
        variable e_cause : std_logic_vector(3 downto 0);
        variable cyc, bad, fires, brs : integer := 0;
    begin
        -- reset: the oracle held reset for its first 3 cycles (recorded lines
        -- include it); mirror by driving reset from the vector's cycle count.
        reset <= L3D_1;
        while not endfile(f) loop
            readline(f, l);
            -- mirror the oracle recorder: inputs applied AT the falling edge,
            -- outputs compared 1 ns later (they reflect the preceding rising edge)
            wait until clk = L3D_0;
            if cyc = 2 then reset <= L3D_0; end if;  -- oracle released reset at its 3rd negedge
            hread(l, v4);  ex_valid <= to_logic3d(v4(0));
            hread(l, exd); ex_data  <= to_l3d(unsigned(exd(EXW-1 downto 0)), EXW);
            hread(l, v4);  rs_ready <= to_logic3d(v4(0));
            hread(l, e_exready); hread(l, e_rsvalid); hread(l, e_rsdata);
            hread(l, e_brvalid); hread(l, e_brwid); hread(l, e_brtaken); hread(l, e_dest);
            hread(l, e_trap); hread(l, e_mret); hread(l, e_cause);
            wait for 1 ns;
            if cyc >= 4 then
                if not matches(to_std_logic_vector(ex_ready), e_exready(0 downto 0))
                   or not matches(to_std_logic_vector(rs_valid), e_rsvalid(0 downto 0))
                   or not matches(to_std_logic_vector(br_valid), e_brvalid(0 downto 0)) then
                    bad := bad + 1;
                    report "cycle " & integer'image(cyc) & ": handshake mismatch ex_ready/rs_valid/br_valid act="
                        & to_string(to_std_logic_vector(ex_ready)) & to_string(to_std_logic_vector(rs_valid)) & to_string(to_std_logic_vector(br_valid))
                        & " exp=" & to_string(e_exready(0)) & to_string(e_rsvalid(0)) & to_string(e_brvalid(0)) severity error;
                end if;
                if e_rsvalid(0) = '1' then
                    fires := fires + 1;
                    if not matches(to_std_logic_vector(rs_data), e_rsdata(RSW-1 downto 0)) then
                        bad := bad + 1;
                        report "cycle " & integer'image(cyc) & ": rs_data mismatch act=" & to_hstring(to_std_logic_vector(rs_data))
                            & " exp=" & to_hstring(e_rsdata(RSW-1 downto 0)) severity error;
                    end if;
                end if;
                if e_brvalid(0) = '1' then
                    brs := brs + 1;
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
                end if;
            end if;
            cyc := cyc + 1;
        end loop;
        running <= false;
        if bad = 0 then
            report "PASS: " & integer'image(cyc) & " cycles replayed, " & integer'image(fires)
                 & " results and " & integer'image(brs) & " branch resolutions identical to the vvp oracle";
        else
            report "FAIL: " & integer'image(bad) & " mismatches" severity failure;
        end if;
        wait;
    end process;
end architecture;
