// Oracle bench for prehist.v with the exectest alignment (tb_exec.sv.in): clk = 0 at t0,
// first rising edge at 5 ns, reset = 1 from t0 released at the third falling edge, inputs
// change only at falling edges, recorder samples 1 ns after each falling edge. Vector layout:
// inputs as %h then outputs as %b, in ports.txt order (clk excluded).
`timescale 1ns/1ns
module tb_prehist;
    reg clk = 0;
    always #5 clk = ~clk;
    reg reset = 1;
    reg [7:0] a = 8'h10;
    wire ready; wire [7:0] cnt, q, junk;
    prehist_top dut(.clk(clk), .reset(reset), .a(a), .ready(ready), .cnt(cnt), .q(q), .junk(junk));
    integer fd, cyc = 0;
    initial fd = $fopen("vectors.txt", "w");
    always @(negedge clk) begin
        #1;
        $fwrite(fd, "%h %h %b %b %b %b\n", reset, a, ready, cnt, q, junk);
        cyc = cyc + 1;
    end
    initial begin repeat (3) @(negedge clk); reset = 0; end
    always @(negedge clk) if (cyc >= 3) a <= a + 8'd3;
    initial begin repeat (12) @(negedge clk); #2 $fclose(fd); $finish; end
endmodule
