# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""Technology descriptions: GDS layer map, connectivity stack, device
recognition, interconnect R/C, and the minimal rule table the moves respect.

sky130 numbers are the kestrel/stat-sim set (kestrel layout/parasitics.py,
stat-sim klayout2spef.py); IHP SG13G2 numbers are the ones stat-sim took from
sg13g2_tech.lef.  Both are analytic-estimate grade, not signoff.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

Layer = Tuple[int, int]


@dataclass
class Tech:
    name: str
    layers: Dict[str, Layer]                      # logical name -> (layer, datatype)
    routing: List[str]                            # conducting wire layers, bottom-up
    vias: List[Tuple[str, str, str]]              # (lower, cut, upper)
    diff: str = "diff"
    poly: str = "poly"
    nwell: str = "nwell"
    nsdm: Optional[str] = None                    # implant markers (optional)
    psdm: Optional[str] = None
    diff_contact: str = "licon"                   # cut layer landing on diffusion / poly
    nfet_model: str = "nfet"
    pfet_model: str = "pfet"
    rsh: Dict[str, float] = field(default_factory=dict)        # ohm/square
    rvia: Dict[str, float] = field(default_factory=dict)       # ohm per cut
    carea: Dict[str, float] = field(default_factory=dict)      # fF/um^2
    cfringe: Dict[str, float] = field(default_factory=dict)    # fF/um
    min_width: Dict[str, float] = field(default_factory=dict)  # um
    min_space: Dict[str, float] = field(default_factory=dict)  # um
    enclosure: Dict[Tuple[str, str], float] = field(default_factory=dict)  # (metal, cut) -> um
    grid_um: float = 0.005
    supply_names: Tuple[str, ...] = ("VDD", "VSS", "VPWR", "VGND", "vdd", "vss")
    text_layers: Dict[Layer, str] = field(default_factory=dict)   # label (layer, datatype) -> conducting layer it names
    # construction constants for generated geometry (um)
    poly_ext_diff: float = 0.13        # poly overhang beyond diffusion along W
    implant_enc: float = 0.125         # nsdm/psdm enclosure of diffusion
    nwell_enc: float = 0.18            # nwell enclosure of p diffusion

    def L(self, name: str) -> Layer:
        return self.layers[name]

    def conducting(self) -> List[str]:
        out = [self.poly] + list(self.routing)
        for lo, cut, up in self.vias:
            out.append(cut)
        out.append(self.diff_contact)
        seen, res = set(), []
        for n in out:
            if n in self.layers and n not in seen:
                seen.add(n); res.append(n)
        return res


SKY130 = Tech(
    name="sky130",
    layers={"diff": (65, 20), "tap": (65, 44), "nwell": (64, 20), "poly": (66, 20),
            "nsdm": (93, 44), "psdm": (94, 20), "licon": (66, 44), "li": (67, 20),
            "mcon": (67, 44), "met1": (68, 20), "via1": (68, 44), "met2": (69, 20),
            "via2": (69, 44), "met3": (70, 20), "via3": (70, 44), "met4": (71, 20),
            "via4": (71, 44), "met5": (72, 20), "text": (83, 44)},
    routing=["li", "met1", "met2", "met3", "met4", "met5"],
    vias=[("li", "mcon", "met1"), ("met1", "via1", "met2"), ("met2", "via2", "met3"),
          ("met3", "via3", "met4"), ("met4", "via4", "met5")],
    nsdm="nsdm", psdm="psdm", diff_contact="licon",
    nfet_model="sky130_fd_pr__nfet_01v8", pfet_model="sky130_fd_pr__pfet_01v8",
    rsh={"poly": 48.2, "li": 12.8, "met1": 0.125, "met2": 0.125, "met3": 0.047, "met4": 0.047, "met5": 0.029},
    rvia={"licon": 70.0, "mcon": 9.3, "via1": 4.5, "via2": 4.5, "via3": 3.4, "via4": 0.38},
    carea={"poly": 0.106, "li": 0.040, "met1": 0.038, "met2": 0.028, "met3": 0.020, "met4": 0.016, "met5": 0.012},
    cfringe={"poly": 0.055, "li": 0.040, "met1": 0.040, "met2": 0.036, "met3": 0.030, "met4": 0.030, "met5": 0.030},
    min_width={"poly": 0.150, "diff": 0.150, "li": 0.170, "met1": 0.140, "met2": 0.140, "met3": 0.300,
               "met4": 0.300, "met5": 1.600, "licon": 0.170, "mcon": 0.170, "via1": 0.150, "via2": 0.200},
    min_space={"poly": 0.210, "diff": 0.270, "li": 0.170, "met1": 0.140, "met2": 0.140, "met3": 0.300,
               "met4": 0.300, "met5": 1.600, "licon": 0.170, "mcon": 0.190, "via1": 0.170, "via2": 0.200,
               "nwell": 1.270},
    enclosure={("diff", "licon"): 0.040, ("li", "licon"): 0.080, ("li", "mcon"): 0.000,
               ("met1", "mcon"): 0.030, ("met1", "via1"): 0.055, ("met2", "via1"): 0.055,
               ("met2", "via2"): 0.040, ("met3", "via2"): 0.065},
    # sky130 label layers (li1/met1..met5 .label = datatype 5; .pin = datatype 16 also names nets)
    text_layers={(67, 5): "li", (68, 5): "met1", (69, 5): "met2", (70, 5): "met3", (71, 5): "met4", (72, 5): "met5",
                 (66, 5): "poly", (67, 16): "li", (68, 16): "met1", (69, 16): "met2", (70, 16): "met3"},
)

