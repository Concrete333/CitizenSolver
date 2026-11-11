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
- Visible minimum gun reach and per-weapon-group damage/range/pellet breakdown, including scattergun assumptions.
- Local-client import with build provenance and raw sequence timing; same-build Meteor damage/signature calibration against erkul.
- Best-compatible / shop-listed equipment modes, exact-UUID UEX NPC reports and in-UI refresh with patch/date provenance. Ship stock is always eligible.
- After-selection stealth and handling explanations: EM/IR plus effective per-axis cross-section, own radar ratings, turning, forward acceleration and braking. Explicit target-independent ranking proxies; no detection-distance claim.
- Optional selected-build component editor, per-port locks and optimization of unlocked equipment. Automatic power profiles remain separate from equipment locks.

## Next

1. Extend the [same-build Meteor calibration](../verification/meteor-erkul-12913470.md) to other stock and changed fits, then compare against measured game behavior. The sequence, low-power capacitor, weapon/plant EM and coolant discrepancies are resolved for the two tested Meteor builds. Ship capacitor buffs/pools, flight curves, transient heat and component modifiers still need broader validation.
2. Add an optional **post-selection matchup** view (owner, 11 November): opposing ship/size/radar, detection and destruction estimates in both directions. Never add target conditions to the initial ship-selection workflow. First validate hit/dispersion, armor/penetration, shield recovery, destruction criteria and the receiver/signature model. Keep distortion separate from hull damage. The current reach filter is a capability constraint, not a target simulation.
3. Validate transient stealth states and flight/pip/boost curves against game measurements. Current ratings and signature proxies are explicit estimates. Extend shop freshness evidence and eventually owned-inventory substitution; do not require an inventory setup to get the first recommendation. Crafted-quality data remains unknown.
4. Add natural-language requests translated into visible, editable goals and constraints. Never let generated text supply uncomputed stats.
5. Refine the existing UI and deploy the free tool on concrete-foundry.com. Confirm data-serving rights and attribution first; use a production service adapter, not the local development server.
6. Validate hangar/spawn fit, especially deployed cargo ships; expand exact market matches and add component costs/current purchase availability. Keep unknown distinct from unavailable.
7. Tune priority curves with player feedback; implement mining/salvage/hauling loop objectives only when their actual inputs are available. Add loading access, container sizes, fuel, travel time and operating costs rather than treating cargo SCU as profit or ore capacity.

The initial engine can already search all imported ships supported by its model, but validation begins with the Meteor and medium fighters. Unsupported ships/components remain explicitly reported.

Save/reopen and sharing workflows, complete purchasing economics, patch-update UX and public hosting remain later work. This iteration does not implement them.
