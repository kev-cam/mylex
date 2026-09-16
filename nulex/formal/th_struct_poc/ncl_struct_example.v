// One DIMS AND2 (dual-rail, .L = value-1): 4 TH22 minterms + rail collectors.
module ncl_and2(input a_L, input a_H, input b_L, input b_H, output z_L, output z_H);
  wire m11, m10, m01, m00;
  th22 u11(.a(a_L), .b(b_L), .y(m11));
  th22 u10(.a(a_L), .b(b_H), .y(m10));
  th22 u01(.a(a_H), .b(b_L), .y(m01));
  th22 u00(.a(a_H), .b(b_H), .y(m00));
  assign z_L = m11;                              // z is value-1 only when both value-1
  th13 zc(.a(m10), .b(m01), .c(m00), .y(z_H));   // z is value-0 for the other three minterms
endmodule

// Top: one dual-rail input `a` fans out to THREE AND2 gates -> a_L and a_H each
// FORK (the QDI-critical dual-rail isochronic fork we want to enumerate+balance).
module fork_top(input a_L, input a_H,
                input b0_L, input b0_H, input b1_L, input b1_H, input b2_L, input b2_H,
                output z0_L, output z0_H, output z1_L, output z1_H, output z2_L, output z2_H);
  ncl_and2 g0(.a_L(a_L), .a_H(a_H), .b_L(b0_L), .b_H(b0_H), .z_L(z0_L), .z_H(z0_H));
  ncl_and2 g1(.a_L(a_L), .a_H(a_H), .b_L(b1_L), .b_H(b1_H), .z_L(z1_L), .z_H(z1_H));
  ncl_and2 g2(.a_L(a_L), .a_H(a_H), .b_L(b2_L), .b_H(b2_H), .z_L(z2_L), .z_H(z2_H));
endmodule
