#!/usr/bin/env python3
"""Parse ORCA VPT2 output files for Fermi resonances."""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import TextIO


@dataclass
class FermiResonance:
    resonance_type: int  # 1 or 2
    modes: list[int]     # [i, j] for type I, [i, j, k] for type II
    denominator: float

    def __str__(self) -> str:
        if self.resonance_type == 1:
            desc = f"Type I:  ω{self.modes[0]} ≈ 2×ω{self.modes[1]}"
        else:
            desc = f"Type II: ω{self.modes[0]} ≈ ω{self.modes[1]} + ω{self.modes[2]}"
        return f"{desc}  |Δ| = {self.denominator:.4f} cm⁻¹"


def parse_fermi_resonances(file: TextIO) -> list[FermiResonance]:
    resonances: list[FermiResonance] = []
    re_type1 = re.compile(
        r"possible Type I resonance mode (\d+) (\d+)\s+([\d.]+)"
    )
    re_type2 = re.compile(
        r"possible Type II resonance \d+ mode (\d+) (\d+) (\d+)\s+([\d.]+)"
    )

    for line in file:
        m = re_type2.search(line)
        if m:
            resonances.append(FermiResonance(
                resonance_type=2,
                modes=[int(m.group(1)), int(m.group(2)), int(m.group(3))],
                denominator=float(m.group(4)),
            ))
            continue
        m = re_type1.search(line)
        if m:
            resonances.append(FermiResonance(
                resonance_type=1,
                modes=[int(m.group(1)), int(m.group(2))],
                denominator=float(m.group(3)),
            ))

    return resonances


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(
        description="Parse Fermi resonances from ORCA VPT2 output."
    )
    parser.add_argument("file", type=str, help="ORCA VPT2 output file (.out)")
    parser.add_argument(
        "--type", type=int, choices=[1, 2],
        help="Filter by resonance type (1 or 2)"
    )
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")

    with path.open() as f:
        resonances = parse_fermi_resonances(f)

    if not resonances:
        print("No Fermi resonances found.")
        return

    type_filter = args.type
    if type_filter:
        resonances = [r for r in resonances if r.resonance_type == type_filter]

    if not resonances:
        print("No matching Fermi resonances.")
        return

    for r in resonances:
        print(r)


if __name__ == "__main__":
    main()
