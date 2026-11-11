# CitizenSolver

An independent, local Star Citizen loadout optimizer, intended to power a free tool on **concrete-foundry.com**. This repository contains the browser workbench, calculation/search engine, optional command-line interface and local JSON API.

**Version 0.1 is experimental.** It finds promising builds under an explicit approximation of SCM combat. It is not an in-game validated simulator, an erkul clone, or a guarantee of the best possible loadout. Read [the model and its limits](docs/model.md) before treating a recommendation as a purchase decision. The [same-build Meteor comparison](verification/meteor-erkul-12913470.md) documents the corrected damage/signature model and its current validation scope.

## Start on Windows

With Python 3.11 or newer installed, double-click **Open CitizenSolver.vbs** (or **CitizenSolver.cmd** with no arguments). It prepares the local catalogue, starts a hidden local server and opens **http://127.0.0.1:8765**. No commands are needed to use the workbench. Reopening the launcher reuses the running server. The server remains available after closing a browser tab and ends when Windows restarts; startup errors are in `data/server.log`.

1. **Fit my ship** optimizes equipment on one hull. **Find a ship** compares ships in a role, or all roles.
2. Choose **My priorities** and divide 100% between firepower, shielding, stealth, handling, speed, hull, armor and cargo. Raising one redistributes the others proportionally. Switch between **Pips** and **Sliders** to compare control styles.
3. Start from PvE, PvP, damage/stealth or cargo presets, or choose a single-stat goal. PvP starts at 75% handling. Mining needs a separate model and is marked as upcoming.
4. Optionally enter ship budgets in USD reference prices and/or aUEC. Both entered limits must be met. Require an in-game shop listing or set the maximum hangar class. Unknown prices/fit cannot pass an active filter. These are **ship-only** prices; component costs are not included.
5. Press **Find my fits**. Expand a result for equipment, actual modeled pips, additional stats and assumptions. Save a build or the whole search with the download buttons.

Set **Minimum gun reach** beside the goal to require every pilot gun to reach your chosen distance. Results show grouped weapon DPS, listed reach and pellet count. Scattergun damage assumes every pellet hits; listed reach is not a guarantee of useful full damage at that distance. Blank leaves range unrestricted.

“Keep at least 90% of damage” means retaining at least 90% of the best feasible engagement DPS found for that ship. It is a minimum-damage constraint used by the dedicated stealth/balanced goals, separate from preference weights. It does not promise 90% of a globally optimal or real in-game build.

Cargo, hull and armor are largely fixed hull traits. Stealth and flight values remain experimental. See [model details](docs/model.md) and [price / hangar provenance](docs/data-sources.md).

### Optional command line

No runtime dependencies or installation are required. In PowerShell:

```powershell
cd C:\Users\cwbec\CitizenSolver
python -m citizensolver sync
python -m citizensolver evaluate RSI_Meteor
python -m citizensolver optimize RSI_Meteor --goal balanced --out builds/meteor.json
```

`CitizenSolver.cmd` with arguments forwards to `python -m citizensolver`. Downloads and project-local builds are git-ignored. Browser exports go to your browser's download folder. The default import is pinned to `4.10.2-LIVE.12881860`, commit `1340c8303709904165e2da0fa7060bce0624260b`. It does not silently update during a calculation.

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
- Provides custom weighted priorities and damage, burst, alpha, stealth, shield capacity/regen, handling, SCM/max speed and cargo objectives; hard limits for signatures, shields, damage, rated pitch/yaw, gun range and projectile speed.
- Keeps damage/signature alternatives in a bounded deterministic beam search. Reports search limits, unsupported components and whether a returned result is dominated by another eligible candidate searched.
- Saves complete JSON results with source revision, model version, equipment and exact pips. Saved-build replay rejects mismatched ship, source or model versions.

The CLI summary is deliberately short. `--json` or `--out` includes the complete loadout and assumptions. `sustained_dps` is the repeating fire/recovery cycle **before ballistic ammunition is depleted**; `duration_dps` includes depletion over `--duration`.

Natural-language interpretation, component shop/ownership filtering, crafting, target-specific hit/armor simulation and the public website are future work, tracked in [the master plan](plans/MASTER-PLAN.md).

## Local API

```powershell
python -m citizensolver serve
```

This runs in the foreground at `http://127.0.0.1:8765`. Stop with Ctrl+C. `Start-API.cmd` is a shortcut. See [API examples](docs/api.md). The standard-library HTTP server is for local development; public hosting is a separate deployment task.

## Data updates and provenance

Game data can come from [StarCitizenWiki/scunpacked-data](https://github.com/StarCitizenWiki/scunpacked-data), generated with [ScDataDumper](https://github.com/octfx/ScDataDumper), or a complete export of a locally installed client. No erkul endpoints, scripts, UI or assets are used. Snapshots are checksummed and activated only after validation. Local imports also retain raw firing-sequence timing, the installed build manifest, extracted database hash and exporter revision. The UI shows the active source and version. See [local extraction details](docs/data-sources.md#local-client-extraction). FleetYards reference prices, shop listings and dock classes are cached separately, matched by exact game class identifier. Searches use the local caches.

```powershell
python -m citizensolver sync --revision latest
```

`latest` resolves the repository head to a commit SHA and records its commit-message build label. This may change the source schema or game mechanics; compare saved results and revalidate the model before using a new patch. A full SHA and `--version` can select another snapshot. The checksums detect accidental local corruption; they do not certify the upstream data's accuracy.

Public sync replaces the active snapshot, including a newer local import. The pinned public export currently lacks sequence timing; such guns are explicitly unsupported until imported with their full records. A newer version label alone never upgrades older data.

Raw game data and imagery are not included in this Git repository. See [data and attribution notes](docs/data-sources.md), including the remaining checks before public hosting.

## Verification

```powershell
python -m unittest discover -s tests -q --durations 10
python -m compileall -q citizensolver tests
node --check citizensolver/static/app.js
node tests/test_priorities.js
```

Tests use synthetic catalogues in temporary directories. They need no network, saved game data, browser, account or credentials. [Verification notes](verification/README.md) distinguish code checks from uncompleted in-game validation.
