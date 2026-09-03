// Repro: entity emission order. `leaf` is discovered from `top` before `mid`
// (DFS parent-first); emitting in reverse discovery order puts `mid` before
// `leaf`, but `mid` instantiates `leaf` -> "design unit LEAF not found".
module leaf(input a, output y);
  assign y = ~a;
endmodule
module mid(input a, output y);
  leaf l(.a(a), .y(y));
endmodule
module top(input a, output y1, output y2);
  leaf l0(.a(a), .y(y1));
  mid  m0(.a(a), .y(y2));
endmodule
