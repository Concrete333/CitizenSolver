# Local API

Run `python -m citizensolver serve --port 8765`, or use the desktop launcher. The development server listens only on `127.0.0.1`, serves the workbench at `/`, and runs one optimization or market refresh at a time. No authentication is implemented. Do not expose this server directly to the Internet. A production adapter can call the same Python functions later.

## Reads

- `GET /api/health`: model version and full snapshot provenance.
- `GET /api/ships`: ship id, name, role, crew and size.
- `GET /api/ships?role=Medium%20Fighter`: exact role filter.
- `GET /api/options`: goals, roles, ship list, hangar labels, data provenance and cached price/fit records. Numeric game `size` in `/api/ships` is **not** a hangar size.

## Browser searches

`POST /api/search` returns HTTP 202 with a job `id`. Read `GET /api/jobs/<id>` until `status` is `complete` (with `result`) or `error` (with `error`). Progress contains completed/total ships and the current ship name. The latest four jobs are kept in memory; restarting loses them.

```json
{
  "scope": "class",
  "role": "Medium Fighter",
  "goal": "custom",
  "max_usd": 300,
  "max_auec": 5000000,
  "require_ingame": true,
  "hangar": "Small",
  "search": {
    "weights": {"handling": 75, "firepower": 20, "shields": 5},
    "duration": 120, "beam": 3, "passes": 1, "limit": 5
  }
}
```

Use `scope: "ship"` and `ship: "RSI_Meteor"` for a single hull. `max_crew` filters ship comparisons. `hangar` is the largest permitted class: Small, Medium, Large or Extra Large. Budgets are inclusive and conjunctive. Missing required evidence excludes a ship, even in single-ship mode. Results include exclusions and market provenance.

Custom weights total 100; omitted dimensions have zero weight. Keys: `firepower`, `shields`, `stealth`, `handling`, `speed`, `hull`, `armor`, `cargo`. A positive priority with an unknown stat excludes that build. `goal: "cargo"` is a separate stock cargo-grid comparison, not an equipment optimization; it rejects combat constraints instead of ignoring them.

`POST /api/market/refresh` with `{}` starts a job that fetches the public FleetYards model pages and atomically replaces `data/market.json`. `POST /api/equipment/refresh` similarly loads UEX NPC component listings into `data/equipment-market.json`. Failed downloads leave the old cache intact. Other endpoints do not download data or write user files.

Search settings accept `equipment_mode: "best"` (default) or `"shop"`. Shop mode requires a downloaded component cache and permits stock equipment plus exact-UUID NPC-listed upgrades. `seed_swaps` supplies the starting fit; `locks` maps ports to components that the search must retain. Both use exact ids and are validated for compatibility. They apply only to one selected ship, never to a class search. Component locks do not lock power allocation. Unlisted locked upgrades are rejected in shop mode.

`GET /api/components?ship=RSI_Meteor` returns modeled ports, stock ids, compatible choices, seller reports and the active revision for the optional editor. It does not expose arbitrary mount changes. Editor requests carry `revision`; a mismatch returns 400 before evaluation/search. `/api/options` includes component-cache download time and count. Evaluations and workbench results include `stealth`, `maneuverability`, per-component `purchase` evidence and `equipment_source`.

## Evaluate

`POST /api/evaluate`, `Content-Type: application/json`:

```json
{"ship":"RSI_Meteor","profile":"damage","duration":120,"swaps":{}}
```

`ship` is a class id or unambiguous name. `swaps` maps exact exported port ids to component class ids; obtain them through `/api/components`. Unknown, fixed and incompatible swaps are rejected. Manual evaluation checks physical feasibility, not the original search's budget, range or priority constraints; the UI states that distinction.

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

Other constraints: `min_dps` (finite-duration hull DPS), `min_pitch`, `min_yaw`, `min_velocity`, `max_em`, `max_ir`. JSON fields use snake_case; CLI flags use hyphens. Known metrics are numerical, unrounded internally; unknown metrics are null. API responses are JSON.

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
