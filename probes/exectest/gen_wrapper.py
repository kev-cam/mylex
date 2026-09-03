#!/usr/bin/env python3
"""Emit exec_top.sv: a flat-port wrapper around Vortex VX_execute.

Every interface port of VX_execute (hw/rtl/core/VX_execute.sv) is
instantiated here and each field is exposed as a packed flat port named
<if>_<idx>_<field> (or <if>_<field> for scalar interfaces).  Directions are
the modport VX_execute binds (see the DIRS table); struct-typed fields are
[$bits(type)-1:0] vectors with a type cast on the input side, as
probes/alutest/alu_top.sv does.  Nothing is tied off: the TB drives every
input.

Interface array sizes inside the wrapper are symbolic (NUM_EX_UNITS *
`VX_CFG_ISSUE_WIDTH, `VX_CFG_NUM_LSU_BLOCKS, `VX_CFG_NUM_ALU_BLOCKS); the
per-index port names need the numeric count, which is passed on the command
line (--num-ex-units 3 for Tier A: ALU, LSU, SFU; 4 with F enabled).  A
generate-time guard ($error) trips if the numbers disagree.

    python3 gen_wrapper.py --num-ex-units 3 -o exec_top.sv
"""
import argparse

# ---------------------------------------------------------------------------
# Field tables.  (name, direction-as-seen-from-VX_execute, width-expr, cast)
#   direction: 'in'  = the TB drives it (wrapper input),
#              'out' = VX_execute drives it (wrapper output)
#   cast: SV type to cast a packed input vector to (struct-typed fields), or None
# ---------------------------------------------------------------------------

# VX_lsu_sched_if.master  (interfaces/VX_lsu_sched_if.sv)
LSU_CLIENT = [
    ("req_valid", "out", "1",                        None),
    ("req_data",  "out", "$bits(lsu_req_data_t)",    None),
    ("req_ready", "in",  "1",                        None),
    ("rsp_valid", "in",  "1",                        None),
    ("rsp_data",  "in",  "$bits(lsu_rsp_data_t)",    "lsu_rsp_data_t"),
    ("rsp_ready", "out", "1",                        None),
]

# VX_dispatch_if.slave  (interfaces/VX_dispatch_if.sv)
DISPATCH = [
    ("valid", "in",  "1",                 None),
    ("data",  "in",  "$bits(dispatch_t)", "dispatch_t"),
    ("ready", "out", "1",                 None),
]

# VX_commit_if.master  (interfaces/VX_commit_if.sv)
COMMIT = [
    ("valid", "out", "1",               None),
    ("data",  "out", "$bits(commit_t)", None),
    ("ready", "in",  "1",               None),
]

# VX_sched_csr_if.slave  (interfaces/VX_sched_csr_if.sv; no VX_CFG_VM_ENABLE)
SCHED_CSR = [
    ("cycles",            "in",  "PERF_CTR_BITS",                                 None),
    ("instret",           "in",  "PERF_CTR_BITS",                                 None),
    ("active_warps",      "in",  "`VX_CFG_NUM_WARPS",                             None),
    ("thread_masks",      "in",  "`VX_CFG_NUM_WARPS*`VX_CFG_NUM_THREADS",         None),
    ("mscratch",          "in",  "`VX_CFG_MEM_ADDR_WIDTH",                        None),
    ("cta_csrs",          "in",  "$bits(cta_csrs_t)",                             "cta_csrs_t"),
    ("cta_lane",          "in",  "`VX_CFG_NUM_THREADS*$bits(cta_lane_t)",         None),
    ("csr_mstatus",       "in",  "`VX_CFG_XLEN",                                  None),
    ("csr_mtvec",         "in",  "`VX_CFG_XLEN",                                  None),
    ("csr_mepc",          "in",  "`VX_CFG_XLEN",                                  None),
    ("csr_mcause",        "in",  "`VX_CFG_XLEN",                                  None),
    ("csr_mtval",         "in",  "`VX_CFG_XLEN",                                  None),
    ("csr_rd_wid",        "out", "NW_WIDTH",                                      None),
    ("csr_rd_cta_id",     "out", "NCTA_WIDTH",                                    None),
    ("csr_wr_valid",      "out", "1",                                             None),
    ("csr_wr_wid",        "out", "NW_WIDTH",                                      None),
    ("csr_wr_data",       "out", "`VX_CFG_MEM_ADDR_WIDTH",                        None),
    ("trap_csr_wr_valid", "out", "1",                                             None),
    ("trap_csr_wr_addr",  "out", "`VX_CSR_ADDR_BITS",                             None),
    ("trap_csr_wr_data",  "out", "`VX_CFG_XLEN",                                  None),
]

