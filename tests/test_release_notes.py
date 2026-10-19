"""Release notes preserve literal Markdown and do not imply unexecuted checks."""

import importlib.util
import subprocess

import pytest

SPEC = importlib.util.spec_from_file_location("release_notes", "scripts/release_notes.py")
release_notes = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_notes)


@pytest.mark.parametrize(
    "version,candidate", [("0.2.0rc1", True), ("0.2.0.dev0", True), ("0.2.0", False)]
)
def test_exact_version_and_literal_markdown(tmp_path, version, candidate):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "--allow-empty",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    (tmp_path / "pyproject.toml").write_text(f'[project]\nversion = "{version}"\n')
    literal = "Use `longguard` and $(touch unwanted-file)."
    (tmp_path / "CHANGELOG.md").write_text(f"## [{version}]\n\n{literal}\n")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    evidence = {
        "commit": commit,
        "checks": {name: {"exit_code": 0} for name in ("ruff", "mypy", "pytest", "docs", "build")},
    }
    body, actual = release_notes.generate(tmp_path, f"v{version}", evidence)
    assert actual is candidate
    assert literal in body
    assert f"longguard=={version}" in body
    assert not (tmp_path / "unwanted-file").exists()
    with pytest.raises(ValueError, match="source commit"):
        release_notes.generate(tmp_path, f"v{version}", {**evidence, "commit": "wrong"})
    with pytest.raises(ValueError, match="checks"):
        release_notes.generate(tmp_path, f"v{version}", {**evidence, "checks": {}})
    with pytest.raises(ValueError, match="match package"):
        release_notes.generate(tmp_path, "v8.0.0", evidence)
