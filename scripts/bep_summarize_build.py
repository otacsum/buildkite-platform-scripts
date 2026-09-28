import json

targets = []
build_tool_version = None
overall_success = None
exit_code = None
actions_created = actions_executed = None
wall_ms = cpu_ms = None

with open('/tmp/bep-build.json') as f:
    for line in f:
        ev = json.loads(line)
        ids = ev.get('id', {})
        if 'started' in ids:
            build_tool_version = ev['started'].get('buildToolVersion')
        if 'buildFinished' in ids:
            fin = ev['finished']
            overall_success = fin.get('overallSuccess', False)
            exit_code = fin.get('exitCode', {}).get('name')
        if 'targetCompleted' in ids:
            label = ids['targetCompleted']['label']
            success = ev.get('completed', {}).get('success', False)
            targets.append((label, success))
        if 'buildMetrics' in ids:
            m = ev['buildMetrics']
            actions_created = m.get('actionSummary', {}).get('actionsCreated')
            actions_executed = m.get('actionSummary', {}).get('actionsExecuted')
            wall_ms = m.get('timingMetrics', {}).get('wallTimeInMs')
            cpu_ms = m.get('timingMetrics', {}).get('cpuTimeInMs')

lines = []
lines.append(f"**Bazel {build_tool_version}** - build {'succeeded' if overall_success else 'FAILED'} ({exit_code})")
lines.append("")
for label, success in targets:
    icon = "✅" if success else "❌"
    lines.append(f"- {icon} `{label}`")
lines.append("")
if wall_ms:
    lines.append(f"Wall time: {int(wall_ms)/1000:.2f}s | CPU time: {int(cpu_ms)/1000:.2f}s")
if actions_created is not None:
    skipped = int(actions_created) - int(actions_executed)
    if skipped > 0:
        lines.append(f"Actions: {actions_executed} executed / {actions_created} created ({skipped} skipped via local cache)")
    else:
        lines.append(f"Actions: {actions_executed} executed / {actions_created} created")

with open('/tmp/bep-build-summary.md', 'w') as out:
    out.write("\n".join(lines))
