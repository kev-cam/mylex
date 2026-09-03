// Two-level derived defaults: B defaults to A, C defaults to B.
// Actuals A=2 B=1 C=1: correct q = d + (2<<6) + (1<<4) + (1<<2) = d + 0x94.
// A stale-default keep of B and C (both equal their pre-chparam default 1)
// leaves the derived module with B = A = 2 and C = B = 2: d + 0xa8.
module chain #(parameter A = 1, parameter B = A, parameter C = B)
             (input clk, input [7:0] d, output reg [7:0] q);
  always @(posedge clk) q <= d + (A << 6) + (B << 4) + (C << 2);
endmodule
