module pinc(input clk, input [3:0] d, output [3:0] q);
  reg [3:0] r0, r1;
  always @(posedge clk) begin r0 <= d; r1 <= r0 + 4'd1; end   // comb (+1) BETWEEN stages
  assign q = r1;
endmodule
