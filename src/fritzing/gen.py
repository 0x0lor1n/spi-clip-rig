"""Generate the bench sketch (Fritzing .fzz): ESP-Prog and a lab PSU to a SOIC-8 clip.

  python3 gen.py <fritzing-parts-dir> <out-dir>

Placement, net checks and the .fzz writer are in mcubench.fritzing (mcu-bench). The real
rig has no breadboard; here it only stands in for the Dupont leads between the three parts.
"""

import functools
import os
import re
import sys

from mcubench.fritzing import espprog, soic8clip
from mcubench.fritzing import part as fzpart
from mcubench.fritzing.part import MM, P, text
from mcubench.fritzing.sketch import BLACK, BLUE, GREEN, ORANGE, RED, YELLOW, Sketch

EP_ID = "spi-clip-rig-espressif-esp-prog"
CLIP_ID = "spi-clip-rig-soic8-clip"
PSU_ID = "spi-clip-rig-lab-psu"

GenPart = functools.partial(fzpart.GenPart, author="spi-clip-rig/src/fritzing/gen.py", tag="spi-clip-rig")

COL0 = 12  # clip pin 1 column
# Lead columns in ESP-Prog header order (TMS TCK TDO TDI, same 0.1 in pitch), so the leads drop straight down.
LEAD = {"CS#": 17, "CLK": 18, "DO": 19, "DI": 20}
# Header pin 9, also GND: right of TDI, so its lead drops straight down beside the others.
EP_GND9 = "connector16"
PSU_PINS = ["+3.3V", "GND"]


def lab_psu():
    w, h = 26 * MM, 18 * MM
    p = GenPart(
        PSU_ID,
        "Lab PSU",
        "PS",
        "power supply",
        "Current-limited bench supply, 3.3 V, limit 300 mA.",
        w,
        h,
        "female",
    )
    p.art.append(f'<rect x="0" y="0" width="{w:.2f}" height="{h:.2f}" rx="2" fill="#3a3a3a"/>')
    p.art.append(text(w / 2, 3.6 * MM, "LAB PSU 3.3 V", 3.6))
    p.art.append(text(w / 2, 6.2 * MM, "CC limit 300 mA", 3, "#ffd27a"))
    for k, (name, color) in enumerate(zip(PSU_PINS, ("#cc1414", "#111111"), strict=True)):
        x, y = w / 2 + (k - 0.5) * 12 * MM, 13.5 * MM
        p.art.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{2.6 * MM:.2f}" fill="{color}" stroke="#c0c0c0"/>')
        p.art.append(text(x, y - 3.2 * MM, name, 3))
        p.pin(name, x, y, "R")
    return p


def psu_pin(name):
    return f"connector{PSU_PINS.index(name)}"


def rail(sk, row, col):
    """The rail hole on row W/X/Y/Z nearest to column col; rails skip every sixth column."""
    x = sk.hole(f"pin{col}A")[0]
    holes = [h for h in sk.bb.pins if re.fullmatch(rf"pin\d+{row}", h)]
    return min(holes, key=lambda h: abs(sk.hole(h)[0] - x))


