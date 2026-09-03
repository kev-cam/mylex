// Repro: the same instance label (and net name) in two sibling non-loop
// generate blocks (sv2v inlines every interface-port module as a named
// generate block, so a flattened design is full of these). Only loop
// iterations contributed to the flattening suffix -> "BUF0 already declared".
module leaf(input a, output y);
  assign y = ~a;
endmodule
module top(input a, output y1, output y2);
  if (1) begin : g_a
    wire w;
    leaf buf0(.a(a), .y(w));
    assign y1 = w;
  end
  if (1) begin : g_b
    wire w;
    leaf buf0(.a(a), .y(w));
    assign y2 = ~w;
  end
endmodule
