"""Release checkout must run after merge without a privileged fork PR event."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml


def test_release_uses_main_push_and_supports_manual_recovery():
    workflow = yaml.load(
        Path(".github/workflows/release-on-merge.yml").read_text(), Loader=yaml.BaseLoader
    )
    events = workflow["on"]
    assert "pull_request_target" not in events, "GitHub blocks fork checkout on this event"
    assert events["push"]["branches"] == ["main"]
    assert events["workflow_dispatch"]["inputs"]["pr_number"]["required"] == "true"


@pytest.mark.skipif(shutil.which("node") is None, reason="Node required to execute workflow script")
@pytest.mark.parametrize(
    "scenario,expected",
    [
        ("fork_merge", "release"),
        ("direct_push", "skip"),
        ("manual_retry", "release"),
        ("unmerged", "error"),
        ("wrong_branch", "error"),
        ("wrong_repository", "error"),
        ("invalid_number", "error"),
    ],
)
def test_resolve_actual_workflow_script(tmp_path, scenario, expected):
    workflow = yaml.load(
        Path(".github/workflows/release-on-merge.yml").read_text(), Loader=yaml.BaseLoader
    )
    step = next(step for step in workflow["jobs"]["prepare"]["steps"] if step.get("id") == "pr")
    harness = r"""
const fs = require('fs');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
process.env.RUNNER_TEMP = input.directory;
const pr = {
  number: 2, merged: true, merged_at: '2026-10-22', merge_commit_sha: 'merged-sha',
  base: { ref: 'main', repo: { full_name: 'ENDEVSOLS/LongGuard' } },
  head: { repo: { full_name: 'contributor/LongGuard' } }
};
const manual = !['fork_merge', 'direct_push'].includes(input.scenario);
if (input.scenario === 'unmerged') pr.merged = false;
if (input.scenario === 'wrong_branch') pr.base.ref = 'other';
if (input.scenario === 'wrong_repository') pr.base.repo.full_name = 'other/LongGuard';
const context = {
  repo: { owner: 'ENDEVSOLS', repo: 'LongGuard' }, sha: 'merged-sha',
  eventName: manual ? 'workflow_dispatch' : 'push',
  payload: { inputs: { pr_number: input.scenario === 'invalid_number' ? 'bad' : '2' } }
};
const outputs = {};
const core = { info: () => {}, setOutput: (key, value) => { outputs[key] = value; } };
const github = {
  rest: { repos: { listPullRequestsAssociatedWithCommit: () => {} },
          pulls: { get: async (args) => {
            if (args.pull_number !== 2) throw new Error('Wrong PR requested');
            return { data: pr };
          } } },
  paginate: async (_method, args) => {
    if (args.commit_sha !== context.sha) throw new Error('Wrong source commit requested');
    return input.scenario === 'direct_push' ? [] : [pr];
  }
};
const AsyncFunction = Object.getPrototypeOf(async function() {}).constructor;
(async () => {
  try {
    await new AsyncFunction('context', 'github', 'core', 'require', input.script)(
      context, github, core, require
    );
    process.stdout.write(JSON.stringify({ status: outputs.sha ? 'release' : 'skip', outputs }));
  } catch (error) {
    process.stdout.write(JSON.stringify({ status: 'error', message: error.message }));
  }
})();
"""
    result = subprocess.run(
        ["node", "-e", harness],
        input=json.dumps(
            {"scenario": scenario, "directory": str(tmp_path), "script": step["with"]["script"]}
        ),
        text=True,
        capture_output=True,
        check=True,
    )
    output = json.loads(result.stdout)
    assert output["status"] == expected, output
    event_path = tmp_path / "release-pr.json"
    if expected == "release":
        assert output["outputs"]["sha"] == "merged-sha"
        assert json.loads(event_path.read_text())["pull_request"]["number"] == 2
    else:
        assert not event_path.exists()
