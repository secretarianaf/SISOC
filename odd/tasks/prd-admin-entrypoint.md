# Production administration entry point
Branch: `hotfix/prd-management-graph`; delivery: single coherent hotfix, ask-on-risk below 400 authored lines excluding earlier documentation.
Runner: focused stdlib/subprocess pytest tests without Django DB setup; read-only production probes. Implementation inline; independent verification required for delivery/runtime safeguards (Risk: items 3, 5).

## Specs

- S1: "Si ya encontraste por que sucede el error, arreglalo eficientemente para que no vuelva a suceder." Provide an automatic administration entry point selecting the running immutable release's full migrator; retain Django arguments and exit status, bypass startup preparation and avoid starting dependencies. Wrong-context graph commands must fail with actionable guidance rather than NodeNotFoundError; do not weaken checks or change graph dependencies.
- S2: "Si hay que ejecutar algo en produccion para dejar funcionando las migraciones, hazlo." Deploy the minimum verified administration repair within the already-authorized PRD scope, with a captured baseline and explicit rollback. Verify graph, dry-run detection, migration plan and health; no migrate writes, fake migrations or account creation without a proven need and applicable authority.

## Tasks

- T1 (S1): complete, inline, commit `32ac9a403` — automatic migrator entry point and pre-Django guard; RED observed, GREEN 9 focused tests and adjacent suite 67 before two added rejection cases. Coverage 90% (manage.py 84%, helper 96%); Black 24.8, Pylint 3.2.6 and docs paths pass. No writer trigger.
- T2 (S1-S2): complete, delegated — independent scratch-copy verifier found no blockers; targeted `.dockerignore` correction `3e7e3b8d6` also passed. Parent reran focused tests. Actual candidate images passed full-graph/drift/plan and baseline-equivalent core checks. RDD remains globally disabled.
- T3 (S2): complete, inline with delegated canonical build — deployed immutable `3e7e3b8d6`, recreated only core; healthy/200, other service IDs unchanged, migration-history hash unchanged, no new error markers. Automatic CLI passes and old entry rejects safely. Rollback: `$HOME/sisoc-admin-hotfix.KRJiG3/rollback.sh`. No DB writes/accounts.

## Log

- L1 (2026-11-11), user request verbatim: "no estas sirviendo de nada. Si ya encontraste por que sucede el error, arreglalo eficientemente para que no vuelva a suceder. Si hay que ejecutar algo en produccion para dejar funcionando las migraciones, hazlo."
- L2: Earlier diagnosis verified valid full graph at production revision `3ab3d849f956682cc7e396816d3c3cee86bb5366`; core is intentionally partial. Documentation-only correction was insufficient for the requested recurrence prevention. This task adds executable prevention, not migration dependency changes.
- L3: Baseline original PRD dry-run command reproduced `NodeNotFoundError` (`users.0033` → `pwa.0018`) before implementation. Local RED also exposed missing local `unfold`, so full-runtime proof must come from actual candidate images, not local Django stubs. Differential stdout/stderr/exit for shared unaffected commands is required. RDD remains off; Risk: items 3 and 5 (shared administrative CLI and production delivery).
- L4: Candidate `32ac9a403` passed independent verification (nine tests, rejection-state hashes and five baseline/candidate command comparisons). Automatic helper also passed real PRD dry-run and plan against the active old release. Snapshot and rollback: `$HOME/sisoc-admin-hotfix.KRJiG3/`; unchanged migration-history fingerprint captured. Canonical image build failed before image creation because Docker traversed protected `.deploy/pwa` scratch content. No permissions weakened or protected content traversed manually. Exclude `.deploy/` from Docker context, consistent with existing operational artifact exclusions, then retry only this corrected build.
- L5: Corrected canonical build and production probes passed. Source branch published; integration into main remains separate and no merge was performed. Full GitHub CI/full Django suite not run for this emergency deployment (local full environment lacks unfold); scoped tests, independent probes, coverage, lint, actual image checks and live read-only checks were observed. Health is not human acceptance. Local scratch cleanup was policy-denied; temp verification artifacts remain outside the worktree.
