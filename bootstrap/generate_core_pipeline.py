"""Entrypoint invoked by the dashboard's "Generate Core Pipeline" step.

Decides whether bazel work can be skipped for this commit, then generates
and uploads the real build/test/static-analysis/status steps. Each
generated step independently clones this same platform-scripts repo (at
the same pinned ref) and runs a plain script file from it - the scripts
are never embedded as literal text in any pipeline YAML, so none of them
are ever subject to Buildkite's environment interpolation. Normal shell
variable references in those script files (scripts/*.sh) are safe exactly
as written.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
from detect_skip import detect_skip  # noqa: E402

PLATFORM_REPO_URL = "https://github.com/otacsum/buildkite-platform-scripts.git"
PLATFORM_REPO_REF = "v1.0.1"

# Cloned to a fresh, unique directory per job (not a fixed path like
# /tmp/platform-scripts) because multiple jobs can share one agent host's
# filesystem - a fixed path would let one job's clone collide with, or fall
# back to, another job's stale/partial checkout. "$$CLONE_DIR" (not
# "$CLONE_DIR") is deliberate: this string is embedded into pipeline YAML
# that Buildkite uploads and then interpolates once as a real step, and the
# double dollar sign is what survives that pass as a real "$CLONE_DIR" for
# bash to resolve - this file's own source is a plain, non-interpolated
# file, so writing it directly here (no chr(36) tricks needed) is safe.
CLONE_CMD = (
    "CLONE_DIR=$(mktemp -d)\n"
    f"git clone --branch {PLATFORM_REPO_REF} --depth 1 {PLATFORM_REPO_URL} \"$$CLONE_DIR\""
)


ANALYSIS_STEPS = ["clang-format", "cppcheck", "buildifier"]
SOFT_FAIL_ANALYSIS = {"clang-format", "cppcheck"}


def truncate(reason, limit=70):
    return reason if len(reason) <= limit else reason[: limit - 3] + "..."


def script_command(script_name):
    return f'{CLONE_CMD}\nbash "$$CLONE_DIR/scripts/{script_name}"'


def build_steps(skip, reason):
    reason_txt = truncate(reason)

    steps = [
        {
            "label": ":bazel: Build",
            "key": "build",
            "command": script_command("build.sh"),
            "timeout_in_minutes": 10,
        },
        {
            "label": ":bazel: Test",
            "key": "test",
            "depends_on": "build",
            "command": script_command("test.sh"),
            "timeout_in_minutes": 10,
        },
    ]

    for name in ANALYSIS_STEPS:
        step = {
            "label": f":clipboard: {name}",
            "key": f"analysis-{name}",
            "command": script_command(f"analysis-{name}.sh"),
            "timeout_in_minutes": 5,
        }
        if name in SOFT_FAIL_ANALYSIS:
            step["soft_fail"] = True
        steps.append(step)

    if skip:
        for step in steps:
            step["skip"] = reason_txt

    steps.append({"wait": None})
    steps.append({
        "label": ":white_check_mark: Status",
        "key": "status",
        "depends_on": ["build", "test"],
        "command": 'echo "Build and test succeeded: critical path is green (prescriptive)."',
        "timeout_in_minutes": 5,
    })
    return steps


def main():
    try:
        skip, reason = detect_skip()
    except Exception as e:
        skip, reason = False, f"change detection error - running everything ({e!r})"

    import yaml
    steps = build_steps(skip, reason)
    pipeline_yaml = yaml.dump({"steps": steps}, sort_keys=False)

    upload = subprocess.run(["buildkite-agent", "pipeline", "upload"], input=pipeline_yaml, text=True)

    style = "info" if skip else "success"
    verb = "Skipping" if skip else "Running"
    body = f"**Change detection**: {verb} bazel build/test/static-analysis - {reason}."
    subprocess.run(["buildkite-agent", "annotate", "--style", style, "--context", "detect-changes"],
                    input=body, text=True)

    if upload.returncode != 0:
        subprocess.run(["buildkite-agent", "annotate", "--style", "error", "--context", "detect-changes"],
                        input="**Error**: `buildkite-agent pipeline upload` failed - see job log above.", text=True)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