# VX_branch_ctl_if.master  (interfaces/VX_branch_ctl_if.sv)
BRANCH_CTL = [
    ("valid",      "out", "1",        None),
    ("wid",        "out", "NW_WIDTH", None),
    ("taken",      "out", "1",        None),
    ("dest",       "out", "PC_BITS",  None),
    ("is_trap",    "out", "1",        None),
    ("is_mret",    "out", "1",        None),
    ("trap_cause", "out", "4",        None),
]

# VX_warp_ctl_if.master  (interfaces/VX_warp_ctl_if.sv)
WARP_CTL = [
    ("wspawn_valid",           "out", "1",                  None),
    ("tmc_valid",              "out", "1",                  None),
    ("split_valid",            "out", "1",                  None),
    ("sjoin_valid",            "out", "1",                  None),
    ("bar_valid",              "out", "1",                  None),
    ("wsync_valid",            "out", "1",                  None),
    ("wid",                    "out", "NW_WIDTH",           None),
    ("wspawn",                 "out", "$bits(wspawn_t)",    None),
    ("tmc",                    "out", "$bits(tmc_t)",       None),
    ("split",                  "out", "$bits(split_t)",     None),
    ("sjoin",                  "out", "$bits(join_t)",      None),
    ("bar",                    "out", "$bits(barrier_t)",   None),
    ("bar_addr",               "out", "BAR_ADDR_W",         None),
    ("dvstack_wid",            "out", "NW_WIDTH",           None),
    ("bar_phase",              "in",  "1",                  None),
    ("warp_pending_alm_empty", "in",  "`VX_CFG_NUM_WARPS",  None),
    ("lsu_sched_drained",      "in",  "1",                  None),
    ("dvstack_ptr",            "in",  "DV_STACK_SIZEW",     None),
]

# VX_dcr_csr_if: VX_execute takes it without a modport and hands it to
# VX_sfu_unit -> VX_csr_unit, which binds VX_dcr_csr_if.slave
# (core/VX_csr_unit.sv:34) and drives value/ready (:77-78).  So inside the
# execute stage valid/addr/mpm_class are inputs and value/ready are outputs.
DCR_CSR = [
    ("valid",     "in",  "1",                  None),
    ("addr",      "in",  "`VX_CSR_ADDR_BITS",  None),
    ("mpm_class", "in",  "8",                  None),
    ("value",     "out", "VX_DCR_DATA_WIDTH",  None),
    ("ready",     "out", "1",                  None),
]

# (interface type, instance name, symbolic array size or None, numeric count key, fields)
IFACES = [
    ("VX_lsu_sched_if", "lsu_client_if", "`VX_CFG_NUM_LSU_BLOCKS",              "num_lsu_blocks", LSU_CLIENT),
    ("VX_dispatch_if",  "dispatch_if",   "NUM_EX_UNITS * `VX_CFG_ISSUE_WIDTH",  "num_disp",       DISPATCH),
    ("VX_commit_if",    "commit_if",     "NUM_EX_UNITS * `VX_CFG_ISSUE_WIDTH",  "num_disp",       COMMIT),
    ("VX_sched_csr_if", "sched_csr_if",  None,                                  None,             SCHED_CSR),
    ("VX_branch_ctl_if","branch_ctl_if", "`VX_CFG_NUM_ALU_BLOCKS",              "num_alu_blocks", BRANCH_CTL),
    ("VX_warp_ctl_if",  "warp_ctl_if",   None,                                  None,             WARP_CTL),
    ("VX_dcr_csr_if",   "dcr_csr_if",    None,                                  None,             DCR_CSR),
]


