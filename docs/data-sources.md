# Data sources and attribution

CitizenSolver is an independent application. It does not use erkul's private backend or redistribute its code, site assets or interface. erkul's [About page](https://erkul.games/about) explains its own access restrictions and licensing.

The initial dataset is [StarCitizenWiki/scunpacked-data](https://github.com/StarCitizenWiki/scunpacked-data), revision [1340c8303709904165e2da0fa7060bce0624260b](https://github.com/StarCitizenWiki/scunpacked-data/commit/1340c8303709904165e2da0fa7060bce0624260b), labeled `4.10.2-LIVE.12881860`. `ships.json` contains full exported ship records; `ship-items.json` supplies standardized component records. Both are downloaded by the user and stored locally, outside Git.

The exporter is [octfx/ScDataDumper](https://github.com/octfx/ScDataDumper), whose package metadata declares MIT. Its exported schema and documented calculations informed the importer and model. Its software license does not, by itself, license underlying CIG game data or imagery. No exporter software is installed or executed by CitizenSolver.

Game content and trademarks belong to their respective owners. CitizenSolver is an unofficial fan project and is not affiliated with or endorsed by Cloud Imperium Games or Roberts Space Industries.

Before hosting a public catalogue on concrete-foundry.com, confirm the dataset's redistribution/serving terms and applicable CIG fan-content requirements, and include required attribution. Public availability alone is not a redistribution license. The initial repository publishes our engine, synthetic tests and documentation, with no bundled game dataset, art or third-party application code. No public deployment has been made.
