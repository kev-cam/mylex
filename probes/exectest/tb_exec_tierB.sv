`include "VX_define.vh"
// Oracle testbench for exec_top (VX_execute, Tier A: ALU+MULDIV, LSU, SFU;
// F disabled).  Drives all three dispatch ports concurrently, models the LSU
// client memory on lsu_client_if, consumes commit_if with per-unit
// backpressure, and records every cycle's inputs and outputs to vectors.txt
// for cycle-accurate replay under NVC: inputs first as nibble-padded hex
// (they never carry x), then every output bit-exact (%b, one character per
// bit, so an x bit never masks its defined neighbours).  Sampling is 1 ns
// after each falling edge; every input changes only at the falling edge.
// The port map and the recorder are generated from ports_<tier>.txt by
// gen_tb.py (this file is the template tb_exec.sv.in).
//
// Tier B (F enabled, soft FPU; VX_CFG_EXT_F_DISABLE not defined) adds a
// fourth stream on dispatch_if[3] (EX_FPU) and consumes commit_if[3]; the SFU
// stream additionally programs FRM for warp 1 first and reads FFLAGS/FCSR
// last.  Everything Tier B is under `ifndef VX_CFG_EXT_F_DISABLE, so the
// Tier A stimulus (and its vectors) is unchanged.
module tb_exec import VX_gpu_pkg::*; ();
    localparam NT   = `VX_CFG_NUM_THREADS;      // 2 lanes
    localparam DW   = $bits(dispatch_t);
    localparam CW   = $bits(commit_t);
    localparam RQW  = $bits(lsu_req_data_t);
    localparam RSW  = $bits(lsu_rsp_data_t);
    localparam CTAW = $bits(cta_csrs_t);
    localparam LNW  = $bits(cta_lane_t);
    localparam MEM_LAT = 3;                     // fixed load latency (cycles)
    localparam ARITH  = ALU_TYPE_ARITH;
    localparam BRANCH = ALU_TYPE_BRANCH;
    localparam MULDIV = ALU_TYPE_MULDIV;

    reg clk = 0;
    always #5 clk = ~clk;
    integer cyc = 0;

    // ------------------------------------------------------------------
    // DUT-side signals, named exactly as the wrapper ports
    // ------------------------------------------------------------------
    reg  reset = 1;
    // lsu_client_if[0]
    wire                lsu_client_if_0_req_valid;
    wire [RQW-1:0]      lsu_client_if_0_req_data;
    reg                 lsu_client_if_0_req_ready = 1;
    reg                 lsu_client_if_0_rsp_valid = 0;
    lsu_rsp_data_t      rsp_tx;
    wire [RSW-1:0]      lsu_client_if_0_rsp_data = rsp_tx;
    wire                lsu_client_if_0_rsp_ready;
    // dispatch_if[0..2]  (EX_ALU=0, EX_LSU=1, EX_SFU=2)
    reg                 dispatch_if_0_valid = 0, dispatch_if_1_valid = 0, dispatch_if_2_valid = 0;
    dispatch_t          tx_alu, tx_lsu, tx_sfu;
    wire [DW-1:0]       dispatch_if_0_data = tx_alu;
    wire [DW-1:0]       dispatch_if_1_data = tx_lsu;
    wire [DW-1:0]       dispatch_if_2_data = tx_sfu;
    wire                dispatch_if_0_ready, dispatch_if_1_ready, dispatch_if_2_ready;
    // commit_if[0..2]
    wire                commit_if_0_valid, commit_if_1_valid, commit_if_2_valid;
    wire [CW-1:0]       commit_if_0_data, commit_if_1_data, commit_if_2_data;
    reg                 commit_if_0_ready = 1, commit_if_1_ready = 1, commit_if_2_ready = 1;
`ifndef VX_CFG_EXT_F_DISABLE
    // dispatch_if[3] / commit_if[3]  (EX_FPU)
    reg                 dispatch_if_3_valid = 0;
    dispatch_t          tx_fpu;
    wire [DW-1:0]       dispatch_if_3_data = tx_fpu;
    wire                dispatch_if_3_ready;
    wire                commit_if_3_valid;
    wire [CW-1:0]       commit_if_3_data;
    reg                 commit_if_3_ready = 1;
