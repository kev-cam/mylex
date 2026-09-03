// Runtime bit-select whose index is a SIGNED narrow value: x[i] with a
// 4-bit signed i = -1 reads x in Verilog (index -1 is out of range), not
// x[15]. The LPM part-select base has no ivl_expr_t, so the translator has
// to derive the signedness from the base nexus (signal / LPM output /
// constant) when it builds the l3d_index(...) call; a 1-bit index (x[sel])
// and an unsigned index take the ordinary path.
module top(input signed [3:0] i, input sel, input [3:0] u, input [15:0] x,
           output y, output w, output v);
  assign y = x[i];        // signed index: -1 and -8 are out of range
  assign w = x[sel];      // 1-bit index
  assign v = x[u];        // unsigned index: 8..15 are in range
endmodule