def bench(parts):
    """Upper rail Y and lower rail W are +3.3 V, lower rail X is GND."""
    sk = Sketch(parts)
    clip = soic8clip.place(sk, CLIP_ID, "SOIC-8 clip", COL0)
    col = {n: int(re.match(r"pin(\d+)", soic8clip.hole(n, COL0))[1]) for n in soic8clip.PINS}

    tms = sk.hole(f"pin{LEAD['CS#']}A")
    ep = espprog.place(sk, EP_ID, "ESP-Prog", (tms[0] + P, tms[1] + 127))

    psu = sk.embed(PSU_ID, "Lab PSU", lab_psu().files())
    psu.place(psu_pin("GND"), (-30, sk.hole("pin1A")[1]))

    # Breadboard end first: lint mutations move the far end (x2).
    sk.wire(rail(sk, "W", 2), (psu, psu_pin("+3.3V")), RED, "+3.3V rail to PSU +")
    sk.wire(rail(sk, "X", 3), (psu, psu_pin("GND")), BLACK, "GND rail to PSU -")
    sk.wire(rail(sk, "W", 30), rail(sk, "Y", 30), RED, "+3.3V lower rail to upper rail")

    sk.wire(f"pin{col['VCC']}J", rail(sk, "Y", col["VCC"]), RED, "VCC to +3.3V")
    sk.wire(f"pin{col['HOLD#']}J", rail(sk, "Y", col["HOLD#"]), RED, "HOLD# to +3.3V")
    sk.wire(f"pin{col['WP#']}A", rail(sk, "W", col["WP#"]), RED, "WP# to +3.3V")
    sk.wire(f"pin{col['GND']}A", rail(sk, "X", col["GND"]), BLACK, "clip GND to GND rail")

    sk.wire(f"pin{col['CS#']}C", f"pin{LEAD['CS#']}C", ORANGE, "CS# to lead column")
    sk.wire(f"pin{col['DO']}B", f"pin{LEAD['DO']}B", GREEN, "DO to lead column")
    sk.wire(f"pin{col['CLK']}H", f"pin{LEAD['CLK']}H", BLUE, "CLK to lead column")
    sk.wire(f"pin{col['DI']}I", f"pin{LEAD['DI']}I", YELLOW, "DI to lead column")
    sk.wire(f"pin{LEAD['CLK']}G", f"pin{LEAD['CLK']}D", BLUE, "CLK across the gap")
    sk.wire(f"pin{LEAD['DI']}G", f"pin{LEAD['DI']}D", YELLOW, "DI across the gap")

    for n, (signal, color) in {
        "CS#": ("CS#", ORANGE),
        "CLK": ("CLK", BLUE),
        "DO": ("MISO", GREEN),
        "DI": ("MOSI", YELLOW),
    }.items():
        sk.wire(f"pin{LEAD[n]}A", (ep, espprog.conn(signal)), color, f"{signal} to ESP-Prog {espprog.silk(signal)}")
    sk.wire(rail(sk, "X", LEAD["DI"] + 1), (ep, EP_GND9), BLACK, "GND to ESP-Prog GND 9")

    for k, p in enumerate((psu, clip, ep)):
        p.sch = (k * 200, 0)
        p.pcb = (k * 120, 0)

    def clipn(n):
        return clip.title, soic8clip.conn(n)

    def epn(n):
        return ep.title, espprog.conn(n)

    def psun(n):
        return psu.title, psu_pin(n)

    sk.check(
        {
            "+3.3V": [psun("+3.3V"), clipn("VCC"), clipn("WP#"), clipn("HOLD#")],
            "GND": [psun("GND"), clipn("GND"), (ep.title, EP_GND9)],
            "CS#": [clipn("CS#"), epn("CS#")],
            "CLK": [clipn("CLK"), epn("CLK")],
            "MOSI": [clipn("DI"), epn("MOSI")],
            "MISO": [clipn("DO"), epn("MISO")],
        }
    )
    sk.note(
        320,
        0,
        400,
        130,
        "No breadboard on the real bench: Dupont leads from the clip\n"
        "straight to the ESP-Prog header and the PSU terminals.\n"
        "ESP-Prog I/O jumper on 3.3 V, VDD (pin 1) open.\n"
        "PSU 3.3 V, limit 300 mA. Clip pin 1 on the chip's dot.\n"
        "Clip on/off only with the PSU off and USB unplugged.",
    )
    return sk


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    parts, out = sys.argv[1:]
    os.makedirs(out, exist_ok=True)
    bench(parts).save(os.path.join(out, "bench.fzz"), "bench")
    print(os.path.join(out, "bench.fzz"))


if __name__ == "__main__":
    main()
