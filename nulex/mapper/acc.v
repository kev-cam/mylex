// sequential: 4-bit accumulator with sync reset
module acc(input clk, input rst, input [3:0] din, output [3:0] q);
  reg [3:0] r;
  always @(posedge clk) if (rst) r <= 4'd0; else r <= r + din;
  assign q = r;
endmodule
