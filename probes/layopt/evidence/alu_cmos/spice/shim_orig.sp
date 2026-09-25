* EXACT copy of the campaign's existing shim (/usr/local/src/stat-sim/qal/sg13lv_compat.sp):
* junction geometry ad/as/pd/ps accepted but NOT forwarded to the device.
.subckt sg13_lv_nmos d g s b l=0.13u w=0.15u ng=1 ad=0 as=0 pd=0 ps=0 m=1 trise=0
M1 d g s b sg13g2_nmos W={w} L={l}
.ends
.subckt sg13_lv_pmos d g s b l=0.13u w=0.15u ng=1 ad=0 as=0 pd=0 ps=0 m=1 trise=0
M1 d g s b sg13g2_pmos W={w} L={l}
.ends
