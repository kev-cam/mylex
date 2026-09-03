module blk (input [3:0] a, input [3:0] b, output reg [3:0] y, output reg [3:0] z);
	always @(*) begin : sv2v_autoblock_1
		reg [3:0] t;
		t = a + b;
		y = t ^ 4'h5;
	end
	always @(*) z = y + a;
endmodule
