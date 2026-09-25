module t0(A, o);
  input A; output o;
  sg13g2_inv_1 u0 (.Y(o), .A(A));
endmodule
module t1(A, o);
  input A; output o;
  sg13g2_buf_1 u0 (.X(o), .A(A));
endmodule
module t2(A, o);
  input A; output o;
  sg13g2_buf_8 u0 (.X(o), .A(A));
endmodule
module t3(A, o);
  input A; output o;
  sg13g2_buf_16 u0 (.X(o), .A(A));
endmodule
module t4(A, B, o);
  input A, B; output o;
  sg13g2_nand2_1 u0 (.Y(o), .A(A), .B(B));
endmodule
module t5(A, B, o);
  input A, B; output o;
  sg13g2_nor2_1 u0 (.Y(o), .A(A), .B(B));
endmodule
module t6(A1, A2, B1, o);
  input A1, A2, B1; output o;
  sg13g2_o21ai_1 u0 (.Y(o), .A1(A1), .A2(A2), .B1(B1));
endmodule
module t7(A1, A2, B1, o);
  input A1, A2, B1; output o;
  sg13g2_a21oi_1 u0 (.Y(o), .A1(A1), .A2(A2), .B1(B1));
endmodule
module t8(A0, A1, S, o);
  input A0, A1, S; output o;
  sg13g2_mux2_1 u0 (.X(o), .A0(A0), .A1(A1), .S(S));
endmodule
module t9(S, A0, A1, o);
  input S, A0, A1; output o;
  sg13g2_mux2_1 u0 (.X(o), .S(S), .A0(A0), .A1(A1));
endmodule
