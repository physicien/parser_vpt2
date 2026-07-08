#!/usr/bin/env python3
"""Parse ORCA VPT2 output files for Fermi resonances.

Fetches Fermi resonances from the VPT2 analysis section of an ORCA
quantum chemistry output file. Supports filtering by resonance type
and IR intensity threshold.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


@dataclass
class FermiResonance:
    """A single Fermi resonance identified in the VPT2 output.

    Parameters
    ----------
    resonance_type : int
        1 for Type I (fundamental near overtone),
        2 for Type II (fundamental near combination band).
    modes : list of int
        Mode indices (ORCA numbering, i.e. including trans/rot offset):
        [i, j] for Type I (omega_i ~ 2*omega_j),
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
        OM = "\u03c9"
        if self.resonance_type == 1:
            desc = (
                f"Type I:  {OM}{self.modes[0]}"
                f" \u2248 2\u00d7{OM}{self.modes[1]}"
            )
        else:
            desc = (
                f"Type II: {OM}{self.modes[0]}"
                f" \u2248 {OM}{self.modes[1]}"
                f" + {OM}{self.modes[2]}"
            )
        return f"{desc}  |\u0394| = {self.denominator:.4f} cm\u207b\u00b9"


# ---------------------------------------------------------------------------
# Single-pass parser
# ---------------------------------------------------------------------------

@dataclass
class _Vpt2Data:
    """Container for all data extracted in a single file pass."""
    ir_intensities: dict[int, float] = field(default_factory=dict)
    vib_offset: int = 0  # number of trans/rot modes before first real vibration
    fermi_resonances: list[FermiResonance] = field(default_factory=list)


# Constants
_IR_TABLE_TITLE = "IR Intensities"
_IR_COL_HEADER = "Mode"
_IR_COL_KEY = "freq"
_RESONANCE_KEY = "resonance"
_TABLE_SEP = "---"

# Pre-compiled regexes (module level, compiled once)
_RE_IR_ROW = re.compile(r"^\s*(\d+)\s+")
_RE_TYPE1 = re.compile(
    r"possible Type I resonance mode (\d+) (\d+)\s+([\d.]+)"
)
_RE_TYPE2 = re.compile(
    r"possible Type II resonance \d+ mode (\d+) (\d+) (\d+)\s+([\d.]+)"
)


def _parse_ir_table(lines: Iterator[str]) -> tuple[dict[int, float], int]:
    """Parse the next IR Intensities table from *lines*.

    Advances the iterator past the end of the table.

    Returns
    -------
    (ints, offset)
        ints : mapping from mode index to IR intensity (km/mol).
        offset : number of leading trans/rot modes (freq < 10 cm^-1).
    """
    all_rows: list[tuple[int, float, float]] = []  # (mode, freq, int)
    past_sep = False
    for line in lines:
        if line.startswith(_TABLE_SEP):
            if past_sep:
                break
            past_sep = True
            continue
        if not past_sep:
            continue
        m = _RE_IR_ROW.match(line)
        if not m:
            break
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            freq = float(parts[1])
        except ValueError:
            continue
        mode = int(m.group(1))
        try:
            val = float(parts[2])
        except ValueError:
            continue
        all_rows.append((mode, freq, val))

    ints = {}
    offset = 0
    for mode, freq, val in all_rows:
        if not (val != val):  # skip NaN
            ints[mode] = val
        if freq < 10:
            offset = mode + 1
    return ints, offset


def parse_file(path: str | Path) -> _Vpt2Data:
    """Parse an ORCA VPT2 output file in a single pass.

    Parameters
    ----------
    path : str or Path
        Path to the ORCA ``.out`` file.

    Returns
    -------
    _Vpt2Data
        Container with ``ir_intensities``, ``vib_offset``, and
        ``fermi_resonances``. Fermi mode indices include ``vib_offset``
        to match the numbering in the ORCA output file.
    """
    data = _Vpt2Data()

    with open(path) as fh:
        for line in fh:
            # --- IR intensity tables (first occurrence only, harmonic) ---
            if _IR_TABLE_TITLE in line and not data.ir_intensities:
                for l in fh:
                    if l.startswith(_IR_COL_HEADER) and _IR_COL_KEY in l:
                        ints, offset = _parse_ir_table(fh)
                        data.ir_intensities = ints
                        if not data.vib_offset:
                            data.vib_offset = offset
                        break
                continue

            # --- Fermi resonances ---
            if _RESONANCE_KEY not in line:
                continue

            # Shift Fermi-block mode numbers by the trans/rot offset so
            # they match the numbering used elsewhere in the ORCA output.
            offset = data.vib_offset
            m = _RE_TYPE2.search(line)
            if m:
                data.fermi_resonances.append(FermiResonance(
                    resonance_type=2,
                    modes=[int(m.group(1)) + offset,
                           int(m.group(2)) + offset,
                           int(m.group(3)) + offset],
                    denominator=float(m.group(4)),
                ))
                continue
            m = _RE_TYPE1.search(line)
            if m:
                data.fermi_resonances.append(FermiResonance(
                    resonance_type=1,
                    modes=[int(m.group(1)) + offset,
                           int(m.group(2)) + offset],
                    denominator=float(m.group(3)),
                ))

    return data


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

    data = parse_file(args.file)

    if not data.fermi_resonances:
        print("No Fermi resonances found.")
        return

    resonances = data.fermi_resonances

    if args.type:
        resonances = [r for r in resonances if r.resonance_type == args.type]

    if args.min_intensity > 0:
        ir = data.ir_intensities

        def _passes_int(r: FermiResonance) -> bool:
            return any(
                ir.get(m, 0) >= args.min_intensity
                for m in r.involved_modes()
            )

        resonances = [r for r in resonances if _passes_int(r)]

    if not resonances:
        print("No matching Fermi resonances.")
        return

    for r in resonances:
        print(r)


if __name__ == "__main__":
    main()
