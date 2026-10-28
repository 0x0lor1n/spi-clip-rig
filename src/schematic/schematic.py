"""Schematic: lab PSU and ESP-Prog JTAG header -> SOIC-8 clip -> 25xx SPI flash on the target PCB.

Usage: schematic.py OUT.svg
"""

import sys

import schemdraw
import schemdraw.elements as elm

from mcubench.fritzing import espprog, soic8clip
from mcubench.schematic import IC, setup, terminal

setup()
OUT = sys.argv[1]

# Chip pin -> SPI signal name as flashrom sees it from the programmer side.
SPI = {"CS#": "CS#", "CLK": "CLK", "DI": "MOSI", "DO": "MISO"}
ROWS = ["VCC", "WP#", "HOLD#", "CS#", "CLK", "DI", "DO", "GND"]


def number(name):
    return str(soic8clip.PINS.index(name) + 1)


def slot(name):
    return f"{len(ROWS) - ROWS.index(name)}/{len(ROWS)}"


def prog_pin(name, side, slot):
    return elm.IcPin(name=name, pin=str(espprog.JTAG[name]), side=side, slot=slot)


with schemdraw.Drawing(file=OUT, show=False) as d:
    d.config(unit=2.5, fontsize=10)

    # The clip is a pass-through: contact n lands on chip pin n.
    clip = elm.Ic(
        pins=[elm.IcPin(name=n, pin=number(n), side="left", slot=slot(n)) for n in ROWS]
        + [elm.IcPin(side="right", slot=slot(n), anchorname=f"{n}_chip") for n in ROWS],
        **{**IC, "edgepadW": 1.8},
    ).label("SOIC-8 clip", loc="top", fontsize=10)
    d += clip.right().at((0, 0))

    chip = elm.Ic(
        pins=[elm.IcPin(name=n, pin=number(n), side="left", slot=slot(n)) for n in ROWS],
        **{**IC, "edgepadW": 3.2},
    ).label("25xx\nSPI flash\nSOIC-8", loc="center", fontsize=10)
    d += chip.right().anchor("VCC").at((clip.VCC_chip[0] + 1.0, clip.VCC_chip[1]))
    for n in ROWS:
        d += elm.Line().at(clip[f"{n}_chip"]).to(chip[n])
    d += (
        elm.EncircleBox([chip], padx=0.5, pady=0.5)
        .linestyle("--")
        .label("target PCB: its own power sources removed", loc="bottom", fontsize=9)
    )

    prog = elm.Ic(
        pins=[prog_pin(espprog.silk(SPI[n]), "right", f"{4 - i}/4") for i, n in enumerate(SPI)]
        + [prog_pin("VDD", "left", "4/4"), prog_pin("GND", "left", "1/4")],
        **{**IC, "edgepadW": 2.6},
    ).label("ESP-Prog\nJTAG header", loc="center", fontsize=10)
    d += prog.right().anchor("TMS").at((clip["CS#"][0] - 4.5, clip["CS#"][1]))
    for n in SPI:
        d += elm.Line().at(prog[espprog.silk(SPI[n])]).to(clip[n]).label(SPI[n], loc="top", fontsize=9)

    d += elm.NoConnect().at(prog.VDD)
    d += (
        elm.Label()
        .at((prog.VDD[0] - 0.4, prog.VDD[1]))
        .label("VDD: do not use", loc="left", halign="right", fontsize=9)
    )

    # 3.3 V rail: PSU terminal -> VCC, with WP# and HOLD# tied high.
    x_rail = clip.VCC[0] - 1.2
    x_psu = prog.VDD[0] - 5.5
    for n in ("WP#", "HOLD#"):
        d += elm.Line().at((x_rail, clip[n][1])).to(clip[n])
    d += elm.Line().at((x_rail, clip["HOLD#"][1])).to((x_rail, clip.VCC[1]))
    d += elm.Dot().at((x_rail, clip.VCC[1]))
    d += elm.Dot().at((x_rail, clip["WP#"][1]))
    d += elm.Line().at(clip.VCC).to((x_psu, clip.VCC[1]))
    terminal(d, "+3.3 V", "left")

    # Common ground: PSU, clip, programmer.
    y_gnd = min(clip.GND[1], prog.GND[1]) - 1.0
    d += elm.Line().at(clip.GND).to((x_rail, clip.GND[1]))
    d += elm.Line().at((x_rail, clip.GND[1])).to((x_rail, y_gnd))
    x_pg = prog.GND[0] - 0.8
    d += elm.Line().at(prog.GND).to((x_pg, prog.GND[1]))
    d += elm.Line().at((x_pg, prog.GND[1])).to((x_pg, y_gnd))
    d += elm.Dot().at((x_pg, y_gnd))
    d += elm.Line().at((x_pg, y_gnd)).down(0.6)
    d += elm.Ground()
    d += elm.Line().at((x_rail, y_gnd)).to((x_psu, y_gnd))
    terminal(d, "GND", "left")

    d += (
        elm.Label()
        .at((x_psu, clip.VCC[1] + 0.9))
        .label("RD6006 or any CC PSU, 3.3 V, limit 300 mA", loc="right", halign="left", fontsize=9)
    )
    d += (
        elm.Label()
        .at((x_psu, y_gnd - 2.2))
        .label(
            "ESP-Prog I/O voltage jumper = 3.3 V.\n"
            "VDD stays open: it feeds voltage into the IC's always-on rail.\n"
            "The flash's pins are nets of the target PCB too: every power source off the board.\n"
            "Clip on/off only with the PSU output off and USB unplugged; clip pin 1 on the chip's dot.",
            loc="right",
            halign="left",
            valign="top",
            fontsize=9,
        )
    )

print(OUT)
