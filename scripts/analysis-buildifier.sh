#!/usr/bin/env bash
set +e

buildifier -mode=diff -lint=warn main/BUILD > /tmp/buildifier-output.txt 2>&1
STATUS=$?

if [ "$STATUS" -eq 0 ]; then
  echo "✅ **buildifier**: BUILD files clean." | buildkite-agent annotate --style success --context buildifier
else
  {
    echo "❌ **buildifier** found issues:"
    echo
    echo '```'
    cat /tmp/buildifier-output.txt
    echo '```'
  } | buildkite-agent annotate --style error --context buildifier
fi

exit "$STATUS"
