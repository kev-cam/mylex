-- Variant of arena_new.vhd shaped like the exec replay bench: one readline,
-- then one textio read per character (each `read` re-allocates the line via
-- consume's `new`) interleaved with a signal assignment whose value is an
-- escaping unconstrained result, with a combinational process on the other
-- side of the signal.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;

entity arena_line is end entity;

architecture t of arena_line is
    signal clk : std_logic := '0';
    signal s, y : std_logic_vector(31 downto 0) := (others => '0');
    signal running : boolean := true;
    function slv(c : character) return std_logic_vector is
        variable r : std_logic_vector(31 downto 0) := (others => '0');
    begin
        r(7 downto 0) := std_logic_vector(to_unsigned(character'pos(c), 8));
        return r;
    end function;
    function inv(v : std_logic_vector) return std_logic_vector is
        variable r : std_logic_vector(v'range);
    begin
        for i in v'range loop r(i) := not v(i); end loop;
        return r;
    end function;
begin
    clkgen: process begin
        while running loop
            clk <= not clk; wait for 5 ns;
        end loop;
        wait;
    end process;

    comb: process (s) begin
        y <= inv(s);
    end process;

    reader: process
        file f : text open read_mode is "arena_new.txt";
        variable l : line;
        variable c : character;
        variable ok : boolean;
        variable i : integer := 0;
        variable expect : character;
    begin
        while not endfile(f) loop
            wait until clk = '0';
            readline(f, l);
            expect := character'val(character'pos('a') + i mod 26);
            for k in 1 to 200 loop
                read(l, c, ok);
                assert ok and c = expect
                    report "line " & integer'image(i) & " char " & integer'image(k) & ": got '" & c & "' expected '" & expect & "'"
                    severity failure;
                s <= slv(c);
            end loop;
            wait for 1 ns;
            assert y = inv(slv(expect)) report "y mismatch at line " & integer'image(i) severity failure;
            i := i + 1;
        end loop;
        report "PASS: " & integer'image(i) & " lines read character by character";
        running <= false;
        wait;
    end process;
end architecture;
