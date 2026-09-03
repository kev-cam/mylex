// Parser / width edge cases for the "keep when equal to default" test.
// oct:  chparam (SigSpec::parse -> const2ast) reads 010 as decimal 10;
//       strtoll(v, &end, 0) reads it as octal 8 == default -> false keep.
module oct #(parameter W = 8) (input clk, input [15:0] d, output reg [15:0] q);
  always @(posedge clk) q <= d & ((16'd1 << W) - 1);
endmodule
// wide: a 32-bit-default parameter overridden with a value that does not fit;
//       Const(4294967296, 32) == 0 == default -> false keep (BASE stays 0).
module wide #(parameter BASE = 0) (input clk, input [63:0] d, output reg [63:0] q);
  always @(posedge clk) q <= d + BASE;
endmodule
// neg: a signed negative default; nvc prints the actual through
//      ivl_expr_uvalue, so -1 arrives as 18446744073709551615.
module neg #(parameter signed [31:0] K = -1) (input clk, input [31:0] d, output reg [31:0] q);
  always @(posedge clk) q <= d + K;
endmodule
