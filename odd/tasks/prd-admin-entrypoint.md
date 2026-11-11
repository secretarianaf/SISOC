# Production administration entry point
Branch: `hotfix/prd-management-graph`; delivery: single coherent hotfix, ask-on-risk below 400 authored lines excluding earlier documentation.
Runner: focused stdlib/subprocess pytest tests without Django DB setup; read-only production probes. Implementation inline; independent verification required for delivery/runtime safeguards (Risk: items 3, 5).

## Specs

- S1: "Si ya encontraste por que sucede el error, arreglalo eficientemente para que no vuelva a suceder." Provide an automatic administration entry point selecting the running immutable release's full migrator; retain Django arguments and exit status, bypass startup preparation and avoid starting dependencies. Wrong-context graph commands must fail with actionable guidance rather than NodeNotFoundError; do not weaken checks or change graph dependencies.
- S2: "Si hay que ejecutar algo en produccion para dejar funcionando las migraciones, hazlo." Deploy the minimum verified administration repair within the already-authorized PRD scope, with a captured baseline and explicit rollback. Verify graph, dry-run detection, migration plan and health; no migrate writes, fake migrations or account creation without a proven need and applicable authority.

## Tasks

- T1 (S1): inline, self-checks complete — automatic migrator entry point and pre-Django guard; RED 6 failing/1 existing preservation pass; GREEN 9 focused tests, adjacent suite 67 before two added rejection cases. Black 24.8 and Pylint 3.2.6 pass; docs paths pass. Parent owns one coherent behavior; no writer trigger.
- T2 (S1-S2): delegated verification, pending — independent scratch-copy verification for items 3/5; no production writes by verifier. RDD remains globally disabled.
- T3 (S2): inline, pending — versioned release, snapshot, minimal PRD installation, read-only runtime probes and bounded rollback. No unrelated services or database changes.

## Log

- L1 (2026-11-11), user request verbatim: "no estas sirviendo de nada. Si ya encontraste por que sucede el error, arreglalo eficientemente para que no vuelva a suceder. Si hay que ejecutar algo en produccion para dejar funcionando las migraciones, hazlo."
- L2: Earlier diagnosis verified valid full graph at production revision `3ab3d849f956682cc7e396816d3c3cee86bb5366`; core is intentionally partial. Documentation-only correction was insufficient for the requested recurrence prevention. This task adds executable prevention, not migration dependency changes.
- L3: Baseline original PRD dry-run command reproduced `NodeNotFoundError` (`users.0033` → `pwa.0018`) before implementation. Local RED also exposed missing local `unfold`, so full-runtime proof must come from actual candidate images, not local Django stubs. Differential stdout/stderr/exit for shared unaffected commands is required. RDD remains off; Risk: items 3 and 5 (shared administrative CLI and production delivery).
- L4: Candidate `32ac9a403` passed independent verification (nine tests, rejection-state hashes and five baseline/candidate command comparisons). Automatic helper also passed real PRD dry-run and plan against the active old release. Snapshot and rollback: `$HOME/sisoc-admin-hotfix.KRJiG3/`; unchanged migration-history fingerprint captured. Canonical image build failed before image creation because Docker traversed protected `.deploy/pwa` scratch content. No permissions weakened or protected content traversed manually. Exclude `.deploy/` from Docker context, consistent with existing operational artifact exclusions, then retry only this corrected build.
