`include "VX_define.vh"
// Flat-port wrapper around VX_alu_int so sv2v can flatten its interface ports.
module alu_top import VX_gpu_pkg::*; #(
    parameter NUM_LANES = `VX_CFG_NUM_ALU_LANES
) (
    input  wire clk,
    input  wire reset,
    // execute (slave side of VX_alu_int)
    input  wire                          ex_valid,
    output wire                          ex_ready,
    input  wire [$bits(alu_execute_t)-1:0] ex_data,
    // result (master side)
    output wire                          rs_valid,
    input  wire                          rs_ready,
    output wire [$bits(alu_result_t)-1:0] rs_data,
    // branch control (master side, valid-only)
    output wire                          br_valid,
    output wire [NW_WIDTH-1:0]           br_wid,
    output wire                          br_taken,
    output wire [PC_BITS-1:0]            br_dest,
    output wire                          br_is_trap,
    output wire                          br_is_mret,
    output wire [3:0]                    br_trap_cause
);
    VX_execute_if #(.data_t(alu_execute_t)) execute_if();
    VX_result_if  #(.data_t(alu_result_t))  result_if();
    VX_branch_ctl_if branch_ctl_if();

    assign execute_if.valid = ex_valid;
    assign execute_if.data  = alu_execute_t'(ex_data);
    assign ex_ready         = execute_if.ready;

    assign rs_valid         = result_if.valid;
    assign rs_data          = result_if.data;
    assign result_if.ready  = rs_ready;

    assign br_valid      = branch_ctl_if.valid;
    assign br_wid        = branch_ctl_if.wid;
    assign br_taken      = branch_ctl_if.taken;
    assign br_dest       = branch_ctl_if.dest;
    assign br_is_trap    = branch_ctl_if.is_trap;
    assign br_is_mret    = branch_ctl_if.is_mret;
    assign br_trap_cause = branch_ctl_if.trap_cause;

    VX_alu_int #(
        .INSTANCE_ID ("alu0"),
        .BLOCK_IDX   (0),
        .NUM_LANES   (NUM_LANES)
    ) alu (
        .clk           (clk),
        .reset         (reset),
        .execute_if    (execute_if),
        .result_if     (result_if),
        .branch_ctl_if (branch_ctl_if)
    );
endmodule
