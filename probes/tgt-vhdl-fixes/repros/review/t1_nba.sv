// Merge-pass NBA semantics: pre-edge reads across merged blocks, opposite
// edges of one clock, per-block enables, same-bit race.
module t1_nba;
  reg clk;
  reg [7:0] q;
  reg [2:0] i, j;
  reg en_a, en_b;

  // A and B: same edge, dynamic indices, each reads the OTHER's target bit
  // (must see the pre-edge value).
  always_ff @(posedge clk) if (en_a) q[i] <= ~q[j];
  always_ff @(posedge clk) if (en_b) q[j] <=  q[i];
  // C: negedge writer on the same reg (same sensitivity set {clk} -> merges).
  always_ff @(negedge clk) if (en_b) q[7] <= q[0];

  initial begin
    // enables low across the time-0 X->0 clk transition (a Verilog negedge)
    clk = 0; q = 8'b0000_0001; i = 0; j = 4; en_a = 0; en_b = 0;
    #1 en_a = 1; en_b = 1;
    #4 clk = 1; #5 clk = 0; #1;
    // posedge: q[0] <= ~q[4] = 1 ; q[4] <= q[0] = 1 ; negedge: q[7] <= q[0] = 1
    $display("T1a q=%b exp=10010001", q);
    en_a = 0; i = 1; j = 4;
    #4 clk = 1; #5 clk = 0; #1;
    // posedge: only B: q[4] <= q[1] = 0 ; negedge: q[7] <= q[0] = 1
    $display("T1b q=%b exp=10000001", q);
    en_a = 1; en_b = 0; i = 2; j = 0;
    #4 clk = 1; #5 clk = 0; #1;
    // posedge: only A: q[2] <= ~q[0] = 0 ; negedge: off
    $display("T1c q=%b exp=10000001", q);
    en_b = 1; i = 3; j = 3;
    #4 clk = 1; #5 clk = 0; #1;
    // posedge: A writes q[3] <= ~q[3] = 1, B writes q[3] <= q[3] = 0 -> race
    // negedge: q[7] <= q[0] = 1
    $display("T1d q=%b (bit3 is a race: 0 if the later block wins)", q);
    $finish;
  end
endmodule
