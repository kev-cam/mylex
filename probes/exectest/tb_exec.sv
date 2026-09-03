`include "VX_define.vh"
// Oracle testbench for exec_top (VX_execute, Tier A: ALU+MULDIV, LSU, SFU;
// F disabled).  Drives all three dispatch ports concurrently, models the LSU
// client memory on lsu_client_if, consumes commit_if with per-unit
// backpressure, and records every cycle's inputs and outputs to vectors.txt
// for cycle-accurate replay under NVC: inputs first as nibble-padded hex
// (they never carry x), then every output bit-exact (%b, one character per
// bit, so an x bit never masks its defined neighbours).  Sampling is 1 ns
// after each falling edge; every input changes only at the falling edge.
// The port map and the recorder are generated from ports_tierA.txt by
// gen_tb.py (this file is the template tb_exec.sv.in).
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
        .commit_if_0_valid(commit_if_0_valid),
        .commit_if_0_data(commit_if_0_data),
        .commit_if_0_ready(commit_if_0_ready),
        .commit_if_1_valid(commit_if_1_valid),
        .commit_if_1_data(commit_if_1_data),
        .commit_if_1_ready(commit_if_1_ready),
        .commit_if_2_valid(commit_if_2_valid),
        .commit_if_2_data(commit_if_2_data),
        .commit_if_2_ready(commit_if_2_ready),
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
        $fwrite(fd, "%h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b %b\n",
            {3'b0, reset},
            {3'b0, lsu_client_if_0_req_ready},
            {3'b0, lsu_client_if_0_rsp_valid},
            {2'b0, lsu_client_if_0_rsp_data},
            {3'b0, dispatch_if_0_valid},
            {3'b0, dispatch_if_0_data},
            {3'b0, dispatch_if_1_valid},
            {3'b0, dispatch_if_1_data},
            {3'b0, dispatch_if_2_valid},
            {3'b0, dispatch_if_2_data},
            {3'b0, commit_if_0_ready},
            {3'b0, commit_if_1_ready},
            {3'b0, commit_if_2_ready},
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
            {3'b0, lsu_client_if_0_req_data},
            {3'b0, lsu_client_if_0_rsp_ready},
            {3'b0, dispatch_if_0_ready},
            {3'b0, dispatch_if_1_ready},
            {3'b0, dispatch_if_2_ready},
            {3'b0, commit_if_0_valid},
            {2'b0, commit_if_0_data},
            {3'b0, commit_if_1_valid},
            {2'b0, commit_if_1_data},
            {3'b0, commit_if_2_valid},
            {2'b0, commit_if_2_data},
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
    always @(negedge clk) begin
        commit_if_0_ready <= !(cyc % 7 == 3 || cyc % 7 == 4);
        // LSU: periodic, plus a 14-cycle stall during the load burst so the
        // response buffers fill and lsu_client_if.rsp_ready is driven low
        commit_if_1_ready <= !(cyc % 5 == 1) && !(cyc >= 36 && cyc < 50);
        commit_if_2_ready <= !(cyc % 6 == 2 || cyc % 6 == 3);
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

    reg done_alu = 0, done_lsu = 0, done_sfu = 0;

    // ------------------------------------------------------------------
    // stimulus
    // ------------------------------------------------------------------
    initial begin
        tx_alu = '0; tx_lsu = '0; tx_sfu = '0; rsp_tx = '0;
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
        done_sfu = 1;
    end

    // ------------------------------------------------------------------
    // end of test: all streams sent and every instruction committed
    // ------------------------------------------------------------------
    initial begin
        wait (done_alu && done_lsu && done_sfu);
        wait (n_commit0 == n_sent0 && n_commit1 == n_sent1 && n_commit2 == n_sent2 && q_rd == q_wr);
        repeat (12) @(negedge clk);
        #2;
        $fclose(fd);
        $display("ORACLE_DONE cycles=%0d sent=%0d/%0d/%0d commits=%0d/%0d/%0d lsu_rd=%0d lsu_wr=%0d lsu_rsp=%0d",
                 cyc, n_sent0, n_sent1, n_sent2, n_commit0, n_commit1, n_commit2, n_req_rd, n_req_wr, n_rsp);
        $finish;
    end

    // watchdog
    initial begin
        #40000;
        $display("ORACLE_TIMEOUT cycles=%0d sent=%0d/%0d/%0d commits=%0d/%0d/%0d q=%0d/%0d",
                 cyc, n_sent0, n_sent1, n_sent2, n_commit0, n_commit1, n_commit2, q_rd, q_wr);
        $fclose(fd);
        $finish;
    end
endmodule
