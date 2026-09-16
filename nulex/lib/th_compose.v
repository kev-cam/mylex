// nulex/lib/th_compose.v — the composed TH cells realized on sky130 std cells,
// for OpenROAD P&R (the ones that are NOT a single sky130 gate). Functionally
// verified against the behavioral spec in th_compose.vhd + tb_compose.vhd; the
// C-element feedback loops route cleanly (mapper/struct/run_th_pnr.sh).

// --- hysteretic C-elements: y = set(inputs) | (y & any(inputs)) ; feedback = state
module th22_c(input a, input b, output y);            // Muller C = maj3(a,b,y)
  sky130_fd_sc_hd__maj3_1 m (.A(a), .B(b), .C(y), .X(y));
endmodule
module th33_c(input a, input b, input c, output y);   // 3-of-3 C-element
  wire s, r, h;
  sky130_fd_sc_hd__and3_1 us (.A(a), .B(b), .C(c), .X(s));   // set = a&b&c
  sky130_fd_sc_hd__or3_1  ur (.A(a), .B(b), .C(c), .X(r));   // any = a|b|c
  sky130_fd_sc_hd__and2_1 uh (.A(y), .B(r), .X(h));          // hold = y & any
  sky130_fd_sc_hd__or2_1  uy (.A(s), .B(h), .X(y));          // y = set | hold  (feedback)
endmodule
module th44_c(input a, input b, input c, input d, output y);   // 4-of-4 C-element
  wire s, r, h;
  sky130_fd_sc_hd__and4_1 us (.A(a), .B(b), .C(c), .D(d), .X(s));
  sky130_fd_sc_hd__or4_1  ur (.A(a), .B(b), .C(c), .D(d), .X(r));
  sky130_fd_sc_hd__and2_1 uh (.A(y), .B(r), .X(h));
  sky130_fd_sc_hd__or2_1  uy (.A(s), .B(h), .X(y));
endmodule

// --- weighted / threshold (combinational) ---
module th23w2(input a, input b, input c, output y);            // a | (b&c)
  wire t; sky130_fd_sc_hd__and2_1 u1 (.A(b), .B(c), .X(t));
  sky130_fd_sc_hd__or2_1  u2 (.A(a), .B(t), .X(y));
endmodule
module th34w2(input a, input b, input c, input d, output y);   // (a&(b|c|d)) | (b&c&d)
  wire t1, t2, t3;
  sky130_fd_sc_hd__or3_1  u1 (.A(b), .B(c), .C(d), .X(t1));
  sky130_fd_sc_hd__and2_1 u2 (.A(a), .B(t1), .X(t2));
  sky130_fd_sc_hd__and3_1 u3 (.A(b), .B(c), .C(d), .X(t3));
  sky130_fd_sc_hd__or2_1  u4 (.A(t2), .B(t3), .X(y));
endmodule
module th24(input a, input b, input c, input d, output y);     // 2-of-4 = OR of 6 pair-ANDs
  wire p1,p2,p3,p4,p5,p6,o1,o2;
  sky130_fd_sc_hd__and2_1 g1(.A(a),.B(b),.X(p1)); sky130_fd_sc_hd__and2_1 g2(.A(a),.B(c),.X(p2));
  sky130_fd_sc_hd__and2_1 g3(.A(a),.B(d),.X(p3)); sky130_fd_sc_hd__and2_1 g4(.A(b),.B(c),.X(p4));
  sky130_fd_sc_hd__and2_1 g5(.A(b),.B(d),.X(p5)); sky130_fd_sc_hd__and2_1 g6(.A(c),.B(d),.X(p6));
  sky130_fd_sc_hd__or3_1 o_1(.A(p1),.B(p2),.C(p3),.X(o1)); sky130_fd_sc_hd__or3_1 o_2(.A(p4),.B(p5),.C(p6),.X(o2));
  sky130_fd_sc_hd__or2_1 uy(.A(o1),.B(o2),.X(y));
endmodule
module th34(input a, input b, input c, input d, output y);     // 3-of-4 = OR of 4 triple-ANDs
  wire t1,t2,t3,t4;
  sky130_fd_sc_hd__and3_1 g1(.A(a),.B(b),.C(c),.X(t1)); sky130_fd_sc_hd__and3_1 g2(.A(a),.B(b),.C(d),.X(t2));
  sky130_fd_sc_hd__and3_1 g3(.A(a),.B(c),.C(d),.X(t3)); sky130_fd_sc_hd__and3_1 g4(.A(b),.B(c),.C(d),.X(t4));
  sky130_fd_sc_hd__or4_1 uy(.A(t1),.B(t2),.C(t3),.D(t4),.X(y));
endmodule
