#!/usr/bin/env bash
# Platform-owned build step. Plain bash - this file is fetched via git clone
# and executed directly, so it is never subject to Buildkite's pipeline-YAML
# environment interpolation. Normal $VAR references are safe here.
set +e

bazel build --build_event_json_file=/tmp/bep-build.json //main:hello-world
STATUS=$?

python3 "$(dirname "$0")/bep_summarize_build.py"

cat /tmp/bep-build-summary.md | buildkite-agent annotate \
  --style "$([ "$STATUS" -eq 0 ] && echo success || echo error)" \
  --context bep-build

buildkite-agent artifact upload /tmp/bep-build.json

exit "$STATUS"
