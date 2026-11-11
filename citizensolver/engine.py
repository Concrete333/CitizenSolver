"""Deterministic experimental SCM model. See docs/model.md for assumptions."""
from __future__ import annotations

from functools import lru_cache
import math

from .catalogue import kind, walk_ports
from .insights import stealth_profile, handling_profile

MODEL_VERSION = "scm-estimate-3"
ASSUMPTIONS = [
    "Experimental model; selected Meteor fits calibrated against erkul on 4.10.2-LIVE.12913470, not validated in game.",
    "SCM, stationary, undamaged, fixed weapons, primary firing mode, all shots hit; no armor/penetration simulation.",
    "Energy capacitor capacity and recharge scale with the weapon group's allocated power divided by its total rated demand. Ship capacitor buffs and synchronized firing groups are not simulated.",
    "EM/IR are steady-state estimates, not detection distances or transient firing/boost signatures.",
    "Flight rates are exported blade ratings; power-dependent handling and atmospheric flight are not simulated.",
    "Catalogue compatibility does not establish shop availability or ownership; crafted quality and attachment customization are excluded.",
]


class ModelError(ValueError):
    pass


def number(value, default=0.0):
    return float(value) if isinstance(value, (int, float)) and math.isfinite(value) else default


def network(item):
    return item.get("ResourceNetwork") or {}


def usage(item, resource="Power", bound="Maximum"):
    return number(network(item).get("Usage", {}).get(resource, {}).get(bound))


def emission(item, field="Maximum"):
    return number((item.get("Emission") or {}).get("Em", {}).get(field))


def modifier(item, pips):
    ranges = [r for state in network(item).get("States", []) if state.get("Name") == "Online"
              for r in state.get("PowerRanges", []) if r.get("RegisterRange") and r["Start"] <= pips]
    return number(max(ranges, key=lambda r: r["Start"])["Modifier"], 1) if ranges else 1.0


def powered_fraction(item, allocated):
    maximum = usage(item)
    return min(1.0, allocated / maximum) if maximum else 1.0


def firing_rate(mode):
    """Shots/second, including the delays between a repeating sequence's actions."""
    if mode.get("FireType") != "sequence":
        return number(mode.get("RoundsPerMinute")) / 60
    entries = mode.get("SequenceEntries") or []
    if mode.get("SequenceMode") not in {"Looping", "Automatically"} or not entries:
        raise ModelError("Sequence timing is missing or unsupported; import complete local records")
    shots = seconds = 0
    payload = None
    for entry in entries:
        if entry.get("FireType") != "single":
            raise ModelError("Only single-shot actions in repeating sequences are modeled")
        signature = tuple(entry.get(k) for k in ("AmmoPerShot", "PelletsPerShot", "ProjectileType", "DamageMultiplier", "HeatPerShot"))
        if payload is not None and signature != payload:
            raise ModelError("Mixed projectiles or damage within a sequence are not modeled")
        payload = signature
        delay, repeats = number(entry.get("Delay")), entry.get("Repetitions")
        if delay <= 0 or type(repeats) is not int or repeats <= 0:
            raise ModelError("Invalid sequence delay or repetition count")
        if entry.get("Unit") == "RPM":
            interval = 60 / delay
        elif entry.get("Unit") == "Seconds":
            interval = delay
        else:
            raise ModelError("Unsupported sequence delay unit")
        shots += repeats
        seconds += interval * repeats
    return shots / seconds


def _finite_damage(alpha, rate, shots, downtime, duration, ammo=None, firing_seconds=None):
    """Continuous firing windows, explicit full recharge/overheat pauses, finite ammo cap."""
    if rate <= 0 or shots <= 0:
        return 0.0
    if math.isinf(shots):
        count = duration * rate
    else:
        firing = shots / rate if firing_seconds is None else firing_seconds
        cycle = firing + downtime
        cycles = math.floor(duration / cycle)
        remainder = max(0, duration - cycles * cycle)
        count = cycles * shots + (shots if remainder >= firing else min(shots, remainder * rate))
    if ammo is not None:
        count = min(count, ammo)
    return max(0.0, count * alpha)


