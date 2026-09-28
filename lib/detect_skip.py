"""Change-detection logic shared by the core pipeline generator.

Decides whether the bazel build/test/static-analysis steps can be skipped
for this commit, based on git diff + a bazel query of the real dependency
closure - not just a naive file-path heuristic.
"""
import subprocess

TARGETS = "//main:hello-world union //main:greet_test"
ALWAYS_RUN_BASENAMES = {"BUILD", "BUILD.bazel", "WORKSPACE", "WORKSPACE.bazel",
                         "MODULE.bazel", "MODULE.bazel.lock"}


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def is_always_run_file(path):
    basename = path.rsplit("/", 1)[-1]
    return basename in ALWAYS_RUN_BASENAMES or path.endswith(".bzl")


def label_to_path(label):
    if not label.startswith("//"):
        return None  # external repo (@...) - never appears in our own git diff
    label = label[2:]
    if ":" in label:
        pkg, name = label.split(":", 1)
    else:
        pkg, name = label, ""
    return f"{pkg}/{name}" if pkg else name


def detect_skip():
    """Returns (skip: bool, reason: str). Any uncertainty defaults to
    skip=False (run everything) - a bug in this function must never
    silently hide a real change from being tested."""
    prev = sh(["git", "rev-parse", "HEAD~1"])
    if prev.returncode != 0:
        return False, "no previous commit to diff against - running everything"

    prev_sha = prev.stdout.strip()
    diff = sh(["git", "diff", "--name-only", prev_sha, "HEAD"])
    if diff.returncode != 0:
        return False, "git diff failed - running everything to be safe"

    changed_files = set(f for f in diff.stdout.split("\n") if f.strip())
    if not changed_files:
        return False, "no changed files detected - running everything"

    if any(is_always_run_file(f) for f in changed_files):
        return False, "a build-definition file changed - always running"

    query = f'kind("source file", deps({TARGETS}))'
    result = sh(["bazel", "query", query, "--output=label"])
    if result.returncode != 0:
        return False, "bazel query failed - running everything to be safe"

    relevant_files = set()
    for label in result.stdout.split():
        path = label_to_path(label)
        if path:
            relevant_files.add(path)

    if changed_files & relevant_files:
        return False, "changed file(s) affect the build/test dependency closure"
    return True, "no changed files are in the bazel dependency closure"
