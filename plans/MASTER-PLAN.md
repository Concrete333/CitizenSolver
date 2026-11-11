# CitizenSolver work

## Implemented initial version

- Pinned public-data importer, checksums and atomic snapshot activation.
- Per-port compatibility, exact build replay and provenance.
- Experimental SCM damage, endurance, power/cooling, signatures and rated flight model.
- Bounded mixed-component search, explicit constraints and multi-ship comparison.
- CLI and local JSON API; synthetic offline regression tests.

## Next

1. Validate exact-build stock and changed Meteor fits against measured game behavior. Resolve ship capacitor buffs/pools, current flight curves, component modifiers and thermal/signature formulas before claiming accurate optimization.
2. Add a validated firing scheduler (shared energy capacity, fire groups, spin-up/charged modes), target range/hit assumptions, armor and penetration. Preserve distinction between distortion and hull damage.
3. Establish current player/shop availability, ownership and crafted-quality data rather than assuming every compatible record is obtainable.
4. Add natural-language requests translated into visible, editable goals and constraints. Never let generated text supply uncomputed stats.
5. Build the UI and deployment for the free tool on concrete-foundry.com. Confirm data-serving rights and attribution first; use a production service adapter, not the local development server.

The initial engine can already search all imported ships supported by its model, but validation begins with the Meteor and medium fighters. Unsupported ships/components remain explicitly reported.
