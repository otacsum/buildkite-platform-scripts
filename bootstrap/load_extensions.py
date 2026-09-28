"""Entrypoint invoked by the dashboard's "Load Extensions" step.

Validates the application repo's optional .buildkite-extensions.yml against
a strict, locked schema and uploads the resulting jobs. See
PRESCRIPTIVE-CI.md in the application repo for the schema and the
governance rationale.

Note: unlike the core build/test/analysis scripts, this file's own escaping
concern doesn't go away just because it's a plain file now - it still has
to escape *maintainer-provided* command text before embedding it into the
pipeline it uploads, since that uploaded content is new pipeline YAML and
will be interpolated once it becomes a real step. What DOES go away is any
concern about this script's *own* source, since it is never itself embedded
as literal pipeline YAML text - a literal "$$" here is just two ordinary
characters as far as Buildkite is concerned.
"""
import os
import re
import subprocess
import sys

import yaml

EXT_FILE = ".buildkite-extensions.yml"
MAX_JOBS = 3
MAX_COMMANDS = 20
MIN_TIMEOUT = 1
MAX_TIMEOUT = 10
NAME_RE = re.compile(r'^[a-z0-9-]{1,40}$')
ALLOWED_JOB_KEYS = {"name", "commands", "timeout_minutes", "soft_fail"}
# No reserved-name check needed: every generated step key is prefixed with
# "ext-", so an extension job can never collide with a core step's key
# (build/test/status/etc.) regardless of what name a maintainer picks.


def annotate(style, body):
    subprocess.run(
        ["buildkite-agent", "annotate", "--style", style, "--context", "extensions"],
        input=body, text=True,
    )


def fail(message):
    annotate("error", f"**.buildkite-extensions.yml validation failed**\n\n{message}\n\nNo extension jobs were loaded.")
    sys.exit(1)


def main():
    if not os.path.isfile(EXT_FILE):
        annotate("info", "**Extensions**: no `.buildkite-extensions.yml` found - no repo-provided jobs this run.")
        sys.exit(0)

    with open(EXT_FILE) as f:
        raw = f.read()

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        fail(f"File is not valid YAML: {e}")

    if not isinstance(data, dict) or set(data.keys()) != {"jobs"}:
        fail("Top level must be a mapping with exactly one key: `jobs`.")

    jobs = data["jobs"]
    if not isinstance(jobs, list) or len(jobs) == 0:
        fail("`jobs` must be a non-empty list.")
    if len(jobs) > MAX_JOBS:
        fail(f"`jobs` has {len(jobs)} entries - max allowed is {MAX_JOBS} (free-tier concurrency protection).")

    seen_names = set()
    generated_steps = []
    for idx, job in enumerate(jobs):
        ctx = f"jobs[{idx}]"
        if not isinstance(job, dict):
            fail(f"{ctx} must be a mapping.")
        extra = set(job.keys()) - ALLOWED_JOB_KEYS
        if extra:
            fail(f"{ctx} has disallowed key(s): {sorted(extra)}. Allowed keys: {sorted(ALLOWED_JOB_KEYS)}.")

        name = job.get("name")
        if not isinstance(name, str) or not NAME_RE.match(name):
            fail(f"{ctx}.name must match ^[a-z0-9-]{{1,40}}$ (got: {name!r}).")
        key = f"ext-{name}"
        if name in seen_names:
            fail(f"{ctx}.name '{name}' is a duplicate - job names must be unique within this file.")
        seen_names.add(name)

        commands = job.get("commands")
        if not isinstance(commands, list) or not commands or not all(isinstance(c, str) and c.strip() for c in commands):
            fail(f"{ctx}.commands must be a non-empty list of non-empty strings.")
        if len(commands) > MAX_COMMANDS:
            fail(f"{ctx}.commands has {len(commands)} entries - max allowed is {MAX_COMMANDS}.")

        timeout = job.get("timeout_minutes", 5)
        if not isinstance(timeout, int) or isinstance(timeout, bool):
            fail(f"{ctx}.timeout_minutes must be an integer.")
        timeout = max(MIN_TIMEOUT, min(MAX_TIMEOUT, timeout))

        soft_fail = job.get("soft_fail", False)
        if not isinstance(soft_fail, bool):
            fail(f"{ctx}.soft_fail must be a boolean.")

        # Escape literal dollar signs in maintainer-provided commands: the
        # UPLOADED pipeline this produces will be interpolated by Buildkite
        # once it becomes a real step, so an un-escaped variable-looking
        # token in a maintainer's command would be silently blanked.
        escaped_commands = [c.replace("$", "$$") for c in commands]
        script = "set -e\n" + "\n".join(escaped_commands)

        generated_steps.append({
            "label": f":gear: {name}",
            "key": key,
            "command": script,
            "timeout_in_minutes": timeout,
            "soft_fail": soft_fail,
        })

    pipeline_yaml = yaml.dump({"steps": generated_steps}, sort_keys=False)

    upload = subprocess.run(["buildkite-agent", "pipeline", "upload"], input=pipeline_yaml, text=True)
    if upload.returncode != 0:
        fail("`buildkite-agent pipeline upload` failed - see job log above.")

    names_list = "\n".join(
        f"- `{j['name']}` (timeout {j.get('timeout_minutes', 5)}m, soft_fail={j.get('soft_fail', False)})"
        for j in jobs
    )
    annotate("success", f"**Extensions loaded**: {len(jobs)} job(s) from `.buildkite-extensions.yml`\n\n{names_list}")
    sys.exit(0)


if __name__ == "__main__":
    main()
