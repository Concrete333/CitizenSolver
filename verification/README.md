# Verification

The offline suite uses only synthetic fixture data and temporary directories. It checks weapon cycles, finite ammunition, distortion separation, heat recovery, compatibility tags, editable guns inside locked mounts, power feasibility, pilot/turret separation, search constraints/bounds/determinism, saved-build replay, importer failure/checksums, and the local HTTP API.

On 11 November 2026, the initial 22-test Windows run passed in 0.606 seconds on Python 3.13.17. Slowest: HTTP integration 0.548 seconds; save/replay 0.015 seconds; bounded search 0.007 seconds. Local verification logs retain later run timings and are ignored by Git.

Development smoke checks used the pinned public 4.10.2 snapshot: stock Meteor evaluation, optimized Meteor builds, medium-fighter comparisons and saved-build replay. These prove the pipeline runs; they do not establish in-game numerical accuracy. In-game validation and same-patch manual erkul comparisons have not been completed.

The [11 November Meteor comparison](meteor-erkul-2026-11-11.md) matched the recommended 50% firepower / 50% stealth fit and eight-pip allocation in erkul. Alpha, shields, hull, armor and base flight ratings agreed; CitizenSolver overstated burst DPS by 17.2% and sustained DPS by 16.9%, with higher EM/IR estimates. Echion firing rate, low-power capacitor load and weapon signature scaling differed. Erkul used a newer 4.10.2 build, so this records a failed cross-calculator accuracy check rather than a same-patch or in-game validation. The report documents the exact loadout, versions, evidence and unresolved causes.

The browser-workbench update on 11 November passed 30 Windows tests in 1.148 seconds. Slowest: existing HTTP integration 0.536 s; browser-assets/background-search integration 0.522 s; save/replay 0.015 s. Python compilation and JavaScript syntax passed. The Node priority test exercised 808 sequential edits, endpoints and rounding, retaining exactly 100%.

Chrome checks covered Meteor optimization, real control redistribution, switching pips/sliders, a PvP medium-fighter comparison with both price ceilings and Small hangar fit (2 eligible of 21), and cargo ranking with both ceilings and a Medium hangar limit (84 eligible of 273). The downloaded Meteor JSON replayed successfully through the engine. Responsive layout was inspected at 390 px; it had no horizontal overflow. Browser console inspection found no application errors. The launcher's startup core started the hidden server and verified its health; the Windows file-association/double-click path was not separately automated.

Current local market coverage: 181 exact class matches out of 273 visible game ship records. Coverage varies by field; a matched record does not guarantee a price or known fit. Cache and API smoke results are evidence of integration only, not validation of live shop prices, spawn fit or combat accuracy.