`endif
    // sched_csr_if (distinctive constants so CSR reads are checkable)
    reg [PERF_CTR_BITS-1:0]   sched_csr_if_cycles  = 44'h123_4567_89AB;
    reg [PERF_CTR_BITS-1:0]   sched_csr_if_instret = 44'h0AB_CDEF_0123;
    reg [`VX_CFG_NUM_WARPS-1:0] sched_csr_if_active_warps = 2'b11;
    reg [`VX_CFG_NUM_WARPS*NT-1:0] sched_csr_if_thread_masks = 4'b10_11;   // warp1=10, warp0=11
    reg [`VX_CFG_MEM_ADDR_WIDTH-1:0] sched_csr_if_mscratch = 32'hCAFE_BABE;
    cta_csrs_t          cta;
    wire [CTAW-1:0]     sched_csr_if_cta_csrs = cta;
    reg [NT*LNW-1:0]    sched_csr_if_cta_lane = {6'b10_01_00, 6'b01_10_11}; // lane1 {z,y,x}=2,1,0 ; lane0 = 1,2,3
    reg [31:0]          sched_csr_if_csr_mstatus = 32'h0000_1800;
    reg [31:0]          sched_csr_if_csr_mtvec   = 32'h8000_0100;
    reg [31:0]          sched_csr_if_csr_mepc    = 32'h8000_0ABC;
    reg [31:0]          sched_csr_if_csr_mcause  = 32'h0000_000B;
    reg [31:0]          sched_csr_if_csr_mtval   = 32'hDEAD_BEEF;
    wire [NW_WIDTH-1:0]   sched_csr_if_csr_rd_wid;
    wire [NCTA_WIDTH-1:0] sched_csr_if_csr_rd_cta_id;
    wire                  sched_csr_if_csr_wr_valid;
    wire [NW_WIDTH-1:0]   sched_csr_if_csr_wr_wid;
    wire [31:0]           sched_csr_if_csr_wr_data;
    wire                  sched_csr_if_trap_csr_wr_valid;
    wire [11:0]           sched_csr_if_trap_csr_wr_addr;
    wire [31:0]           sched_csr_if_trap_csr_wr_data;
    // branch_ctl_if[0]
    wire                  branch_ctl_if_0_valid, branch_ctl_if_0_taken, branch_ctl_if_0_is_trap, branch_ctl_if_0_is_mret;
    wire [NW_WIDTH-1:0]   branch_ctl_if_0_wid;
    wire [PC_BITS-1:0]    branch_ctl_if_0_dest;
    wire [3:0]            branch_ctl_if_0_trap_cause;
    // warp_ctl_if
    wire warp_ctl_if_wspawn_valid, warp_ctl_if_tmc_valid, warp_ctl_if_split_valid, warp_ctl_if_sjoin_valid, warp_ctl_if_bar_valid, warp_ctl_if_wsync_valid;
    wire [NW_WIDTH-1:0]         warp_ctl_if_wid, warp_ctl_if_dvstack_wid;
    wire [$bits(wspawn_t)-1:0]  warp_ctl_if_wspawn;
    wire [$bits(tmc_t)-1:0]     warp_ctl_if_tmc;
    wire [$bits(split_t)-1:0]   warp_ctl_if_split;
    wire [$bits(join_t)-1:0]    warp_ctl_if_sjoin;
    wire [$bits(barrier_t)-1:0] warp_ctl_if_bar;
    wire [BAR_ADDR_W-1:0]       warp_ctl_if_bar_addr;
    reg                         warp_ctl_if_bar_phase = 0;
    reg [`VX_CFG_NUM_WARPS-1:0] warp_ctl_if_warp_pending_alm_empty = 2'b11;
    reg                         warp_ctl_if_lsu_sched_drained = 1;
    reg [DV_STACK_SIZEW-1:0]    warp_ctl_if_dvstack_ptr = 0;
    // dcr_csr_if (slave side inside execute: valid/addr/mpm_class in, value/ready out)
    reg                         dcr_csr_if_valid = 0;
    reg [11:0]                  dcr_csr_if_addr = 12'h000;
    reg [7:0]                   dcr_csr_if_mpm_class = 8'h00;
    wire [VX_DCR_DATA_WIDTH-1:0] dcr_csr_if_value;
    wire                        dcr_csr_if_ready;

    exec_top #(.CORE_ID(0)) dut (
        .clk(clk),
        .reset(reset),
        .lsu_client_if_0_req_valid(lsu_client_if_0_req_valid),
        .lsu_client_if_0_req_data(lsu_client_if_0_req_data),
        .lsu_client_if_0_req_ready(lsu_client_if_0_req_ready),
        .lsu_client_if_0_rsp_valid(lsu_client_if_0_rsp_valid),
        .lsu_client_if_0_rsp_data(lsu_client_if_0_rsp_data),
        .lsu_client_if_0_rsp_ready(lsu_client_if_0_rsp_ready),
        .dispatch_if_0_valid(dispatch_if_0_valid),
        .dispatch_if_0_data(dispatch_if_0_data),
        .dispatch_if_0_ready(dispatch_if_0_ready),
        .dispatch_if_1_valid(dispatch_if_1_valid),
        .dispatch_if_1_data(dispatch_if_1_data),
        .dispatch_if_1_ready(dispatch_if_1_ready),
        .dispatch_if_2_valid(dispatch_if_2_valid),
        .dispatch_if_2_data(dispatch_if_2_data),
        .dispatch_if_2_ready(dispatch_if_2_ready),
        .dispatch_if_3_valid(dispatch_if_3_valid),
        .dispatch_if_3_data(dispatch_if_3_data),
        .dispatch_if_3_ready(dispatch_if_3_ready),
        .commit_if_0_valid(commit_if_0_valid),
        .commit_if_0_data(commit_if_0_data),
        .commit_if_0_ready(commit_if_0_ready),
        .commit_if_1_valid(commit_if_1_valid),
        .commit_if_1_data(commit_if_1_data),
        .commit_if_1_ready(commit_if_1_ready),
        .commit_if_2_valid(commit_if_2_valid),
        .commit_if_2_data(commit_if_2_data),
        .commit_if_2_ready(commit_if_2_ready),
        .commit_if_3_valid(commit_if_3_valid),
        .commit_if_3_data(commit_if_3_data),
        .commit_if_3_ready(commit_if_3_ready),
        .sched_csr_if_cycles(sched_csr_if_cycles),
        .sched_csr_if_instret(sched_csr_if_instret),
        .sched_csr_if_active_warps(sched_csr_if_active_warps),
        .sched_csr_if_thread_masks(sched_csr_if_thread_masks),
        .sched_csr_if_mscratch(sched_csr_if_mscratch),
        .sched_csr_if_cta_csrs(sched_csr_if_cta_csrs),
        .sched_csr_if_cta_lane(sched_csr_if_cta_lane),
        .sched_csr_if_csr_mstatus(sched_csr_if_csr_mstatus),
        .sched_csr_if_csr_mtvec(sched_csr_if_csr_mtvec),
        .sched_csr_if_csr_mepc(sched_csr_if_csr_mepc),
        .sched_csr_if_csr_mcause(sched_csr_if_csr_mcause),
        .sched_csr_if_csr_mtval(sched_csr_if_csr_mtval),
        .sched_csr_if_csr_rd_wid(sched_csr_if_csr_rd_wid),
        .sched_csr_if_csr_rd_cta_id(sched_csr_if_csr_rd_cta_id),
        .sched_csr_if_csr_wr_valid(sched_csr_if_csr_wr_valid),
        .sched_csr_if_csr_wr_wid(sched_csr_if_csr_wr_wid),
        .sched_csr_if_csr_wr_data(sched_csr_if_csr_wr_data),
        .sched_csr_if_trap_csr_wr_valid(sched_csr_if_trap_csr_wr_valid),
        .sched_csr_if_trap_csr_wr_addr(sched_csr_if_trap_csr_wr_addr),
        .sched_csr_if_trap_csr_wr_data(sched_csr_if_trap_csr_wr_data),
        .branch_ctl_if_0_valid(branch_ctl_if_0_valid),
        .branch_ctl_if_0_wid(branch_ctl_if_0_wid),
        .branch_ctl_if_0_taken(branch_ctl_if_0_taken),
        .branch_ctl_if_0_dest(branch_ctl_if_0_dest),
        .branch_ctl_if_0_is_trap(branch_ctl_if_0_is_trap),
        .branch_ctl_if_0_is_mret(branch_ctl_if_0_is_mret),
        .branch_ctl_if_0_trap_cause(branch_ctl_if_0_trap_cause),
        .warp_ctl_if_wspawn_valid(warp_ctl_if_wspawn_valid),
        .warp_ctl_if_tmc_valid(warp_ctl_if_tmc_valid),
        .warp_ctl_if_split_valid(warp_ctl_if_split_valid),
        .warp_ctl_if_sjoin_valid(warp_ctl_if_sjoin_valid),
        .warp_ctl_if_bar_valid(warp_ctl_if_bar_valid),
        .warp_ctl_if_wsync_valid(warp_ctl_if_wsync_valid),
        .warp_ctl_if_wid(warp_ctl_if_wid),
        .warp_ctl_if_wspawn(warp_ctl_if_wspawn),
        .warp_ctl_if_tmc(warp_ctl_if_tmc),
        .warp_ctl_if_split(warp_ctl_if_split),
        .warp_ctl_if_sjoin(warp_ctl_if_sjoin),
        .warp_ctl_if_bar(warp_ctl_if_bar),
        .warp_ctl_if_bar_addr(warp_ctl_if_bar_addr),
        .warp_ctl_if_dvstack_wid(warp_ctl_if_dvstack_wid),
        .warp_ctl_if_bar_phase(warp_ctl_if_bar_phase),
        .warp_ctl_if_warp_pending_alm_empty(warp_ctl_if_warp_pending_alm_empty),
        .warp_ctl_if_lsu_sched_drained(warp_ctl_if_lsu_sched_drained),
        .warp_ctl_if_dvstack_ptr(warp_ctl_if_dvstack_ptr),
        .dcr_csr_if_valid(dcr_csr_if_valid),
        .dcr_csr_if_addr(dcr_csr_if_addr),
        .dcr_csr_if_mpm_class(dcr_csr_if_mpm_class),
        .dcr_csr_if_value(dcr_csr_if_value),
        .dcr_csr_if_ready(dcr_csr_if_ready)
    );

    // ------------------------------------------------------------------
    // recorder: sample 1ns after each negedge (inputs just applied, outputs settled)
    // ------------------------------------------------------------------
    integer fd;
    initial fd = $fopen("vectors.txt", "w");
    always @(negedge clk) begin
        #1;
        $fwrite(fd, "%h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b\n",
            {3'b0, reset},
            {3'b0, lsu_client_if_0_req_ready},
            {3'b0, lsu_client_if_0_rsp_valid},
            {1'b0, lsu_client_if_0_rsp_data},
            {3'b0, dispatch_if_0_valid},
            {2'b0, dispatch_if_0_data},
            {3'b0, dispatch_if_1_valid},
            {2'b0, dispatch_if_1_data},
            {3'b0, dispatch_if_2_valid},
            {2'b0, dispatch_if_2_data},
            {3'b0, dispatch_if_3_valid},
            {2'b0, dispatch_if_3_data},
            {3'b0, commit_if_0_ready},
            {3'b0, commit_if_1_ready},
            {3'b0, commit_if_2_ready},
            {3'b0, commit_if_3_ready},
            sched_csr_if_cycles,
            sched_csr_if_instret,
            {2'b0, sched_csr_if_active_warps},
            sched_csr_if_thread_masks,
            sched_csr_if_mscratch,
            {1'b0, sched_csr_if_cta_csrs},
            sched_csr_if_cta_lane,
            sched_csr_if_csr_mstatus,
            sched_csr_if_csr_mtvec,
            sched_csr_if_csr_mepc,
            sched_csr_if_csr_mcause,
            sched_csr_if_csr_mtval,
            {3'b0, warp_ctl_if_bar_phase},
            {2'b0, warp_ctl_if_warp_pending_alm_empty},
            {3'b0, warp_ctl_if_lsu_sched_drained},
            {3'b0, warp_ctl_if_dvstack_ptr},
            {3'b0, dcr_csr_if_valid},
            dcr_csr_if_addr,
            dcr_csr_if_mpm_class,
            {3'b0, lsu_client_if_0_req_valid},
            {2'b0, lsu_client_if_0_req_data},
            {3'b0, lsu_client_if_0_rsp_ready},
            {3'b0, dispatch_if_0_ready},
            {3'b0, dispatch_if_1_ready},
            {3'b0, dispatch_if_2_ready},
            {3'b0, dispatch_if_3_ready},
            {3'b0, commit_if_0_valid},
            {1'b0, commit_if_0_data},
            {3'b0, commit_if_1_valid},
            {1'b0, commit_if_1_data},
            {3'b0, commit_if_2_valid},
            {1'b0, commit_if_2_data},
            {3'b0, commit_if_3_valid},
            {1'b0, commit_if_3_data},
            {3'b0, sched_csr_if_csr_rd_wid},
            {3'b0, sched_csr_if_csr_rd_cta_id},
            {3'b0, sched_csr_if_csr_wr_valid},
            {3'b0, sched_csr_if_csr_wr_wid},
            sched_csr_if_csr_wr_data,
            {3'b0, sched_csr_if_trap_csr_wr_valid},
            sched_csr_if_trap_csr_wr_addr,
            sched_csr_if_trap_csr_wr_data,
            {3'b0, branch_ctl_if_0_valid},
            {3'b0, branch_ctl_if_0_wid},
            {3'b0, branch_ctl_if_0_taken},
            {2'b0, branch_ctl_if_0_dest},
            {3'b0, branch_ctl_if_0_is_trap},
            {3'b0, branch_ctl_if_0_is_mret},
            branch_ctl_if_0_trap_cause,
            {3'b0, warp_ctl_if_wspawn_valid},
            {3'b0, warp_ctl_if_tmc_valid},
            {3'b0, warp_ctl_if_split_valid},
            {3'b0, warp_ctl_if_sjoin_valid},
            {3'b0, warp_ctl_if_bar_valid},
            {3'b0, warp_ctl_if_wsync_valid},
            {3'b0, warp_ctl_if_wid},
            warp_ctl_if_wspawn,
            {2'b0, warp_ctl_if_tmc},
            {1'b0, warp_ctl_if_split},
            {1'b0, warp_ctl_if_sjoin},
            {3'b0, warp_ctl_if_bar},
            warp_ctl_if_bar_addr,
            {3'b0, warp_ctl_if_dvstack_wid},
            dcr_csr_if_value,
            {3'b0, dcr_csr_if_ready});
        cyc = cyc + 1;
    end

    // ------------------------------------------------------------------
    // cycle-indexed input patterns (all applied at the falling edge)
    // ------------------------------------------------------------------
    integer drain_blk_t0 = -1000;   // lsu_sched_drained low for [t0, t0+8)
    integer wsync_blk_t0 = -1000;   // warp_pending_alm_empty[1] low for [t0, t0+8)
`ifndef VX_CFG_EXT_F_DISABLE
    integer fpu_bp_t0 = -1000;      // commit_if[3].ready low for [t0, t0+12): fills the FPU response buffers
`endif
    always @(negedge clk) begin
        commit_if_0_ready <= !(cyc % 7 == 3 || cyc % 7 == 4);
        // LSU: periodic, plus a 14-cycle stall during the load burst so the
        // response buffers fill and lsu_client_if.rsp_ready is driven low
        commit_if_1_ready <= !(cyc % 5 == 1) && !(cyc >= 36 && cyc < 50);
        commit_if_2_ready <= !(cyc % 6 == 2 || cyc % 6 == 3);
`ifndef VX_CFG_EXT_F_DISABLE
        commit_if_3_ready <= !(cyc % 9 == 4 || cyc % 9 == 5) && !(cyc >= fpu_bp_t0 && cyc < fpu_bp_t0 + 12);
`endif
        lsu_client_if_0_req_ready <= !(cyc % 4 == 1);
        warp_ctl_if_lsu_sched_drained <= !(cyc >= drain_blk_t0 && cyc < drain_blk_t0 + 8);
        warp_ctl_if_warp_pending_alm_empty <= {!(cyc >= wsync_blk_t0 && cyc < wsync_blk_t0 + 8), 1'b1};
        warp_ctl_if_bar_phase <= ((cyc % 16) >= 8);
        warp_ctl_if_dvstack_ptr <= (cyc % 3 == 0);
        // DCR read bridge: three read windows on different CSRs
        dcr_csr_if_valid <= (cyc >= 30 && cyc < 34) || (cyc >= 70 && cyc < 73) || (cyc >= 110 && cyc < 112);
        dcr_csr_if_addr  <= (cyc < 50) ? `VX_CSR_MCYCLE : (cyc < 90) ? `VX_CSR_MSCRATCH : `VX_CSR_NUM_WARPS;
    end

    // ------------------------------------------------------------------
    // LSU client memory model: word-addressed RAM, byte enables on stores,
    // in-order load responses after MEM_LAT cycles, honours rsp_ready.
    // ------------------------------------------------------------------
    lsu_req_data_t req_rx;
    assign req_rx = lsu_req_data_t'(lsu_client_if_0_req_data);
    reg [31:0] mem [0:255];
    localparam QN = 16;
    reg [LSU_CLIENT_TAG_WIDTH-1:0] q_tag [0:QN-1];
    reg [NT-1:0] q_mask [0:QN-1];
    reg [31:0]   q_d0 [0:QN-1];
    reg [31:0]   q_d1 [0:QN-1];
    integer      q_due [0:QN-1];
    integer q_wr = 0, q_rd = 0;
    reg rsp_fire_r = 0;
    integer n_req_rd = 0, n_req_wr = 0, n_rsp = 0;
    integer n_commit0 = 0, n_commit1 = 0, n_commit2 = 0;
    integer n_sent0 = 0, n_sent1 = 0, n_sent2 = 0;
`ifndef VX_CFG_EXT_F_DISABLE
    integer n_commit3 = 0, n_sent3 = 0;
`endif
    integer mi, mb;

    initial begin
        for (mi = 0; mi < 256; mi = mi + 1)
            mem[mi] = {mi[7:0], ~mi[7:0], 8'hA5, mi[7:0] ^ 8'h3C};
    end

    always @(posedge clk) begin
        if (!reset) begin
            if (lsu_client_if_0_req_valid && lsu_client_if_0_req_ready) begin
                if (req_rx.rw) begin
                    n_req_wr = n_req_wr + 1;
                    for (mi = 0; mi < NT; mi = mi + 1) begin
                        if (req_rx.mask[mi]) begin
                            for (mb = 0; mb < 4; mb = mb + 1) begin
                                if (req_rx.byteen[mi][mb])
                                    mem[req_rx.addr[mi][7:0]][mb*8 +: 8] = req_rx.data[mi][mb*8 +: 8];
                            end
                        end
                    end
                end else begin
                    n_req_rd = n_req_rd + 1;
                    q_tag [q_wr % QN] = req_rx.tag;
                    q_mask[q_wr % QN] = req_rx.mask;
                    q_d0  [q_wr % QN] = mem[req_rx.addr[0][7:0]];
                    q_d1  [q_wr % QN] = mem[req_rx.addr[1][7:0]];
                    q_due [q_wr % QN] = cyc + MEM_LAT;
                    q_wr = q_wr + 1;
                end
            end
            rsp_fire_r <= lsu_client_if_0_rsp_valid && lsu_client_if_0_rsp_ready;
            if (commit_if_0_valid && commit_if_0_ready) n_commit0 = n_commit0 + 1;
            if (commit_if_1_valid && commit_if_1_ready) n_commit1 = n_commit1 + 1;
            if (commit_if_2_valid && commit_if_2_ready) n_commit2 = n_commit2 + 1;
`ifndef VX_CFG_EXT_F_DISABLE
            if (commit_if_3_valid && commit_if_3_ready) n_commit3 = n_commit3 + 1;
`endif
        end
    end

    always @(negedge clk) begin
        if (rsp_fire_r) begin
            lsu_client_if_0_rsp_valid = 0;
            q_rd = q_rd + 1;
            n_rsp = n_rsp + 1;
        end
        if (!lsu_client_if_0_rsp_valid && (q_rd != q_wr) && (cyc >= q_due[q_rd % QN])) begin
            rsp_tx = '0;
            rsp_tx.mask    = q_mask[q_rd % QN];
            rsp_tx.data[0] = q_d0[q_rd % QN];
            rsp_tx.data[1] = q_d1[q_rd % QN];
            rsp_tx.tag     = q_tag[q_rd % QN];
            rsp_tx.sop     = 1;
            rsp_tx.eop     = 1;
            lsu_client_if_0_rsp_valid = 1;
        end
    end

    // ------------------------------------------------------------------
    // dispatch drivers (one per unit; each waits for ready at the rising
    // edge and changes its port only at the falling edge)
    // ------------------------------------------------------------------
    function automatic dispatch_t mk_hdr(input [NT-1:0] tmask, input wis, input [PC_BITS-1:0] pc,
                                         input wb, input [NUM_REGS_BITS-1:0] rd);
        dispatch_t t;
        begin
            t = '0;
            t.uuid = cyc[UUID_WIDTH-1:0];
            t.wis = wis; t.cta_id = 0; t.sid = 0;
            t.tmask = tmask; t.PC = pc; t.wb = wb; t.wr_xregs = 2'b01; t.rd = rd;
            t.bytesel = BYTESEL_DEFAULT;
            t.sop = 1; t.eop = 1;
            mk_hdr = t;
        end
    endfunction

    // ---- ALU (dispatch_if[0]) ----
    task automatic send_alu(input [3:0] op, input [1:0] xtype, input use_imm, input use_pc, input [19:0] imm,
                            input [31:0] a0, input [31:0] a1, input [31:0] b0, input [31:0] b1,
                            input [PC_BITS-1:0] pc, input [NT-1:0] tmask, input wis, input integer gap);
        begin
            tx_alu = mk_hdr(tmask, wis, pc, 1'b1, 5'd5);
            tx_alu.op_type = op;
            tx_alu.op_args.alu.xtype = xtype;
            tx_alu.op_args.alu.use_imm = use_imm;
            tx_alu.op_args.alu.use_PC = use_pc;
            tx_alu.op_args.alu.imm20 = imm;
            tx_alu.rs1_data[0] = a0; tx_alu.rs1_data[1] = a1;
            tx_alu.rs2_data[0] = b0; tx_alu.rs2_data[1] = b1;
            dispatch_if_0_valid = 1;
            @(posedge clk); while (!dispatch_if_0_ready) @(posedge clk);
            n_sent0 = n_sent0 + 1;
            @(negedge clk); dispatch_if_0_valid = 0;
            repeat (gap) @(negedge clk);
        end
    endtask

    // ---- LSU (dispatch_if[1]) ----
    task automatic send_lsu(input [3:0] op, input is_store, input [11:0] offset,
                            input [31:0] base0, input [31:0] base1, input [31:0] sd0, input [31:0] sd1,
                            input [NT-1:0] tmask, input wis, input [PC_BITS-1:0] pc, input integer gap);
        begin
            tx_lsu = mk_hdr(tmask, wis, pc, !is_store && (op != INST_LSU_FENCE), 5'd7);
            tx_lsu.op_type = op;
            tx_lsu.op_args.lsu.is_store = is_store;
            tx_lsu.op_args.lsu.is_float = 0;
            tx_lsu.op_args.lsu.pack = 2'b00;
            tx_lsu.op_args.lsu.offset = offset;
            tx_lsu.rs1_data[0] = base0; tx_lsu.rs1_data[1] = base1;
            tx_lsu.rs2_data[0] = sd0;   tx_lsu.rs2_data[1] = sd1;
            dispatch_if_1_valid = 1;
            @(posedge clk); while (!dispatch_if_1_ready) @(posedge clk);
            n_sent1 = n_sent1 + 1;
            @(negedge clk); dispatch_if_1_valid = 0;
            repeat (gap) @(negedge clk);
        end
    endtask

    // ---- SFU (dispatch_if[2]): CSR ops ----
    task automatic send_csr(input [3:0] op, input use_imm, input [11:0] addr, input [4:0] imm5,
                            input [31:0] r0, input [31:0] r1, input [NT-1:0] tmask, input wis, input integer gap);
        begin
            tx_sfu = mk_hdr(tmask, wis, 30'h300 + n_sent2, 1'b1, 5'd9);
            tx_sfu.op_type = op;
            tx_sfu.op_args.csr.use_imm = use_imm;
            tx_sfu.op_args.csr.addr = addr;
            tx_sfu.op_args.csr.imm5 = imm5;
            tx_sfu.rs1_data[0] = r0; tx_sfu.rs1_data[1] = r1;
            dispatch_if_2_valid = 1;
            @(posedge clk); while (!dispatch_if_2_ready) @(posedge clk);
            n_sent2 = n_sent2 + 1;
            @(negedge clk); dispatch_if_2_valid = 0;
            repeat (gap) @(negedge clk);
        end
    endtask

    // ---- SFU (dispatch_if[2]): warp-control ops ----
    task automatic send_wctl(input [3:0] op, input cond_neg, input sync_bar, input bar_arrive,
                             input [31:0] r1_0, input [31:0] r1_1, input [31:0] r2_0, input [31:0] r2_1,
                             input [NT-1:0] tmask, input wis, input integer gap);
        begin
            tx_sfu = mk_hdr(tmask, wis, 30'h400 + n_sent2, 1'b0, 5'd0);
            tx_sfu.op_type = op;
            tx_sfu.op_args.wctl.is_cond_neg = cond_neg;
            tx_sfu.op_args.wctl.is_sync_bar = sync_bar;
            tx_sfu.op_args.wctl.is_bar_arrive = bar_arrive;
            tx_sfu.rs1_data[0] = r1_0; tx_sfu.rs1_data[1] = r1_1;
            tx_sfu.rs2_data[0] = r2_0; tx_sfu.rs2_data[1] = r2_1;
            dispatch_if_2_valid = 1;
            @(posedge clk); while (!dispatch_if_2_ready) @(posedge clk);
            n_sent2 = n_sent2 + 1;
            @(negedge clk); dispatch_if_2_valid = 0;
            repeat (gap) @(negedge clk);
        end
    endtask

`ifndef VX_CFG_EXT_F_DISABLE
    // ---- FPU (dispatch_if[3]) ----
    // op = INST_FPU_*, fmt = op_args.fpu.fmt (fmt[1] = SUB variant of ADD/MADD/NMADD;
    // for FCVT fmt[0] = F32, fmt[1] = I32), frm = rounding mode or the sub-op
    // selector of CMP (LE/LT/EQ) and MISC (SGNJ/SGNJN/SGNJX/CLASS/MVXW/MVWX/MIN/MAX).
    // PC = 0x600 + sequence number, so a commit can be matched to its dispatch
    // packet in the vectors (the FPU returns out of order across its four cores).
    task automatic send_fpu(input [3:0] op, input [1:0] fmt, input [2:0] frm,
                            input [31:0] a0, input [31:0] a1, input [31:0] b0, input [31:0] b1,
                            input [31:0] c0, input [31:0] c1,
                            input [NT-1:0] tmask, input wis, input [NUM_REGS_BITS-1:0] rd, input integer gap);
        begin
            tx_fpu = mk_hdr(tmask, wis, 30'h600 + n_sent3, 1'b1, rd);
            tx_fpu.op_type = op;
            tx_fpu.op_args.fpu.fmt = fmt;
            tx_fpu.op_args.fpu.frm = frm;
            tx_fpu.rs1_data[0] = a0; tx_fpu.rs1_data[1] = a1;
            tx_fpu.rs2_data[0] = b0; tx_fpu.rs2_data[1] = b1;
            tx_fpu.rs3_data[0] = c0; tx_fpu.rs3_data[1] = c1;
            dispatch_if_3_valid = 1;
            @(posedge clk); while (!dispatch_if_3_ready) @(posedge clk);
            n_sent3 = n_sent3 + 1;
            @(negedge clk); dispatch_if_3_valid = 0;
            repeat (gap) @(negedge clk);
        end
    endtask

    // F32 operands (IEEE-754 binary32 bit patterns)
    localparam [31:0] F_P0     = 32'h0000_0000;  // +0
    localparam [31:0] F_N0     = 32'h8000_0000;  // -0
    localparam [31:0] F_PINF   = 32'h7F80_0000;  // +inf
    localparam [31:0] F_NINF   = 32'hFF80_0000;  // -inf
    localparam [31:0] F_QNAN   = 32'h7FC0_0000;  // canonical qNaN
    localparam [31:0] F_QNANP  = 32'h7FC1_2345;  // qNaN with payload
    localparam [31:0] F_NQNAN  = 32'hFFC0_0000;  // -qNaN
    localparam [31:0] F_SNAN   = 32'h7F80_0001;  // sNaN (min payload)
    localparam [31:0] F_SNAN2  = 32'h7FA0_0000;  // sNaN
    localparam [31:0] F_NSNAN  = 32'hFFA0_0000;  // -sNaN
    localparam [31:0] F_MINSUB = 32'h0000_0001;  // 2^-149, smallest subnormal
    localparam [31:0] F_MAXSUB = 32'h007F_FFFF;  // largest subnormal
    localparam [31:0] F_NMINSUB= 32'h8000_0001;  // -2^-149
    localparam [31:0] F_SUB    = 32'h0040_0000;  // 2^-127 (subnormal)
    localparam [31:0] F_NSUB   = 32'h8040_0000;  // -2^-127
    localparam [31:0] F_MINNRM = 32'h0080_0000;  // 2^-126, smallest normal
    localparam [31:0] F_MAXNRM = 32'h7F7F_FFFF;  // largest normal
    localparam [31:0] F_NMAXNRM= 32'hFF7F_FFFF;  // -largest normal
    localparam [31:0] F_1      = 32'h3F80_0000;
    localparam [31:0] F_N1     = 32'hBF80_0000;
    localparam [31:0] F_1P     = 32'h3F80_0001;  // 1 + 2^-23
    localparam [31:0] F_2      = 32'h4000_0000;
    localparam [31:0] F_N2     = 32'hC000_0000;
    localparam [31:0] F_3      = 32'h4040_0000;
    localparam [31:0] F_4      = 32'h4080_0000;
    localparam [31:0] F_6      = 32'h40C0_0000;
    localparam [31:0] F_7      = 32'h40E0_0000;
    localparam [31:0] F_N7     = 32'hC0E0_0000;
    localparam [31:0] F_10     = 32'h4120_0000;
    localparam [31:0] F_100    = 32'h42C8_0000;
    localparam [31:0] F_HALF   = 32'h3F00_0000;
    localparam [31:0] F_N1P5   = 32'hBFC0_0000;
    localparam [31:0] F_2P5    = 32'h4020_0000;
    localparam [31:0] F_N2P5   = 32'hC020_0000;
    localparam [31:0] F_0P1    = 32'h3DCC_CCCD;
    localparam [31:0] F_N0P1   = 32'hBDCC_CCCD;
    localparam [31:0] F_0P3    = 32'h3E99_999A;
    localparam [31:0] F_PI     = 32'h4049_0FDB;
    localparam [31:0] F_1E38   = 32'h7E96_7699;
    localparam [31:0] F_1E20   = 32'h60AD_78EC;
    localparam [31:0] F_1EN20  = 32'h1E3C_E508;
    localparam [31:0] F_EPS24  = 32'h3380_0000;  // 2^-24
    localparam [31:0] F_NEPS24 = 32'hB380_0000;  // -2^-24
    localparam [31:0] F_3E9    = 32'h4F32_D05E;  // 3e9 (> INT_MAX, < UINT_MAX)
    localparam [31:0] F_N3E9   = 32'hCF32_D05E;
    localparam [31:0] F_2P31   = 32'h4F00_0000;  // 2^31
    localparam [31:0] F_N2P31  = 32'hCF00_0000;  // -2^31 (INT_MIN, exact)
    localparam [31:0] F_2P32   = 32'h4F80_0000;  // 2^32
    localparam [31:0] F_1E10   = 32'h5015_02F9;
    localparam [31:0] F_2P24   = 32'h4B80_0000;  // 16777216
    localparam [31:0] F_12345  = 32'h4640_E6B6;  // 12345.678
    localparam [1:0]  FMT_S   = 2'b00;           // fmt: single, plain op
    localparam [1:0]  FMT_SUB = 2'b10;           // fmt: single, SUB variant (fmt[1])
    localparam [2:0]  RNE = INST_FRM_RNE, RTZ = INST_FRM_RTZ, RDN = INST_FRM_RDN,
                      RUP = INST_FRM_RUP, RMM = INST_FRM_RMM, DYN = INST_FRM_DYN;
    localparam [2:0]  M_SGNJ = 3'd0, M_SGNJN = 3'd1, M_SGNJX = 3'd2, M_CLASS = 3'd3,
                      M_MVXW = 3'd4, M_MVWX = 3'd5, M_MIN = 3'd6, M_MAX = 3'd7;
    localparam [2:0]  C_LE = 3'd0, C_LT = 3'd1, C_EQ = 3'd2;
    localparam [NUM_REGS_BITS-1:0] FR = 32;      // f-register destinations are rd = 32 + n, n in 0..31 (REG_TYPE_F; NUM_REGS_BITS is 6 with F)
    integer frm_wr_target = -1;                  // n_sent2 after the SFU stream's FRM write
`endif

    reg done_alu = 0, done_lsu = 0, done_sfu = 0;
`ifndef VX_CFG_EXT_F_DISABLE
    reg done_fpu = 0;
`endif

    // ------------------------------------------------------------------
    // stimulus
    // ------------------------------------------------------------------
    initial begin
        tx_alu = '0; tx_lsu = '0; tx_sfu = '0; rsp_tx = '0;
`ifndef VX_CFG_EXT_F_DISABLE
        tx_fpu = '0;                             // dispatch_if[3] data and its combinational ready defined from row 0
`endif
        cta = '0;
        cta.cta_id = 1; cta.cta_rank = 1; cta.cta_size = 2'd2;
        cta.block_idx[0] = 32'd3; cta.block_idx[1] = 32'd2; cta.block_idx[2] = 32'd1;
        cta.block_dim[0] = 3'd4; cta.block_dim[1] = 3'd2; cta.block_dim[2] = 3'd1;
        cta.grid_dim[0] = 32'd16; cta.grid_dim[1] = 32'd8; cta.grid_dim[2] = 32'd4;
        cta.entry = 30'h2000_0040;
        cta.param = 32'h9000_0010;
        cta.lmem_addr = 32'hFFFF_0000;
        cta.cluster_size = 32'd1;
        repeat (3) @(negedge clk); reset = 0;
    end

    // ALU stream: arithmetic, Zicond, MULDIV, branches, traps
    initial begin
        wait (reset == 0); @(negedge clk);
        // arithmetic (xtype=ARITH)
        send_alu(INST_ALU_ADD,  ARITH, 0, 0, 20'h0,     32'd10, 32'hFFFFFFF0, 32'd32, 32'd16, 30'h100, 2'b11, 0, 0);
        send_alu(INST_ALU_ADD,  ARITH, 1, 0, 20'hFFFFC, 32'd10, 32'd7,        32'd0,  32'd0,  30'h101, 2'b11, 1, 0); // ADDI -4
        send_alu(INST_ALU_SUB,  ARITH, 0, 0, 20'h0,     32'd10, 32'd3,        32'd32, 32'd3,  30'h102, 2'b11, 0, 0);
        send_alu(INST_ALU_SLT,  ARITH, 0, 0, 20'h0,     32'hFFFFFFFF, 32'd5,  32'd1,  32'd5,  30'h103, 2'b11, 0, 0);
        send_alu(INST_ALU_SLTU, ARITH, 0, 0, 20'h0,     32'hFFFFFFFF, 32'd5,  32'd1,  32'd6,  30'h104, 2'b01, 1, 2);
        send_alu(INST_ALU_AND,  ARITH, 0, 0, 20'h0,     32'hF0F0F0F0, 32'h1234, 32'h0FF00FF0, 32'hFFFF, 30'h105, 2'b11, 0, 0);
        send_alu(INST_ALU_OR,   ARITH, 1, 0, 20'h00F0F, 32'h10000000, 32'h1, 32'h0, 32'h0, 30'h106, 2'b11, 0, 0);
        send_alu(INST_ALU_XOR,  ARITH, 0, 0, 20'h0,     32'hAAAAAAAA, 32'h1, 32'h55555555, 32'h1, 30'h107, 2'b10, 1, 0);
        send_alu(INST_ALU_SLL,  ARITH, 0, 0, 20'h0,     32'h1, 32'h80000001, 32'd31, 32'd4, 30'h108, 2'b11, 0, 0);
        send_alu(INST_ALU_SRL,  ARITH, 0, 0, 20'h0,     32'h80000000, 32'hFFFFFFFF, 32'd4, 32'd31, 30'h109, 2'b11, 0, 0);
        send_alu(INST_ALU_SRA,  ARITH, 1, 0, 20'h00004, 32'h80000000, 32'h7FFFFFFF, 32'd0, 32'd0, 30'h10A, 2'b11, 1, 1);
        send_alu(INST_ALU_LUI,  ARITH, 1, 0, 20'hABCDE, 32'd0, 32'd0, 32'd0, 32'd0, 30'h10B, 2'b11, 0, 0);
        send_alu(INST_ALU_AUIPC,ARITH, 1, 1, 20'h00001, 32'd0, 32'd0, 32'd0, 32'd0, 30'h10C, 2'b11, 0, 0);
        send_alu(INST_ALU_CZEQ, ARITH, 0, 0, 20'h0,     32'h1234, 32'h5678, 32'd0, 32'd9, 30'h10D, 2'b11, 0, 0); // czero.eqz
        send_alu(INST_ALU_CZNE, ARITH, 0, 0, 20'h0,     32'h1234, 32'h5678, 32'd0, 32'd9, 30'h10E, 2'b11, 1, 0); // czero.nez
        // MULDIV (xtype=MULDIV, op_type[2:0] = INST_M_*)
        send_alu({1'b0, INST_M_MUL},    MULDIV, 0, 0, 20'h0, 32'd7, 32'hFFFFFFFD, 32'd6, 32'd5, 30'h110, 2'b11, 0, 0);
        send_alu({1'b0, INST_M_MULH},   MULDIV, 0, 0, 20'h0, 32'h80000000, 32'h12345678, 32'h7FFFFFFF, 32'hFFFFFFFF, 30'h111, 2'b11, 0, 0);
        send_alu({1'b0, INST_M_MULHU},  MULDIV, 0, 0, 20'h0, 32'hFFFFFFFF, 32'h12345678, 32'hFFFFFFFF, 32'h9ABCDEF0, 30'h112, 2'b11, 1, 0);
        send_alu({1'b0, INST_M_MULHSU}, MULDIV, 0, 0, 20'h0, 32'hFFFFFFFE, 32'h7FFFFFFF, 32'hFFFFFFFF, 32'h80000000, 30'h113, 2'b11, 0, 0);
        send_alu({1'b0, INST_M_DIV},    MULDIV, 0, 0, 20'h0, 32'hFFFFFF9C, 32'd100, 32'd7, 32'd0, 30'h114, 2'b11, 0, 0); // -100/7, 100/0
        send_alu({1'b0, INST_M_DIVU},   MULDIV, 0, 0, 20'h0, 32'hFFFFFFFF, 32'd100, 32'd16, 32'd0, 30'h115, 2'b11, 1, 0); // div by zero lane1
        send_alu(INST_ALU_ADD,  ARITH, 0, 0, 20'h0, 32'd1, 32'd2, 32'd3, 32'd4, 30'h116, 2'b11, 0, 0); // int op overlapping the divider
        send_alu({1'b0, INST_M_REM},    MULDIV, 0, 0, 20'h0, 32'hFFFFFF9C, 32'h80000000, 32'd7, 32'hFFFFFFFF, 30'h117, 2'b11, 0, 0); // -100%7, INT_MIN%-1
        send_alu({1'b0, INST_M_REMU},   MULDIV, 0, 0, 20'h0, 32'd100, 32'hFFFFFFFF, 32'd0, 32'd10, 30'h118, 2'b01, 0, 0); // rem by zero lane0
        send_alu({1'b0, INST_M_DIV},    MULDIV, 0, 0, 20'h0, 32'h80000000, 32'd9, 32'hFFFFFFFF, 32'd3, 30'h119, 2'b11, 1, 0); // INT_MIN/-1
        send_alu({1'b0, INST_M_MUL},    MULDIV, 0, 0, 20'h0, 32'd0, 32'hFFFFFFFF, 32'd0, 32'hFFFFFFFF, 30'h11A, 2'b10, 0, 3);
        // branches (xtype=BRANCH): target = PC + (imm<<1)
        send_alu(INST_BR_BEQ,  BRANCH, 1, 1, 20'h00008, 32'd7, 32'd9, 32'd7, 32'd9, 30'h200, 2'b11, 0, 0); // taken
        send_alu(INST_BR_BEQ,  BRANCH, 1, 1, 20'h00008, 32'd7, 32'd9, 32'd8, 32'd9, 30'h201, 2'b01, 0, 0); // lane0 differs, tmask=01 -> not taken
        send_alu(INST_BR_BNE,  BRANCH, 1, 1, 20'hFFFF0, 32'd1, 32'd2, 32'd1, 32'd3, 30'h202, 2'b11, 1, 0);
        send_alu(INST_BR_BLT,  BRANCH, 1, 1, 20'h00010, 32'hFFFFFFFE, 32'd5, 32'd1, 32'd4, 30'h203, 2'b11, 0, 0);
        send_alu(INST_BR_BGE,  BRANCH, 1, 1, 20'h00010, 32'hFFFFFFFE, 32'd5, 32'd1, 32'd4, 30'h204, 2'b11, 0, 0);
        send_alu(INST_BR_BLTU, BRANCH, 1, 1, 20'h00010, 32'hFFFFFFFE, 32'd5, 32'd1, 32'd4, 30'h205, 2'b11, 1, 0);
        send_alu(INST_BR_BGEU, BRANCH, 1, 1, 20'h00010, 32'hFFFFFFFE, 32'd5, 32'd1, 32'd4, 30'h206, 2'b11, 0, 0);
        send_alu(INST_BR_JAL,  BRANCH, 1, 1, 20'h00020, 32'd0, 32'd0, 32'd0, 32'd0, 30'h207, 2'b11, 0, 0);
        send_alu(INST_BR_JALR, BRANCH, 1, 0, 20'h00010, 32'h80000400, 32'h80000800, 32'd0, 32'd0, 30'h208, 2'b11, 1, 0); // dest = rs1 + imm
        send_alu(INST_BR_ECALL, BRANCH, 0, 0, 20'h0, 32'd0, 32'd0, 32'd0, 32'd0, 30'h209, 2'b11, 0, 0); // trap, cause 11
        send_alu(INST_BR_EBREAK, BRANCH, 0, 0, 20'h0, 32'd0, 32'd0, 32'd0, 32'd0, 30'h20A, 2'b11, 1, 0); // trap, cause 3
        send_alu(INST_BR_MRET, BRANCH, 1, 0, 20'h0, 32'h80000ABC, 32'd0, 32'd0, 32'd0, 30'h20B, 2'b11, 0, 0); // mret
        send_alu(INST_BR_BEQ,  BRANCH, 1, 1, 20'h00004, 32'd1, 32'd2, 32'd1, 32'd3, 30'h20C, 2'b10, 0, 0); // lane1 differs, tmask=10 -> not taken
        done_alu = 1;
    end

    // LSU stream: stores/loads (word, byte, half), partial masks, IO range, fence, bursts
    initial begin
        wait (reset == 0); @(negedge clk);
        send_lsu(INST_LSU_SW, 1, 12'h000, 32'h20, 32'h24, 32'h11223344, 32'h55667788, 2'b11, 0, 30'h500, 0);
        send_lsu(INST_LSU_LW, 0, 12'h000, 32'h20, 32'h24, 32'h0, 32'h0, 2'b11, 0, 30'h501, 0);
        send_lsu(INST_LSU_SB, 1, 12'h001, 32'h20, 32'h24, 32'h000000AA, 32'h000000BB, 2'b11, 1, 30'h502, 0);
        send_lsu(INST_LSU_SH, 1, 12'h002, 32'h20, 32'h24, 32'h0000CCDD, 32'h0000EEFF, 2'b11, 0, 30'h503, 0);
        send_lsu(INST_LSU_LB, 0, 12'h001, 32'h20, 32'h24, 32'h0, 32'h0, 2'b11, 0, 30'h504, 0);
        send_lsu(INST_LSU_LBU,0, 12'h001, 32'h20, 32'h24, 32'h0, 32'h0, 2'b11, 1, 30'h505, 0);
        send_lsu(INST_LSU_LH, 0, 12'h002, 32'h20, 32'h24, 32'h0, 32'h0, 2'b11, 0, 30'h506, 0);
        send_lsu(INST_LSU_LHU,0, 12'h002, 32'h20, 32'h24, 32'h0, 32'h0, 2'b11, 0, 30'h507, 2);
        send_lsu(INST_LSU_LB, 0, 12'h003, 32'h20, 32'h24, 32'h0, 32'h0, 2'b11, 1, 30'h508, 0); // align 3
        send_lsu(INST_LSU_LW, 0, 12'hFFC, 32'h1104, 32'h1108, 32'h0, 32'h0, 2'b11, 0, 30'h509, 0); // offset -4, IO range
        send_lsu(INST_LSU_LW, 0, 12'h000, 32'h20200, 32'h20204, 32'h0, 32'h0, 2'b10, 0, 30'h50A, 0); // lane1 only
        send_lsu(INST_LSU_SW, 1, 12'h004, 32'h20200, 32'h20204, 32'hDEADBEEF, 32'hCAFEF00D, 2'b01, 1, 30'h50B, 0); // lane0 only
        send_lsu(INST_LSU_LW, 0, 12'h004, 32'h20200, 32'h20204, 32'h0, 32'h0, 2'b11, 0, 30'h50C, 0);
        send_lsu(INST_LSU_FENCE, 0, 12'h000, 32'h0, 32'h0, 32'h0, 32'h0, 2'b11, 0, 30'h50D, 0);
        send_lsu(INST_LSU_LW, 0, 12'h000, 32'h1100, 32'h1104, 32'h0, 32'h0, 2'b11, 1, 30'h50E, 0);
        // burst of back-to-back loads to fill the response queue under backpressure
        send_lsu(INST_LSU_LW, 0, 12'h000, 32'h00, 32'h04, 32'h0, 32'h0, 2'b11, 0, 30'h50F, 0);
        send_lsu(INST_LSU_LW, 0, 12'h008, 32'h00, 32'h04, 32'h0, 32'h0, 2'b11, 1, 30'h510, 0);
        send_lsu(INST_LSU_LHU,0, 12'h010, 32'h00, 32'h04, 32'h0, 32'h0, 2'b11, 0, 30'h511, 0);
        send_lsu(INST_LSU_LBU,0, 12'h01A, 32'h00, 32'h04, 32'h0, 32'h0, 2'b11, 1, 30'h512, 0);
        send_lsu(INST_LSU_LW, 0, 12'h020, 32'h00, 32'h04, 32'h0, 32'h0, 2'b11, 0, 30'h513, 0);
        send_lsu(INST_LSU_SH, 1, 12'h022, 32'h00, 32'h04, 32'h1234, 32'h5678, 2'b11, 0, 30'h514, 0);
        send_lsu(INST_LSU_LW, 0, 12'h020, 32'h00, 32'h04, 32'h0, 32'h0, 2'b11, 1, 30'h515, 0);
        send_lsu(INST_LSU_SB, 1, 12'h03B, 32'h00, 32'h04, 32'h99, 32'h77, 2'b11, 0, 30'h516, 4);
        send_lsu(INST_LSU_LB, 0, 12'h03B, 32'h00, 32'h04, 32'h0, 32'h0, 2'b11, 0, 30'h517, 0);
        send_lsu(INST_LSU_FENCE, 0, 12'h000, 32'h0, 32'h0, 32'h0, 32'h0, 2'b11, 1, 30'h518, 0);
        send_lsu(INST_LSU_SW, 1, 12'h000, 32'h30, 32'h34, 32'h01020304, 32'h05060708, 2'b11, 0, 30'h519, 0);
        send_lsu(INST_LSU_LW, 0, 12'h000, 32'h30, 32'h34, 32'h0, 32'h0, 2'b11, 0, 30'h51A, 0);
        done_lsu = 1;
    end

    // SFU stream: CSR reads/writes and warp control
    initial begin
        wait (reset == 0); @(negedge clk);
`ifndef VX_CFG_EXT_F_DISABLE
        // Tier B: program FRM = RDN for warp 1 first; the FPU stream's frm=DYN
        // ops on warp 1 resolve their rounding mode through fpu_csr_if.read_frm
        send_csr(INST_SFU_CSRRW, 1, `VX_CSR_FRM, 5'd2, 32'd0, 32'd0, 2'b11, 1, 0);
        frm_wr_target = n_sent2;
`endif
        // CSR reads (CSRRS with rs1=0 is a pure read)
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_MCYCLE,        5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_MCYCLE_H,      5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_MINSTRET,      5'd0, 32'd0, 32'd0, 2'b11, 1, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_MINSTRET_H,    5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_MHARTID,       5'd0, 32'd0, 32'd0, 2'b11, 1, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_THREAD_ID,     5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_WARP_ID,       5'd0, 32'd0, 32'd0, 2'b11, 1, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_CORE_ID,       5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_ACTIVE_WARPS,  5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_ACTIVE_THREADS,5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_ACTIVE_THREADS,5'd0, 32'd0, 32'd0, 2'b11, 1, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_NUM_THREADS,   5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_NUM_WARPS,     5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_NUM_CORES,     5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_MSCRATCH,      5'd0, 32'd0, 32'd0, 2'b11, 1, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_MSTATUS,       5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_MTVEC,         5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_MEPC,          5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_MCAUSE,        5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_MTVAL,         5'd0, 32'd0, 32'd0, 2'b01, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_MISA,          5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_MVENDORID,     5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_MARCHID,       5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_MIMPID,        5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_CTA_ID,        5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_CTA_RANK,      5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_CTA_SIZE,      5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_CTA_BLOCK_ID_X,5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_CTA_BLOCK_ID_Y,5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_CTA_BLOCK_ID_Z,5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_CTA_BLOCK_DIM_X,5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_CTA_GRID_DIM_Y,5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_CTA_LMEM_ADDR, 5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_CTA_CLUSTER_SIZE,5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_CTA_ENTRY,     5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_CTA_THREAD_ID_X,5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_CTA_THREAD_ID_Y,5'd0, 32'd0, 32'd0, 2'b11, 1, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_CTA_THREAD_ID_Z,5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_NUM_BARRIERS,  5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_LOCAL_MEM_BASE,5'd0, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_SATP,          5'd0, 32'd0, 32'd0, 2'b11, 0, 0);   // reads 0 (VM off)
        send_csr(INST_SFU_CSRRS, 0, 12'h7C5,               5'd0, 32'd0, 32'd0, 2'b11, 0, 0);   // undefined -> 0
        // CSR writes
        send_csr(INST_SFU_CSRRW, 0, `VX_CSR_MSCRATCH, 5'd0, 32'h600D_F00D, 32'h0BAD_F00D, 2'b11, 0, 0); // csr_wr_valid
        send_csr(INST_SFU_CSRRW, 1, `VX_CSR_MSCRATCH, 5'h1F, 32'd0, 32'd0, 2'b11, 1, 0);          // imm write
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_MSTATUS,  5'd0, 32'h0000_0008, 32'd0, 2'b11, 0, 0);   // trap csr: read|8
        send_csr(INST_SFU_CSRRC, 0, `VX_CSR_MTVEC,    5'd0, 32'h0000_00FF, 32'd0, 2'b11, 0, 0);   // trap csr: read&~ff
        send_csr(INST_SFU_CSRRW, 0, `VX_CSR_MEPC,     5'd0, 32'h8000_1234, 32'd0, 2'b11, 1, 0);
        send_csr(INST_SFU_CSRRW, 1, `VX_CSR_MCAUSE,   5'd7, 32'd0, 32'd0, 2'b11, 0, 0);
        send_csr(INST_SFU_CSRRS, 1, `VX_CSR_MTVAL,    5'd1, 32'd0, 32'd0, 2'b11, 0, 1);
        send_csr(INST_SFU_CSRRC, 0, `VX_CSR_MSCRATCH, 5'd0, 32'd0, 32'd0, 2'b11, 0, 0);          // rs1=0: read only, no write
        // warp control
        send_wctl(INST_SFU_TMC,    0, 0, 0, 32'h3, 32'h1, 32'h0, 32'h0, 2'b11, 0, 0);            // tmask <- rs1[last_tid=1][1:0] = 01
        send_wctl(INST_SFU_TMC,    0, 0, 0, 32'h2, 32'h0, 32'h0, 32'h0, 2'b01, 1, 0);            // last_tid=0 -> 10
        send_wctl(INST_SFU_WSPAWN, 0, 0, 0, 32'd2, 32'd2, 32'h8000_0200, 32'h8000_0200, 2'b11, 0, 0);
        send_wctl(INST_SFU_SPLIT,  0, 0, 0, 32'h1, 32'h0, 32'h0, 32'h0, 2'b11, 0, 0);            // divergent
        send_wctl(INST_SFU_SPLIT,  1, 0, 0, 32'h1, 32'h1, 32'h0, 32'h0, 2'b11, 1, 0);            // all else, not divergent
        send_wctl(INST_SFU_JOIN,   0, 0, 0, 32'h1, 32'h1, 32'h0, 32'h0, 2'b11, 0, 0);
        drain_blk_t0 = cyc + 1;                                                                    // BAR must wait for lsu_sched_drained
        send_wctl(INST_SFU_BAR,    0, 0, 0, 32'h0000_0100, 32'h0000_0100, 32'd2, 32'd2, 2'b11, 0, 0); // id 1, 2 warps
        send_wctl(INST_SFU_BAR,    0, 0, 1, 32'h0000_0200, 32'h0000_0200, 32'd1, 32'd1, 2'b11, 1, 0); // arrive -> result = bar_phase
        send_wctl(INST_SFU_BAR,    0, 1, 0, 32'h8000_0300, 32'h8000_0300, 32'd2, 32'd2, 2'b11, 0, 0); // sync bar, global
        send_wctl(INST_SFU_BAR,    0, 0, 1, 32'h0000_0100, 32'h0000_0100, 32'h8000_0003, 32'h8000_0003, 2'b11, 0, 0); // expect_tx (rs2[31])
        send_wctl(INST_SFU_PRED,   0, 0, 0, 32'h0, 32'h0, 32'h2, 32'h2, 2'b11, 0, 0);            // no lane taken -> rs2 mask
        send_wctl(INST_SFU_PRED,   0, 0, 0, 32'h1, 32'h0, 32'h3, 32'h3, 2'b11, 1, 0);            // lane0 taken
        send_wctl(INST_SFU_PRED,   1, 0, 0, 32'h1, 32'h0, 32'h3, 32'h3, 2'b11, 0, 0);            // negated: lane1
        wsync_blk_t0 = cyc + 1;                                                                    // WSYNC on warp 1 must wait
        send_wctl(INST_SFU_WSYNC,  0, 0, 0, 32'h0, 32'h0, 32'h0, 32'h0, 2'b11, 1, 0);
        send_wctl(INST_SFU_WSYNC,  0, 0, 0, 32'h0, 32'h0, 32'h0, 32'h0, 2'b11, 0, 0);            // warp 0: no wait
        send_wctl(INST_SFU_JOIN,   0, 0, 0, 32'h0, 32'h0, 32'h0, 32'h0, 2'b10, 1, 0);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_MHARTID,       5'd0, 32'd0, 32'd0, 2'b10, 0, 0);
        send_wctl(INST_SFU_TMC,    0, 0, 0, 32'h0, 32'h0, 32'h0, 32'h0, 2'b11, 0, 0);            // tmc 0 (warp exit)
`ifndef VX_CFG_EXT_F_DISABLE
        // Tier B: once the FPU stream has drained, read back the fflags the
        // FPU accumulated into fcsr (per warp), FRM of warp 1, clear and re-read
        wait (done_fpu && n_commit3 == n_sent3);
        repeat (4) @(negedge clk);
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_FFLAGS, 5'd0, 32'd0, 32'd0, 2'b11, 0, 0);            // warp 0 fflags
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_FCSR,   5'd0, 32'd0, 32'd0, 2'b11, 1, 0);            // warp 1 {frm, fflags}
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_FRM,    5'd0, 32'd0, 32'd0, 2'b11, 1, 0);            // warp 1 frm = RDN
        send_csr(INST_SFU_CSRRC, 0, `VX_CSR_FFLAGS, 5'd0, 32'h1F, 32'h1F, 2'b11, 0, 0);          // clear warp 0 fflags
        send_csr(INST_SFU_CSRRS, 0, `VX_CSR_FCSR,   5'd0, 32'd0, 32'd0, 2'b11, 0, 0);            // warp 0 fcsr now 0
`endif
        done_sfu = 1;
    end

`ifndef VX_CFG_EXT_F_DISABLE
    // FPU stream (dispatch_if[3], EX_FPU): two lanes with different operands;
    // expected results in the comments are IEEE-754 binary32 (lane0 ; lane1).
    // send_fpu(op, fmt, frm, a0, a1, b0, b1, c0, c1, tmask, wis, rd, gap)
    initial begin
        wait (reset == 0); @(negedge clk);
        // ---- FMA core: FADD/FSUB (fmt[1] = SUB), rounding modes, specials ----
        send_fpu(INST_FPU_ADD, FMT_S,   RNE, F_1, F_2P5, F_2, F_N1P5, 0, 0, 2'b11, 0, FR+1, 0);            // 3 ; 1
        send_fpu(INST_FPU_ADD, FMT_SUB, RNE, F_1, F_3, F_2, F_3, 0, 0, 2'b11, 1, FR+2, 0);                 // -1 ; +0
        send_fpu(INST_FPU_ADD, FMT_SUB, RDN, F_3, F_1, F_3, F_1P, 0, 0, 2'b11, 0, FR+3, 0);                // -0 (RDN exact zero) ; -2^-23
        send_fpu(INST_FPU_ADD, FMT_S,   RNE, F_1, F_1P, F_EPS24, F_EPS24, 0, 0, 2'b11, 0, FR+4, 0);        // 1 (tie->even, NX) ; 1+2^-22 (tie->even up)
        send_fpu(INST_FPU_ADD, FMT_S,   RUP, F_1, F_N1, F_EPS24, F_EPS24, 0, 0, 2'b11, 1, FR+5, 0);        // 1+2^-23 ; -(1-2^-24) exact
        send_fpu(INST_FPU_ADD, FMT_S,   RTZ, F_1, F_N1, F_EPS24, F_NEPS24, 0, 0, 2'b11, 0, FR+6, 0);       // 1 ; -1
        send_fpu(INST_FPU_ADD, FMT_S,   RMM, F_1, F_0P1, F_EPS24, F_0P3, 0, 0, 2'b11, 0, FR+7, 0);         // 1+2^-23 (ties away) ; ~0.4
        send_fpu(INST_FPU_ADD, FMT_S,   RNE, F_PINF, F_PINF, F_NINF, F_1, 0, 0, 2'b11, 1, FR+8, 0);        // qNaN NV ; +inf
        send_fpu(INST_FPU_ADD, FMT_S,   RNE, F_QNANP, F_SNAN, F_1, F_1, 0, 0, 2'b11, 0, FR+9, 0);          // canonical qNaN ; qNaN NV
        send_fpu(INST_FPU_ADD, FMT_S,   RNE, F_P0, F_N0, F_N0, F_N0, 0, 0, 2'b11, 0, FR+10, 0);            // +0 ; -0
        send_fpu(INST_FPU_ADD, FMT_SUB, RNE, F_P0, F_N0, F_P0, F_P0, 0, 0, 2'b11, 1, FR+11, 0);            // +0 ; -0
        send_fpu(INST_FPU_ADD, FMT_S,   RNE, F_MAXNRM, F_NMAXNRM, F_MAXNRM, F_NMAXNRM, 0, 0, 2'b11, 0, FR+12, 0); // +inf OF NX ; -inf
        send_fpu(INST_FPU_ADD, FMT_S,   RTZ, F_MAXNRM, F_MAXNRM, F_MAXNRM, F_1, 0, 0, 2'b11, 0, FR+13, 0);   // MAXNRM (RTZ overflow) ; MAXNRM NX
        send_fpu(INST_FPU_ADD, FMT_S,   RNE, F_MINSUB, F_MAXSUB, F_MINSUB, F_MINSUB, 0, 0, 2'b11, 1, FR+14, 0); // 2^-148 ; MINNRM (subnormal -> normal)
        send_fpu(INST_FPU_ADD, FMT_S,   RNE, F_MINNRM, F_1E20, F_NSUB, F_1EN20, 0, 0, 2'b11, 0, FR+15, 0);   // 2^-127 (normal -> subnormal) ; 1e20 NX
        send_fpu(INST_FPU_ADD, FMT_SUB, RNE, F_1, F_PI, F_1P, F_3, 0, 0, 2'b01, 0, FR+16, 0);              // lane0 only: -2^-23
        send_fpu(INST_FPU_ADD, FMT_S,   RDN, F_0P1, F_12345, F_0P3, F_0P1, 0, 0, 2'b11, 1, FR+17, 0);      // ~0.4 RDN ; 12345.78 RDN
        // ---- FMUL ----
        send_fpu(INST_FPU_MUL, FMT_S,   RNE, F_2, F_N1P5, F_3, F_2, 0, 0, 2'b11, 0, FR+18, 0);             // 6 ; -3
        send_fpu(INST_FPU_MUL, FMT_S,   RNE, F_1E38, F_1E38, F_10, 32'hC120_0000, 0, 0, 2'b11, 0, FR+19, 0); // +inf OF NX ; -inf
        send_fpu(INST_FPU_MUL, FMT_S,   RTZ, F_1E38, F_1E20, F_10, F_1E20, 0, 0, 2'b11, 1, FR+20, 0);       // MAXNRM OF NX ; MAXNRM
        send_fpu(INST_FPU_MUL, FMT_S,   RNE, F_MINSUB, F_MINNRM, F_HALF, F_HALF, 0, 0, 2'b11, 0, FR+21, 0);  // +0 UF NX ; 2^-127 exact
        send_fpu(INST_FPU_MUL, FMT_S,   RUP, F_MINSUB, F_NMINSUB, F_HALF, F_HALF, 0, 0, 2'b11, 0, FR+22, 0); // MINSUB UF NX ; -0
        send_fpu(INST_FPU_MUL, FMT_S,   RNE, F_P0, F_PINF, F_PINF, F_N2, 0, 0, 2'b11, 1, FR+23, 0);        // qNaN NV ; -inf
        send_fpu(INST_FPU_MUL, FMT_S,   RNE, F_N0, F_0P1, 32'h40A0_0000, F_3, 0, 0, 2'b11, 0, FR+24, 0);   // -0 ; ~0.3 NX
        send_fpu(INST_FPU_MUL, FMT_S,   RNE, F_SUB, F_MAXSUB, F_2, F_MAXSUB, 0, 0, 2'b11, 0, FR+25, 0);     // MINNRM exact ; +0 UF NX
        send_fpu(INST_FPU_MUL, FMT_S,   RNE, F_PI, F_1P, F_PI, F_1P, 0, 0, 2'b11, 1, FR+26, 0);            // ~9.8696 ; 1+2^-22 NX
        send_fpu(INST_FPU_MUL, FMT_S,   RNE, F_QNAN, F_SNAN2, F_1, F_PINF, 0, 0, 2'b11, 0, FR+27, 0);      // qNaN ; qNaN NV
        // ---- FMADD / FMSUB / FNMADD / FNMSUB ----
        send_fpu(INST_FPU_MADD,  FMT_S,   RNE, F_2, F_HALF, F_3, F_4, F_1, F_N2, 2'b11, 0, FR+28, 0);       // 7 ; +0
        send_fpu(INST_FPU_MADD,  FMT_SUB, RNE, F_2, F_1, F_3, F_1, F_1, F_1P, 2'b11, 1, FR+29, 0);          // 5 ; -2^-23
        send_fpu(INST_FPU_NMADD, FMT_S,   RNE, F_2, F_N2, F_3, F_3, F_1, F_N1, 2'b11, 0, FR+30, 0);         // -7 ; 7
        send_fpu(INST_FPU_NMADD, FMT_SUB, RNE, F_2, F_2, F_3, F_3, F_1, F_6, 2'b11, 0, FR+31, 0);           // -5 ; +0
        send_fpu(INST_FPU_MADD,  FMT_S,   RNE, F_PINF, F_PINF, F_P0, F_2, F_1, F_NINF, 2'b11, 1, FR+0, 0); // qNaN NV ; qNaN NV
        send_fpu(INST_FPU_MADD,  FMT_S,   RNE, F_1E20, F_1E20, F_1E20, F_1E20, F_1, F_NINF, 2'b11, 0, FR+1, 0); // +inf OF NX ; -inf (exact product, no NV)
        send_fpu(INST_FPU_MADD,  FMT_S,   RNE, F_MINSUB, F_MINNRM, F_MINSUB, F_HALF, F_1, F_SUB, 2'b11, 0, FR+2, 0); // 1 NX ; MINNRM exact
        send_fpu(INST_FPU_MADD,  FMT_SUB, RTZ, F_PI, F_10, F_0P1, F_0P1, F_0P3, F_1, 2'b11, 1, FR+3, 0);   // pi*0.1-0.3 ; 10*0.1f-1 (fused, ~1.49e-8)
        send_fpu(INST_FPU_NMADD, FMT_S,   RDN, F_PI, F_QNAN, F_2, F_1, F_1, F_1, 2'b11, 0, FR+4, 0);       // -(2pi)-1 RDN ; qNaN
        wait (frm_wr_target >= 0 && n_commit2 >= frm_wr_target);                                           // FRM(warp1) = RDN is in fcsr
        send_fpu(INST_FPU_MADD,  FMT_S,   DYN, F_1, F_N1, F_1, F_1, F_EPS24, F_NEPS24, 2'b11, 1, FR+5, 0); // DYN=RDN: 1 NX ; -(1+2^-23)
        send_fpu(INST_FPU_MADD,  FMT_S,   DYN, F_1, F_N1, F_1, F_1, F_EPS24, F_NEPS24, 2'b11, 0, FR+6, 0); // DYN=RNE (warp 0): 1 ; -1
        send_fpu(INST_FPU_MADD,  FMT_S,   RNE, F_1, F_3, F_1, F_3, F_1, F_1, 2'b10, 0, FR+7, 0);           // lane1 only: 10
        // ---- FDIV / FSQRT (17-cycle), interleaved with NCP ops so results return out of order ----
        send_fpu(INST_FPU_DIV,  FMT_S, RNE, F_1, F_10, F_3, F_4, 0, 0, 2'b11, 0, FR+8, 0);                // 0x3EAAAAAB NX ; 2.5
        fpu_bp_t0 = cyc + 1;                                                                               // hold commit_if[3].ready low 12 cycles
        send_fpu(INST_FPU_MISC, FMT_S, M_SGNJ, F_1, F_N1P5, F_N2, F_2, 0, 0, 2'b11, 1, FR+9, 0);           // -1 ; 1.5  (returns before the FDIV)
        send_fpu(INST_FPU_DIV,  FMT_S, RTZ, F_1, F_2, F_3, F_3, 0, 0, 2'b11, 0, FR+10, 0);                 // 0x3EAAAAAA ; 2/3 RTZ
        send_fpu(INST_FPU_MISC, FMT_S, M_CLASS, F_NINF, F_N1, 0, 0, 0, 0, 2'b11, 0, 12, 0);                // 0x001 ; 0x002
        send_fpu(INST_FPU_DIV,  FMT_S, RDN, F_1, F_N1, F_3, F_3, 0, 0, 2'b11, 1, FR+11, 0);                // 0x3EAAAAAA ; 0xBEAAAAAB
        send_fpu(INST_FPU_DIV,  FMT_S, RNE, F_1, F_N1, F_P0, F_P0, 0, 0, 2'b11, 0, FR+12, 0);              // +inf DZ ; -inf DZ
        send_fpu(INST_FPU_MISC, FMT_S, M_CLASS, F_NMINSUB, F_N0, 0, 0, 0, 0, 2'b11, 1, 13, 0);             // 0x004 ; 0x008
        send_fpu(INST_FPU_DIV,  FMT_S, RNE, F_P0, F_PINF, F_P0, F_PINF, 0, 0, 2'b11, 0, FR+13, 0);         // qNaN NV ; qNaN NV
        send_fpu(INST_FPU_DIV,  FMT_S, RNE, F_NINF, F_2, F_2, F_PINF, 0, 0, 2'b11, 0, FR+14, 0);           // -inf ; +0
        send_fpu(INST_FPU_MISC, FMT_S, M_CLASS, F_P0, F_SUB, 0, 0, 0, 0, 2'b11, 0, 14, 0);                 // 0x010 ; 0x020
        send_fpu(INST_FPU_DIV,  FMT_S, RNE, F_MINNRM, F_1E38, F_4, F_0P1, 0, 0, 2'b11, 1, FR+15, 0);       // 2^-128 subnormal ; +inf OF NX
        send_fpu(INST_FPU_DIV,  FMT_S, RNE, F_QNAN, F_1, F_1, F_SNAN, 0, 0, 2'b11, 0, FR+16, 0);           // qNaN ; qNaN NV
        send_fpu(INST_FPU_MISC, FMT_S, M_CLASS, F_1, F_PINF, 0, 0, 0, 0, 2'b11, 0, 15, 0);                 // 0x040 ; 0x080
        send_fpu(INST_FPU_DIV,  FMT_S, RNE, F_P0, F_SUB, 32'hC0A0_0000, F_2, 0, 0, 2'b11, 0, FR+17, 0);    // -0 ; 2^-128 exact
        send_fpu(INST_FPU_DIV,  FMT_S, RNE, F_1, F_100, F_N0, F_7, 0, 0, 2'b11, 1, FR+18, 0);              // -inf DZ ; 14.2857 NX
        send_fpu(INST_FPU_MISC, FMT_S, M_CLASS, F_SNAN, F_QNAN, 0, 0, 0, 0, 2'b11, 0, 16, 0);              // 0x100 ; 0x200
        send_fpu(INST_FPU_SQRT, FMT_S, RNE, F_4, F_2, 0, 0, 0, 0, 2'b11, 0, FR+19, 0);                     // 2 ; sqrt2 NX
        send_fpu(INST_FPU_SQRT, FMT_S, RNE, F_N1, F_N0, 0, 0, 0, 0, 2'b11, 0, FR+20, 0);                   // qNaN NV ; -0
        send_fpu(INST_FPU_MISC, FMT_S, M_MVXW, 32'hDEAD_BEEF, F_N0, 0, 0, 0, 0, 2'b11, 1, 17, 0);          // 0xDEADBEEF ; 0x80000000
        send_fpu(INST_FPU_SQRT, FMT_S, RNE, F_PINF, F_P0, 0, 0, 0, 0, 2'b11, 1, FR+21, 0);                 // +inf ; +0
        send_fpu(INST_FPU_SQRT, FMT_S, RNE, F_SUB, F_MINSUB, 0, 0, 0, 0, 2'b11, 0, FR+22, 0);              // 2^-63.5 NX ; 2^-74.5 NX
        send_fpu(INST_FPU_MISC, FMT_S, M_MVWX, 32'h1234_5678, 32'hFFFF_FFFF, 0, 0, 0, 0, 2'b11, 0, FR+23, 0); // 0x12345678 ; 0xFFFFFFFF
        send_fpu(INST_FPU_SQRT, FMT_S, RTZ, F_0P1, F_1E38, 0, 0, 0, 0, 2'b11, 0, FR+24, 0);                // sqrt(0.1) RTZ ; 1e19 RTZ
        send_fpu(INST_FPU_SQRT, FMT_S, RUP, F_2, F_PI, 0, 0, 0, 0, 2'b11, 1, FR+25, 0);                    // sqrt2 RUP ; sqrt(pi) RUP
        send_fpu(INST_FPU_SQRT, FMT_S, RNE, F_QNAN, F_NINF, 0, 0, 0, 0, 2'b11, 0, FR+26, 0);               // qNaN ; qNaN NV
        send_fpu(INST_FPU_SQRT, FMT_S, RNE, F_100, 32'h4110_0000, 0, 0, 0, 0, 2'b01, 0, FR+27, 0);         // lane0 only: 10
        send_fpu(INST_FPU_DIV,  FMT_S, RNE, F_1, F_7, F_3, F_2, 0, 0, 2'b10, 1, FR+28, 0);                 // lane1 only: 3.5
        send_fpu(INST_FPU_SQRT, FMT_S, RNE, F_1P, F_0P3, 0, 0, 0, 0, 2'b11, 0, FR+29, 0);                  // 1 NX (below the tie) ; sqrt(0.3)
        // ---- FCVT: float -> int (F2I signed, F2U unsigned) with every rounding mode; int -> float ----
        send_fpu(INST_FPU_F2I, FMT_S, RNE, F_2P5, F_N2P5, 0, 0, 0, 0, 2'b11, 0, 1, 0);                     // 2 NX ; -2 NX
        send_fpu(INST_FPU_F2I, FMT_S, RMM, F_2P5, F_N2P5, 0, 0, 0, 0, 2'b11, 0, 2, 0);                     // 3 ; -3
        send_fpu(INST_FPU_F2I, FMT_S, RTZ, F_2P5, F_N2P5, 0, 0, 0, 0, 2'b11, 1, 3, 0);                     // 2 ; -2
        send_fpu(INST_FPU_F2I, FMT_S, RUP, F_2P5, F_N2P5, 0, 0, 0, 0, 2'b11, 0, 4, 0);                     // 3 ; -2
        send_fpu(INST_FPU_F2I, FMT_S, RDN, F_2P5, F_N2P5, 0, 0, 0, 0, 2'b11, 0, 5, 0);                     // 2 ; -3
        fpu_bp_t0 = cyc + 1;                                                                               // second backpressure window
        send_fpu(INST_FPU_F2I, FMT_S, RNE, F_3E9, F_N3E9, 0, 0, 0, 0, 2'b11, 1, 6, 0);                     // INT_MAX NV ; INT_MIN NV
        send_fpu(INST_FPU_F2I, FMT_S, RNE, F_QNAN, F_NINF, 0, 0, 0, 0, 2'b11, 0, 7, 0);                    // INT_MAX NV ; INT_MIN NV
        send_fpu(INST_FPU_F2I, FMT_S, RNE, F_2P31, F_N2P31, 0, 0, 0, 0, 2'b11, 0, 8, 0);                   // INT_MAX NV ; INT_MIN exact
        send_fpu(INST_FPU_F2I, FMT_S, RNE, F_MINSUB, F_N0P1, 0, 0, 0, 0, 2'b11, 1, 9, 0);                  // 0 NX ; 0 NX
        send_fpu(INST_FPU_F2U, FMT_S, RNE, F_3E9, F_N1, 0, 0, 0, 0, 2'b11, 0, 10, 0);                      // 3000000000 ; 0 NV
        send_fpu(INST_FPU_F2U, FMT_S, RNE, F_2P32, F_N0P1, 0, 0, 0, 0, 2'b11, 0, 11, 0);                   // UINT_MAX NV ; 0 NX
        send_fpu(INST_FPU_F2U, FMT_S, RUP, F_N0P1, F_0P1, 0, 0, 0, 0, 2'b11, 1, 12, 0);                    // 0 NX ; 1 NX
        send_fpu(INST_FPU_F2U, FMT_S, RNE, F_QNAN, F_PINF, 0, 0, 0, 0, 2'b11, 0, 13, 0);                   // UINT_MAX NV ; UINT_MAX NV
        send_fpu(INST_FPU_F2U, FMT_S, DYN, F_2P5, F_0P1, 0, 0, 0, 0, 2'b11, 1, 14, 0);                     // DYN=RDN: 2 NX ; 0 NX
        send_fpu(INST_FPU_I2F, FMT_S, RNE, 32'd7, 32'hFFFF_FFFF, 0, 0, 0, 0, 2'b11, 0, FR+15, 0);          // 7.0 ; -1.0
        send_fpu(INST_FPU_I2F, FMT_S, RNE, 32'h7FFF_FFFF, 32'h8000_0000, 0, 0, 0, 0, 2'b11, 0, FR+16, 0);  // 2^31 NX ; -2^31 exact
        send_fpu(INST_FPU_I2F, FMT_S, RTZ, 32'h7FFF_FFFF, 32'd16777217, 0, 0, 0, 0, 2'b11, 1, FR+17, 0);   // 0x4EFFFFFF NX ; 16777216 NX
        send_fpu(INST_FPU_I2F, FMT_S, RUP, 32'd16777217, 32'hFEFF_FFFF, 0, 0, 0, 0, 2'b11, 0, FR+18, 0);   // 16777218 ; -16777216
        send_fpu(INST_FPU_I2F, FMT_S, RMM, 32'd16777217, 32'd16777219, 0, 0, 0, 0, 2'b11, 0, FR+19, 0);    // 16777218 (tie away) ; 16777220
        send_fpu(INST_FPU_U2F, FMT_S, RNE, 32'hFFFF_FFFF, 32'h8000_0000, 0, 0, 0, 0, 2'b11, 1, FR+20, 0);  // 2^32 NX ; 2^31 exact
        send_fpu(INST_FPU_U2F, FMT_S, RNE, 32'd0, 32'd1, 0, 0, 0, 0, 2'b11, 0, FR+21, 0);                  // +0 ; 1.0
        send_fpu(INST_FPU_U2F, FMT_S, DYN, 32'hFFFF_FFFF, 32'd3000000000, 0, 0, 0, 0, 2'b11, 1, FR+22, 0); // DYN=RDN: 0x4F7FFFFF NX ; 3e9 RDN
        send_fpu(INST_FPU_I2F, FMT_S, RNE, 32'd12345, 32'd99, 0, 0, 0, 0, 2'b01, 0, FR+23, 0);             // lane0 only: 12345.0
        // ---- NCP core: FMIN/FMAX, FSGNJ*, FEQ/FLT/FLE (FCLASS/FMV above) ----
        send_fpu(INST_FPU_MISC, FMT_S, M_MIN,   F_1, F_P0, F_2, F_N0, 0, 0, 2'b11, 0, FR+24, 0);           // 1 ; -0
        send_fpu(INST_FPU_MISC, FMT_S, M_MAX,   F_1, F_N0, F_2, F_P0, 0, 0, 2'b11, 1, FR+25, 0);           // 2 ; +0
        send_fpu(INST_FPU_MISC, FMT_S, M_MIN,   F_QNAN, F_SNAN, F_1, F_1, 0, 0, 2'b11, 0, FR+26, 0);       // 1 ; 1 NV
        send_fpu(INST_FPU_MISC, FMT_S, M_MAX,   F_QNAN, F_NINF, F_QNANP, 32'h40A0_0000, 0, 0, 2'b11, 0, FR+27, 0); // canonical qNaN ; 5
        send_fpu(INST_FPU_MISC, FMT_S, M_MIN,   F_NINF, F_SUB, F_NMAXNRM, F_MINSUB, 0, 0, 2'b11, 1, FR+28, 0); // -inf ; MINSUB
        send_fpu(INST_FPU_MISC, FMT_S, M_SGNJN, F_1, F_1, F_N2, F_2, 0, 0, 2'b11, 0, FR+29, 0);            // 1 ; -1
        send_fpu(INST_FPU_MISC, FMT_S, M_SGNJX, F_N1, F_1, F_N2, F_N2, 0, 0, 2'b11, 0, FR+30, 0);          // 1 ; -1
        send_fpu(INST_FPU_MISC, FMT_S, M_SGNJ,  F_QNANP, F_SUB, F_N1, F_N0, 0, 0, 2'b11, 1, FR+31, 0);     // 0xFFC12345 ; -2^-127
        send_fpu(INST_FPU_CMP,  FMT_S, C_EQ, F_1, F_P0, F_1, F_N0, 0, 0, 2'b11, 0, 18, 0);                 // 1 ; 1
        send_fpu(INST_FPU_CMP,  FMT_S, C_EQ, F_QNAN, F_SNAN, F_1, F_1, 0, 0, 2'b11, 0, 19, 0);             // 0 ; 0 NV (signalling only)
        send_fpu(INST_FPU_CMP,  FMT_S, C_LT, F_1, F_2, F_2, F_1, 0, 0, 2'b11, 1, 20, 0);                   // 1 ; 0
        send_fpu(INST_FPU_CMP,  FMT_S, C_LT, F_QNAN, F_NINF, F_1, F_NMAXNRM, 0, 0, 2'b11, 0, 21, 0);       // 0 NV ; 1
        send_fpu(INST_FPU_CMP,  FMT_S, C_LE, F_1, F_N0, F_1, F_P0, 0, 0, 2'b11, 0, 22, 0);                 // 1 ; 1
        send_fpu(INST_FPU_CMP,  FMT_S, C_LE, F_QNAN, F_2, F_QNAN, F_1, 0, 0, 2'b11, 1, 23, 0);             // 0 NV ; 0
        send_fpu(INST_FPU_CMP,  FMT_S, C_LE, F_SUB, F_N1, F_MINSUB, F_N2, 0, 0, 2'b11, 0, 24, 0);          // 0 ; 0
        send_fpu(INST_FPU_CMP,  FMT_S, C_LT, F_1, F_N2, F_1, F_N1, 0, 0, 2'b10, 0, 25, 0);                 // lane1 only: 1
        done_fpu = 1;
    end
`endif

    // ------------------------------------------------------------------
    // end of test: all streams sent and every instruction committed
    // ------------------------------------------------------------------
    initial begin
`ifdef VX_CFG_EXT_F_DISABLE
        wait (done_alu && done_lsu && done_sfu);
        wait (n_commit0 == n_sent0 && n_commit1 == n_sent1 && n_commit2 == n_sent2 && q_rd == q_wr);
`else
        wait (done_alu && done_lsu && done_sfu && done_fpu);
        wait (n_commit0 == n_sent0 && n_commit1 == n_sent1 && n_commit2 == n_sent2 && n_commit3 == n_sent3 && q_rd == q_wr);
`endif
        repeat (12) @(negedge clk);
        #2;
        $fclose(fd);
`ifdef VX_CFG_EXT_F_DISABLE
        $display("ORACLE_DONE cycles=%0d sent=%0d/%0d/%0d commits=%0d/%0d/%0d lsu_rd=%0d lsu_wr=%0d lsu_rsp=%0d",
                 cyc, n_sent0, n_sent1, n_sent2, n_commit0, n_commit1, n_commit2, n_req_rd, n_req_wr, n_rsp);
`else
        $display("ORACLE_DONE cycles=%0d sent=%0d/%0d/%0d/%0d commits=%0d/%0d/%0d/%0d lsu_rd=%0d lsu_wr=%0d lsu_rsp=%0d",
                 cyc, n_sent0, n_sent1, n_sent2, n_sent3, n_commit0, n_commit1, n_commit2, n_commit3, n_req_rd, n_req_wr, n_rsp);
`endif
        $finish;
    end

    // watchdog
    initial begin
        #40000;
`ifdef VX_CFG_EXT_F_DISABLE
        $display("ORACLE_TIMEOUT cycles=%0d sent=%0d/%0d/%0d commits=%0d/%0d/%0d q=%0d/%0d",
                 cyc, n_sent0, n_sent1, n_sent2, n_commit0, n_commit1, n_commit2, q_rd, q_wr);
`else
        $display("ORACLE_TIMEOUT cycles=%0d sent=%0d/%0d/%0d/%0d commits=%0d/%0d/%0d/%0d q=%0d/%0d done=%0d%0d%0d%0d",
                 cyc, n_sent0, n_sent1, n_sent2, n_sent3, n_commit0, n_commit1, n_commit2, n_commit3, q_rd, q_wr,
                 done_alu, done_lsu, done_sfu, done_fpu);
`endif
        $fclose(fd);
        $finish;
    end
endmodule
