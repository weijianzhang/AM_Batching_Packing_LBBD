# Additive manufacturing batching, packing, and scheduling benchmarks

This repository provides 180 synthetic benchmark instances for integrated batching, two-dimensional packing, and scheduling on unrelated parallel additive manufacturing machines with sequence-dependent setup times. The objective is to minimize makespan.

Each part requires one material. A batch contains parts of the same material, whose rectangular footprints must fit on a machine platform without overlap or vertical stacking. A 90-degree in-plane rotation is permitted. Machines can process every material, but differ in capacity and material-dependent processing and setup parameters.

## Benchmark design

| Group | Number of parts | (Machines, materials) configurations for each part count | Configurations | Instances per configuration | Total |
| --- | --- | --- | --- | --- | --- |
| Small | 15, 20, 25 | (2,2), (2,3), (3,2), (3,3) | 12 | 5 | 60 |
| Medium | 30, 35, 40 | (3,2), (3,3), (5,3), (5,5) | 12 | 5 | 60 |
| Large | 60, 80, 100 | (5,3), (5,5), (7,3), (7,5) | 12 | 5 | 60 |
| Total | | | 36 | | 180 |

## Files

```text
Small/P15_M2_F2/seed_20261016.json
Small/...
Medium/...
Large/...
manifest.csv
DATA_FORMAT.md
generate_instances.py
README.md
```

`P15_M2_F2` denotes 15 parts, two machines, and two materials. Each configuration contains five JSON files. Seeds are globally unique, from 20261016 to 20261195. The manifest lists instance identifiers, configurations, relative paths, and SHA-256 checksums. These JSON files are the original experiment inputs, copied without modification.

Lengths and heights are in **mm**, volumes in **mm^3**, and printing/setup times in **minutes**. Computational runtime, when reported in the associated experiments, is measured in seconds. Parameters are synthetic and are not calibrated operating data for specific equipment.

## Data generation

The same distributions apply to all three size groups:

- Machine platform/height profiles `(L,W,H)` are sampled uniformly from `(200,200,200)`, `(250,200,250)`, `(250,250,300)`, `(300,250,300)`, and `(300,300,350)` mm.
- Part size categories have probabilities 0.3, 0.4, and 0.3. Conditional on category, length and width are sampled independently from integer intervals [20,70], [70,120], and [120,180], respectively.
- Part height is integer-uniform on [10,150]. Actual volume is a uniform fraction in [0.1,0.6] of the bounding-box volume.
- Each material appears at least once; remaining material labels are sampled uniformly and the labels are shuffled.
- Fixed batch time `tau`: uniform [0.35,1.05] min.
- Height coefficient `alpha`: uniform [0.0175,0.07] min/mm.
- Volume coefficient `beta`: uniform [0.0000035,0.000014] min/mm^3.
- Initial setup: uniform [0.7,3.5] min.
- Same-material setup: uniform [0.35,1.05] min.
- Different-material setup: uniform [0.7,4.2] min, sampled separately for each directed material pair.

Setup symmetry and the triangle inequality are not enforced; violations are not forced either. Every machine can accommodate every part individually. This does not imply that an arbitrary group of parts can fit in one batch.

## Reproducibility

The generator uses Python's standard library and requires no optimization solver. Python 3.10 was used in the experimental implementation. To generate a separate dataset directory:

```bash
python generate_instances.py --base-seed 20261016 --output reproduced_instances
```

The output directory must not already exist. The exact random stream key is stored in each JSON as `rng_key`, combining seed, part count, machine count, material count, and replication index. Stored time coefficients are already scaled to the final minute-based values; do not apply an additional scaling factor.

See [DATA_FORMAT.md](DATA_FORMAT.md) for the data schema and processing-time definition. This release contains benchmark inputs and the generator, not solver implementations, schedules, or claimed optimal objective values.
