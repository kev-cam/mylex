* 8-bit NCL ripple adder MC subckt (kvt threaded to each nclfa)
.subckt nclfa8 a0H a0L a1H a1L a2H a2L a3H a3L a4H a4L a5H a5L a6H a6L a7H a7L b0H b0L b1H b1L b2H b2L b3H b3L b4H b4L b5H b5L b6H b6L b7H b7L ciH ciL s0H s0L s1H s1L s2H s2L s3H s3L s4H s4L s5H s5L s6H s6L s7H s7L coH coL VDD VSS
.param kvt=1
Xfa0 a0H a0L b0H b0L ciH ciL s0H s0L c1H c1L VDD VSS nclfa kvt={kvt}
Xfa1 a1H a1L b1H b1L c1H c1L s1H s1L c2H c2L VDD VSS nclfa kvt={kvt}
Xfa2 a2H a2L b2H b2L c2H c2L s2H s2L c3H c3L VDD VSS nclfa kvt={kvt}
Xfa3 a3H a3L b3H b3L c3H c3L s3H s3L c4H c4L VDD VSS nclfa kvt={kvt}
Xfa4 a4H a4L b4H b4L c4H c4L s4H s4L c5H c5L VDD VSS nclfa kvt={kvt}
Xfa5 a5H a5L b5H b5L c5H c5L s5H s5L c6H c6L VDD VSS nclfa kvt={kvt}
Xfa6 a6H a6L b6H b6L c6H c6L s6H s6L c7H c7L VDD VSS nclfa kvt={kvt}
Xfa7 a7H a7L b7H b7L c7H c7L s7H s7L coH coL VDD VSS nclfa kvt={kvt}
.ends nclfa8
