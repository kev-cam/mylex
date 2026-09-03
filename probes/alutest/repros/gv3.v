// sv2v inlines a module with interface ports as a named generate block that
// carries the module's parameters -- including string ones.
module gv3 (input [3:0] a, output [3:0] y);
	generate
		if (1) begin : alu
			localparam INSTANCE_ID = "alu0";
			localparam N = 4;
			genvar i;
			for (i = 0; i < N; i = i + 1) begin : g
				assign y[i] = ~a[i];
			end
		end
	endgenerate
endmodule
