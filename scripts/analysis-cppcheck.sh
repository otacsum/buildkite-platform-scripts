#!/usr/bin/env bash
set +e

cppcheck --enable=warning,style --language=c++ --error-exitcode=1 main/*.cc main/*.h > /tmp/cppcheck-output.txt 2>&1
STATUS=$?

if [ "$STATUS" -eq 0 ]; then
  echo "✅ **cppcheck**: no findings." | buildkite-agent annotate --style success --context cppcheck
else
  {
    echo "⚠️ **cppcheck** findings (informational only):"
    echo
    echo '```'
    cat /tmp/cppcheck-output.txt
    echo '```'
  } | buildkite-agent annotate --style warning --context cppcheck
fi

exit "$STATUS"
