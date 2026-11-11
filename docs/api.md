# Local API

Run `python -m citizensolver serve --port 8765`. The development server listens only on `127.0.0.1`, performs no writes/downloads, and runs one optimization at a time. There is no UI or authentication. Do not expose this server directly to the Internet. A production adapter can call the same Python functions later.

## Reads

- `GET /api/health`: model version and full snapshot provenance.
- `GET /api/ships`: ship id, name, role, crew and size.
- `GET /api/ships?role=Medium%20Fighter`: exact role filter.

## Evaluate

`POST /api/evaluate`, `Content-Type: application/json`:

```json
{"ship":"RSI_Meteor","profile":"damage","duration":120,"swaps":{}}
```

`ship` is a class id or unambiguous name. `swaps` maps exact exported port ids to component class ids; obtain them from `python -m citizensolver components RSI_Meteor --json`. Unknown, locked and incompatible swaps are rejected.

Optional `pips` supplies a complete mapping of powered port ids and `weapons` to integer allocations. Copy the `power.allocation` from an evaluated result and adjust within `power.bounds`. If present it replaces the automatic profile allocation. Bounds errors return 400; a within-bounds but over-budget or undercooled build returns `feasible: false` with violations.

## Optimize

`POST /api/optimize`:

```json
{
  "ship":"RSI_Meteor",
  "search":{
    "goal":"stealth",
    "duration":120,
    "damage_floor":0.9,
    "min_range":2000,
    "min_shield":4000,
    "beam":6,
    "passes":2,
    "limit":5,
    "max_evaluations":15000
  }
}
```

Other constraints: `min_dps` (finite-duration hull DPS), `min_pitch`, `min_yaw`, `min_velocity`, `max_em`, `max_ir`. JSON fields use snake_case; CLI flags use hyphens. All metrics are numerical, unrounded internally. All responses are JSON.

Errors: 400 invalid input, 403 disallowed Origin, 404 unknown route, 409 search busy, 415 wrong media type. Body limit: 64 KiB. The local API does not enable cross-origin access.

## Python usage

```python
from citizensolver.catalogue import Catalogue
from citizensolver.optimizer import Search, optimize, compare

data = Catalogue()
meteor = optimize(data, data.ship("RSI_Meteor"), Search(goal="stealth"))
fighters = compare(data, role="Medium Fighter", request=Search(goal="pve"))
```

The CLI can write these complete reports with `--out builds/name.json`. A report includes the request, stock baseline, ranked results, search disclosure, full assumptions and source revision. Each build includes exact swaps/pips, per-gun stats, fleet-comparable metrics and feasibility violations.
