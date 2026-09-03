// tgt-vhdl (-psv2vhdl=1): the fused combinational cones of an architecture
// (comb_fused_N) were emitted in the iteration order of a std::map keyed by
// member pointer, so their numbering and order changed with the heap layout
// -- the length of argv (an absolute vs a relative path) was enough to
// permute them.  Equivalent VHDL, but not byte-reproducible.
// Fixed: components are visited in order of first appearance (process.cc).
// Check: translate with different argv/env lengths and compare after path
// normalisation (run_fusedorder.sh).
module fusedorder(input clk, input [7:0] a, input [7:0] b,
                  output reg [7:0] q0, q1, q2, q3, q4, q5, q6, q7,
                  output [7:0] y0, y1, y2, y3, y4, y5, y6, y7);
  always @(posedge clk) begin
    q0 <= a; q1 <= a + b; q2 <= a ^ b; q3 <= a & b;
    q4 <= a | b; q5 <= a - b; q6 <= ~a; q7 <= b;
  end
  // eight independent two-member cones, each fed by one registered signal
  wire [7:0] t0 = q0 + 8'd1;   assign y0 = t0 ^ q0;
  wire [7:0] t1 = q1 - 8'd1;   assign y1 = t1 & q1;
  wire [7:0] t2 = ~q2;         assign y2 = t2 | q2;
  wire [7:0] t3 = q3 << 1;     assign y3 = t3 + q3;
  wire [7:0] t4 = q4 >> 1;     assign y4 = t4 - q4;
  wire [7:0] t5 = q5 ^ 8'h55;  assign y5 = t5 ^ q5;
  wire [7:0] t6 = q6 + 8'd3;   assign y6 = t6 & q6;
  wire [7:0] t7 = q7 * 8'd3;   assign y7 = t7 | q7;
endmodule
