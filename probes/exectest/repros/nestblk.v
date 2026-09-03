// Repro: an `always @*` whose body holds a NAMED block (sv2v_autoblock_N --
// sv2v hoists a loop variable into one) with a local `integer`, nested
// below the top level of the body, whose name (__i) is not a legal VHDL
// identifier: the variable is declared under its safe name but the signal
// was never renamed to it, so every reference looked up `__i` and failed.
module top(input [3:0] mask, input [19:0] fl, output reg [4:0] merged);
  always @(*) begin
    merged = 5'b0;
    begin : blk
      integer __i;
      for (__i = 0; __i < 4; __i = __i + 1)
        if (mask[__i])
          merged = merged | fl[__i*5 +: 5];
    end
  end
endmodule
