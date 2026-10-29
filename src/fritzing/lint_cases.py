"""Lint mutations for the bench sketch. Every one is a real bench mistake.

python3 lint_cases.py <Fritzing binary> <dir with gen.py output>
"""

import sys

from mcubench.fritzing.linttest import move_wire_end, run, shift_instance
from mcubench.fritzing.part import MM, P

# ESP-Prog header: odd pins on the lower row, so one row down from TMS is VDD.
ROW = (0, P)
NEXT_PIN = (P, 0)
PSU_PITCH = (-12 * MM, 0)

CASES = [
    ("bench", "CS# lead one row off: on VDD instead of TMS", lambda fz: move_wire_end(fz, "CS# to ESP-Prog TMS", *ROW)),
    (
        "bench",
        "CLK lead one pin over: on TDO instead of TCK",
        lambda fz: move_wire_end(fz, "CLK to ESP-Prog TCK", *NEXT_PIN),
    ),
    (
        "bench",
        "PSU leads swapped: GND rail on the + terminal",
        lambda fz: move_wire_end(fz, "GND rail to PSU -", *PSU_PITCH),
    ),
    ("bench", "clip one column right", lambda fz: shift_instance(fz, "SOIC-8 clip", P, 0)),
]

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(run(*sys.argv[1:], CASES))
