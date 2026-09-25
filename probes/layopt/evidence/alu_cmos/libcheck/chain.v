module chain(n0, hi, lo, n4);
  input n0, hi, lo; output n4;
  wire n1, n2, n3;
  sg13g2_inv_1   u1 (.Y(n1), .A(n0));
  sg13g2_nand2_1 u2 (.Y(n2), .A(n1), .B(hi));
  sg13g2_nor2_1  u3 (.Y(n3), .A(n2), .B(lo));
  sg13g2_inv_1   u4 (.Y(n4), .A(n3));
endmodule
