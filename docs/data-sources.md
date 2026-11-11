# Data sources and attribution

CitizenSolver is an independent application. It does not use erkul's private backend or redistribute its code, site assets or interface. erkul's [About page](https://erkul.games/about) explains its own access restrictions and licensing.

The initial dataset is [StarCitizenWiki/scunpacked-data](https://github.com/StarCitizenWiki/scunpacked-data), revision [1340c8303709904165e2da0fa7060bce0624260b](https://github.com/StarCitizenWiki/scunpacked-data/commit/1340c8303709904165e2da0fa7060bce0624260b), labeled `4.10.2-LIVE.12881860`. `ships.json` contains full exported ship records; `ship-items.json` supplies standardized component records. Both are downloaded by the user and stored locally, outside Git.

The exporter is [octfx/ScDataDumper](https://github.com/octfx/ScDataDumper), whose package metadata declares MIT. Its exported schema and documented calculations informed the importer and model. Its software license does not, by itself, license underlying CIG game data or imagery. The application does not automatically install or run the exporter; local extraction is a separate developer step.

Game content and trademarks belong to their respective owners. CitizenSolver is an unofficial fan project and is not affiliated with or endorsed by Cloud Imperium Games or Roberts Space Industries.

## Local client extraction

The installed LIVE client on 11 November 2026 has `RequestedP4ChangeNum=12913470`, branch `sc-alpha-4.10.2`, executable version `4.10.197.2878` and build ID `2cae0dfc-a941-4dcc-b82a-543b08b52d97`. This matches erkul's displayed `4.10.2-LIVE.12913470`. The public standardized dataset above had not yet advanced to that build, so the comparison uses a fresh local extraction, not a relabeled public snapshot.

Developer reproduction (the workbench itself still requires no commands):

1. Read the installed channel's `build_manifest.id`; extract `*.xml`, `*.ini` and `*.socpak` from that same installation's `Data.p4k` into an ignored local directory with [unp4k v4.0.87](https://github.com/dolkensp/unp4k/releases/tag/v4.0.87). The XML filter also extracts `Data/Game2.dcb`.
2. Convert the database and binary XML with unforge. The local v4.0.87 source build used `MemoryStream(File.ReadAllBytes(path))` instead of `File.OpenRead(path)` for the database input to avoid slow random disk reads, and `File.Create` instead of `File.OpenWrite` for complete output replacement. Parsing rules were unchanged. This release writes individual database records, rather than a monolithic `Game2.xml`.
3. Use [ScDataDumper commit 120a728](https://github.com/octfx/ScDataDumper/tree/120a728639bdd1b06525a0f8574cb0e91d0fbf8d) with PHP 8.5.12 and its Composer lockfile. Run `generate:cache`, `load:items` and `load:vehicles` against the converted directory. On Windows, normalize cached paths to forward slashes before the `VehicleService::initialize` spaceship/ground-vehicle/actor directory filters: the cache contains `/` even though `DIRECTORY_SEPARATOR` is `\\`. Without this exporter fix, it exports zero vehicles. Keep the individual `items/*.json` raw records as well as `ships.json` and `ship-items.json`. The cache scans the individual records; a missing monolithic `Game2.xml` message from this exporter is expected with this unforge version, but completeness must be checked in the resulting catalogue.
4. Activate the complete export with `python -m citizensolver import-local <export-folder> <installed-LIVE-folder> <unpacked-folder> --exporter-revision 120a728639bdd1b06525a0f8574cb0e91d0fbf8d`. Restart the local CitizenSolver server after activation.

`import-local` derives the version from the installed build manifest and channel folder. It records the manifest, extracted database SHA-256, exporter commit, snapshot checksums and hashes of the raw sequence records. The local snapshot ID is a content-derived SHA-1 identifier, not a Git commit. Activation follows schema/checksum validation, so a failed import keeps the previous active manifest. Raw records supply the sequence entries omitted by the standard export; no erkul scripts or backend data are imported. The extraction and export must actually come from that client: supplying a different build manifest cannot prove arbitrary JSON has that provenance.

Extraction tools, game files, raw captures and generated catalogues remain under ignored `data/`. Only our importer, calculation changes, synthetic tests and verification documentation are committed.

## Price and hangar records

[FleetYards](https://github.com/fleetyards/fleetyards) exposes its public model API at `https://api.fleetyards.net/v1/models`. CitizenSolver caches its paginated model records locally and matches `scIdentifier` to the game `ClassName`, case-insensitively. No fuzzy-name prices or variant inheritance are used. The cache records download time and source record/shop update times; downloading today does not make an old price current.

USD uses `pledgePrice`: a reference standalone pledge value, not a live offer, tax-inclusive total, discount, upgrade route or resale quote. aUEC uses the cheapest positive `availability.soldAt` shop listing. No listing means **no recorded listing**, not definitive proof a ship is unobtainable. Both budgets are hard ceilings when supplied. Equipment costs and component shop availability remain unmodeled.

Hangar filtering uses `metrics.dockSize`, not the game export's numeric size or FleetYards' general ship-size label. `extra_extra_small`, `extra_small` and `small` are grouped into Small; medium/large/extra_large map directly. `capital` and missing values stay unknown. This is an **inferred fit class**, not a validated spawn guarantee at every location or with deployed cargo. In particular, a Hull C's loaded configuration needs separate treatment.

CIG's [Hangar FAQ](https://support.robertsspaceindustries.com/hc/en-us/articles/115013325128-Hangar-FAQs) names Small, Medium, Large and Extra Large hangars. Its Retaliator, Caterpillar, Starfarer, Reclaimer and 890 Jump examples agree with the corresponding FleetYards classes inspected during development. It does not certify every ship in this cache. Public hosting still needs review of data-serving terms for these sources.

## Activity objectives

The first presets express user preferences, not official balance guidance or proven PvP win rates. Further useful dimensions include acceleration/boost endurance, weapon reach and velocity, shield recovery, quantum range and fuel, crew requirements, container sizes/loading access, running costs and salvage throughput.

Mining needs a separate model for fracture power, rock resistance/instability, extraction and ore containers. CIG's [Mining Basics](https://support.robertsspaceindustries.com/hc/en-us/articles/360007611573-Mining-Basics) and [Commodities](https://support.robertsspaceindustries.com/hc/en-us/articles/360034785754-Commodities) distinguish this from ordinary cargo. We therefore expose cargo-grid capacity now and leave the mining preset unavailable until those inputs are modeled.

Before hosting a public catalogue on concrete-foundry.com, confirm the dataset's redistribution/serving terms and applicable CIG fan-content requirements, and include required attribution. Public availability alone is not a redistribution license. The initial repository publishes our engine, synthetic tests and documentation, with no bundled game dataset, art or third-party application code. No public deployment has been made.
