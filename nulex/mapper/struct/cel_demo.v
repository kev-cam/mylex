module cel_demo(input [3:0] a, input [3:0] b, input w_b, input w_c, input w_d,
                output [3:0] cy, output wy);
  sky130_fd_sc_hd__maj3_1 m0 (.A(a[0]), .B(b[0]), .C(cy[0]), .X(cy[0]));
  sky130_fd_sc_hd__maj3_1 m1 (.A(a[1]), .B(b[1]), .C(cy[1]), .X(cy[1]));
  sky130_fd_sc_hd__maj3_1 m2 (.A(a[2]), .B(b[2]), .C(cy[2]), .X(cy[2]));
  sky130_fd_sc_hd__maj3_1 m3 (.A(a[3]), .B(b[3]), .C(cy[3]), .X(cy[3]));
  wire t1, t2, t3;
  sky130_fd_sc_hd__or3_1  u1 (.A(w_b), .B(w_c), .C(w_d), .X(t1));
  sky130_fd_sc_hd__and2_1 u2 (.A(a[0]), .B(t1), .X(t2));
  sky130_fd_sc_hd__and3_1 u3 (.A(w_b), .B(w_c), .C(w_d), .X(t3));
  sky130_fd_sc_hd__or2_1  u4 (.A(t2), .B(t3), .X(wy));
endmodule
