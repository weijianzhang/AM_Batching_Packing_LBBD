# Instance data format

Each JSON object describes one instance. IDs are one-based. Materials are strings such as `F1`, `F2`, and `F3`.

## Instance metadata

| Field | Meaning |
| --- | --- |
| `name` | Unique instance name, including configuration, seed, and `_min` suffix |
| `configuration` | Part/machine/material count identifier |
| `units` | Length: mm; volume: mm^3; time: min |
| `seed` | Integer seed identifying the replication |
| `replication_index` | Replication number from 1 to 5 within a configuration |
| `rng_key` | Exact string used to initialize the random stream |
| `numeric_time_factor_from_original_hour_data` | Legacy generation metadata, equal to 3.5; already applied to stored coefficients |
| `parts` | List of part records |
| `machines` | List of machine records |

## Part records

| Field | Meaning |
| --- | --- |
| `id` | Part identifier |
| `material` | Required material |
| `length`, `width`, `height` | Bounding-box dimensions in mm |
| `volume` | Actual printing volume in mm^3 |
| `size_category` | Sampling category: small, medium, or large |
| `volume_ratio` | Actual volume divided by length × width × height |

A permitted in-plane rotation exchanges length and width; height and actual volume remain unchanged.

## Machine records

| Field | Meaning |
| --- | --- |
| `id` | Machine identifier |
| `profile` | Index of the sampled capacity profile |
| `length`, `width` | Platform dimensions in mm |
| `height` | Maximum printing height in mm |
| `tau[f]` | Fixed batch-operation time for material f, in min |
| `alpha[f]` | Height-dependent coefficient, in min/mm |
| `beta[f]` | Volume-dependent coefficient, in min/mm^3 |
| `initial[f]` | Setup before the first batch of material f, in min |
| `setup[f][g]` | Setup from preceding material f to succeeding material g, in min |

For a nonempty batch B of material f on machine m, printing time is:

```text
t(B,m) = tau_m[f] + alpha_m[f] * max(height_p for p in B)
                    + beta_m[f] * sum(volume_p for p in B)
```

Setup time is additional to printing time. Diagonal setup entries apply between distinct consecutive batches using the same material. Initial setup is applied once to the first batch on each used machine. No terminal setup is specified.

## Manifest

`manifest.csv` contains one row per instance. `file` is relative to the repository root. `sha256` is computed from the original JSON file bytes. The manifest can be used to check completeness and integrity without executing the instance generator or an optimization solver.
