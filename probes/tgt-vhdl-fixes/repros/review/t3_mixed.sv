// Cross-block mixing of blocking and nonblocking writes to one reg.
// Block A uses NBA semantics (z must read the PRE-edge q); block B writes q
// with a blocking assignment (a race with A's read only when clr is set).
// With clr = 0 the only legal outcome is z = old q.
module t3_mixed;
  reg clk, clr;
  reg [3:0] q, z, d;

  always_ff @(posedge clk) begin q <= d; z <= q; end
  always_ff @(posedge clk) if (clr) q = 4'd0;

  initial begin
    clk = 0; clr = 0; q = 4'd5; d = 4'd9; z = 4'd0;
    #5 clk = 1; #5 clk = 0;
    $display("T3a q=%0d z=%0d exp q=9 z=5", q, z);
    d = 4'd3;
    #5 clk = 1; #5 clk = 0;
    $display("T3b q=%0d z=%0d exp q=3 z=9", q, z);
    $finish;
  end
endmodule
