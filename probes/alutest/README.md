# VX_alu_int through the in-house chain (2026-09-03)

`VX_alu_int` — Vortex's integer ALU, with SV interface ports, package
imports, packed structs and a string parameter — simulated under NVC and
proved **cycle-for-cycle equivalent** to Icarus on the same flattened Verilog:
`PASS: 42 cycles replayed, 27 results and 7 branch resolutions identical to
the vvp oracle`.

## Chain

    SV (interfaces, packages)  --sv2v-->  plain Verilog  --iverilog tgt-vhdl-->  VHDL  --nvc --std=2040-->  sim
                                  (oracle: iverilog/vvp on the same plain Verilog)

Icarus cannot parse SV interface ports at all, so sv2v (v0.0.13 release
binary, zachjs/sv2v) does the interface/package/struct flattening — the same
tool Vortex's own Yosys flow uses. sv2v *inlines* a module with interface
ports into its instantiator as a named generate block, so a flat-port wrapper
(`alu_top.sv`) is the top.

## Recipe

    # config headers: build axes are -D's, everything else comes from the TOML
    XLEN=32 python3 ci/gen_config.py --config VX_config.toml --output inc/VX_config.vh --format verilog
    XLEN=32 python3 ci/gen_config.py --config VX_types.toml  --output inc/VX_types.vh  --format verilog --resolved
    DEFS=$(cat defs.txt)     # tinygpu: 1 core, 2 warps x 2 threads, caches off, XLEN/FLEN=32
    R=hw/rtl
    sv2v --top=alu_top $DEFS -I$R -I$R/interfaces -I$R/libs -I$R/core -I$R/fpu -Ihw/dpi -Iinc \
         $R/VX_gpu_pkg.sv $R/interfaces/VX_{execute,result,branch_ctl}_if.sv $R/libs/*.sv $R/core/VX_alu_int.sv alu_top.sv -w alu.v
    iverilog -g2012 -tvhdl -psv2vhdl=1 -s alu_top -o alu.vhd alu.v
    nvc --std=2040 -a alu.vhd && nvc --std=2040 -e alu_top          # NVC_LIBPATH=<nvc>/build/lib

    # differential test: vvp records every cycle's inputs+outputs, NVC replays and compares
    sv2v --top=tb_alu $DEFS <same -I/-D> <same sources> alu_top.sv tb_alu.sv -w tb.v
    iverilog -g2012 -s tb_alu -o tb.vvp tb.v && LD_LIBRARY_PATH=<ivl>/_install/lib vvp -n tb.vvp   # -> vectors.txt
    nvc --std=2040 -a alu.vhd tb_alu_replay.vhd && nvc --std=2040 -e tb_alu_replay && nvc --std=2040 -r tb_alu_replay

`vectors.txt` here is the oracle output of this run (42 cycles, nibble-padded hex).

## Translator fixes this probe forced (iverilog fork, tgt-vhdl)

1. `scope.cc genvar_unique_suffix`: a string/real parameter in a generate
   scope aborted translation ("Only numeric genvars supported") — sv2v's
   inlined module block carries `localparam INSTANCE_ID = "alu0"`. Skipped.
2. Same function: only loop-iteration scopes (`name[idx]`) contribute to the
   instance-name suffix. Previously every numeric parameter of every generate
   scope was folded in — with the inlined ALU scope's ~40 localparams that
   produced 1.5 KB identifiers and a 2.1 MB VHDL file (now 163 KB).
3. `process.cc strip_local_vars_from_sensitivity`: a block-local reg inside
   `always @*` (sv2v's `sv2v_tmp_cast` temporaries) was listed in the VHDL
   sensitivity list but declared as a process variable — "no visible
   declaration". Repro: `repros/blk.v`; `repros/gv3.v` covers 1–2.

Stimulus covers ADD/ADDI/SUB/SLT/SLTU/AND/OR(I)/XOR/SLL/SRL/SRA(I)/LUI/AUIPC and
BEQ (taken and not), BNE, BLT, BGE, BLTU, JAL on two lanes, with a periodic
`rs_ready` backpressure pattern.