# IHP SG13G2 -- layer numbers from sg13g2.map; interconnect from sg13g2_tech.lef (via stat-sim)
SG13G2 = Tech(
    name="sg13g2",
    layers={"diff": (1, 0), "nwell": (31, 0), "poly": (5, 0), "psdm": (14, 0), "nsdm": (7, 0),
            "licon": (6, 0), "met1": (8, 0), "via1": (19, 0), "met2": (10, 0), "via2": (29, 0),
            "met3": (30, 0), "via3": (49, 0), "met4": (50, 0), "via4": (66, 0), "met5": (67, 0),
            "topvia1": (125, 0), "topmet1": (126, 0), "topvia2": (133, 0), "topmet2": (134, 0),
            "text": (8, 25)},
    routing=["met1", "met2", "met3", "met4", "met5", "topmet1", "topmet2"],
    vias=[("met1", "via1", "met2"), ("met2", "via2", "met3"), ("met3", "via3", "met4"),
          ("met4", "via4", "met5"), ("met5", "topvia1", "topmet1"), ("topmet1", "topvia2", "topmet2")],
    nsdm="nsdm", psdm="psdm", diff_contact="licon",
    nfet_model="sg13_lv_nmos", pfet_model="sg13_lv_pmos",
    rsh={"poly": 7.0, "met1": 0.135, "met2": 0.103, "met3": 0.103, "met4": 0.103, "met5": 0.103,
         "topmet1": 0.021, "topmet2": 0.0145},
    rvia={"licon": 25.0, "via1": 20.0, "via2": 20.0, "via3": 20.0, "via4": 20.0, "topvia1": 4.0, "topvia2": 2.2},
    carea={"met1": 0.0349, "met2": 0.0181, "met3": 0.0120, "met4": 0.00894, "met5": 0.00713,
           "topmet1": 0.00564, "topmet2": 0.00323},
    cfringe={"met1": 0.0316, "met2": 0.0447, "met3": 0.0448, "met4": 0.0450, "met5": 0.0437,
             "topmet1": 0.0508, "topmet2": 0.0418},
    min_width={"poly": 0.130, "diff": 0.150, "met1": 0.160, "met2": 0.200, "met3": 0.200, "met4": 0.200,
               "met5": 0.200, "topmet1": 1.640, "topmet2": 2.000, "licon": 0.160, "via1": 0.190},
    min_space={"poly": 0.180, "diff": 0.210, "met1": 0.180, "met2": 0.210, "met3": 0.210, "met4": 0.210,
               "met5": 0.210, "topmet1": 1.640, "topmet2": 2.000, "licon": 0.180, "via1": 0.220},
    enclosure={("met1", "licon"): 0.005, ("met1", "via1"): 0.010, ("met2", "via1"): 0.005},
)

TECHS = {"sky130": SKY130, "sg13g2": SG13G2}


def get(name: str) -> Tech:
    try:
        return TECHS[name]
    except KeyError:
        raise SystemExit("unknown tech %r (have %s)" % (name, ", ".join(TECHS)))
