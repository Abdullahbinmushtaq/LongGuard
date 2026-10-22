# Contributing to LongGuard

Thank you for your interest in contributing to **LongGuard**! We welcome bug reports, feature requests, documentation improvements, and pull requests.

LongGuard is an open-source project by [EnDevSols](https://github.com/ENDEVSOLS).

---

## Development Setup

LongGuard uses [`uv`](https://github.com/astral-sh/uv) for fast and deterministic Python environment management.

### 1. Clone the repository

```bash
git clone https://github.com/ENDEVSOLS/LongGuard.git
cd LongGuard
```

### 2. Install dependencies

```bash
# Install package with all dev dependencies
uv sync --extra dev
```

### 3. Run Tests

```bash
# Run all unit tests
uv run pytest tests/ -v

# Run with test coverage
uv run pytest tests/ --cov=longguard --cov-report=term-missing
```

### 4. Code Quality Checks

We enforce formatting and linting with **Ruff** and strict static typing with **MyPy**:

```bash
# Run linter
uv run ruff check src/ tests/

# Run type checker
uv run mypy src/
```

Ensure all tests, lint checks, and type checks pass before submitting a Pull Request.

---

## Pull Request Guidelines

1. **Focus on solving real agent failure modes**: If adding a new detector, provide synthetic or real-world traces in `tests/` demonstrating both positive detection and non-interference on legitimate tasks.
2. **Keep overhead minimal**: Loop detection runs synchronously on each agent step; algorithms should execute in sub-millisecond time.
3. **Preserve framework neutrality**: Core detection mechanisms (`src/longguard/core/`) must remain independent of specific agent frameworks (LangGraph, LangChain, etc.). Framework integrations belong in `src/longguard/integrations/`.
4. **Follow Semantic Versioning**: Major for breaking changes, minor for new detectors/adapters, patch for bug fixes.

---

## Automatic GitHub releases

Every PR merged into `main` automatically publishes a GitHub prerelease after
the release checks pass. Closing a PR without merging does not release.
For example, PR #42 with source version `0.2.0.dev0` releases `v0.2.0.dev42`.
The PR number makes versions unique even when several PRs merge together.
Development version ordering follows PR numbers, rather than merge times.

The release tag points to a commit whose parent is the PR's merged commit.
That commit updates `pyproject.toml`, `__version__`, `uv.lock`, and the changelog.
It is pushed only as a tag; no bot commits or branch protection bypass are
needed on `main`. The branch keeps its development version. Automatic releases
require an `X.Y.Z.devN` source version; stable releases remain a separate decision.

The existing release checks must pass before the GitHub release is published.
Wheel, source distribution, and verification evidence are attached. This does
not publish to PyPI. Tag-triggered and manually dispatched releases still create
drafts. Failed automatic runs can be rerun; the same PR reuses its existing tag.

The workflows use the repository's `GITHUB_TOKEN` with `contents: write`;
repository policies must permit that permission and creation of version tags.
The reusable release job runs explicitly because tags pushed with `GITHUB_TOKEN`
do not start another tag workflow. Enable GitHub Actions and merge these workflow
files into the default branch to activate the automation.

## License

By contributing to LongGuard, you agree that your contributions will be licensed under the [MIT License](LICENSE).
