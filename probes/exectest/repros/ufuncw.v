// Repro: a function called from a continuous assignment with an actual
// whose width differs from the formal (VX_csa_tree passes a WN-bit slice
// to sv2v_cast_<hash> whose input is WI bits). Verilog resizes the actual
// on the call; the translated call passed it unchanged -> nvc "actual
// length 6 does not match formal length 4". Self-check: tb_ufuncw.vhd.
module top(input [5:0] wide, input [1:0] narrow, output [3:0] y1, output [3:0] y2);
  function automatic [3:0] cast; input [3:0] inp; cast = inp; endfunction
  assign y1 = cast(wide);    // truncated to wide[3:0]
  assign y2 = cast(narrow);  // zero-extended
endmodule
