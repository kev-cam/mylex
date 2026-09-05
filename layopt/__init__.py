# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""layopt -- post-layout, boundary-free geometry optimizer (working name).

Flattens a layout to transistor-level rectangles with provenance, extracts
devices / nets / RC from the geometry, then applies topology-preserving
moves (device W, wire width) under a rule check, driven by a timing-balance
objective.  See LAYOUT-OPT.md at the repository root.
"""
__version__ = "0.1.0"
