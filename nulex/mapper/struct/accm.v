module accm(input clk, input [3:0] din, output [3:0] q);
  reg [3:0] r;
  always @(posedge clk) r <= r + din;
  assign q = r;
endmodule
