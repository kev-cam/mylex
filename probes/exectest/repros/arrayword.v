// Repro: words of an unpacked array net used in continuous logic
// (VX_csa_tree `Ct[i]` passed to a cast function, VX_ks_adder `P[k][i]`
// bit-selects). The nexus of word i carried the array signal with pin i,
// but (1) the nexus-join assignment referenced the bare array and cast it
// to the peer's vector type -> `tmp := A(0 + 7 downto 0)`, and (2) a
// part-select LPM on the word replaced the word index with the bit offset
// -> `A(3)` for A[1][3] (a whole word, type error; wrong word when it
// analysed). Self-check: tb_arrayword.vhd.
module top(input [7:0] a, input [7:0] b, output [7:0] y, output z, output [7:0] w);
  wire [7:0] A [0:1];
  function automatic [7:0] cast; input [7:0] inp; cast = inp; endfunction
  assign A[0] = a;
  assign A[1] = b;
  assign y = cast(A[1]);            // word as a function argument
  assign z = A[1][3] ^ A[0][5];     // bit-selects of two words
  assign w = {A[0][7:4], A[1][3:0]}; // part-selects of two words
endmodule
