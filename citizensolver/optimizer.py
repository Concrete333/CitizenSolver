"""Bounded, deterministic beam search; never claims a global optimum."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import time

from .engine import ModelError, ShipModel

GOALS = ("damage", "burst", "alpha", "stealth", "balanced", "pve", "pvp", "shields", "shield_regen", "handling", "speed", "scm_speed", "custom")
PRIORITIES = {"firepower": ("duration_dps", 1500), "shields": ("shield_hp", 10000),
              "stealth": ("signature", 10000), "handling": ("handling", 60),
              "speed": ("max_speed", 1000), "hull": ("hull_hp", 20000),
              "armor": ("armor_hp", 10000), "cargo": ("cargo_scu", 100)}


@dataclass(frozen=True)
class Search:
    goal: str = "balanced"
    duration: float = 120
    beam: int = 6
    passes: int = 2
    limit: int = 5
    damage_floor: float = 0.9
    min_shield: float = 0
    min_dps: float = 0
    min_pitch: float = 0
    min_yaw: float = 0
    min_range: float = 0
    min_velocity: float = 0
    max_em: float | None = None
    max_ir: float | None = None
    max_evaluations: int = 15000
    weights: dict = field(default_factory=lambda: {"firepower": 50, "stealth": 50})

    def __post_init__(self):
        if self.goal not in GOALS:
            raise ValueError(f"Goal must be one of {GOALS}")
        for name, low, high in (("beam", 3, 24), ("passes", 1, 4), ("limit", 1, 50), ("max_evaluations", 10, 100000)):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{name} must be an integer in {low}..{high}")
        for name in ("duration", "damage_floor", "min_shield", "min_dps", "min_pitch", "min_yaw", "min_range", "min_velocity", "max_em", "max_ir"):
            value = getattr(self, name)
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                raise ValueError(f"{name} must be a finite, nonnegative number")
        if not 1 <= self.duration <= 3600 or not 0 <= self.damage_floor <= 1:
            raise ValueError("Duration must be 1..3600 seconds and damage_floor 0..1")
        if (not isinstance(self.weights, dict) or not self.weights or set(self.weights) - PRIORITIES.keys()
            or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 100 for v in self.weights.values())
            or not math.isclose(sum(self.weights.values()), 100, abs_tol=1e-6)):
            raise ValueError("Priority percentages must total 100")


def score(metrics, goal, weights=None):
    dps = metrics["duration_dps"]
    signature = max(metrics["em"], metrics["ir"] or 0)
    if goal == "custom":
        return sum(weight / 100 * utility(metrics, key) for key, weight in weights.items() if weight)
    if goal == "damage":
        return metrics["sustained_dps"]
    if goal == "burst":
        return metrics["burst_dps"]
    if goal == "alpha":
        return metrics["alpha"]
    if goal == "stealth":
        return -signature
    if goal == "shields":
        return metrics["shield_hp"]
    if goal == "shield_regen":
        return metrics["shield_regen"]
    if goal == "handling":
        return metrics["handling"] or 0
    if goal in {"speed", "scm_speed"}:
        return metrics["max_speed" if goal == "speed" else "scm_speed"] or 0
    if goal == "pvp":
        # Bounded utility terms keep handling dominant regardless of raw stat scale.
        handling = (metrics["handling"] or 0) / ((metrics["handling"] or 0) + 60)
        damage = dps / (dps + 1500)
        shield = metrics["shield_hp"] / (metrics["shield_hp"] + 5000)
        return .75 * handling + .20 * damage + .05 * shield
    if goal == "pve":
        # Explicit fixed units prevent the cohort changing the meaning of the score.
        return .7 * dps / 1000 + .25 * metrics["shield_hp"] / 10000 + .05 * (metrics["pitch"] or 0) / 100
    return dps / (1 + signature / 10000)


def utility(metrics, key):
    metric, scale = PRIORITIES[key]
    if key == "stealth":
        value = max(metrics["em"], metrics["ir"]) if metrics.get("em") is not None and metrics.get("ir") is not None else None
    else:
        value = metrics.get(metric)
    if value is None or value < 0:
        return 0
    return scale / (scale + value) if key == "stealth" else value / (scale + value)


def known_priorities(metrics, weights):
    for key, weight in weights.items():
        if not weight:
            continue
        required = ("em", "ir") if key == "stealth" else (PRIORITIES[key][0],)
        if any(metrics.get(k) is None for k in required):
            return False
    return True


def meets(metrics, request):
    return (metrics["shield_hp"] >= request.min_shield and metrics["duration_dps"] >= request.min_dps
            and (metrics["pitch"] or 0) >= request.min_pitch and (metrics["yaw"] or 0) >= request.min_yaw
            and metrics["minimum_weapon_range"] >= request.min_range
            and metrics["minimum_projectile_speed"] >= request.min_velocity
            and (request.max_em is None or metrics["em"] <= request.max_em)
            and (request.max_ir is None or metrics["ir"] is not None and metrics["ir"] <= request.max_ir))


def dominates(a, b):
    """Trade-offs among finite-duration damage, EM, IR and shield HP."""
    def vector(m):
        return (m["duration_dps"], -m["em"], -(m["ir"] if m["ir"] is not None else math.inf), m["shield_hp"])
    va, vb = vector(a), vector(b)
    return all(x >= y for x, y in zip(va, vb)) and any(x > y for x, y in zip(va, vb))


def optimize(catalogue, ship, request=None):
    request = request or Search()
    started = time.monotonic()
    model = ShipModel(catalogue, ship)
    if request.goal in {"damage", "burst", "alpha", "pve", "pvp", "balanced"} and not model.pilot_ports:
        raise ModelError("No verified pilot-controlled guns for this combat objective")
    baseline = model.evaluate(duration=request.duration)
    archive = {}
    errors = dict(model.excluded)
    exhausted = False

    def evaluate(swaps):
        nonlocal exhausted
        states = []
        swaps = {k: v for k, v in swaps.items() if v != model.stock.get(k)}
        signature = tuple(sorted(swaps.items()))
        for profile in ("damage", "balanced", "stealth"):
            key = (signature, profile)
            if key not in archive:
                if len(archive) >= request.max_evaluations:
                    exhausted = True
                    break
                try:
                    result = model.evaluate(swaps, profile=profile, duration=request.duration)
                except ModelError as exc:
                    errors[str(signature)] = str(exc)
                    continue
                archive[key] = {"swaps": swaps, "profile": profile, "metrics": result["metrics"],
                                "feasible": result["feasible"], "key": key}
            states.append(archive[key])
        return states

    def beam_from(states):
        unique = {s["key"]: s for s in states}
        pool = list(unique.values())
        chosen = []
        # Keep damage and signature extremes alive even while searching for a compromise.
        goals = [request.goal, "damage", "stealth"]
        lists = [sorted(pool, key=lambda s: (s["feasible"], meets(s["metrics"], request), score(s["metrics"], g, request.weights)), reverse=True)
                 for g in goals]
        seen = set()
        index = 0
        while len(chosen) < request.beam and any(index < len(rows) for rows in lists):
            for rows in lists:
                if index < len(rows):
                    state = rows[index]
                    equipment = state["key"][0]
                    if equipment not in seen:
                        chosen.append(state)
                        seen.add(equipment)
                        if len(chosen) == request.beam:
                            break
            index += 1
        return chosen

    beam = beam_from(evaluate({}))
    # First pass changes interchangeable slots together; following passes allow mixed fits.
    groups = {}
    for port, choices in model.variables:
        groups.setdefault(choices, []).append(port)
    completed_passes = 0
    for pass_index in range(request.passes):
        dimensions = [(ports, choices) for choices, ports in groups.items()] if pass_index == 0 else [([port], choices) for port, choices in model.variables]
        for ports, choices in dimensions:
            candidates = list(beam)
            for state in beam:
                for choice in choices:
                    swaps = {**state["swaps"], **dict.fromkeys(ports, choice)}
                    candidates.extend(evaluate(swaps))
                    if exhausted:
                        break
                if exhausted:
                    break
            beam = beam_from(candidates)
            if exhausted:
                break
        if exhausted:
            break
        completed_passes += 1
    feasible = [s for s in archive.values() if s["feasible"] and meets(s["metrics"], request)]
    if request.goal == "custom":
        feasible = [s for s in feasible if known_priorities(s["metrics"], request.weights)]
    required = {"handling": "pitch", "speed": "max_speed", "scm_speed": "scm_speed"}.get(request.goal)
    if required:
        feasible = [s for s in feasible if s["metrics"].get(required) is not None
                    and (request.goal != "handling" or s["metrics"].get("yaw") is not None)]
    best_damage = max((s["metrics"]["duration_dps"] for s in feasible), default=0)
    if request.goal in {"stealth", "balanced"}:
        feasible = [s for s in feasible if s["metrics"]["duration_dps"] >= request.damage_floor * best_damage - 1e-8]
    ranked = sorted(feasible, key=lambda s: (score(s["metrics"], request.goal, request.weights), s["metrics"]["duration_dps"]), reverse=True)
    selected = []
    seen_results = set()
    seen_metrics = set()
    for state in ranked:
        result = model.evaluate(state["swaps"], profile=state["profile"], duration=request.duration)
        # Profiles producing identical equipment and pips are the same build.
        identity = (state["key"][0], tuple(sorted(result["power"]["allocation"].items())))
        # Stat-identical alternatives obscure the trade-offs; keep one exact fit.
        metric_identity = tuple((k, round(v, 6) if v is not None else None) for k, v in sorted(result["metrics"].items()))
        if identity in seen_results or metric_identity in seen_metrics:
            continue
        seen_results.add(identity)
        seen_metrics.add(metric_identity)
        result["score"] = score(result["metrics"], request.goal, request.weights)
        if request.goal == "custom":
            result["priority_scores"] = {k: utility(result["metrics"], k) * 100 for k, w in request.weights.items() if w}
        result["nondominated_in_searched_candidates"] = not any(dominates(s["metrics"], state["metrics"]) for s in feasible)
        selected.append(result)
        if len(selected) == request.limit:
            break
    return {"request": asdict(request), "baseline": baseline, "results": selected,
            "search": {"algorithm": "deterministic beam, grouped then individual slots; three power profiles",
                       "globally_optimal": False, "evaluations": len(archive),
                       "completed_passes": completed_passes, "evaluation_limit_reached": exhausted,
                       "seconds": time.monotonic() - started,
                       "best_feasible_duration_dps_found": best_damage,
                       "excluded_components": errors,
                       "scope": "Installed pilot guns, shields, power plants, coolers, radar and flight blades. Mount topology and other equipment stay stock."},
            "message": "Candidates found" if selected else "No modeled feasible build satisfies these constraints"}


def compare(catalogue, role="Medium Fighter", request=None, ship_ids=None):
    request = request or Search(goal="pve")
    ids = ship_ids or [s["id"] for s in catalogue.list_ships(role)]
    results, skipped = [], []
    for ship_id in ids:
        try:
            report = optimize(catalogue, catalogue.ship(ship_id), request)
            results.extend(report["results"][:1])
            if not report["results"]:
                skipped.append({"ship": ship_id, "reason": report["message"]})
        except ModelError as exc:
            skipped.append({"ship": ship_id, "reason": str(exc)})
    results.sort(key=lambda r: r["score"], reverse=True)
    return {"request": asdict(request), "role": role, "results": results[:request.limit],
            "ships_considered": len(ids), "skipped": skipped, "globally_optimal": False,
            "data": catalogue.manifest}
