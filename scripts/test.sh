#!/usr/bin/env bash
# Platform-owned test step. Plain bash - see build.sh for why this is safe.
set +e

bazel test --build_event_json_file=/tmp/bep-test.json //main:greet_test --test_output=errors
STATUS=$?

python3 "$(dirname "$0")/bep_summarize_test.py"

cat /tmp/bep-test-summary.md | buildkite-agent annotate \
  --style "$([ "$STATUS" -eq 0 ] && echo success || echo error)" \
  --context bep-test

buildkite-agent artifact upload /tmp/bep-test.json

exit "$STATUS"
