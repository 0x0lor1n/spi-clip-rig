"""Schematic: lab PSU and ESP-Prog JTAG header -> SOIC-8 clip on a 25xx SPI flash.

Usage: schematic.py OUT.svg
"""

import sys

import schemdraw
import schemdraw.elements as elm

from mcubench.fritzing import espprog, soic8clip
from mcubench.schematic import IC, setup, terminal

setup()
OUT = sys.argv[1]

# Clip pin -> SPI signal name as flashrom sees it from the programmer side.
SPI = {"CS#": "CS#", "CLK": "CLK", "DI": "MOSI", "DO": "MISO"}
ROWS = ["CS#", "CLK", "DI", "DO"]


def clip_pin(name, side, slot):
    return elm.IcPin(name=name, pin=str(soic8clip.PINS.index(name) + 1), side=side, slot=slot)


def prog_pin(name, side, slot):
    return elm.IcPin(name=name, pin=str(espprog.JTAG[name]), side=side, slot=slot)


with schemdraw.Drawing(file=OUT, show=False) as d:
    d.config(unit=2.5, fontsize=10)

    clip = elm.Ic(
        pins=[clip_pin(n, "right", f"{4 - i}/4") for i, n in enumerate(ROWS)]
        + [
            clip_pin("VCC", "left", "4/4"),
            clip_pin("WP#", "left", "3/4"),
            clip_pin("HOLD#", "left", "2/4"),
            clip_pin("GND", "bottom", "1/1"),
        ],
        **{**IC, "edgepadW": 2.6},
    ).label("SOIC-8 clip\n25xx SPI flash", loc="center", fontsize=10)
    d += clip.right().at((0, 0))

    prog = elm.Ic(
        pins=[prog_pin(espprog.silk(SPI[n]), "left", f"{4 - i}/4") for i, n in enumerate(ROWS)]
        + [
            prog_pin("VDD", "right", "4/4"),
            prog_pin("GND", "bottom", "1/1"),
        ],
        **{**IC, "edgepadW": 2.6},
    ).label("ESP-Prog\nJTAG header", loc="center", fontsize=10)
    d += prog.right().anchor("TMS").at((clip["CS#"][0] + 6.0, clip["CS#"][1]))

    for n in ROWS:
        d += elm.Line().at(clip[n]).to(prog[espprog.silk(SPI[n])]).label(SPI[n], loc="top", fontsize=9)

    d += elm.NoConnect().at(prog.VDD)
    d += (
        elm.Label()
        .at((prog.VDD[0] + 0.4, prog.VDD[1]))
        .label("VDD: do not use", loc="right", halign="left", fontsize=9)
    )

    # 3.3 V rail: PSU terminal -> VCC, with WP# and HOLD# tied high.
    x_rail = clip.VCC[0] - 1.5
    x_psu = x_rail - 2.5
    d += elm.Line().at(clip.VCC).to((x_rail, clip.VCC[1]))
    d += elm.Line().at((x_rail, clip.VCC[1])).to((x_rail, clip["HOLD#"][1]))
    for n in ("WP#", "HOLD#"):
        d += elm.Line().at(clip[n]).to((x_rail, clip[n][1]))
    d += elm.Dot().at((x_rail, clip.VCC[1]))
    d += elm.Dot().at((x_rail, clip["WP#"][1]))
    d += elm.Line().at((x_rail, clip.VCC[1])).to((x_psu, clip.VCC[1]))
    terminal(d, "+3.3 V", "left")

    # Common ground: PSU, clip, programmer.
    y_gnd = clip.GND[1] - 1.2
    d += elm.Line().at(clip.GND).to((clip.GND[0], y_gnd))
    d += elm.Line().at(prog.GND).to((prog.GND[0], y_gnd))
    d += elm.Dot().at((clip.GND[0], y_gnd))
    d += elm.Line().at((clip.GND[0], y_gnd)).down(0.6)
    d += elm.Ground()
    d += elm.Line().at((prog.GND[0], y_gnd)).to((x_psu, y_gnd))
    terminal(d, "GND", "left")

    d += (
        elm.Label()
        .at((x_psu, clip.VCC[1] + 1.6))
        .label("RD6006 or any CC PSU, 3.3 V, limit 300 mA", loc="right", halign="left", fontsize=9)
    )
    d += (
        elm.Label()
        .at((x_psu, y_gnd - 1.8))
        .label(
            "ESP-Prog I/O voltage jumper = 3.3 V.\n"
            "VDD stays open: it feeds voltage into the IC's always-on rail.\n"
            "Clip on/off only with the PSU output off and USB unplugged; the board under test fully unpowered.",
            loc="right",
            halign="left",
            valign="top",
            fontsize=9,
        )
    )

print(OUT)
