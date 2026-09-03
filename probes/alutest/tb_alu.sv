`include "VX_define.vh"
// Oracle testbench: drives alu_top, records every cycle's inputs and outputs
// (hex, nibble-padded) to vectors.txt for cycle-accurate replay under NVC.
module tb_alu import VX_gpu_pkg::*; ();
    localparam NUM_LANES = `VX_CFG_NUM_ALU_LANES;
    localparam EXW = $bits(alu_execute_t);
    localparam RSW = $bits(alu_result_t);
    reg clk = 0, reset = 1;
    always #5 clk = ~clk;
    reg ex_valid = 0;  wire ex_ready;
    alu_execute_t tx;  wire [EXW-1:0] ex_data = tx;
    wire rs_valid; reg rs_ready = 1; wire [RSW-1:0] rs_data;
    wire br_valid, br_taken, br_is_trap, br_is_mret;
    wire [NW_WIDTH-1:0] br_wid; wire [PC_BITS-1:0] br_dest; wire [3:0] br_trap_cause;

    alu_top #(.NUM_LANES(NUM_LANES)) dut (
        .clk(clk), .reset(reset),
        .ex_valid(ex_valid), .ex_ready(ex_ready), .ex_data(ex_data),
        .rs_valid(rs_valid), .rs_ready(rs_ready), .rs_data(rs_data),
        .br_valid(br_valid), .br_wid(br_wid), .br_taken(br_taken), .br_dest(br_dest),
        .br_is_trap(br_is_trap), .br_is_mret(br_is_mret), .br_trap_cause(br_trap_cause));

    // recorder: sample 1ns after each negedge (inputs just applied, outputs settled)
    integer fd, cyc = 0;
    initial fd = $fopen("vectors.txt", "w");
    always @(negedge clk) begin
        #1;
        $fwrite(fd, "%h %h %h  %h %h %h %h %h %h %h %h %h %h\n",
            {3'b0, ex_valid}, {2'b0, ex_data}, {3'b0, rs_ready},
            {3'b0, ex_ready}, {3'b0, rs_valid}, {1'b0, rs_data},
            {3'b0, br_valid}, {3'b0, br_wid}, {3'b0, br_taken}, {2'b0, br_dest},
            {3'b0, br_is_trap}, {3'b0, br_is_mret}, br_trap_cause);
        cyc = cyc + 1;
    end

    task automatic send(input [3:0] op, input [1:0] xtype, input use_imm, input use_pc,
                        input [19:0] imm, input [31:0] a0, input [31:0] a1,
                        input [31:0] b0, input [31:0] b1, input [PC_BITS-1:0] pc);
        begin
            tx = '0;
            tx.header.tmask = {NUM_LANES{1'b1}};
            tx.header.sop = 1; tx.header.eop = 1;
            tx.header.PC = pc; tx.header.wb = 1; tx.header.rd = 5;
            tx.header.uuid = cyc[UUID_WIDTH-1:0];
            tx.op_type = op;
            tx.op_args.alu.xtype = xtype;
            tx.op_args.alu.use_imm = use_imm;
            tx.op_args.alu.use_PC = use_pc;
            tx.op_args.alu.imm20 = imm;
            tx.rs1_data[0] = a0; tx.rs1_data[1] = a1;
            tx.rs2_data[0] = b0; tx.rs2_data[1] = b1;
            ex_valid = 1;
            @(posedge clk); while (!ex_ready) @(posedge clk);
            @(negedge clk); ex_valid = 0;
        end
    endtask

    // backpressure: rs_ready low in a fixed pattern
    always @(negedge clk) rs_ready <= !(cyc % 7 == 3 || cyc % 7 == 4);

    initial begin
        tx = '0;
        repeat (3) @(negedge clk); reset = 0;
        @(negedge clk);
        // arithmetic (xtype=ARITH=0)
        send(INST_ALU_ADD,  0, 0, 0, 20'h0,     32'd10, 32'hFFFFFFF0, 32'd32, 32'd16, 30'h100);
        send(INST_ALU_ADD,  0, 1, 0, 20'hFFFFC, 32'd10, 32'd7,        32'd0,  32'd0,  30'h101); // ADDI -4
        send(INST_ALU_SUB,  0, 0, 0, 20'h0,     32'd10, 32'd3,        32'd32, 32'd3,  30'h102);
        send(INST_ALU_SLT,  0, 0, 0, 20'h0,     32'hFFFFFFFF, 32'd5,  32'd1,  32'd5,  30'h103);
        send(INST_ALU_SLTU, 0, 0, 0, 20'h0,     32'hFFFFFFFF, 32'd5,  32'd1,  32'd6,  30'h104);
        send(INST_ALU_AND,  0, 0, 0, 20'h0,     32'hF0F0F0F0, 32'h1234, 32'h0FF00FF0, 32'hFFFF, 30'h105);
        send(INST_ALU_OR,   0, 1, 0, 20'h00F0F, 32'h10000000, 32'h1, 32'h0, 32'h0, 30'h106);
        send(INST_ALU_XOR,  0, 0, 0, 20'h0,     32'hAAAAAAAA, 32'h1, 32'h55555555, 32'h1, 30'h107);
        send(INST_ALU_SLL,  0, 0, 0, 20'h0,     32'h1, 32'h80000001, 32'd31, 32'd4, 30'h108);
        send(INST_ALU_SRL,  0, 0, 0, 20'h0,     32'h80000000, 32'hFFFFFFFF, 32'd4, 32'd31, 30'h109);
        send(INST_ALU_SRA,  0, 1, 0, 20'h00004,  32'h80000000, 32'h7FFFFFFF, 32'd0, 32'd0, 30'h10A);
        send(INST_ALU_LUI,  0, 1, 0, 20'hABCDE, 32'd0, 32'd0, 32'd0, 32'd0, 30'h10B);
        send(INST_ALU_AUIPC,0, 1, 1, 20'h00001, 32'd0, 32'd0, 32'd0, 32'd0, 30'h10C);
        // branches (xtype=BRANCH=1): target = PC + (imm<<1)
        send(INST_BR_BEQ,  1, 1, 1, 20'h00008, 32'd7, 32'd9, 32'd7, 32'd9, 30'h200); // taken
        send(INST_BR_BEQ,  1, 1, 1, 20'h00008, 32'd7, 32'd9, 32'd8, 32'd9, 30'h201); // lane0 differs
        send(INST_BR_BNE,  1, 1, 1, 20'hFFFF0, 32'd1, 32'd2, 32'd1, 32'd3, 30'h202);
        send(INST_BR_BLT,  1, 1, 1, 20'h00010, 32'hFFFFFFFE, 32'd5, 32'd1, 32'd4, 30'h203);
        send(INST_BR_BGE,  1, 1, 1, 20'h00010, 32'hFFFFFFFE, 32'd5, 32'd1, 32'd4, 30'h204);
        send(INST_BR_BLTU, 1, 1, 1, 20'h00010, 32'hFFFFFFFE, 32'd5, 32'd1, 32'd4, 30'h205);
        send(INST_BR_JAL,  1, 1, 1, 20'h00020, 32'd0, 32'd0, 32'd0, 32'd0, 30'h206);
        repeat (12) @(negedge clk);
        $fclose(fd);
        $display("ORACLE_DONE cycles=%0d", cyc);
        $finish;
    end
endmodule
