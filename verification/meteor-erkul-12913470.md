# Meteor recalibration — 4.10.2-LIVE.12913470

**11 November 2026: both matched fits now agree with erkul's displayed alpha, burst DPS and sustained DPS.** Component EM/IR readings also agree to displayed precision. Aggregate signatures are abbreviated in erkul, so this does not establish exact total-signature equality or in-game accuracy.

This supersedes the failed [initial comparison](meteor-erkul-2026-11-11.md). CitizenSolver uses `scm-estimate-2`. Both calculators now use **4.10.2-LIVE.12913470**. The local catalogue was extracted from the installed LIVE client: 331 exported vehicles, 273 visible ship choices, 5,597 components and 145 sequence-weapon records. It is not the older public dataset with a new label.

## Original fit, replayed

[Erkul: Predator + Echion fit](https://erkul.games/s/whmettuk). Four S3 Predator Scatterguns, two S5 Echion Repeaters, two AllStop shields, two HeatSafe coolers, DeltaMax plant, Abetti radar, standard Meteor flight blade and ComfortAir life support. Other equipment stays stock. SCM, fixed/LOCK, no crafting, pilot guns only.

| Metric | CitizenSolver | Erkul display |
|---|---:|---:|
| Alpha | 3,550 | 3,550 |
| Burst DPS | 5,028.29 | 5,028 |
| Sustained DPS | 4,969.92 | 4,970 |
| EM | 3,766.73 | 3.7k |
| IR | 1,207.36 | 1.2k |
| Shield HP | 6,336 | 6,336 |
| Shield regeneration, HP/s | 280.93 | 281 |

The old predictions were 5,893.33 burst and 5,810.15 sustained DPS. The corrected values match erkul's rounded display without per-weapon correction constants.

## Re-run recommendation

[Erkul: new Predator + Leonids fit](https://erkul.games/s/bojxrfcw). With the same **50% firepower / 50% stealth**, the search now keeps the two stock **S5 Leonids Cannons** instead of fitting Echions. The four Predators and all support equipment listed above remain the same.

| Metric | CitizenSolver | Erkul display |
|---|---:|---:|
| Alpha | 6,560 | 6,560 |
| Burst DPS | 6,982.64 | 6,983 |
| Sustained DPS | 5,923.35 | 5,923 |
| EM | 3,776.87 | 3.7k |
| IR | 1,165.00 | 1.1k |
| Shield HP | 6,336 | 6,336 |
| Shield regeneration, HP/s | 280.93 | 281 |
| Total part hull HP | 30,150 | 30,150 |
| Armor HP | 7,200 | 7,200 |
| Pitch / yaw / roll, degrees/s | 46 / 38 / 155 | 46 / 38 / 155 |
| Unboosted SCM speed, m/s | 229 | 229 |
| Cross-section Z | 14,000 | 14.0k |

Erkul separately shows **2,750 vital hull HP**; summed part HP is not a destruction threshold. Both fits have eight allocated pips: weapons 1, flight 1, shields 1 each, coolers 1 each, radar 1 and life support 1. Quantum drive is off in SCM. Five of the plant's 13 pips remain unassigned. The all-ballistic fit consumes 7.6 power despite allocating eight whole pips.

The reproducible search used beam 3, one pass, a 3,000-evaluation ceiling and a 120-second engagement, without price/hangar constraints. It evaluated 906 candidates and returned this fit. The browser's Damage + stealth preset found the same first result among five displayed alternatives. This is the best found by a bounded search, not proof of a global optimum.

The workbench's **6,045.95 engagement DPS** includes the initial full firing window and partial final cycle over 120 seconds. It is not the **5,923.35 repeating/sustained DPS** compared above. All guns in the new recommendation use finite ballistic ammunition, and scattergun damage assumes all pellets hit. Range, hit probability, armor and target behavior could change a practical recommendation substantially.

## Calculation changes and checks

- **Sequence cadence:** the Echion's three delays are 800, 450 and 450 RPM. `60 × 3 / (60/800 + 60/450 + 60/450)` gives **526.829 RPM**, matching erkul's 527. These delays are present in both the older raw record and the current local extraction; the previous standardized import omitted them. Leonids' automatically repeated 40/225 RPM sequence gives **67.925 RPM**, matching 68. Unsupported or mixed-payload sequences remain explicitly excluded.
- **Capacitors:** scale capacity and recharge by shared weapon pips divided by total fractional gun demand, including ballistics. Round capacity half up. The Echion fit's 2.8 demand gives **80 / 161 / 225 shots** at 1 / 2 / 3 weapon pips, matching all three manual erkul checks. At one pip: 9.111 seconds firing, 0.330 seconds recovery, 804.958 sustained DPS per Echion; erkul shows 9.1, 0.3 and 805.
- **Heat:** count the final shot that crosses the threshold, while retaining continuous threshold time. Leonids uses `ceil(100/6) = 17` shots over 14.722 seconds with 6.5 seconds recovery, yielding **1,281.675 sustained DPS**. Erkul shows 17, 14.7, 6.5 and 1,282. This remains a cycle approximation, not a discrete firing scheduler.
- **EM:** all guns scale with allocated weapon pips over the rounded-up group demand. Predators show 14 / 28 / 41 EM across the original fit's three weapon-pip settings. Plant EM follows actual consumed power: DeltaMax shows **2,000** on the Echion fit and **1,900** on the Leonids fit, matching the model. Shields, coolers, radar and life support also match their rounded component badges.
- **IR:** shield coolant demand includes its power-range modifier, and unused capacity in the last weapon pip produces no heat. The original fit needs 11.4 coolant against 44 output; each HeatSafe predicts 603.682 IR and displays **604**. The new fit needs 11 coolant; each predicts 582.5 and displays **583**. Erkul's signature badges were refreshed after power changes before comparison.

No erkul application code, private API or hidden state was used. Visible UI values were the comparison reference; sequence and component inputs came from our local extraction. See [model scope](../docs/model.md) and [extraction procedure](../docs/data-sources.md#local-client-extraction).

## Provenance and verification

- Local snapshot: `1fc283c48f620d2e43974cb99b0dfb6ac68ddb28` (content identifier).
- Extracted `Game2.dcb` SHA-256: `5817856a190e22ba4cc9e90bc1978d73a633b0f182a00b95636cd40b449c06c7`.
- `ships.json` SHA-256: `3d948fa251f1833dbdb592dc78ec430b9b0adcd4712d7e22f74196923d7c2310`.
- `ship-items.json` SHA-256: `26f16a8cbc2d7cc422dca070ab0913500970c3aebd89b78551a36eb19fe90684`.
- ScDataDumper commit `120a728639bdd1b06525a0f8574cb0e91d0fbf8d`, with the documented Windows path normalization fix. unp4k/unforge v4.0.87; local buffering/output-file fixes did not change parsing rules.
- **36 offline Windows tests passed in 1.160 seconds**. Slowest: HTTP integration 0.536 s, browser-assets/background-search integration 0.522 s, save/replay 0.017 s. Python compilation and JavaScript syntax passed; Node's 808 sequential priority edits retained exactly 100%.
- Browser verification confirmed the active version/source, 50/50 Meteor search, first result's detailed damage/signatures and absence of application console errors. Both comparison pages were left open.

Ignored local evidence beside this report: `meteor-matched-12913470.json`, `meteor-damage-stealth-12913470.json`, `erkul-matched-12913470.json`, `erkul-recommended-12913470.json`, `erkul-leonids-details-12913470.json`, the two `erkul-meteor-*-weapon-pips.json` captures, `meteor-erkul-12913470.jpg`, `meteor-workbench-12913470.jpg` and `meteor-calibration-tests.log`. The complete manifest also retains the installed build stamp and raw sequence-record hashes. Game data and screenshots remain outside Git.

Remaining validation includes other ship/weapon families, ship capacitor buffs, flight curves, actual detection, transient heat and measured in-game outcomes. Agreement with this calculator on these fits is a calibration result, not validation of every possible loadout.
