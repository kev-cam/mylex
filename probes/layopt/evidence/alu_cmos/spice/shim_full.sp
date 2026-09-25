* IHP stdcell device -> PSP103 shim, FORWARDING junction geometry (ad/as/pd/ps).
* The campaign's existing shim (/usr/local/src/stat-sim/qal/sg13lv_compat.sp) drops
* ad/as/pd/ps, which removes drain/source junction capacitance -- a real part of a
* small gate's internal switching energy. This version forwards it.
.subckt sg13_lv_nmos d g s b l=0.13u w=0.15u ng=1 ad=0 as=0 pd=0 ps=0 m=1 trise=0
M1 d g s b sg13g2_nmos W={w} L={l} AD={ad} AS={as} PD={pd} PS={ps}
.ends
.subckt sg13_lv_pmos d g s b l=0.13u w=0.15u ng=1 ad=0 as=0 pd=0 ps=0 m=1 trise=0
M1 d g s b sg13g2_pmos W={w} L={l} AD={ad} AS={as} PD={pd} PS={ps}
.ends
