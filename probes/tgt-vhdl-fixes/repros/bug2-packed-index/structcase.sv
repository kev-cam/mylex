// Sibling path: variable index into a PACKED ARRAY OF STRUCT with a [0:0] dim
// -> check_for_struct_members -> collapse_array_exprs (netmisc.cc:1654).
module structcase;
   typedef struct packed { logic a; logic [2:0] b; } s_t;   // width 4
   s_t [0:0] arr;    // one-element packed array of struct (stride 4, msb==lsb)
   s_t [1:0] arr2;   // control (msb > lsb)
   int i, fails;
   logic [2:0] rb;
   initial begin
      fails = 0;
      arr  = 4'b1101;          // a=1 b=101
      arr2 = 8'b1101_0010;     // [1]: a=1 b=101 ; [0]: a=0 b=010
      i = 0;
      rb = arr[i].b;
      if (rb !== 3'b101) begin fails++; $display("S1 FAIL arr[0].b=%b (want 101)", rb); end
      rb = arr2[i].b;
      if (rb !== 3'b010) begin fails++; $display("S2 FAIL arr2[0].b=%b (want 010)", rb); end
      i = 1;
      rb = arr2[i].b;
      if (rb !== 3'b101) begin fails++; $display("S3 FAIL arr2[1].b=%b (want 101)", rb); end
      if (fails == 0) $display("PASSED"); else $display("FAILED (%0d)", fails);
   end
endmodule
