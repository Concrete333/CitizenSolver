# Meteor damage / stealth comparison — 11 November 2026

> Follow-up: the discrepancies below were resolved for these Meteor fits in the [same-build recalibration](meteor-erkul-12913470.md). This report preserves the original failed comparison.

**Result: partial agreement; damage and signature predictions do not pass validation.**

The same equipment and power allocation were entered in erkul's public calculator. Alpha damage, shields, hull, armor and base flight ratings agree. CitizenSolver overstates burst DPS by **17.2%** and sustained DPS by **16.9%**. Its EM/IR estimates are also higher. This does not establish that the recommended fit is optimal or that either calculator matches the game.

- [Matched erkul loadout](https://erkul.games/s/whmettuk)
- CitizenSolver: `scm-estimate-1`, application commit `7f8bc622111acf2d3765aca6a31fa3ab07eee9eb`.
- CitizenSolver data: `4.10.2-LIVE.12881860`, [scunpacked-data revision 1340c83](https://github.com/StarCitizenWiki/scunpacked-data/tree/1340c8303709904165e2da0fa7060bce0624260b).
- Erkul v5 data shown in the calculator: **`4.10.2-LIVE.12913470`**.

The game builds differ. These are matched-loadout comparisons, **not same-patch validation**. The latest upstream `ship-items.json` commit checked during this comparison was still the pinned revision. No data or formulas were changed to force agreement.

## Reproduction

The workbench search used RSI Meteor, custom priorities **50% firepower / 50% stealth**, all other priorities zero, no price or hangar constraints, a 120-second duration, beam 3, one pass, 3,000 maximum evaluations and one returned result. The resulting power profile was `stealth`. This is a bounded search, not a proof of the global optimum.

Both calculators used SCM mode, the standard flight blade, uncrafted components, pilot weapons and fixed/LOCK firing. Other equipment stayed stock. In erkul, five of thirteen pips remained unallocated after matching CitizenSolver's eight allocated pips.

| Equipment | Count | Size |
|---|---:|---:|
| Predator Scattergun | 4 | 3 |
| Echion Repeater | 2 | 5 |
| AllStop shield | 2 | 1 |
| HeatSafe cooler | 2 | 1 |
| DeltaMax power plant | 1 | 1 |
| Abetti radar | 1 | 1 |
| Meteor Standard Flight Blade | 1 | 1 |
| ComfortAir life support | 1 | 1 |

| System | Allocated pips |
|---|---:|
| Weapons, shared | 1 |
| Flight | 1 |
| Shields | 2 total, 1 each |
| Coolers | 2 total, 1 each |
| Radar | 1 |
| Life support | 1 |
| Quantum drive | Off in SCM |
| Total | 8 / 13 |

## Results

Percent differences use `(CitizenSolver / erkul - 1) × 100`. Erkul values below are the displayed values, which are rounded or abbreviated; no hidden application data or private API was used.

| Metric | CitizenSolver | Erkul | Assessment |
|---|---:|---:|---|
| Alpha damage | 3,550 | 3,550 | Matches |
| Burst DPS | 5,893.33 | 5,028 | +17.2% |
| Sustained DPS | 5,810.15 | 4,970 | +16.9% |
| Shield HP | 6,336 | 6,336 | Matches |
| Shield regeneration, HP/s | 280.93 | 281 | Matches displayed precision |
| Total part hull HP | 30,150 | 30,150 | Matches; not vital hull HP |
| Armor HP | 7,200 | 7,200 | Matches |
| Pitch / yaw / roll, degrees/s | 46 / 38 / 155 | 46 / 38 / 155 | Matches base ratings |
| SCM speed, m/s | 229 | 229 | Matches base rating |
| EM | 3,876.87 | 3.7k | Higher; display too coarse for an exact percentage |
| IR | 1,270.91 | 1.2k | Higher; display too coarse for an exact percentage |
| Cross-section Z | 14,000 | 14.0k | Matches exported axis; excluded from current stealth score |

Erkul separately shows **2,750 vital hull HP**. The 30,150 total must not be interpreted as the damage required to destroy the ship. Its cross-section remains substantial even with low EM/IR; a low signature score is not a detection-distance guarantee.

CitizenSolver's 120-second average DPS (5,820.76) was not compared with erkul's sustained DPS. They are different quantities. Maximum NAV speed, boosted flight, transient heat, actual detection, target armor/penetration and in-game hit rates were not tested.

## What explains the differences

### Echion firing rate and capacitor behavior

| Per Echion | CitizenSolver | Erkul |
|---|---:|---:|
| Alpha | 95 | 95 |
| Fire rate, RPM | 800 | 527 |
| Burst DPS | 1,266.67 | 834 |
| Sustained DPS at matched pips | 1,225.07 | 805 |
| Shots per capacitor load | 225 | 80 |
| Continuous fire, seconds | 16.875 | 9.1 |
| Full recovery, seconds | 0.573 | 0.3 |
| Projectile speed, m/s | 1,390 | 1,390 |
| Range, m | 3,197 | 3,197 |

The pinned export gives the Echion primary mode `FireType=sequence`, `RoundsPerMinute=800`, alpha 95, `MaxAmmoLoad=225`, `MaxRegenPerSec=2787` and cooldown 0.25. The engine treats that sequence as uninterrupted fire at 800 RPM. Erkul shows 527 RPM both in the swap table and component details, including at full weapon power. The exported record does not contain the sequence timing needed to explain that rate. A patch change and a difference in sequence modeling remain possible; this comparison cannot distinguish them.

CitizenSolver keeps the capacitor load fixed at 225 shots and scales only recharge with remaining power after ballistic demand. Erkul showed 225 shots at full weapon power and **80 at the matched one-pip setting**, with a displayed 36% efficiency. This confirms that our low-power capacitor behavior differs materially from erkul. The actual game's behavior still needs verification.

Each Predator agreed on alpha 840, 60 RPM, 840 burst/sustained DPS, ammunition 1,980, velocity 888 m/s and range 1,501 m. Thus the two Echions account for essentially the entire burst-DPS discrepancy, within displayed rounding. Both calculators' nominal scattergun damage assumes the pellets hit; this is not a practical hit-rate comparison.

### Signatures and cooling

Erkul's per-component EM display showed DeltaMax 2,000, AllStop 289 each, HeatSafe 250 each, Abetti 320 and ComfortAir 313. Those agree with our corresponding calculations to displayed precision. Each Predator showed **14 EM**, while CitizenSolver assigns its full exported **41.3 EM** at the matched power setting. That identifies weapon-power scaling as a specific signature difference to investigate; the rounded component displays are not exact totals.

Each HeatSafe showed **604 IR** in erkul, with other displayed component IR values zero. CitizenSolver predicts 1,270.91 combined IR from modeled coolant demand 12 against output 44. Erkul displayed 25% cooling utilization and a different per-cooler IR result. Coolant demand/scaling must be reconciled before treating the stealth score as accurate.

## Evidence and follow-up

Local captures live beside this report and are intentionally Git-ignored:

- `meteor-damage-stealth-2026-11-11.json`: original search result, exact swaps/pips, metrics and source hashes.
- `erkul-meteor-matched-2026-11-11.json`: visible calculator snapshot and share URL.
- `erkul-echion-details-2026-11-11.json`: visible component detail panel.
- `meteor-erkul-2026-11-11.jpg`: screenshot of matched results and data version.
- `erkul-meteor-stock.json`: initial stock comparison context.

Next work is tracked in [the master plan](../plans/MASTER-PLAN.md): establish the Echion sequence rate for a shared game revision, reconcile low-power ammo/recharge and weapon EM/cooling, then re-run the search and compare the newly recommended fit. Do not hard-code erkul's displayed numbers as universal correction factors.
