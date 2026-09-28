# buildkite-platform-scripts

Platform-owned CI logic for the `otacsum/buildkite-bazel-example` Buildkite
evaluation POC, specifically its `prescriptive-cicd` branch.

## Why this is a separate repo

The whole point of `prescriptive-cicd` is that a maintainer of the
*application* repo cannot alter, bypass, or extend the mandatory CI logic
through a pull request or commit there. That only holds if the logic
genuinely lives somewhere they don't have write access to - this repo, not
a directory inside the application repo.

This mirrors the same pattern the org already uses for its real GitHub
Actions framework (`ccf-ci-bazel`): a separate, reusable-tooling repo that
consumer repos reference by pinned version, but do not control.

## How it's consumed

The application repo's Buildkite dashboard pipeline (not stored in any
repo - see its `PRESCRIPTIVE-CI.md`) clones this repo at a **pinned tag**
(currently `v1.0.0`, see `bootstrap/generate_core_pipeline.py` and the
dashboard's own bootstrap steps) and runs one entrypoint script. Every
generated build/test/static-analysis step independently re-clones this
repo at the same pinned ref and runs a plain script from `scripts/` -
nothing here is ever embedded as literal text in a pipeline YAML, so
ordinary shell/Python code in these files is never subject to Buildkite's
environment interpolation.

## Layout

- `bootstrap/generate_core_pipeline.py` - entrypoint for the dashboard's
  "Generate Core Pipeline" step. Runs change detection, then generates and
  uploads the real build/test/static-analysis/status steps.
- `bootstrap/load_extensions.py` - entrypoint for the dashboard's "Load
  Extensions" step. Validates and uploads the application repo's optional
  `.buildkite-extensions.yml`.
- `lib/detect_skip.py` - change-detection logic (git diff + bazel query),
  shared/importable.
- `scripts/*.sh`, `scripts/*.py` - the actual build/test/static-analysis
  commands and their result summarizers, as plain, independently runnable
  files.

## Releasing a change

Tag a new version (e.g. `v1.1.0`) after merging, then update the
`PLATFORM_REPO_REF` constant in `bootstrap/generate_core_pipeline.py` (and
in the dashboard's own bootstrap steps) to point at it. Never point at a
floating branch - pin to a tag or commit SHA, same supply-chain principle
as pinning a Buildkite plugin version.
