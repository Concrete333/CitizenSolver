"""Target-independent signature and rated handling summaries; no detection/TTK simulation."""
import math


def finite(value):
    return float(value) if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def stealth_profile(ship, em, ir):
    raw = ship.get("CrossSection") or {}
    multiplier = finite((ship.get("Armor") or {}).get("SignalMultipliers", {}).get("CrossSection", 1))
    axes = {axis: finite(raw.get(axis)) for axis in ("X", "Y", "Z")}
    axes = {k: v * multiplier if v is not None and multiplier is not None else None for k, v in axes.items()}
    complete = all(v is not None for v in (*axes.values(), em, ir))
    envelopes = {k: max(em, ir, v) for k, v in axes.items()} if complete else {}
    return {"axes": axes, "signal_by_axis": envelopes,
            "ranking_signal": sum(envelopes.values()) / 3 if complete else None,
            "best_axis_signal": min(envelopes.values()) if complete else None,
            "worst_axis_signal": max(envelopes.values()) if complete else None,
            "signature_multipliers": (ship.get("Armor") or {}).get("SignalMultipliers", {}),
            "scope": "Stationary SCM emissions plus hull cross-section. Axis-average strongest signal ranks stealth; it is not detection distance.",
            "detection_note": "The other ship's radar, viewing angle, background noise, active scans and changing emissions affect detection. Your radar sensitivity describes what you can see, not how hidden you are.",
            "operation_note": "Lower allocated power can reduce EM. Firing, thrust and boost can change signatures; their transient effects are not simulated."}


def handling_profile(ship, rates, boosted, speeds):
    flight = ship.get("FlightCharacteristics") or {}
    accel = (flight.get("Acceleration") or {}).get("Raw") or {}
    forward, braking = finite(accel.get("Main")), finite(accel.get("Retro"))
    pitch, yaw = finite(rates.get("Pitch")), finite(rates.get("Yaw"))
    score = None
    if None not in (forward, braking, pitch, yaw):
        turning = (pitch / (pitch + 60) + yaw / (yaw + 60)) / 2
        score = .7 * turning + .2 * braking / (braking + 50) + .1 * forward / (forward + 100)
    scm = finite(speeds.get("Scm"))
    return {"rated_turning": rates, "rated_boost_turning": boosted,
            "forward_acceleration": forward, "braking_acceleration": braking,
            "zero_to_scm_seconds": scm / forward if scm is not None and forward else None,
            "scm_to_zero_seconds": scm / braking if scm is not None and braking else None,
            "score": score,
            "scope": "Rated space-flight estimate: 70% pitch/yaw, 20% braking, 10% forward acceleration. Weights and scales are product choices, not game constants.",
            "limits": "Hull acceleration ratings stay fixed during equipment swaps. Power, mass changes, atmosphere, jerk, boost endurance and damaged thrusters are not simulated. Timing assumes immediate constant acceleration."}
