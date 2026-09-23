# Validation

## Public release candidate 1.5.2.post2 — 2026-09-23

- Installed the built wheel in an isolated InvenTree 1.3.2 / PostgreSQL 15 instance.
- All 44 unit tests passed.
- All 13 freezer acceptance tests passed in 52.8 seconds.
- Frontend TypeScript/Vite production build and package metadata checks passed.
- Browser: previewed and created Demo_Box_01 with 81 empty child locations;
  captured four screenshots from fictional inventory.
- Installed CLI: read-only preview, creation, and exact retry passed for both layouts.
- Runtime Python files match 1.5.2.post1 except for the package version.

## Previous implementation validation

Validated on InvenTree 1.3.2 (Python 3.14.3) with isolated PostgreSQL 15.

- Frontend TypeScript check and Vite production build: passed.
- 44 upstream-generator and CSV unit tests: passed.
- 12 Django/PostgreSQL acceptance tests: passed (26.6 seconds after rebuild optimization).
- Additional PostgreSQL test for simultaneous creation in different slots of the
  same tree: passed, including descendant counts and position integrity.
- Covers 81/100-position layouts, parent placement, empty stock destinations,
  read-only previews, exact retries preserving stock, occupied/partial boxes,
  invalid inputs, rollback after injected position failure, simultaneous identical
  and conflicting submissions, native roles, session CSRF, revoked/expired tokens,
  template-write restrictions, and portable template equivalence.
- CSV tests cover duplicate normalized slot IDs, all-or-nothing preflight,
  stop-on-first-error, and resume without recreating completed boxes.

- Browser: authenticated InvenTree interface loaded the panel, resolved the slot
  path, previewed A1–I9, and created an empty 81-position box successfully.
- Representative batch: 100 alternating 9×9/10×10 boxes in one rack tree.
  Resumed an interrupted run: 84 created, 16 verified/skipped, 1,089 seconds.
  A subsequent full rerun skipped all 100 in 10.2 seconds. Timing is specific to
  this host and tree size; native tree maintenance grows with the hierarchy.
- Creation retains native validation, path generation, MPTT insertion, and save
  signals. Redundant per-position tree rebuilds are deferred to one final rebuild.
