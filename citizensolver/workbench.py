"""User-facing objective definitions and filtered ship searches."""
from dataclasses import replace
from .optimizer import Search, optimize
from .engine import ModelError
from .market import limits, exclusion

OBJECTIVES = [
    {"id": "custom", "name": "My priorities", "category": "Priorities", "detail": "Split 100% across the stats you care about. Higher priority gives a stat more influence on the ranking, not a promised percentage improvement.", "metric": "duration_dps", "unit": "DPS"},
    {"id": "balanced", "name": "Damage + stealth", "category": "Combat", "detail": "Keep most of your firepower while reducing EM and IR.", "metric": "duration_dps", "unit": "DPS"},
    {"id": "damage", "name": "Sustained damage", "category": "Combat", "detail": "Maximize repeating gun damage before ballistic ammo runs out.", "metric": "sustained_dps", "unit": "DPS"},
    {"id": "burst", "name": "Burst damage", "category": "Combat", "detail": "Maximize damage while all guns are firing.", "metric": "burst_dps", "unit": "DPS"},
    {"id": "alpha", "name": "First-strike damage", "category": "Combat", "detail": "Maximize the damage of one complete salvo.", "metric": "alpha", "unit": "damage"},
    {"id": "stealth", "name": "Lowest signatures", "category": "Combat", "detail": "Minimize the larger of estimated EM and IR, while retaining your chosen damage.", "metric": "em", "unit": "EM"},
    {"id": "shields", "name": "Shield capacity", "category": "Defense", "detail": "Maximize shield HP with a power- and cooling-feasible loadout.", "metric": "shield_hp", "unit": "HP"},
    {"id": "shield_regen", "name": "Shield regeneration", "category": "Defense", "detail": "Maximize modeled shield regeneration per second.", "metric": "shield_regen", "unit": "HP/s"},
    {"id": "handling", "name": "Maneuverability", "category": "Flight", "detail": "Maximize average rated pitch and yaw. Roll is shown separately; acceleration and pip effects are not simulated.", "metric": "handling", "unit": "°/s"},
    {"id": "speed", "name": "Straight-line speed", "category": "Flight", "detail": "Maximize the exported maximum speed rating. This is not quantum travel speed or loaded atmospheric performance.", "metric": "max_speed", "unit": "m/s"},
    {"id": "scm_speed", "name": "Combat speed", "category": "Flight", "detail": "Maximize the unboosted SCM speed rating.", "metric": "scm_speed", "unit": "m/s"},
    {"id": "cargo", "name": "Cargo capacity", "category": "Utility", "detail": "Compare cargo-grid SCU between ships. Ore bags and personal storage are separate; this does not change the cargo grid.", "metric": "cargo_scu", "unit": "SCU"},
    {"id": "pve", "name": "PvE combat", "category": "Activity presets", "detail": "Favor damage over the engagement and shield capacity, with a small handling preference.", "metric": "duration_dps", "unit": "DPS", "weights": "Damage 70% · shields 25% · pitch 5% (normalized stats)"},
    {"id": "pvp", "name": "PvP combat", "category": "Activity presets", "detail": "Handling comes first, followed by engagement damage and shields. An initial preference model, not a prediction of duel outcomes.", "metric": "handling", "unit": "°/s", "weights": "Handling 75% · damage 20% · shields 5% (bounded utility scores)"},
]
ROADMAP = [
    {"name": "Cargo hauling", "detail": "Cargo grids, container sizes, loading access, travel time, fuel and survivability. Cargo capacity is available now; route profit and loading time are not yet modeled."},
    {"name": "Mining", "detail": "Fracturing capability, stability, extraction rate, ore-bag capacity and crew. Ordinary cargo SCU cannot stand in for mining capacity."},
    {"name": "Other player goals", "detail": "Quantum range, fuel endurance, low running cost, solo practicality, salvage throughput, interception and escape performance are candidates for later objectives."},
]


