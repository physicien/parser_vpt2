#!/usr/bin/env python3
"""Parse ORCA VPT2 output files for Fermi resonances.

Fetches Fermi resonances from the VPT2 analysis section of an ORCA
quantum chemistry output file. Supports filtering by resonance type
and IR intensity threshold.
"""

import re
from pathlib import Path
from dataclasses import dataclass


@dataclass
class FermiResonance:
    """A single Fermi resonance identified in the VPT2 output.

    Parameters
    ----------
    resonance_type : int
        1 for Type I (fundamental near overtone),
        2 for Type II (fundamental near combination band).
    modes : list of int
        Mode indices: [i, j] for Type I (omega_i ~ 2*omega_j),
        [i, j, k] for Type II (omega_i ~ omega_j + omega_k).
    denominator : float
        Energy difference in cm^-1.
    """
    resonance_type: int
    modes: list[int]
    denominator: float

    def involved_modes(self) -> set[int]:
        """Return the set of all normal mode indices involved."""
        return set(self.modes)

    def __str__(self) -> str:
        if self.resonance_type == 1:
            desc = f"Type I:  ω{self.modes[0]} ≈ 2×ω{self.modes[1]}"
        else:
            desc = (
                f"Type II: ω{self.modes[0]} ≈ ω{self.modes[1]}"
                f" + ω{self.modes[2]}"
            )
        return f"{desc}  |Δ| = {self.denominator:.4f} cm⁻¹"


def parse_ir_intensities(lines: list[str]) -> dict[int, float]:
    """Parse harmonic IR intensities from the VPT2 output.

    Locates the ``IR Intensities`` table printed by the ``orca_vpt2``
    program and extracts the intensity (km/mol) for each normal mode.

    Parameters
    ----------
    lines : list of str
        All lines of the ORCA output file.

    Returns
    -------
    dict of int -> float
        Mapping from mode index to IR intensity in km/mol.
        Only modes with a finite numeric intensity are included.
    """
    ints: dict[int, float] = {}
    header_re = re.compile(r"^\s*Mode\s+freq\s+Int")
    data_re = re.compile(
        r"^\s*(\d+)\s+[-\d]+\.[\d]+\s+([-\d.]+(?:e[+-]?\d+)?)\s"
    )

    in_table = False
    saw_sep = False
    for line in lines:
        if header_re.match(line):
            in_table = True
            saw_sep = False
            continue
        if in_table and line.startswith("---"):
            if saw_sep:
                in_table = False
            else:
                saw_sep = True
            continue
        if not in_table:
            continue
        m = data_re.match(line)
        if m:
            mode = int(m.group(1))
            raw = m.group(2)
            try:
                val = float(raw)
            except ValueError:
                continue
            if not (val != val):  # skip NaN
                ints[mode] = val
    return ints


def parse_fermi_resonances(lines: list[str]) -> list[FermiResonance]:
    """Parse Fermi resonances from the VPT2 output.

    Scans the ``Analysis of possible Fermi resonances with VPT2
    denominators`` block for Type I and Type II resonance lines.

    Parameters
    ----------
    lines : list of str
        All lines of the ORCA output file.

    Returns
    -------
    list of FermiResonance
        Every resonance found in the output.
    """
    resonances: list[FermiResonance] = []
    re_type1 = re.compile(
        r"possible Type I resonance mode (\d+) (\d+)\s+([\d.]+)"
    )
    re_type2 = re.compile(
        r"possible Type II resonance \d+ mode (\d+) (\d+) (\d+)\s+([\d.]+)"
    )

    for line in lines:
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
    """Command-line entry point.

    Parses arguments, reads the ORCA file, and prints matching
    Fermi resonances to stdout.
    """
    import argparse
    parser = argparse.ArgumentParser(
        description="Parse Fermi resonances from ORCA VPT2 output."
    )
    parser.add_argument("file", type=str, help="ORCA VPT2 output file (.out)")
    parser.add_argument(
        "--type", type=int, choices=[1, 2],
        help="Filter by resonance type (1 or 2)"
    )
    parser.add_argument(
        "-I", "--min-intensity", type=float, default=0,
        help="Minimum IR intensity (km/mol) of any mode in the resonance"
    )
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")

    lines = path.read_text().splitlines(keepends=True)

    ir_ints = parse_ir_intensities(lines)
    resonances = parse_fermi_resonances(lines)

    if not resonances:
        print("No Fermi resonances found.")
        return

    if args.type:
        resonances = [r for r in resonances if r.resonance_type == args.type]

    if args.min_intensity > 0:
        def passes_intensity(r: FermiResonance) -> bool:
            return any(ir_ints.get(m, 0) >= args.min_intensity
                       for m in r.involved_modes())
        resonances = [r for r in resonances if passes_intensity(r)]

    if not resonances:
        print("No matching Fermi resonances.")
        return

    for r in resonances:
        print(r)


if __name__ == "__main__":
    main()
