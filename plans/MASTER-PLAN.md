# CitizenSolver work

## Implemented initial version

- Pinned public-data importer, checksums and atomic snapshot activation.
- Per-port compatibility, exact build replay and provenance.
- Experimental SCM damage, endurance, power/cooling, signatures and rated flight model.
- Bounded mixed-component search, explicit constraints and multi-ship comparison.
- CLI and local JSON API; synthetic offline regression tests.
- Browser workbench and double-click Windows launcher, with progress and JSON downloads.
- Shared 100% priorities, pips/slider views, editable PvE/PvP/cargo presets and single-stat goals.
- Ship-only USD/aUEC ceilings, recorded in-game listings, crew and inferred maximum hangar-class filters, with explicit unknown/exclusion reporting.
- FleetYards local market cache, exact class matching, provenance and UI refresh.

## Next

1. Resolve the [Meteor comparison discrepancies](../verification/meteor-erkul-2026-11-11.md): Echion sequence firing (800 vs 527 RPM), low-power capacitor load/recharge (225 vs 80 shots), ballistic weapon EM scaling and coolant demand/IR. Establish a shared game revision, then re-run the recommendation and compare the resulting fit. Validate stock and changed fits against measured game behavior; also resolve ship capacitor buffs/pools, flight curves and component modifiers before claiming accurate optimization.
2. Add a validated firing scheduler (shared energy capacity, fire groups, spin-up/charged modes), target range/hit assumptions, armor and penetration. Preserve distinction between distortion and hull damage.
3. Establish current player/shop availability, ownership and crafted-quality data rather than assuming every compatible record is obtainable.
4. Add natural-language requests translated into visible, editable goals and constraints. Never let generated text supply uncomputed stats.
5. Refine the existing UI and deploy the free tool on concrete-foundry.com. Confirm data-serving rights and attribution first; use a production service adapter, not the local development server.
6. Validate hangar/spawn fit, especially deployed cargo ships; expand exact market matches and add component costs/current purchase availability. Keep unknown distinct from unavailable.
7. Tune priority curves with player feedback; implement mining/salvage/hauling loop objectives only when their actual inputs are available. Add loading access, container sizes, fuel, travel time and operating costs rather than treating cargo SCU as profit or ore capacity.

The initial engine can already search all imported ships supported by its model, but validation begins with the Meteor and medium fighters. Unsupported ships/components remain explicitly reported.
