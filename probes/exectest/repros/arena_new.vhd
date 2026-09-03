-- NVC fork: a `new` executed by JIT-compiled code was served from the
-- reset-per-evaluation eval arena (default on since the arena's default
-- flipped), so a textio `line` allocated by readline once its helpers
-- (grow/shrink) tiered up did not survive the next process evaluation.
-- Each iteration: readline into l, wait (another process evaluates, the
-- arena is reset), readline into l2 (reuses l's storage), check l.
-- 200 iterations so the readline helpers pass the 100-call tier-up threshold.
-- Expected: "PASS: 200 lines kept across waits".  Broken runtime: the
-- assertion fails (or the run dies with SIGSEGV) after ~100 iterations.
-- Workaround on an unfixed build: NVC_NO_EVAL_ARENA=1.
library ieee;
use std.textio.all;

entity arena_new is end entity;

architecture t of arena_new is
    signal clk : bit := '0';
    signal running : boolean := true;
begin
    clkgen: process begin
        while running loop
            clk <= not clk; wait for 5 ns;
        end loop;
        wait;
    end process;

    reader: process
        file f : text open read_mode is "arena_new.txt";
        variable l, l2 : line;
        variable i : integer := 0;
        variable expect : character;
    begin
        while not endfile(f) loop
            readline(f, l);
            expect := character'val(character'pos('a') + (2 * i) mod 26);
            wait until clk = '1';
            readline(f, l2);
            assert l'length = 200
                report "iteration " & integer'image(i) & ": line length " & integer'image(l'length)
                severity failure;
            for k in l'range loop
                assert l(k) = expect
                    report "iteration " & integer'image(i) & ": line corrupted at " & integer'image(k)
                         & " ('" & l(k) & "' expected '" & expect & "')"
                    severity failure;
            end loop;
            i := i + 1;
        end loop;
        report "PASS: " & integer'image(i) & " lines kept across waits";
        running <= false;
        wait;
    end process;
end architecture;