def width_decl(w):
    return "" if w == "1" else f"[{w}-1:0] "


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--num-ex-units", type=int, default=3,
                    help="NUM_EX_UNITS from VX_gpu_pkg (3 = ALU,LSU,SFU; 4 with F)")
    ap.add_argument("--issue-width", type=int, default=1)
    ap.add_argument("--num-lsu-blocks", type=int, default=1)
    ap.add_argument("--num-alu-blocks", type=int, default=1)
    ap.add_argument("-o", "--output", default="exec_top.sv")
    a = ap.parse_args()

    counts = {
        "num_disp": a.num_ex_units * a.issue_width,
        "num_lsu_blocks": a.num_lsu_blocks,
        "num_alu_blocks": a.num_alu_blocks,
    }

    ports = []    # (dir, width, name)
    assigns = []  # SV assign lines
    decls = []    # interface instantiations

    for itype, iname, asize, ckey, fields in IFACES:
        if asize is None:
            decls.append(f"    {itype} {iname}();")
            idxs = [None]
        else:
            decls.append(f"    {itype} {iname}[{asize}]();")
            idxs = list(range(counts[ckey]))
        for idx in idxs:
            pfx = f"{iname}_{idx}_" if idx is not None else f"{iname}_"
            ref = f"{iname}[{idx}]" if idx is not None else iname
            for fname, d, w, cast in fields:
                pname = pfx + fname
                if d == "in":
                    ports.append(("input", w, pname))
                    rhs = f"{cast}'({pname})" if cast else pname
                    assigns.append(f"    assign {ref}.{fname} = {rhs};")
                else:
                    ports.append(("output", w, pname))
                    assigns.append(f"    assign {pname} = {ref}.{fname};")

    out = []
    out.append('`include "VX_define.vh"')
    out.append("// Flat-port wrapper around VX_execute so sv2v can flatten its interface ports.")
    out.append(f"// Generated by gen_wrapper.py --num-ex-units {a.num_ex_units} "
               f"--issue-width {a.issue_width} --num-lsu-blocks {a.num_lsu_blocks} "
               f"--num-alu-blocks {a.num_alu_blocks}")
    out.append("module exec_top import VX_gpu_pkg::*; #(")
    out.append("    parameter CORE_ID = 0")
    out.append(") (")
    out.append("    input  wire clk,")
    out.append("    input  wire reset,")
    n = len(ports)
    for i, (d, w, name) in enumerate(ports):
        comma = "," if i < n - 1 else ""
        out.append(f"    {d:6s} wire {width_decl(w)}{name}{comma}")
    out.append(");")
    out.append("")
    out.append("    // guard: the numeric counts baked into the port names must match the package")
    out.append(f"    if (NUM_EX_UNITS * `VX_CFG_ISSUE_WIDTH != {counts['num_disp']}) begin : g_chk_disp")
    out.append("        $error(\"exec_top: regenerate with --num-ex-units/--issue-width\");")
    out.append("    end")
    out.append(f"    if (`VX_CFG_NUM_LSU_BLOCKS != {counts['num_lsu_blocks']}) begin : g_chk_lsu")
    out.append("        $error(\"exec_top: regenerate with --num-lsu-blocks\");")
    out.append("    end")
    out.append(f"    if (`VX_CFG_NUM_ALU_BLOCKS != {counts['num_alu_blocks']}) begin : g_chk_alu")
    out.append("        $error(\"exec_top: regenerate with --num-alu-blocks\");")
    out.append("    end")
    out.append("")
    out.extend(decls)
    out.append("")
    out.extend(assigns)
    out.append("")
    out.append("    VX_execute #(")
    out.append('        .INSTANCE_ID ("exec0"),')
    out.append("        .CORE_ID     (CORE_ID)")
    out.append("    ) execute (")
    out.append("        .clk           (clk),")
    out.append("        .reset         (reset),")
    out.append("        .lsu_client_if (lsu_client_if),")
    out.append("        .dispatch_if   (dispatch_if),")
    out.append("        .commit_if     (commit_if),")
    out.append("        .sched_csr_if  (sched_csr_if),")
    out.append("        .branch_ctl_if (branch_ctl_if),")
    out.append("        .warp_ctl_if   (warp_ctl_if),")
    out.append("        .dcr_csr_if    (dcr_csr_if)")
    out.append("    );")
    out.append("endmodule")
    with open(a.output, "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"wrote {a.output}: {n} flat ports "
          f"({sum(1 for p in ports if p[0]=='input')} in, {sum(1 for p in ports if p[0]=='output')} out)")


if __name__ == "__main__":
    main()
