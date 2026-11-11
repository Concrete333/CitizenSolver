# Calculation model: scm-estimate-2

This model is an explicit engineering approximation. Selected Meteor fits were calibrated against erkul on the same 4.10.2-LIVE.12913470 build; see the [comparison](../verification/meteor-erkul-12913470.md). This does not establish accuracy across ships or in the live game. The optimizer can only be as accurate as this model and its source snapshot.

## Scope

SCM mode, stationary, undamaged ship, fixed firing, primary gun mode, solo pilot. All projectiles and scattergun pellets are assumed to hit, within their rated range. Quantum drive and non-pilot turret weapons are not operated. Life support, radar, flight controller, installed shields and coolers remain powered. Mounts, missiles and other equipment remain stock. Missile damage is not added to gun DPS. Empty hardpoints and alternative mount topology are not searched.

Source `Weaponry` evidence identifies pilot guns and pilot-slaveable turrets. Manned/unproven turret guns do not inflate pilot damage. Unknown essential component records and unsupported stock gun modes prevent analysis of that ship and produce a reason in multi-ship comparisons.

## Damage

The primary mode's typed alpha damage already includes the extractor's projectile multipliers. Hull alpha sums physical, energy and thermal damage. Distortion is tracked separately and never counted as hull DPS. This does not model shield absorption, armor, penetration, fuses, damage falloff, component destruction or time to kill.

`burst_dps = hull_alpha * rounds_per_minute / 60`

Looping and automatically repeated single-shot sequences use every entry's delay and repetition count: `effective_rpm = 60 * total_shots / total_sequence_seconds`. RPM delays become `60 / delay` seconds. The inner action's rate is not the sequence's rate. For example, the Echion's three intervals (800, 450, 450 RPM) yield 526.829 RPM. Local imports retain those previously omitted raw entries. Missing timing, mixed projectile/damage sequences and unsupported action types are rejected.

Energy weapons use the exported `Capacitor.MaxAmmoLoad`, `MaxRegenPerSec`, cooldown and ammo-per-shot. The shared power fraction is `min(1, allocated_weapon_pips / total_rated_gun_power)` including ballistic guns. Capacity rounds half up after scaling by this fraction; recharge scales by the same fraction. Recovery time is cooldown plus the scaled, rounded load divided by scaled recharge. Burst damage stays unchanged by capacitor power; the firing/recovery duty cycle changes.

`cycle_dps = shots_in_cycle * hull_alpha / (firing_seconds + recovery_seconds)`

The heat model uses threshold temperature divided by heat per shot, falling back to exported shots-to-overheat if those inputs are absent. The shot that crosses the threshold counts: cycle damage uses the ceiling of that ratio, while firing time uses the continuous threshold time. This reproduces erkul's Leonids display of 17 shots over 14.7 seconds, followed by 6.5 seconds recovery; it is a cycle approximation, not discrete shot scheduling. If heat is the limiting cycle, energy recharge and heat recovery are assumed to happen concurrently after firing stops; recovery is the longer duration. Continuous cooling while firing, intentional trigger pacing, spin-up and synchronization between gun groups are not simulated. Charged, burst and beam primary modes are excluded rather than assigned a fabricated firing cycle.

Finite engagement damage counts complete cycles plus the partial final firing window and caps ballistic shots at ammunition capacity. It uses continuous time windows, not discrete first-shot timing. Sustained DPS therefore need not equal finite-duration DPS, especially in a short engagement. Ballistic `ammo_trigger_seconds` means active trigger time to empty, excluding cooling pauses.

Weapons are cycled independently. The importer does not expose all ship-level capacitor assignment curves/buffs, so this is not a shared-capacitor scheduler. This is a material limitation for energy-heavy builds, and is included in every report's assumptions.

## Power and cooling

Each powered subsystem has integer pip bounds from the resource network. Each gun shares a weapon-group allocation limited by the ship's exported weapon pool. We retain at least one weapon pip and each essential subsystem's minimum; the optimizer cannot win stealth by turning the whole ship off.

For multiple plants the current model follows the community extractor's formula:

`available = sum(round_half_up(plant_generation / plant_count)) + (plant_count - 1) * sum(plant_size)`

Cooler output is exported coolant generation times its allocated-power fraction and exported power-range modifier. Estimated heat load is consumed power plus proportional coolant demand from shields, radar and life support, including their power-range modifiers. Weapon consumption is capped at actual fractional gun demand; unused capacity in the last integer weapon pip does not produce heat. Insufficient power or cooling makes a candidate infeasible. This is not a physical thermal simulation, damage network or relay simulation.

Three deterministic allocation policies are searched:

- **damage:** start at subsystem minima, then fill weapons, shields, flight and radar in that order; add cooler pips as needed.
- **balanced:** the same process with shields before weapons.
- **stealth:** remain at subsystem minima, adding cooler pips only as needed.

These policies do not enumerate every legal pip allocation. The evaluate API also accepts an exact allocation, checked against the bounds and total power/cooling constraints.

## Signatures

Power-plant EM scales with consumed power relative to total available power. Consumption excludes unused capacity in the last integer weapon pip. Consumer EM scales with allocation and exported power-range modifiers. All gun EM, including ballistics, scales with `allocated_weapon_pips / ceil(total_rated_gun_power)`, capped at one. This signature fraction uses whole pips, while capacitor capacity/recharge uses fractional rated demand. Armor EM multipliers are applied. Estimated IR is summed nominal component IR times cooling utilization, then the armor IR multiplier. Cross-section is exported per axis and shown separately.

