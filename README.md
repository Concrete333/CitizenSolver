# CitizenSolver

An independent, local Star Citizen loadout optimizer, intended to power a free tool on **concrete-foundry.com**. The website UI comes later; this repository contains the calculation/search engine, a command-line interface, and a local JSON API.

**Version 0.1 is experimental.** It finds promising builds under an explicit approximation of SCM combat. It is not an in-game validated simulator, an erkul clone, or a guarantee of the best possible loadout. Read [the model and its limits](docs/model.md) before treating a recommendation as a purchase decision.

## Start on Windows

Python 3.11 or newer; no runtime dependencies or installation required. In PowerShell:

```powershell
cd C:\Users\cwbec\CitizenSolver
python -m citizensolver sync
python -m citizensolver evaluate RSI_Meteor
python -m citizensolver optimize RSI_Meteor --goal balanced --out builds/meteor.json
```

`CitizenSolver.cmd` is a shortcut for `python -m citizensolver`. Downloads and saved builds are local and git-ignored. The default import is pinned to `4.10.2-LIVE.12881860`, commit `1340c8303709904165e2da0fa7060bce0624260b`. It does not silently update during a calculation.

## Useful searches

Keep at least 90% of the best 120-second damage found, then minimize the larger of EM and IR:

```powershell
python -m citizensolver optimize RSI_Meteor --goal stealth --damage-floor .9 --out builds/meteor-stealth.json
```

Find high sustained damage, while requiring every gun to have at least 2 km rated range:

```powershell
python -m citizensolver optimize RSI_Meteor --goal damage --min-range 2000 --out builds/meteor-damage.json
```

Compare optimized medium fighters for a three-minute PvE engagement:

```powershell
python -m citizensolver compare --role "Medium Fighter" --goal pve --duration 180 --min-range 2000 --out builds/medium-fighters.json
```

Or compare only ships you actually want to consider:

```powershell
python -m citizensolver compare --ships RSI_Meteor ANVL_Hornet_F7C_Mk2 --goal pve
```

Inspect compatible choices or replay the first result of a saved search:

```powershell
python -m citizensolver components RSI_Meteor --json
python -m citizensolver evaluate RSI_Meteor --build builds/meteor-stealth.json
python -m citizensolver ships --role "Medium Fighter"
```

Use class ids when display names are ambiguous. The source contains collector editions and variants with the same display names; the comparison retains their identities. Temporary/test/display variants are excluded from the default ship list. Inclusion does not prove current player availability.

## What it does

- Checks port size, type/subtype, per-port editability, and required/excluded tags, including bespoke Meteor equipment.
- Searches installed pilot guns, shields, power plants, coolers, radars, and flight blades. Identical slots are searched together first, then individually to allow mixed fits.
- Returns alpha, burst and sustained hull DPS, finite-engagement damage, separate distortion damage, per-gun cycles/ammunition/range/velocity, estimated EM/IR, shield HP/regen, rated flight stats, and directional cross-section.
- Provides damage, burst, alpha, stealth, balanced and PvE objectives; hard limits for signatures, shields, damage, rated pitch/yaw, gun range and projectile speed.
- Keeps damage/signature alternatives in a bounded deterministic beam search. Reports search limits, unsupported components and whether a returned result is dominated by another eligible candidate searched.
- Saves complete JSON results with source revision, model version, equipment and exact pips. Saved-build replay rejects mismatched ship, source or model versions.

The CLI summary is deliberately short. `--json` or `--out` includes the complete loadout and assumptions. `sustained_dps` is the repeating fire/recovery cycle **before ballistic ammunition is depleted**; `duration_dps` includes depletion over `--duration`.

Natural-language interpretation, shop/ownership filtering, crafting, target-specific hit/armor simulation and the public website are future work, tracked in [the master plan](plans/MASTER-PLAN.md). For now, goals and constraints are explicit CLI/API fields.

## Local API

```powershell
python -m citizensolver serve
```

This runs in the foreground at `http://127.0.0.1:8765`. Stop with Ctrl+C. `Start-API.cmd` is a shortcut. See [API examples](docs/api.md). The standard-library HTTP server is for local development; public hosting is a separate deployment task.

## Data updates and provenance

Data comes from [StarCitizenWiki/scunpacked-data](https://github.com/StarCitizenWiki/scunpacked-data), generated with [ScDataDumper](https://github.com/octfx/ScDataDumper). No erkul endpoints, scripts, UI or assets are used. Two public bulk JSON files are cached under an immutable revision, checksummed and activated only after validation. Network access occurs only during `sync`.

```powershell
python -m citizensolver sync --revision latest
```

`latest` resolves the repository head to a commit SHA and records its commit-message build label. This may change the source schema or game mechanics; compare saved results and revalidate the model before using a new patch. A full SHA and `--version` can select another snapshot. The checksums detect accidental local corruption; they do not certify the upstream data's accuracy.

Raw game data and imagery are not included in this Git repository. See [data and attribution notes](docs/data-sources.md), including the remaining checks before public hosting.

## Verification

```powershell
python -m unittest discover -s tests -q --durations 10
python -m compileall -q citizensolver tests
```

Tests use synthetic catalogues in temporary directories. They need no network, saved game data, browser, account or credentials. [Verification notes](verification/README.md) distinguish code checks from uncompleted in-game validation.
