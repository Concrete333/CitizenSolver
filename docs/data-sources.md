# Data sources and attribution

CitizenSolver is an independent application. It does not use erkul's private backend or redistribute its code, site assets or interface. erkul's [About page](https://erkul.games/about) explains its own access restrictions and licensing.

The initial dataset is [StarCitizenWiki/scunpacked-data](https://github.com/StarCitizenWiki/scunpacked-data), revision [1340c8303709904165e2da0fa7060bce0624260b](https://github.com/StarCitizenWiki/scunpacked-data/commit/1340c8303709904165e2da0fa7060bce0624260b), labeled `4.10.2-LIVE.12881860`. `ships.json` contains full exported ship records; `ship-items.json` supplies standardized component records. Both are downloaded by the user and stored locally, outside Git.

The exporter is [octfx/ScDataDumper](https://github.com/octfx/ScDataDumper), whose package metadata declares MIT. Its exported schema and documented calculations informed the importer and model. Its software license does not, by itself, license underlying CIG game data or imagery. No exporter software is installed or executed by CitizenSolver.

Game content and trademarks belong to their respective owners. CitizenSolver is an unofficial fan project and is not affiliated with or endorsed by Cloud Imperium Games or Roberts Space Industries.

## Price and hangar records

[FleetYards](https://github.com/fleetyards/fleetyards) exposes its public model API at `https://api.fleetyards.net/v1/models`. CitizenSolver caches its paginated model records locally and matches `scIdentifier` to the game `ClassName`, case-insensitively. No fuzzy-name prices or variant inheritance are used. The cache records download time and source record/shop update times; downloading today does not make an old price current.

USD uses `pledgePrice`: a reference standalone pledge value, not a live offer, tax-inclusive total, discount, upgrade route or resale quote. aUEC uses the cheapest positive `availability.soldAt` shop listing. No listing means **no recorded listing**, not definitive proof a ship is unobtainable. Both budgets are hard ceilings when supplied. Equipment costs and component shop availability remain unmodeled.

Hangar filtering uses `metrics.dockSize`, not the game export's numeric size or FleetYards' general ship-size label. `extra_extra_small`, `extra_small` and `small` are grouped into Small; medium/large/extra_large map directly. `capital` and missing values stay unknown. This is an **inferred fit class**, not a validated spawn guarantee at every location or with deployed cargo. In particular, a Hull C's loaded configuration needs separate treatment.

CIG's [Hangar FAQ](https://support.robertsspaceindustries.com/hc/en-us/articles/115013325128-Hangar-FAQs) names Small, Medium, Large and Extra Large hangars. Its Retaliator, Caterpillar, Starfarer, Reclaimer and 890 Jump examples agree with the corresponding FleetYards classes inspected during development. It does not certify every ship in this cache. Public hosting still needs review of data-serving terms for these sources.

## Activity objectives

The first presets express user preferences, not official balance guidance or proven PvP win rates. Further useful dimensions include acceleration/boost endurance, weapon reach and velocity, shield recovery, quantum range and fuel, crew requirements, container sizes/loading access, running costs and salvage throughput.

Mining needs a separate model for fracture power, rock resistance/instability, extraction and ore containers. CIG's [Mining Basics](https://support.robertsspaceindustries.com/hc/en-us/articles/360007611573-Mining-Basics) and [Commodities](https://support.robertsspaceindustries.com/hc/en-us/articles/360034785754-Commodities) distinguish this from ordinary cargo. We therefore expose cargo-grid capacity now and leave the mining preset unavailable until those inputs are modeled.

Before hosting a public catalogue on concrete-foundry.com, confirm the dataset's redistribution/serving terms and applicable CIG fan-content requirements, and include required attribution. Public availability alone is not a redistribution license. The initial repository publishes our engine, synthetic tests and documentation, with no bundled game dataset, art or third-party application code. No public deployment has been made.