def weapon_stats(item, power_ratio=1.0, duration=120.0):
    weapon = item.get("Weapon") or {}
    modes = weapon.get("Modes", [])
    if not modes:
        raise ModelError(f"Missing firing data: {item.get('Name')}")
    mode = modes[0]
    if mode.get("FireType") not in {"single", "rapid", "sequence"} or mode.get("ShotCount", 1) != 1:
        raise ModelError(f"Unsupported primary fire mode: {item.get('Name')}")
    rate = firing_rate(mode)
    ammo_cost = number(mode.get("AmmoPerShot"), 1)
    if rate <= 0 or ammo_cost <= 0:
        raise ModelError(f"Missing firing rate/ammunition cost: {item.get('Name')}")
    # Alpha* fields already include projectile/pellet multipliers from the extractor.
    damage = {k: number(mode.get("Alpha" + k)) for k in ("Physical", "Energy", "Thermal", "Distortion")}
    if not any(damage.values()):
        raise ModelError(f"Missing typed projectile damage: {item.get('Name')}")
    alpha = sum(damage[k] for k in ("Physical", "Energy", "Thermal"))
    cap = weapon.get("Capacitor") or {}
    heat = weapon.get("Heat") or {}
    ammo = None
    shots = math.inf
    firing_seconds = None
    cooldown = 0.0
    if cap:
        fraction = max(0.0, min(1.0, power_ratio))
        load = math.floor(number(cap.get("MaxAmmoLoad")) * fraction + .5)
        regen = number(cap.get("MaxRegenPerSec")) * fraction
        if load <= 0 or regen <= 0:
            raise ModelError(f"No powered capacitor data: {item.get('Name')}")
        shots = math.floor(load / ammo_cost)
        cooldown = number(cap.get("Cooldown")) + load / regen
    else:
        ammunition = item.get("Ammunition") or {}
        capacity = number(ammunition.get("Capacity"))
        if capacity <= 0:
            raise ModelError(f"Unknown finite ammunition: {item.get('Name')}")
        ammo = math.floor(capacity / ammo_cost)
    heat_shots = number(heat.get("ShotsToOverheat"))
    if number(heat.get("HeatPerShot")) > 0 and number(heat.get("OverheatTemperature")) > 0:
        heat_shots = number(heat["OverheatTemperature"]) / number(heat["HeatPerShot"])
    if heat_shots > 0 and heat_shots <= shots:
        # The shot that crosses the thermal threshold still deals damage.
        # Keep the continuous threshold time separate from the whole shot count.
        shots = math.ceil(heat_shots)
        firing_seconds = heat_shots / rate
        # Conservatively allow recharge and heat recovery concurrently after firing stops.
        recharge = (number(cap.get("Cooldown")) + shots * ammo_cost /
                    (number(cap.get("MaxRegenPerSec")) * power_ratio)) if cap else 0
        cooldown = max(number(heat.get("OverheatFixTime")), recharge)
    burst = alpha * rate
    if firing_seconds is None and not math.isinf(shots):
        firing_seconds = shots / rate
    sustained = burst if math.isinf(shots) else alpha * shots / (firing_seconds + cooldown)
    distortion = damage["Distortion"]
    finite = _finite_damage(alpha, rate, shots, cooldown, duration, ammo, firing_seconds)
    fired = _finite_damage(1, rate, shots, cooldown, duration, ammo, firing_seconds)
    return {"name": item["Name"], "id": item["ClassName"], "alpha": alpha, "rounds_per_minute": rate * 60,
            "burst_dps": burst, "sustained_dps": sustained,
            "distortion_alpha": distortion, "distortion_burst_dps": distortion * rate,
            "damage_over_duration": finite, "distortion_over_duration": fired * distortion,
            "duration_dps": finite / duration, "energy": bool(cap),
            "shots_per_cycle": None if math.isinf(shots) else shots,
            "fire_seconds": firing_seconds,
            "recovery_seconds": cooldown, "ammunition_shots": ammo,
            "ammo_trigger_seconds": ammo / rate if ammo is not None else None,
            "projectile_speed_m_s": (item.get("Ammunition") or {}).get("Speed"),
            "range_m": weapon.get("EffectiveRange"), "pellets_per_shot": mode.get("PelletsPerShot"),
            "power_ratio": power_ratio}


