// Bit-select of a word of an unpacked array whose ELEMENT is 1 bit
// (sv2v's `logic [N-1:0] x [K]` with N = 1 and a per-thread `x[i][j]`).
// The word ref carries a slice (nexus_to_var_ref) and its type is a scalar
// logic3d, so the array-word part-select path must not append a bit index
// to the scalar: `m(2)(idx)` -> nvc "cannot index non-array type LOGIC3D".
// Verilog: index 0 reads the bit, any other index reads x.
module top(input [1:0] idx, output y, output z, output q);
  wire [0:0] m [0:3];
  assign m[0] = 1'b0;
  assign m[1] = 1'b1;
  assign m[2] = 1'b1;
  assign m[3] = 1'b0;
  assign y = m[2][idx];   // runtime bit-select of a 1-bit word
  assign z = m[1][0];     // constant bit-select of a 1-bit word
  assign q = m[3][0] | m[1][0];
endmodule
