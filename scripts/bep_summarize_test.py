import json

tests = []
overall_success = None
exit_code = None

with open('/tmp/bep-test.json') as f:
    for line in f:
        ev = json.loads(line)
        ids = ev.get('id', {})
        if 'buildFinished' in ids:
            fin = ev['finished']
            overall_success = fin.get('overallSuccess', False)
            exit_code = fin.get('exitCode', {}).get('name')
        if 'testSummary' in ids:
            label = ids['testSummary']['label']
            summary = ev.get('testSummary', {})
            status = summary.get('overallStatus')
            duration_ms = summary.get('totalRunDurationMillis')
            tests.append((label, status, duration_ms))

lines = []
lines.append(f"**Test run** - {'succeeded' if overall_success else 'FAILED'} ({exit_code})")
lines.append("")
for label, status, duration_ms in tests:
    icon = "✅" if status == "PASSED" else "❌"
    dur = f"{int(duration_ms)/1000:.2f}s" if duration_ms else "?"
    lines.append(f"- {icon} `{label}`: {status} ({dur})")

with open('/tmp/bep-test-summary.md', 'w') as out:
    out.write("\n".join(lines))
