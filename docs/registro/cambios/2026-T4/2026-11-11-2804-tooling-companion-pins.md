# Change: compatible Black and Pylint companion pins (#2804)

## Scope

The development-tool update raised Black to 26.10.1 and Pylint to 4.0.9,
but the shared dependency pins in `requirements/base.txt` still selected
pathspec 0.12.1 and astroid 3.2.4. CI could not build its development image.

## Behavior

Align pathspec to 1.0.0 and astroid to 4.0.2, the minimum compatible versions
required by these tool releases. Keep the requested Black and Pylint upgrades,
the existing development/lint split, and all other pins unchanged. This follows
the existing exact-pin convention; no new project dependency is introduced.

Requires technical review: shared dependency pins also enter runtime images.
This fixes dependency resolution, not any new formatter or lint diagnostics.

## Verification

An isolated `uv pip compile` of the explicitly pinned tooling dependency graph
on Python 3.12 failed before the change with the Black/pathspec conflict.
The same resolver command succeeds after the companion pins are aligned.
Upstream PyPI metadata for Black 26.10.1 and Pylint 4.0.9 confirms their
pathspec>=1.0.0 and astroid>=4.0.2,<=4.1.dev0 requirements.
No application behavior changes, so resolver compatibility is the regression
check instead of an application test. Full service image builds, full lint,
and CI remain required; no deployment or real database access was performed.
Dependabot's missing GitHub App key in artifact/autofix CI is a separate blocker.