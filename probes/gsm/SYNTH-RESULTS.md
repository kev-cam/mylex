# Baseline Yosys synthesis of sv2v-flattened Vortex (tinygpu, XLEN=32), 2026-09-03
Yosys 0.68+ (0bf55a858), scripts synth_alu.ys / synth_exec.ys:
read_verilog -sv; hierarchy; proc; flatten; opt -full; synth -flatten; abc -g AND,NAND,OR,NOR,XOR,XNOR,MUX

| design | comb. 2-input gates | flops | notes |
|---|---|---|---|
| alu_top (VX_alu_int, 2 lanes) | 4,582 (NAND 1701, MUX 865, AND 790, OR 384, ORNOT 240, ANDNOT 167, NOR 162, XNOR 130, XOR 121, NOT 22) | 188 (DFFE 151, DFF 35, SDFF 2) | |
| exec_top (VX_execute Tier A: ALU+MULDIV, LSU, SFU) | 26,181 (NAND 10874, XOR 5045, AND 4393, MUX 2847, OR 1152, XNOR 714, ORNOT 455, ANDNOT 388, NOR 254, NOT 59) | 3,696 (DFFE 3432, DFF 140, SDFFE 84, SDFFCE 30, SDFF 10) | |

Artifacts: alu.baseline.il / exec.baseline.il (post-proc RTLIL), *.gates.il and *.gates.v (mapped).
This is the netlist shape the P3 NCL mapper consumes (2-input gates + flops); NCL_D dual-rail expansion
would roughly double the combinational gate count before completion detection is added.

## gen_statemachine (sv2ghdl/yosys, pinned Yosys bd5c524d = master 2026-08-13, pre "log: convert all to sinks")
| design | comb cells | registers | time | output |
|---|---|---|---|---|
| alu_top | 189 | 2 | 0.5 s | alu.c 446 KB |
| exec_top (Tier A) | 1092 | 66 | 3.1 s | exec.c 4.4 MB |
