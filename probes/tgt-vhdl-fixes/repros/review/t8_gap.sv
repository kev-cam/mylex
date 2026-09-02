// (1) Two always_ff blocks with a blocking temp read later in the block
//     (drawn as `wait until rising_edge`): both write dynamic indices of one
//     reg -- outside the merge pass; does anything warn, and is data lost?
// (2) Two blocks with different sensitivity sets on one reg (expected warning).
module t8_gap;
  reg clk, clk2;
  reg [3:0] q, r;
  reg [1:0] i, j;
  reg [3:0] d;
  reg [3:0] t;

  always_ff @(posedge clk) begin
    t = d & 4'hC;
    q[i] <= t[i];
  end
  always_ff @(posedge clk) begin
    t = d & 4'h3;
    q[j] <= t[j];
  end
  always_ff @(posedge clk)  r[i] <= d[i];
  always_ff @(posedge clk2) r[j] <= d[j];

  initial begin
    clk = 0; clk2 = 0; q = 4'b0000; r = 4'b0000; d = 4'b1111; i = 2; j = 0;
    #5 clk = 1; #5 clk = 0;
    // q[2] <= (d&C)[2] = 1 ; q[0] <= (d&3)[0] = 1
    $display("T8a q=%b exp=0101", q);
    i = 3; j = 1;
    #5 clk = 1; #5 clk = 0;
    $display("T8b q=%b exp=1111", q);
    $finish;
  end
endmodule
