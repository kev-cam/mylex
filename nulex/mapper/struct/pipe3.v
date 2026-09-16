module pipe3(input clk, input [3:0] d, output [3:0] q);
  reg [3:0] r0, r1, r2;
  always @(posedge clk) begin r0 <= d; r1 <= r0; r2 <= r1; end
  assign q = r2;
endmodule
