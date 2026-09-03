// Minimal repro for the two --accel text-path gaps on tgt-vhdl output
// (nvc/src/rt/model.c accel_install_subtree):
//
//  (1) a parameterised module instantiated under two parameterisations is
//      emitted as entities VX_preg and VX_preg1 (tgt-vhdl, one entity per
//      parameterisation, nvc_verilog_src "params.v:<module line>"); the
//      synth top was the LOWERED ENTITY name, which yosys (case-sensitive)
//      does not have: "ERROR: Module `vx_preg1' not found!".
//  (2) the top carries every localparam of the module in nvc_verilog_params
//      (sv2v-flattened Vortex tops carry 24-58 package constants); the
//      256-byte buffer cut the string mid-token, the tail had no '=' and
//      gen_statemachine took it for the top module: "chparam N = 2 on
//      VX_gpu_pk" ... "Module `VX_gpu_pk' not found".
//  (3) once the subtree installs, ports the translator writes with the
//      fork's blocking `:=` inside a fused comb process (a concatenation
//      slice of a register output: `assign {valid, cause, rst} = r;
//      assign v = valid;` -> `comb_fused_0: ... v := valid;`) have no
//      driver source; the bridge's NBA-region publication of registered
//      outputs then never reaches the port's readers (they keep the
//      initial value) -- ptop's v/c ports take that shape, q takes the
//      `<=` shape that always worked.
//
// ptop is sequential (24 flops), so a correct text path installs it whole.
module VX_preg #(
    parameter W = 8,
    parameter INIT = 0
) (
    input  wire         clk,
    input  wire         reset,
    input  wire         en,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    always @(posedge clk)
        if (reset)   q <= INIT;
        else if (en) q <= d;
endmodule

module ptop #(
    parameter N = 2
) (
    input  wire        clk,
    input  wire        reset,
    input  wire        en,
    input  wire [11:0] d,
    output wire [11:0] q,
    output wire        v,
    output wire [3:0]  c
);
    localparam VX_gpu_pkg_ALU_TYPE_BITS = 2;
    localparam VX_gpu_pkg_BYTESEL_BITS = 4;
    localparam VX_gpu_pkg_INST_ARGS_BITS = 27;
    localparam VX_gpu_pkg_INST_FMT_BITS = 2;
    localparam VX_gpu_pkg_INST_FRM_BITS = 3;
    localparam VX_gpu_pkg_INST_OP_BITS = 4;
    localparam VX_gpu_pkg_NCTA_BITS = 1;
    localparam VX_gpu_pkg_NCTA_WIDTH = 1;
    localparam VX_gpu_pkg_NUM_CTA_MAX = 2;
    localparam VX_gpu_pkg_NUM_REGS = 64;
    localparam VX_gpu_pkg_NUM_REGS_BITS = 6;
    localparam VX_gpu_pkg_NUM_XREGS = 2;
    localparam VX_gpu_pkg_NW_BITS = 1;
    localparam VX_gpu_pkg_PC_BITS = 30;

    wire [7:0] lo;
    wire [3:0] hi;

    VX_preg #(.W(8), .INIT(0)) u_lo (
        .clk(clk), .reset(reset), .en(en), .d(d[7:0]),  .q(lo)
    );
    VX_preg #(.W(4), .INIT(1)) u_hi (
        .clk(clk), .reset(reset), .en(en), .d(d[11:8]), .q(hi)
    );

    assign q = {hi, lo};

    wire [11:0] r;
    wire        valid;
    wire [3:0]  cause;
    wire [6:0]  rst;
    VX_preg #(.W(12), .INIT(0)) u_r (
        .clk(clk), .reset(reset), .en(en), .d(d), .q(r)
    );
    assign {valid, cause, rst} = r;
    assign v = valid;
    assign c = cause;
endmodule
