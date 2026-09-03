// gen_statemachine repro: a parameter override equal to the module's own
// default must not go through yosys `chparam`.
//
// sv2v inlines a module with interface ports into its instantiator as a
// generate block and reaches the interface signals through a hierarchical
// reference BY MODULE NAME -- here a part-select of it passed to a function,
// `sv2v_cast_4(alu_top.execute_if.data[222-:4])` in the Vortex ALU wrapper
// (alu.v:3871/3875).  yosys resolves that in the module as read, but
// `chparam` re-derives the module from its AST and in the derived copy the
// reference no longer resolves (a bare `hier.execute_if.data` or a
// part-select outside a function argument survives the re-derivation):
//     hier.v:25: ERROR: Failed to detect width for identifier \alu.hier.execute_if.data!
// nvc --accel passes every generic actual of the entity (nvc_verilog_params),
// so a top whose actuals equal its defaults still hit this.  Fixed
// gen_statemachine keeps the parsed module when the value equals the
// default ("keep N = 2 (default of hier)"); a genuinely different value
// (N=3) still needs chparam and still fails on this shape -- that is the
// yosys limitation, not the generator's.
module hier #(parameter N = 2) (input wire clk, input wire [7:0] d, output reg [7:0] q);
    function automatic [3:0] cast4; input reg [3:0] x; cast4 = x; endfunction
    generate if (1) begin : execute_if
        wire [7:0] data = d;
    end endgenerate
    generate if (1) begin : alu
        wire [3:0] v = cast4(hier.execute_if.data[6-:4]);
        always @(posedge clk) q <= v + N;
    end endgenerate
endmodule
