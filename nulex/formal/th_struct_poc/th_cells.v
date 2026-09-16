// Opaque threshold-gate cells (blackbox): dual-rail nets are single std_logic bits.
// These stand in for the real hysteretic TH cells; kept opaque so the DIMS
// structure survives to the fork extractor (constraints.py reads their ports).
(* blackbox *) module th22(input a, input b, output y); endmodule            // C-element (2-of-2)
(* blackbox *) module th12(input a, input b, output y); endmodule            // OR / 1-of-2 rail collector
(* blackbox *) module th13(input a, input b, input c, output y); endmodule   // 1-of-3 rail collector
(* blackbox *) module th23(input a, input b, input c, output y); endmodule   // majority
(* blackbox *) module th33(input a, input b, input c, output y); endmodule   // 3-of-3
