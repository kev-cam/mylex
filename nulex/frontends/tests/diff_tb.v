`timescale 1ns/1ps
module diff_tb;
  reg [7:0] a,b,c,e,f,g;
  wire [7:0] maj0,ch0,sum0, maj1,ch1,sum1;
  gold dut0(.a(a),.b(b),.c(c),.e(e),.f(f),.g(g),.maj(maj0),.ch(ch0),.sum(sum0));
  gate dut1(.a(a),.b(b),.c(c),.e(e),.f(f),.g(g),.maj(maj1),.ch(ch1),.sum(sum1));
  integer i, errs;
  initial begin
    errs = 0;
    a=8'hff; b=8'hff; c=0; e=8'hff; f=0; g=8'hff; #1;
    if ({maj0,ch0,sum0} !== {maj1,ch1,sum1}) errs = errs+1;
    for (i=0;i<200000;i=i+1) begin
      a=$random; b=$random; c=$random; e=$random; f=$random; g=$random; #1;
      if ({maj0,ch0,sum0} !== {maj1,ch1,sum1}) begin
        errs = errs+1;
        if (errs<4) $display("MISMATCH a=%h b=%h c=%h e=%h f=%h g=%h", a,b,c,e,f,g);
      end
    end
    $display("DIFF VECTORS=200001 ERRS=%0d", errs);
    $finish;
  end
endmodule
