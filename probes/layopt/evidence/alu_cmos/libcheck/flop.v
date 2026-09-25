module tf(clk, d, rb, q);
  input clk, d, rb; output q;
  sg13g2_dfrbpq_1 u0 (.CLK(clk), .D(d), .RESET_B(rb), .Q(q));
endmodule
