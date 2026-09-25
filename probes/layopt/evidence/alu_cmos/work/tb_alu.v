// alu_top gate-level activity testbench.
// ex_data field map verified against /usr/local/src/mylex/nulex/mapper/alu/work/alu.v:3862-4128
//   [273:223] header(51b): tmask=[270:269], PC=[265:236]
//   [222:219] alu_op/br_op   [216] add_in1<=PC   [215] in2<=imm
//   [213:212] ALU type (0=ARITH,1=BRANCH,2=MULDIV,3=OTHER)
//   [211:192] imm20          [191:128] alu_in1(2x32)
//   [127:64]  alu_in2(2x32)  [63:0] alu_in3(2x32)
// Stimulus is applied on negedge and the valid/ready handshake is evaluated on
// negedge (a full half-cycle after the launching posedge) so the zero-delay gate
// netlist has fully settled before it is sampled.
`timescale 1ns/1ps
module tb;
  localparam integer NOPS = `NOPS;
  reg clk=0, reset=1, ex_valid=0, rs_ready=1;
  reg [273:0] ex_data = 274'b0;
  wire ex_ready, rs_valid, br_valid, br_taken, br_is_trap, br_is_mret;
  wire [114:0] rs_data; wire [29:0] br_dest; wire [3:0] br_trap_cause; wire [0:0] br_wid;

  alu_top dut(.clk(clk), .reset(reset), .ex_valid(ex_valid), .ex_ready(ex_ready),
              .ex_data(ex_data), .rs_valid(rs_valid), .rs_ready(rs_ready), .rs_data(rs_data),
              .br_valid(br_valid), .br_wid(br_wid), .br_taken(br_taken), .br_dest(br_dest),
              .br_is_trap(br_is_trap), .br_is_mret(br_is_mret), .br_trap_cause(br_trap_cause));

  always #(`HALFP) clk = ~clk;

  integer seed = 32'h1234_5678;
  integer nsent = 0, ndone = 0, cyc = 0;
  reg [31:0] a;

  // Realistic GPU-ALU operand mix: mostly small ints / sign-extended, some
  // addresses, some full range. NOT uniform 32-bit (that pins alpha at 0.5).
  function [31:0] operand;
    input integer dummy;
    reg [2:0] cls;
    begin
      cls = $random(seed);
      case (cls)
        3'd0, 3'd1, 3'd2: operand = $random(seed) & 32'h0000_00FF;
        3'd3:             operand = $random(seed) | 32'hFFFF_FF00;
        3'd4, 3'd5:       operand = 32'h8000_0000 + ($random(seed) & 32'h0000_FFFF);
        default:          operand = $random(seed);
      endcase
    end
  endfunction

  task new_vector;
    begin
      a = operand(0);
      ex_data = 274'b0;
      ex_data[191:160] = a;
      ex_data[159:128] = operand(0);
      ex_data[127:96]  = operand(0);
      ex_data[95:64]   = operand(0);
      ex_data[63:32]   = operand(0);
      ex_data[31:0]    = operand(0);
      ex_data[211:192] = $random(seed);
      ex_data[213:212] = nsent[1:0];          // cycle the 4 ALU types
      ex_data[216:215] = $random(seed);
      ex_data[222:219] = nsent[3:0] ^ a[3:0]; // sweep the 16 opcodes
      // randomise the WHOLE 51-bit header [273:223] (uuid/wid/tmask/PC/wb/rd/...)
      // then force tmask=11 so both lanes stay active. Leaving the rest of the
      // header at 0 held ex_data[266] low, which pins br_valid deasserted and
      // leaves 17 of the 188 flops static.
      ex_data[273:242] = $random(seed);
      ex_data[241:223] = $random(seed);
      ex_data[270:269] = 2'b11;               // both lanes active
    end
  endtask

  // free-running consumer backpressure: ~1 cycle in 16, INDEPENDENT of the
  // producer's progress (gating this on the op index deadlocks the handshake).
  always @(negedge clk) begin
    cyc <= cyc + 1;
    rs_ready <= ((cyc % 16) != 7);
  end

  // producer
  always @(negedge clk) begin
    if (!reset) begin
      if (!ex_valid || ex_ready) begin        // previous beat was accepted
        if (ex_valid && ex_ready) nsent <= nsent + 1;
        if (nsent < NOPS) begin new_vector(); ex_valid <= 1'b1; end
        else ex_valid <= 1'b0;
      end
    end
  end

  initial begin
    $dumpfile(`VCDF);
    $dumpvars(0, tb.dut);
    repeat (4) @(posedge clk);
    reset = 0;
    wait (nsent >= NOPS);
    repeat (16) @(posedge clk);
    $display("TB: sent %0d ops in %0d cycles (%.2f cyc/op)", nsent, cyc, cyc*1.0/nsent);
    $finish;
  end

  // watchdog -- never spin silently again
  initial begin
    #(`HALFP*2*(NOPS*8 + 200));
    $display("TB WATCHDOG: DEADLOCK. nsent=%0d/%0d cyc=%0d ex_valid=%b ex_ready=%b rs_ready=%b rs_valid=%b",
             nsent, NOPS, cyc, ex_valid, ex_ready, rs_ready, rs_valid);
    $fatal;
  end
endmodule
