# `parse_vpt2`

Parse Fermi resonances and IR intensities from ORCA VPT2 output files.

## Usage

```console
python3 parse_vpt2.py [OPTIONS] file.out
```

## Examples

List all Fermi resonances:

```console
python3 parse_vpt2.py data/VPT2_furan_vpt2.out
```

Filter by Type I only:

```console
python3 parse_vpt2.py data/VPT2_furan_vpt2.out --type 1
```

Require all coupling modes to have IR intensity ≥ 10 km/mol:

```console
python3 parse_vpt2.py data/VPT2_furan_vpt2.out -I 10
```

Print the harmonic IR table instead of Fermi resonances:

```console
python3 parse_vpt2.py data/VPT2_furan_vpt2.out --ir-table
```

## Command-line options

- `file` , required: ORCA VPT2 output file (`.out`)
- `--type` {1,2} , optional: filter by resonance type
- `-I` , `--min-intensity` `N` , optional: minimum IR intensity (km/mol) for coupling modes
- `--ir-table` , optional: print the IR intensity table instead of Fermi resonances

## Output format

- Type I: `ω_i ≈ 2×ω_j` — fundamental i is near-degenerate with overtone 2×ω_j
- Type II: `ω_i ≈ ω_j + ω_k` — fundamental i is near-degenerate with combination ω_j + ω_k

The `|Δ|` value is the energy difference in cm⁻¹ (denominator). Lower values indicate stronger coupling.

## Note

- The number at the end is the denominator = |ω_i - 2ω_j| (Type I) or |ω_i - ω_j - ω_k| (Type II) in cm⁻¹. The threshold 10 means only resonances with denominator < 10 cm⁻¹ are printed. A smaller denominator means a stronger resonance / more severe VPT2 singularity.

- Mode numbers follow ORCA's output conventions (i.e., including translational/rotational modes). The offset (typically 6) is automatically detected from the IR table and applied to all Fermi mode indices.

## Contributor

Contributed by Emmanuel Bourret