class ShipModel:
    def __init__(self, catalogue, ship):
        self.catalogue, self.ship = catalogue, ship
        self.ports = dict((p["PortId"], (p, editable)) for p, editable in walk_ports(ship["Loadout"]))
        self.stock = {key: p["ClassName"] for key, (p, _) in self.ports.items() if p.get("ClassName")}
        self.pilot_ports = set()
        fixed = (ship.get("Weaponry") or {}).get("FixedWeapons", {}).get("Weapons", [])
        # Turret ownership is from extractor control evidence, never from the component name.
        turrets = (ship.get("Weaponry") or {}).get("Turrets", [])
        turret_roots = {t["HardpointName"]: bool(t.get("IsPilotSlaveable")) for t in turrets}
        fixed_classes = {w["ClassName"] for w in fixed}
        for key, (p, _) in self.ports.items():
            if kind(p) != "WeaponGun":
                continue
            owners = [turret_roots[x] for x in p.get("Path", []) if x in turret_roots]
            if (owners and all(owners)) or (not owners and p.get("ClassName") in fixed_classes):
                self.pilot_ports.add(key)
        self.active = {}
        missing = []
        for key, (port, _) in self.ports.items():
            k = kind(port)
            if k in {"WeaponGun", "Shield", "PowerPlant", "Cooler", "Radar", "FlightController", "LifeSupportGenerator"}:
                item = catalogue.items.get(port.get("ClassName"))
                if item is None:
                    missing.append(port.get("ClassName", key))
                elif k != "WeaponGun" or key in self.pilot_ports:
                    self.active[key] = item
        if missing:
            raise ModelError("Missing component records: " + ", ".join(missing))
        if not any(kind(x) == "PowerPlant" for x in self.active.values()):
            raise ModelError("No power plant in the snapshot")
        self.variables = []
        self.excluded = {}
        for key, item in self.active.items():
            p, editable = self.ports[key]
            choices = []
            for candidate in catalogue.options(ship, p, editable):
                if kind(item) == "WeaponGun":
                    try:
                        weapon_stats(catalogue.items[candidate])
                    except ModelError as exc:
                        self.excluded[candidate] = str(exc)
                        continue
                choices.append(candidate)
            if len(choices) > 1:
                self.variables.append((key, tuple(choices)))
        self._weapon_cached = lru_cache(maxsize=8192)(self._weapon)

    def _weapon(self, class_name, ratio, duration):
        return weapon_stats(self.catalogue.items[class_name], ratio, duration)

    def selection(self, swaps):
        selected = dict(self.active)
        for key, name in swaps.items():
            if key not in self.ports:
                raise ValueError(f"Unknown port: {key}")
            p, editable = self.ports[key]
            if key not in self.active:
                raise ValueError(f"Swaps for this subsystem are not modeled: {key}")
            if name not in self.catalogue.options(self.ship, p, editable):
                raise ValueError(f"Incompatible or locked component: {name} on {key}")
            selected[key] = self.catalogue.items[name]
        return selected

    @staticmethod
    def available_power(items):
        plants = [i for i in items.values() if kind(i) == "PowerPlant"]
        n = len(plants)
        if not n:
            return 0
        return sum(math.floor(number(network(i).get("Generation", {}).get("Power")) / n + .5)
                   for i in plants) + (n - 1) * sum(i["Size"] for i in plants)

    def bounds(self, items):
        limits = {}
        for key, item in items.items():
            if kind(item) in {"PowerPlant", "WeaponGun"}:
                continue
            maximum = math.ceil(usage(item))
            if maximum:
                limits[key] = (max(1, math.ceil(usage(item, bound="Minimum"))), maximum)
        raw_weapons = sum(usage(i) for i in items.values() if kind(i) == "WeaponGun")
        pool = (self.ship.get("PowerPools") or {}).get("WeaponGun", {}).get("Size", raw_weapons)
        if pool < 0:
            pool = raw_weapons
        if any(kind(i) == "WeaponGun" for i in items.values()):
            limits["weapons"] = (1, max(1, math.ceil(min(raw_weapons, pool))))
        return limits

    @staticmethod
    def consumed_power(items, pips):
        weapon_demand = sum(usage(i) for i in items.values() if kind(i) == "WeaponGun")
        return sum(pips.values()) - max(0, pips.get("weapons", 0) - weapon_demand)

    def cooling(self, items, pips):
        available = sum(number(network(i).get("Generation", {}).get("Coolant")) *
                        powered_fraction(i, pips.get(k, 0)) * modifier(i, pips.get(k, 0))
                        for k, i in items.items() if kind(i) == "Cooler")
        used = self.consumed_power(items, pips)
        extra = sum(usage(i, "Coolant") * powered_fraction(i, pips.get(k, 0)) * modifier(i, pips.get(k, 0))
                    for k, i in items.items() if kind(i) in {"Shield", "Radar", "LifeSupportGenerator"})
        return used + extra, available

    def allocate(self, items, profile="damage"):
        if profile not in {"damage", "balanced", "stealth"}:
            raise ValueError("Unknown power profile")
        bounds = self.bounds(items)
        pips = {k: low for k, (low, _) in bounds.items()}
        available = self.available_power(items)
        coolers = [k for k, i in items.items() if kind(i) == "Cooler"]

        def ensure_cooling(candidate):
            while self.cooling(items, candidate)[0] > self.cooling(items, candidate)[1] + 1e-8:
                possible = [k for k in coolers if candidate.get(k, 0) < bounds.get(k, (0, 0))[1]]
                if not possible:
                    return None
                # Choose the extra pip that produces most cooling, recomputing range transitions.
                key = max(possible, key=lambda k: self.cooling(items, {**candidate, k: candidate[k] + 1})[1])
                candidate[key] += 1
            return candidate if sum(candidate.values()) <= available else None

        valid = ensure_cooling(dict(pips))
        if valid is None:
            return pips
        pips = valid
        if profile != "stealth":
            priority = ["WeaponGun", "Shield", "FlightController", "Radar"] if profile == "damage" else ["Shield", "WeaponGun", "FlightController", "Radar"]
            for typ in priority:
                keys = (["weapons"] if "weapons" in bounds else []) if typ == "WeaponGun" else [k for k, i in items.items() if kind(i) == typ and k in bounds]
                changing = True
                while changing:
                    changing = False
                    for key in keys:
                        if pips[key] < bounds[key][1]:
                            candidate = ensure_cooling({**pips, key: pips[key] + 1})
                            if candidate is not None:
                                pips, changing = candidate, True
        return pips

    def evaluate(self, swaps=None, *, profile="damage", pips=None, duration=120.0):
        if not isinstance(duration, (int, float)) or not math.isfinite(duration) or not 1 <= duration <= 3600:
            raise ValueError("Duration must be between 1 and 3600 seconds")
        swaps = swaps or {}
        items = self.selection(swaps)
        bounds = self.bounds(items)
        if pips is None:
            pips = self.allocate(items, profile)
        else:
            if set(pips) != set(bounds):
                raise ValueError("Explicit pips must specify every powered port and 'weapons'")
            if any(type(v) is not int or not bounds[k][0] <= v <= bounds[k][1] for k, v in pips.items()):
                raise ValueError("Pips must be integers within each subsystem's bounds")
        available = self.available_power(items)
        used = sum(pips.values())
        cooling_load, cooling_output = self.cooling(items, pips)
        violations = []
        if used > available:
            violations.append(f"Power demand {used} exceeds supply {available}")
        if cooling_load > cooling_output + 1e-8:
            violations.append("Insufficient modeled cooling")
        guns = [i for i in items.values() if kind(i) == "WeaponGun"]
        ballistic_demand = sum(usage(i) for i in guns if not (i.get("Weapon") or {}).get("Capacitor"))
        energy_demand = sum(usage(i) for i in guns if (i.get("Weapon") or {}).get("Capacitor"))
        weapon_demand = ballistic_demand + energy_demand
        weapon_ratio = min(1, pips.get("weapons", 0) / weapon_demand) if weapon_demand else 1
        weapon_em_ratio = min(1, pips.get("weapons", 0) / math.ceil(weapon_demand)) if weapon_demand else 1
        if ballistic_demand > pips.get("weapons", 0):
            violations.append("Insufficient power for ballistic weapons")
        weapons = [{**self._weapon_cached(i["ClassName"], round(weapon_ratio, 8), duration), "port": k}
                   for k, i in items.items() if kind(i) == "WeaponGun"]
        shield_hp = shield_regen = em = ir_nominal = 0.0
        plants_em = sum(emission(i) for i in items.values() if kind(i) == "PowerPlant")
        em += plants_em * self.consumed_power(items, pips) / available if available else 0
        flight = self.ship.get("FlightCharacteristics") or {}
        rates = flight.get("AngularRates", {})
        boosted = flight.get("AngularRatesBoosted", {})
        speed = flight.get("Speeds", {})
        for key, item in items.items():
            typ = kind(item)
            ratio = weapon_em_ratio if typ == "WeaponGun" else powered_fraction(item, pips.get(key, 0))
            if typ != "PowerPlant":
                em += emission(item) * ratio * modifier(item, pips.get(key, 0))
            ir_nominal += number((item.get("Emission") or {}).get("Ir"))
            if typ == "Shield":
                shield = item.get("Shield") or {}
                shield_hp += number(shield.get("MaxShieldHealth"))
                shield_regen += number(shield.get("MaxShieldRegen")) * ratio * modifier(item, pips.get(key, 0))
            if typ == "FlightController" and item.get("Ifcs"):
                ifcs = item["Ifcs"]
                rates = {axis: ifcs.get(axis) for axis in ("Pitch", "Yaw", "Roll")}
                boosted = {axis: ifcs.get(axis + "Boosted") for axis in rates}
                speed = {"Scm": ifcs.get("ScmSpeed"), "Max": ifcs.get("MaxSpeed"), "BoostForward": ifcs.get("BoostSpeedForward")}
        armor = self.ship.get("Armor") or {}
        signals = armor.get("SignalMultipliers", {})
        em *= number(signals.get("Electromagnetic"), 1)
        ir = ir_nominal * min(1, cooling_load / cooling_output) * number(signals.get("Infrared"), 1) if cooling_output else None
        metrics = {name: sum(w[name] for w in weapons) for name in
                   ("alpha", "burst_dps", "sustained_dps", "duration_dps", "damage_over_duration", "distortion_alpha", "distortion_burst_dps")}
        metrics.update(em=em, ir=ir, shield_hp=shield_hp, shield_regen=shield_regen,
                       pitch=rates.get("Pitch"), yaw=rates.get("Yaw"), roll=rates.get("Roll"),
                       minimum_weapon_range=min((number(w["range_m"]) for w in weapons), default=0),
                       minimum_projectile_speed=min((number(w["projectile_speed_m_s"]) for w in weapons), default=0),
                       scm_speed=speed.get("Scm"), max_speed=speed.get("Max"),
                       cargo_scu=self.ship.get("Cargo"),
                       hull_hp=self.ship.get("Health"), armor_hp=armor.get("Health"),
                       handling=(rates["Pitch"] + rates["Yaw"]) / 2 if rates.get("Pitch") is not None and rates.get("Yaw") is not None else None)
        stealth = stealth_profile(self.ship, em, ir)
        handling = handling_profile(self.ship, rates, boosted, speed)
        metrics.update(signature=stealth["ranking_signal"], maneuverability_score=handling["score"])
        radars = [{"name": i["Name"], "sensitivity": (i.get("Radar") or {}).get("Sensitivity"),
                   "aim_assist": (i.get("Radar") or {}).get("AimAssist"), "pips": pips.get(k)}
                  for k, i in items.items() if kind(i) == "Radar"]
        return {"ship": {"id": self.ship["ClassName"], "name": self.ship["Name"], "role": self.ship.get("Role")},
                "model_version": MODEL_VERSION, "data": self.catalogue.manifest,
                "status": "experimental", "feasible": not violations, "violations": violations,
                "scenario": {"mode": "SCM", "duration_seconds": duration, "power_profile": profile, "crew": "pilot only"},
                "metrics": metrics, "weapons": weapons,
                "flight": {"rated": rates, "boosted_rated": boosted, "speeds_m_s": speed},
                "cross_section": self.ship.get("CrossSection"),
                "stealth": {**stealth, "own_radars": radars}, "maneuverability": handling,
                "power": {"available": available, "used": used, "consumed": self.consumed_power(items, pips), "allocation": pips, "bounds": bounds},
                "cooling": {"demand": cooling_load, "available": cooling_output},
                "loadout": [{"port": k, "hardpoint": self.ports[k][0]["HardpointName"],
                             "path": self.ports[k][0].get("Path", [self.ports[k][0]["HardpointName"]]), "size": i.get("Size"),
                             "id": i["ClassName"], "name": i["Name"], "type": kind(i),
                             "changed": i["ClassName"] != self.stock.get(k)} for k, i in items.items()],
                "swaps": {k: i["ClassName"] for k, i in items.items() if i["ClassName"] != self.stock.get(k)},
                "assumptions": list(ASSUMPTIONS)}