These are **steady-state estimates**. Ambient temperature, transient heat, weapon firing, thrust, boost, receiver sensitivity and aspect-dependent detection are not simulated. No detection-distance claim is made. The stealth score minimizes `max(EM, IR)`; it does not minimize cross-section, so compare cross-section separately when choosing different ships.

## Shields and flight

Shield HP is the sum of installed generators. Regen is rated regen times allocation fraction and its power-range modifier. Regen delays, damage interruptions and face allocation are not simulated. The model has primarily been exercised on fighters; multi-generator capital-ship behavior needs validation.

Pitch, yaw, roll, boost rates and speed are source flight-blade ratings. Swapping an eligible blade changes those ratings. Pips do **not** modify the displayed rates in this version. There are both current/legacy-looking flight records in the source; resolving their exact in-game applicability is validation work. Hard handling limits apply to these ratings, not measured flight performance. Acceleration and atmospheric handling are not optimized.

## Objective meanings

| Goal | Score |
| --- | --- |
| damage | Cycle sustained hull DPS, before ammunition depletion |
| burst | Hull burst DPS |
| alpha | Hull damage in one full salvo |
| stealth | Negative of the larger estimated EM or IR |
| balanced | Finite-duration hull DPS / (1 + max(EM, IR) / 10,000) |
| pve | 0.70 × duration DPS / 1,000 + 0.25 × shield HP / 10,000 + 0.05 × rated pitch / 100 |
| pvp | 75% bounded handling utility, 20% duration DPS utility, 5% shield utility |
| shields / shield_regen | Total shield HP / modeled regeneration |
| handling | Mean of rated pitch and yaw |
| speed / scm_speed | Maximum / SCM speed rating |
| custom | Weighted sum of bounded stat utilities, described below |
| cargo (workbench) | Exported cargo-grid SCU; no equipment search |

These are explicit preference scores, not physical units. PvE gives handling less weight and uses finite-duration DPS to include ammo endurance. It is not a universal definition of PvE quality. The same normalization is used across ships so the score does not change merely because the comparison group changes.

For stealth and balanced, `damage_floor` retains at least that fraction of the highest finite-duration DPS among feasible candidates found that meet the hard constraints. Default 0.9. This is relative to this search, not a proven theoretical maximum. In cross-ship comparisons the floor applies separately to each ship.

`min_range` and `min_velocity` require every installed pilot gun to meet the threshold. They do not estimate hit probability. The browser exposes Minimum gun reach beside the goal and lists grouped gun DPS, nominal reach and pellets per shot. A multi-pellet fit explicitly warns that spread can reduce damage before the range limit. No distance-dependent damage curve or target-size/spread model is implied; a blank range constraint leaves short-range guns eligible. Collector and special equipment may be compatible but unobtainable; the source has no trusted availability contract here, and all results disclose this.

### Browser priority budget

The UI activity buttons set **custom** weights that the player can change; they do not call the older CLI `pve` scoring formula. Initial presets: PvE 65% firepower / 25% shields / 10% handling; PvP 75% handling / 20% firepower / 5% shields; damage + stealth 50% each; cargo 65% cargo / 15% shields / 15% speed / 5% handling.

For an increasing stat, utility is `value / (value + scale)`. For stealth it is `scale / (scale + max(EM, IR))`. The preference score is `100 * sum(weight/100 * utility)`. Fixed scales allow comparisons without changing the meaning when candidates change. The following initial scales are design choices, not game constants:

| Priority | Stat | Half-score scale |
| --- | --- | --- |
| Firepower | Finite-engagement pilot hull DPS | 1,500 DPS |
| Shielding | Shield HP | 10,000 HP |
| Stealth | Larger of estimated EM and IR | 10,000 |
| Maneuverability | Average pitch and yaw | 60 degrees/second |
| Speed | Maximum rated speed | 1,000 m/s |
| Hull | Exported total part health | 20,000 HP |
| Armor | Exported armor health | 10,000 HP |
| Cargo | Exported cargo-grid capacity | 100 SCU |

Weights are nonnegative percentages totaling 100. UI redistribution is proportional across the other weights, using largest-remainder integer rounding. When all other weights were zero, the released share is divided evenly. Missing positively weighted stats exclude a candidate; zero cargo or zero damage is known zero, not missing. Ratings are bounded to stop a stat's raw unit magnitude from overwhelming another priority. They are not a win probability, guaranteed percentage improvement, or strict lexicographic ranking.

Hull part HP and armor HP are hull characteristics, **not effective hit points, damage-to-destruction or armor penetration simulation**. Cargo grids do not include ore bags. Their weights generally affect ship selection, not equipment selection on a fixed hull. Unarmed ships may qualify for noncombat goals. Stat-identical equipment alternatives are collapsed to one result so the returned cards show distinct modeled trade-offs.

## Search guarantees

The beam search first groups interchangeable slots, then allows independent slot choices. Each retained beam includes goal-ranked candidates plus damage and signature extremes. Every equipment candidate is evaluated with the three power policies. Results are deterministic for the same snapshot and settings, apart from timings.

This is a bounded heuristic. It may miss a better combination, and failure to find a feasible build is not proof that none exists. The report includes evaluation count, completed passes, evaluation-limit status, rejected component reasons and `globally_optimal: false`.

`nondominated_in_searched_candidates` compares finite-duration hull damage, EM, IR and shield HP against the eligible candidates found. It does not certify the complete game's Pareto frontier.

## Before presenting the public tool as validated

Match exact game builds and verify several stock and changed fits against in-game measurements. Test each weapon family, mixed guns, power changes, flight blades, thermal recovery and signatures individually. erkul may be a manual reference with its displayed assumptions, but is not an automated data source. Keep measured evidence separate from source-derived calculations.