def search_workbench(catalogue, body, progress=lambda *args: None, market=None):
    market = market or {"ships": {}}
    limits(body)
    scope = body.get("scope", "ship")
    goal = body.get("goal", "balanced")
    if scope not in {"ship", "class"} or goal not in {x["id"] for x in OBJECTIVES}:
        raise ValueError("Unknown search scope or objective")
    settings = body.get("search", {})
    if not isinstance(settings, dict):
        raise ValueError("Search settings must be an object")
    request = Search(**{**settings, "goal": "balanced" if goal == "cargo" else goal})
    if goal == "cargo" and (any((request.min_shield, request.min_dps, request.min_pitch, request.min_yaw,
                                request.min_range, request.min_velocity)) or request.max_em is not None or request.max_ir is not None):
        raise ValueError("Cargo capacity compares stock cargo grids. Use My priorities to combine cargo with combat constraints.")
    if scope == "ship":
        ships = [catalogue.ship(body["ship"])]
    else:
        crew = body.get("max_crew")
        if crew is not None and (type(crew) is not int or crew < 1):
            raise ValueError("Crew limit must be a positive integer")
        ships = [catalogue.ships[s["id"]] for s in catalogue.list_ships(body.get("role") or None)
                 if crew is None or isinstance(s["crew"], (int, float)) and s["crew"] <= crew]
    results, skipped, reports = [], [], []
    considered = len(ships)
    eligible = []
    for ship in ships:
        reason = exclusion(market["ships"].get(ship["ClassName"].casefold(), {}), body)
        if reason:
            skipped.append({"ship": ship["ClassName"], "name": ship["Name"], "reason": reason})
        else:
            eligible.append(ship)
    ships = eligible
    baseline = None
    for index, ship in enumerate(ships):
        progress(index, len(ships), ship["Name"])
        if goal == "cargo":
            cargo = ship.get("Cargo")
            if not isinstance(cargo, (int, float)) or cargo < 0:
                skipped.append({"ship": ship["ClassName"], "reason": "Cargo capacity is not known"})
                continue
            flight = ship.get("FlightCharacteristics") or {}
            rates, speeds = flight.get("AngularRates", {}), flight.get("Speeds", {})
            results.append({"ship": {"id": ship["ClassName"], "name": ship["Name"], "role": ship.get("Role")},
                            "score": cargo, "kind": "ship", "metrics": {"cargo_scu": cargo,
                            "pitch": rates.get("Pitch"), "yaw": rates.get("Yaw"), "max_speed": speeds.get("Max"),
                            "shield_hp": ship.get("ShieldHp")}, "data": catalogue.manifest,
                            "cargo_grids": ship.get("CargoGrids", []), "crew": ship.get("Crew"),
                            "assumptions": ["Exported cargo-grid capacity; not ore capacity, loose cargo or personal storage.",
                                            "Stock ship ratings; this ranking does not change equipment or model hauling profit."]})
            continue
        try:
            report = optimize(catalogue, ship, request if scope == "ship" else replace(request, limit=1))
            if scope == "ship":
                baseline = report["baseline"]
            results.extend(report["results"])
            reports.append({"ship": ship["ClassName"], **report["search"]})
            if not report["results"]:
                skipped.append({"ship": ship["ClassName"], "reason": report["message"]})
        except ModelError as exc:
            skipped.append({"ship": ship["ClassName"], "reason": str(exc)})
    progress(len(ships), len(ships), "Finished")
    for result in results:
        result["market"] = market["ships"].get(result["ship"]["id"].casefold(), {})
    results.sort(key=lambda r: r["score"], reverse=True)
    return {"scope": scope, "goal": goal, "results": results[:request.limit], "baseline": baseline,
            "request": body, "ships_considered": considered, "ships_eligible": len(ships), "skipped": skipped, "searches": reports,
            "market_downloaded_at": market.get("downloaded_at"),
            "data": catalogue.manifest, "globally_optimal": False if goal != "cargo" else None}
