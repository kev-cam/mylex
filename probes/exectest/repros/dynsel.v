// Repro: a bit-select / part-select with a runtime base in a CONTINUOUS
// assignment (VX_fdiv_unit_rtl `s_man[dsh - 1]`). The expression path
// already reads such selects through the bounds-safe l3d_bit_read /
// l3d_part_read (an x or out-of-range index reads x, as in Verilog), but
// the LPM path emitted `s_man(To_Integer(dsh - 1))`, fatal under nvc while
// dsh is still x ("index 2147483647 outside of NATURAL range 23 downto 0").
// Self-check: tb_dynsel.vhd (index left x, then in range, then out of range).
module top(input [23:0] v, input [4:0] sh, output y, output [3:0] p);
  wire [4:0] idx = sh - 5'd1;
  assign y = v[idx];
  assign p = v[idx +: 4];
endmodule
