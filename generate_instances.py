"""Generate the 180 AM benchmark instances without importing a solver.

Run: .venv\\Scripts\\python.exe generate_instances.py
Optional: --output PATH --base-seed 20261016
An existing destination is never overwritten. Times are synthetic minutes.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROFILES = ((200, 200, 200), (250, 200, 250), (250, 250, 300),
            (300, 250, 300), (300, 300, 350))
SIZE_RANGES = {'small': (20, 70), 'medium': (70, 120), 'large': (120, 180)}
CONFIGURATIONS = {
    'Small': [(n, m, f) for n in (15, 20, 25)
              for m, f in ((2, 2), (2, 3), (3, 2), (3, 3))],
    'Medium': [(n, m, f) for n in (30, 35, 40)
               for m, f in ((3, 2), (3, 3), (5, 3), (5, 5))],
    'Large': [(n, m, f) for n in (60, 80, 100)
              for m, f in ((5, 3), (5, 5), (7, 3), (7, 5))],
}
REPLICATIONS = 5
TIME_FACTOR = 3.5


def generate_instance(n, machine_count, material_count, seed, replicate):
    """Retain MIP.py's sampling order and parameter distributions.

    Each instance receives a distinct integer seed. The reproducible stream key
    includes the configuration and replication index, as in MIP.random_instance.
    The replication index is metadata only, not part of the displayed name.
    """
    if n < material_count or min(n, machine_count, material_count, replicate) < 1:
        raise ValueError('Positive sizes and n >= material_count are required.')
    configuration = f'P{n}_M{machine_count}_F{material_count}'
    rng_key = f'{seed}:{n}:{machine_count}:{material_count}:{replicate}'
    rng = random.Random(rng_key)
    materials = [f'F{i}' for i in range(1, material_count + 1)]
    labels = materials + [rng.choice(materials) for _ in range(n - material_count)]
    rng.shuffle(labels)
    parts = []
    for part_id, material in enumerate(labels, 1):
        category = rng.choices(['small', 'medium', 'large'], [.3, .4, .3])[0]
        lo, hi = SIZE_RANGES[category]
        length = rng.randint(lo, hi)
        width = rng.randint(lo, hi)
        height = rng.randint(10, 150)
        fill = rng.uniform(.1, .6)
        parts.append(dict(id=part_id, material=material, length=length, width=width,
                          height=height, volume=fill * length * width * height,
                          size_category=category, volume_ratio=fill))
    machines = []
    for machine_id in range(1, machine_count + 1):
        profile = rng.randrange(len(PROFILES))
        length, width, height = PROFILES[profile]
        machines.append(dict(
            id=machine_id, profile=profile + 1, length=length, width=width, height=height,
            tau={f: rng.uniform(.1, .3) for f in materials},
            alpha={f: rng.uniform(.005, .020) for f in materials},
            beta={f: 1e-6 * rng.uniform(1, 4) for f in materials},
            initial={f: rng.uniform(.2, 1.0) for f in materials},
            setup={f: {g: rng.uniform(.1, .3) if f == g else rng.uniform(.2, 1.2)
                       for g in materials} for f in materials}))
    for machine in machines:
        for key in ('tau', 'alpha', 'beta', 'initial'):
            machine[key] = {f: value * TIME_FACTOR for f, value in machine[key].items()}
        machine['setup'] = {
            f: {g: value * TIME_FACTOR for g, value in transitions.items()}
            for f, transitions in machine['setup'].items()}
    return dict(name=f'{configuration}_seed{seed}_min', configuration=configuration,
                units=dict(length='mm', volume='mm^3', time='min'),
                numeric_time_factor_from_original_hour_data=TIME_FACTOR,
                seed=seed, replication_index=replicate, rng_key=rng_key,
                parts=parts, machines=machines)


def validate_instance(data, n, machine_count, material_count):
    """Check schema, distributions, material coverage and individual eligibility."""
    def require(condition, message):
        if not condition:
            raise ValueError(f'{data["name"]}: {message}')

    def in_range(value, lo, hi):
        return math.isfinite(value) and lo - 1e-12 <= value <= hi + 1e-12

    parts, machines = data['parts'], data['machines']
    materials = {f'F{i}' for i in range(1, material_count + 1)}
    require(len(parts) == n and len(machines) == machine_count, 'incorrect counts')
    require([p['id'] for p in parts] == list(range(1, n + 1)), 'part IDs')
    require([m['id'] for m in machines] == list(range(1, machine_count + 1)), 'machine IDs')
    require({p['material'] for p in parts} == materials, 'missing material')
    for p in parts:
        lo, hi = SIZE_RANGES[p['size_category']]
        require(all(isinstance(p[k], int) and lo <= p[k] <= hi
                    for k in ('length', 'width')), 'footprint range')
        require(isinstance(p['height'], int) and 10 <= p['height'] <= 150, 'height range')
        require(in_range(p['volume_ratio'], .1, .6), 'volume ratio')
        box_volume = p['length'] * p['width'] * p['height']
        require(0 < p['volume'] <= box_volume and
                math.isclose(p['volume'], p['volume_ratio'] * box_volume), 'volume')
        for m in machines:
            fits = ((p['length'] <= m['length'] and p['width'] <= m['width']) or
                    (p['width'] <= m['length'] and p['length'] <= m['width']))
            require(fits and p['height'] <= m['height'], 'individual machine eligibility')
    ranges = {'tau': (.35, 1.05), 'alpha': (.0175, .07),
              'beta': (3.5e-6, 14e-6), 'initial': (.7, 3.5)}
    for m in machines:
        require(tuple(m[k] for k in ('length', 'width', 'height')) ==
                PROFILES[m['profile'] - 1], 'capacity profile')
        for key, (lo, hi) in ranges.items():
            require(set(m[key]) == materials, f'{key} material coverage')
            require(all(in_range(v, lo, hi) for v in m[key].values()), f'{key} range')
        require(set(m['setup']) == materials, 'setup rows')
        for f in materials:
            require(set(m['setup'][f]) == materials, 'setup columns')
            for g in materials:
                lo, hi = (.35, 1.05) if f == g else (.7, 4.2)
                require(in_range(m['setup'][f][g], lo, hi), 'setup range')


def generate_suite(output, base_seed=20261016):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f'Destination already exists; choose a new --output: {output}')
    # Prepare and validate every instance before writing the new directory.
    records, payloads = [], []
    for group, configurations in CONFIGURATIONS.items():
        for n, m, f in configurations:
            for replicate in range(1, REPLICATIONS + 1):
                seed = base_seed + len(records)
                data = generate_instance(n, m, f, seed, replicate)
                data['instance_group'] = group
                validate_instance(data, n, m, f)
                relative = Path(group) / data['configuration'] / f'seed_{seed}.json'
                content = (json.dumps(data, indent=2, allow_nan=False) + '\n').encode('utf-8')
                records.append(dict(group=group, configuration=data['configuration'],
                                    parts=n, machines=m, materials=f, seed=seed,
                                    replication_index=replicate, name=data['name'],
                                    file=relative.as_posix(),
                                    sha256=hashlib.sha256(content).hexdigest()))
                payloads.append((relative, content))
    if len(records) != 180 or len({r['seed'] for r in records}) != 180:
        raise ValueError('Expected 180 instances with distinct seeds.')
    output.mkdir(parents=True, exist_ok=False)
    for relative, content in payloads:
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        if target.read_bytes() != content:
            raise OSError(f'Write verification failed: {target}')
    with (output / 'manifest.csv').open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    readme = f'''# AM benchmark instances

180 instances: 12 configurations x 5 seeds in each of Small, Medium and Large.
Lengths/heights: mm. Actual volumes: mm^3. Processing/setup times: min.
These are synthetic parameters, not calibrated equipment operating data.

Each configuration has five distinct seeds. All 180 seeds are globally unique,
from {base_seed} through {base_seed + 179}, assigned in the generator's listed order.
The exact Python random.Random stream key is stored in each JSON as rng_key:
seed:n:machine_count:material_count:replication_index.
The replication index is metadata; file names use seeds, not _R identifiers.
The unique name inside each JSON prevents solver output-directory collisions.

Both MIP.py and LBBD.py accept these JSON files using --input PATH.
No solver is imported or run by generate_instances.py.
manifest.csv lists all files, dimensions, seeds and SHA-256 checksums.
To reproduce: python generate_instances.py --base-seed {base_seed} --output NEW_FOLDER
The script refuses to overwrite an existing destination.

## Distributions (same for all groups)
- Machine profiles: uniform choice of (L, W, H) in mm:
  {PROFILES}
- Part categories: small/medium/large with probabilities 0.3/0.4/0.3.
- Conditional on category, length and width are independent integer uniform:
  [20,70], [70,120], [120,180], respectively.
- Height: integer uniform [10,150]; volume ratio: uniform [0.1,0.6].
- Actual volume = ratio x length x width x height.
- Each material appears at least once; remaining material labels are sampled
  uniformly, and the complete label list is shuffled.
- tau: uniform [0.35,1.05] min; alpha: [0.0175,0.07] min/mm;
  beta: [3.5e-6,14e-6] min/mm^3.
- Initial setup: [0.7,3.5] min; same-material setup: [0.35,1.05] min;
  different-material setup: [0.7,4.2] min, sampled for each directed pair.
- No triangle-inequality restrictions or forced violations are imposed.
- Sampling order and coefficient scaling match MIP.py's random generator.
  Distinct seeds mean these are new instances, not the earlier pilot data.

All instances are validated for parameter ranges, material coverage, volume
consistency and the ability of every machine to process every part individually.
No batch packing, schedule or optimal objective is claimed by data generation.
'''
    (output / 'README.md').write_text(readme, encoding='utf-8')
    print(f'Generated and validated {len(records)} instances in {output}')
    for group in CONFIGURATIONS:
        print(f'{group}: 12 configurations, 60 instances')
    print(f'Seeds: {base_seed}..{base_seed + 179}; no optimization was performed.')
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'benchmark_instances_180_revised')
    parser.add_argument('--base-seed', type=int, default=20261016)
    args = parser.parse_args()
    generate_suite(args.output, args.base_seed)


if __name__ == '__main__':
    main()
