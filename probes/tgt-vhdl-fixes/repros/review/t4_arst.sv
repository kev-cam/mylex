// Async-reset template pair merged (same sensitivity set {clk, rst_n}):
// asynchronous reset asserted with no clock edge, whole-signal reset in one
// block and a static bit in the other, dynamic index on the data path.
module t4_arst;
  reg clk, rst_n;
  reg [3:0] q, d;
  reg [1:0] i;

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) q <= 4'b0000; else q[i] <= d[i];
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) q[3] <= 1'b0; else q[3] <= ~q[3];

  initial begin
    clk = 0; rst_n = 0; d = 4'b0111; i = 0;
    #5 rst_n = 1;
    #5 clk = 1; #5 clk = 0;      // q[0] <= 1 ; q[3] <= ~0 = 1
    $display("T4a q=%b exp=1001", q);
    i = 1;
    #5 clk = 1; #5 clk = 0;      // q[1] <= 1 ; q[3] <= 0
    $display("T4b q=%b exp=0011", q);
    #2 rst_n = 0;                // async reset, no clock edge
    #1 $display("T4c q=%b exp=0000 (async)", q);
    #2 rst_n = 1; i = 2;
    #5 clk = 1; #5 clk = 0;      // q[2] <= 1 ; q[3] <= 1
    $display("T4d q=%b exp=1100", q);
    $finish;
  end
endmodule
