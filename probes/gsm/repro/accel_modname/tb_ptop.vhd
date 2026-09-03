-- Self-checking bench for the --accel module-name / params repro.  Same
-- protocol as the Vortex replay benches: reset asserted from t0, inputs
-- change at the falling edge (10+10k ns), outputs compared 1 ns later
-- against a VHDL reference model of the two VX_preg stages.  Results must
-- be identical with and without --accel; what --accel must add is an
-- "accel-jit: ACTIVE" install of the ptop subtree.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.logic3d_types_pkg.all;

entity tb_ptop is end entity;

architecture t of tb_ptop is
    signal clk     : logic3d := L3D_0;
    signal reset   : logic3d := L3D_1;
    signal en      : logic3d := L3D_0;
    signal d       : logic3d_vector(11 downto 0) := (others => L3D_0);
    signal q       : logic3d_vector(11 downto 0);
    signal v       : logic3d;
    signal c       : logic3d_vector(3 downto 0);
    signal running : boolean := true;

    -- reference model state (after the last rising edge)
    signal mlo : std_logic_vector(7 downto 0) := (others => 'U');
    signal mhi : std_logic_vector(3 downto 0) := (others => 'U');
    signal mr  : std_logic_vector(11 downto 0) := (others => 'U');

    function slv2l3d(s : std_logic_vector) return logic3d_vector is
        alias a : std_logic_vector(s'length-1 downto 0) is s;
        variable r : logic3d_vector(s'length-1 downto 0);
    begin
        for i in a'range loop r(i) := to_logic3d(a(i)); end loop;
        return r;
    end function;
begin
    dut: entity work.ptop
        port map (clk => clk, reset => reset, en => en, d => d, q => q,
                  v => v, c => c);

    -- same phase as `reg clk = 0; always #5 clk = ~clk`
    clkgen: process begin
        wait for 5 ns;
        while running loop
            clk <= L3D_1; wait for 5 ns;
            clk <= L3D_0; wait for 5 ns;
        end loop;
        wait;
    end process;

    model: process (clk) is
    begin
        if clk'event and clk = L3D_1 then
            if reset = L3D_1 then
                mlo <= x"00";
                mhi <= x"1";
                mr  <= x"000";
            elsif en = L3D_1 then
                mlo <= to_std_logic_vector(d(7 downto 0));
                mhi <= to_std_logic_vector(d(11 downto 8));
                mr  <= to_std_logic_vector(d);
            end if;
        end if;
    end process;

    stim: process
        variable cyc, bad : integer := 0;
        variable act, exp : std_logic_vector(11 downto 0);
        variable actv, expv : std_logic_vector(4 downto 0);
    begin
        for k in 0 to 23 loop
            wait until clk'event and clk = L3D_0;      -- falling edge 10+10k ns
            if k < 2 then
                reset <= L3D_1; en <= L3D_0; d <= (others => L3D_0);
            elsif k < 20 then
                reset <= L3D_0;
                if k mod 3 = 2 then en <= L3D_0; else en <= L3D_1; end if;
                d <= slv2l3d(std_logic_vector(to_unsigned((k * 293) mod 4096, 12)));
            else
                reset <= L3D_0; en <= L3D_0; d <= (others => L3D_1);
            end if;
            wait for 1 ns;
            act := to_std_logic_vector(q);
            exp := mhi & mlo;
            if act /= exp then
                bad := bad + 1;
                report "cycle " & integer'image(k) & ": q=" & to_hstring(act)
                    & " expected " & to_hstring(exp) severity error;
            end if;
            actv := to_std_logic_vector(v) & to_std_logic_vector(c);
            expv := mr(11) & mr(10 downto 7);
            if actv /= expv then
                bad := bad + 1;
                report "cycle " & integer'image(k) & ": v&c=" & to_string(actv)
                    & " expected " & to_string(expv) severity error;
            end if;
            cyc := cyc + 1;
        end loop;
        if bad = 0 then
            report "PASS: " & integer'image(cyc)
                & " cycles, ptop outputs identical to the reference model";
        else
            report "FAIL: " & integer'image(bad) & " of " & integer'image(cyc)
                & " cycles mismatch" severity failure;
        end if;
        running <= false;
        wait;
    end process;
end architecture;
