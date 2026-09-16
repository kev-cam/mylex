# Dump the physical isochronic-fork set from the routed alu_top DB:
# for every SIGNAL net with fanout>=2, the driver output pin + receiver input
# pins with real placed coordinates (DBU). Feeds the layopt fork-balance probe.
# Clock/reset/power nets are excluded here (they are skew-distribution, not
# isochronic orphan forks — same split constraints.py makes with CTRL_PINS).
set P /home/claude/tools/orfs-sky130hd
set D [file dirname [file normalize [info script]]]
set ODB [expr {[info exists ::env(ODB)] ? $::env(ODB) : "$D/alu_top.odb"}]
set OUT [expr {[info exists ::env(OUT)] ? $::env(OUT) : "$D/alu_forks_phys.json"}]
read_lef $P/sky130_fd_sc_hd.tlef
read_lef $P/sky130_fd_sc_hd_merged.lef
read_liberty $P/sky130_fd_sc_hd__tt_025C_1v80.lib
read_db $ODB
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
# JSON-escape: backslash first, then doublequote (Verilog escaped ids carry both)
proc jesc {s} { return [string map [list "\\" "\\\\" "\"" "\\\""] $s] }

set forks {}
foreach net [$block getNets] {
    if {[$net isSpecial]} continue
    if {[$net getSigType] ne "SIGNAL"} continue
    set drv ""; set rcvs {}
    foreach it [$net getITerms] {
        set io [$it getIoType]
        set xy [$it getAvgXY]
        if {![lindex $xy 0]} continue
        set x [lindex $xy 1]; set y [lindex $xy 2]
        set inst [[$it getInst] getName]
        set pin  [[$it getMTerm] getName]
        if {$io eq "OUTPUT"} {
            set drv [list $inst $pin $x $y]
        } elseif {$io eq "INPUT"} {
            lappend rcvs [list $inst $pin $x $y]
        }
    }
    if {$drv eq "" || [llength $rcvs] < 2} continue
    lappend forks [list [$net getName] $drv $rcvs]
}
# sort by fanout desc
set forks [lsort -integer -decreasing -index 0 [lmap f $forks {list [llength [lindex $f 2]] $f}]]

set fh [open $OUT w]
puts $fh "\{ \"design\": \"alu_top\", \"dbu\": $dbu, \"n_forks\": [llength $forks], \"forks\": \["
set first 1
foreach entry $forks {
    set fo [lindex $entry 0]; set f [lindex $entry 1]
    set name [lindex $f 0]; set drv [lindex $f 1]; set rcvs [lindex $f 2]
    if {!$first} { puts $fh "," }; set first 0
    puts -nonewline $fh " \{ \"net\": \"[jesc $name]\", \"fanout\": $fo,"
    puts -nonewline $fh " \"driver\": \{ \"inst\": \"[jesc [lindex $drv 0]]\", \"pin\": \"[jesc [lindex $drv 1]]\", \"x\": [lindex $drv 2], \"y\": [lindex $drv 3] \},"
    puts -nonewline $fh " \"receivers\": \["
    set rf 1
    foreach r $rcvs {
        if {!$rf} { puts -nonewline $fh "," }; set rf 0
        puts -nonewline $fh " \{ \"inst\": \"[jesc [lindex $r 0]]\", \"pin\": \"[jesc [lindex $r 1]]\", \"x\": [lindex $r 2], \"y\": [lindex $r 3] \}"
    }
    puts -nonewline $fh " \] \}"
}
puts $fh " \] \}"
close $fh
puts "dump_forks: wrote $OUT  ([llength $forks] signal forks, fanout>=2)"
exit
