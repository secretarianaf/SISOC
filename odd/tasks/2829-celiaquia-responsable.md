# Issue 2829 — Responsible eligibility in approved payroll
Branch: `fix/2829-celiaquia-responsable`, base `origin/homologacion` at `b548d634d98b56ff1d929a2a04e736496f0adc09`.
Delivery: single PR (forecast under 400 authored lines); pytest in isolated offline Docker with synthetic SQLite.

## Specs

- S1: "Una persona a cargo no se incluye en la nómina si su responsable no tiene revisión técnica Aprobado en el mismo expediente."
- S2: "Una persona a cargo no se incluye en la nómina si su responsable no figura en el archivo de cruce de Sintys." Preserve existing child-owned MATCH semantics, including responsible-only SIN_CRUCE.
- S3: "Para la nómina, solo se considera responsable de una persona a cargo a quien tenga legajo en el mismo expediente. Los vínculos familiares que vengan de otros expedientes o de otras fuentes no se toman en cuenta."
- S4: "partiendo de la branch homologacion, resuelve el issue 2829, crea pr y monitorea que se mergee"

## Tasks

- T1 | S1–S3 | inline: one understood payroll behavior, no writer trigger | verified | RED 8 failed / 1 passed; GREEN 25 passed; module suite 632 passed; commit `7818b438cd2de8754c31add23d7ca46799b6ac92`.
- T2 | S4 | inline: publication and external monitoring | monitoring | PR [2831](https://github.com/secretarianaf/SISOC/pull/2831), base homologacion; CI/merge pending; agent does not merge or deploy.

## Log

- L1 (2026-10-29): Original request: "partiendo de la branch homologacion, resuelve el issue 2829, crea pr y monitorea que se mergee"
- L2: User: "autorizo" — authorizes the requested gpt-6-luna explorer substitute because configured gpt-6.1-luna is unavailable.
- L3: Existing checkout is dirty and detached; created a clean sibling worktree, preserving all original changes. Base explicitly selected by user overrides repository default development base.
- L4: Explorer mapped the flow; parent checked implementation and corrected its suggestion: pure responsible legajos intentionally stay SIN_CRUCE, and dependent MATCH already certifies responsible presence in Sintys. Do not require MATCH on the responsible.
- L5: Payroll-only scope: resolve family links against all current-expediente legajos before checking the selected responsible's approval. Preserve alphabetical ambiguity handling, pure-role exclusion, independent beneficiaries, headers/order and quota labels. Availability must agree with actual exported rows. Do not modify crossing, quota assignment or shared family helper.
- L6: Native Python fails before collection (missing unfold); old virtualenvs point to missing Python 3.10. Existing local image sisoc-2789-django:latest runs offline with synthetic SQLite; original export tests: 13 passed. No dependencies installed, no real DB/provider connections.
- L7: Tracking is needed for external PR/CI/merge continuation; implementation stays inline. Risk: none — payroll filtering requested by issue, no shared helper/contract/schema/auth/delivery changes.
- L8: Implemented scoped responsible resolution and approval check, reused for export and availability. Existing alphabetical selection and responsible-only SIN_CRUCE retained. Regression cases cover every technical review state, outsider with/without another expediente, local responsible plus alphabetically earlier outsider, and real Sintys file presence/absence. S2 preserves existing behavior, so its tests are compatibility checks rather than fabricated RED.
- L9: Full Celiaquia suite delegated as a bounded long-running action (not independent risk verification): 632 passed, 8 warnings, 127.68 seconds. Service coverage 95%; no source edits by runner. Black check passed. No app environment or real database configured in this clean worktree; browser/human acceptance is not established.
- L10: Pylint initially could not infer the compatibility alias for FamiliaService. Import the same class from its implementation module, without changing the shared helper or suppressing diagnostics. Pylint now 10/10; documentation path check: 86 documents, zero broken/obsolete references. Native precommit assessment could not classify untracked documentation; assessment will use the committed range to avoid ambiguous inventory.
- L11: Work-unit commit `7818b438cd2de8754c31add23d7ca46799b6ac92`, 314 authored changed lines. Native committed assessment: medium, review_due=false, under_budget; no additional review started. Parent spot check of final import: 25 tests passed. Published PR2831 against homologacion using the configured GitHub session; initial head has checks queued and merge status BLOCKED/MERGEABLE. No merge/deploy performed.
