# Verification

The offline suite uses only synthetic fixture data and temporary directories. It checks weapon cycles, finite ammunition, distortion separation, heat recovery, compatibility tags, editable guns inside locked mounts, power feasibility, pilot/turret separation, search constraints/bounds/determinism, saved-build replay, importer failure/checksums, and the local HTTP API.

On 11 November 2026, the initial 22-test Windows run passed in 0.606 seconds on Python 3.13.17. Slowest: HTTP integration 0.548 seconds; save/replay 0.015 seconds; bounded search 0.007 seconds. Local verification logs retain later run timings and are ignored by Git.

Development smoke checks used the pinned public 4.10.2 snapshot: stock Meteor evaluation, optimized Meteor builds, medium-fighter comparisons and saved-build replay. These prove the pipeline runs; they do not establish in-game numerical accuracy. In-game validation and same-build manual erkul comparisons have not been completed.
