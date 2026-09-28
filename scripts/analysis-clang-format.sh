#!/usr/bin/env bash
set +e

clang-format --dry-run --Werror main/*.cc main/*.h > /tmp/clang-format-output.txt 2>&1
STATUS=$?

if [ "$STATUS" -eq 0 ]; then
  echo "✅ **clang-format**: no formatting issues found." | buildkite-agent annotate --style success --context clang-format
else
  {
    echo "⚠️ **clang-format** found formatting issues (informational only):"
    echo
    echo '```'
    cat /tmp/clang-format-output.txt
    echo '```'
  } | buildkite-agent annotate --style warning --context clang-format
fi

exit "$STATUS"
