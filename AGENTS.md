# pyku Agent Notes


## Design Philosophy

### Data Types & Interfaces

* **Grid Data:** Functions must strictly accept and return `xarray.Dataset`. Do
  NOT use `xarray.DataArray` in function signatures to preserve critical
  metadata (e.g., `crs` grid mapping variables).
* **Vector Data:** Functions handling point, line, or polygon geometries must
  strictly accept and return `geopandas.GeoDataFrame`.

### Functional Design

* **Stateless & Modular:** Prefer pure, independent functions over custom
  classes or object-oriented abstractions unless managing state is explicitly
  required.

* **Path Type Safety:** Always validate or assert that variables are not `None` before passing them to file path parameters (`StrPath`). Use explicit type guards, default fallback values, or assertions (e.g., `assert path_var is not None`).

### Core Function Simplicity

* Make the smallest change that satisfies the stated requirements and follow
  existing design patterns.
* Keep tests thorough, but avoid speculative edge-case handling, defensive
  branches, helpers, or abstractions that are not justified by a requirement
  or a failing test.
* Add implementation complexity when a requirement or failing test justifies
  it.
* Briefly explain why each new branch or abstraction is needed.

### Reuse Scientific Libraries

* Before implementing scientific or geospatial functionality, check whether
  the project already depends on a library that provides it. Prefer Pint and
  pint-xarray for unit-aware quantities, cf-xarray for CF metadata and axis
  selection, MetPy for meteorological calculations, and xclim for climate
  indicators and related climate operations when they fit the use case.
* Prefer composing established library APIs over duplicating conversions,
  metadata interpretation, algorithms, or validation. Preserve pyku's public
  interfaces and metadata requirements when integrating them.
* Check `pyproject.toml` before relying on a library. Do not assume a
  transitive or optional dependency is always available; justify and declare
  any new direct dependency rather than introducing it implicitly.

### Visualisation Metrics

* Evaluation maps are provided by `pyku.visualisation.metric_map`.
* Supported metrics are `mae`, `bias`, `mse`, `rmse`, and `pcc`.
* Use `groupby="time.month"` or `groupby="time.season"` for grouped
  metric maps. Grouped maps label each panel with their month or season.
* Do not add metric-specific wrapper functions or restore
  `seasonal_mean_bias_map`; extend `metric_map` instead.

### Code & Docstring Formatting Rules

- Format all function signatures with one parameter per line, including a
  trailing comma on the final parameter.
- **ASCII Space Enforcement:** NEVER use non-breaking space characters (`\xa0` /
  `U+00A0`) in code, docstrings, or Sphinx directives. Always use standard ASCII
  spaces (`U+0020`).
- **Sphinx IPython Directives:** When writing `.. ipython::` blocks:
  - Ensure `In [X]:` and continuation prompts (`...:`) use standard ASCII space
    padding.
  - Do not introduce hidden unicode whitespace characters when copying or
    indenting multi-line execution blocks.

## Python Type Hints

All Python functions and methods must include explicit type hints for both
parameters and return values.

* **Existing Functions:** Update untyped functions with accurate type hints when
  modifying or refactoring them.
* **New Functions:** Always include complete type hints from the start.
* **Complex Types:** Use `typing` primitives (e.g., `Union`, `Optional`,
  `Callable`) or standard collections (`list[str]`, `dict[str, Any]`) as
  appropriate.
* **Return Types:** Always specify explicit return types, including `-> None`
  for functions without a return statement.

## Testing

Run tests in the active Python environment provided by the host and OpenCode
setup. Do not reset or replace it before running tests.

The canonical test command uses pytest for clean, concise output:

```bash
pytest testing/ -v --tb=short
```

This collects all test files matching `*_test.py` in the `testing/` directory.

**Why pytest?** It provides:
- Clean progress indicators with dots
- ✓ markers for passed tests
- Concise summary (e.g., `46 passed, 7 warnings, 45 subtests passed`)
- Short tracebacks for easy debugging

For detailed testing guidelines and additional commands, see `./.opencode/skills/TESTING.md`.

## Tooling and verification

- Keep all lines at 80 characters or fewer; this is the repository default.
- As the final coding check, run `ruff check` and `flake8` on the Python files
  changed during the task. These checks can run after implementation is complete;
  they do not need to run after every intermediate edit.
- Do not use autofix options. Correct lint findings only when they are in code
  written or changed by the agent. Leave pre-existing findings, including those
  elsewhere in a changed file, untouched and report them separately.
- If `flake8` is unavailable, report that instead of installing it.

## Python Docstrings

Before writing, updating, or reviewing Python docstrings:
1. Read `./skills/DOCSTRINGS.md` for exact formatting rules.
2. Apply the guidelines strictly to all docstrings in the targeted scope.

## RST Documentation

Before writing, updating, or reviewing any `.rst` file under `doc/`:
1. Read `./.opencode/skills/RST-FORMATTER.md` for the exact formatting
   rules.
2. Apply the guidelines strictly to all reST content in the targeted scope
   (heading hierarchy and underline length matching).

## Deprecated modules

**DO NOT modify `pyku/analyse.py`** - this module is deprecated and maintained
solely for backward compatibility. It contains deprecated wrapper functions
that redirect to newer implementations in other modules.

If you need to make changes to `analyse.py`, **inform the user first** and wait
for explicit approval. Do not modify this file unless the user explicitly
agrees to the changes.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes,
community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or
instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when
  graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for
  relationships and `graphify explain "<concept>"` for focused concepts.
  These return a scoped subgraph, usually much smaller than
  GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental
  updates; dirty graph files are not a reason to skip graphify. Only
  skip graphify if the task is about stale or incorrect graph output,
  or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation
  instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review
  or when query/path/explain do not surface enough context.
- After any code update, run `graphify update .` to keep the graph current
  (AST-only, no API cost).

## Documentation build

All documentation tools (Sphinx, nbsphinx, etc.) are already installed in the current environment; no extra installation is required.

Build the complete documentation by omitting `include_patterns`:

```bash
cd doc
sphinx-build -j 10 -T ./ _build/html
```

Use `include_patterns` only when intentionally building a selected part of
the documentation. A partial build is useful for focused iteration, but it
does not validate the complete documentation tree:

```bash
# Build selected parts of the documentation
sphinx-build -j 10 -T -D include_patterns=index.rst,api.rst,visualisation/* ./ _build/html

# Serve the built docs
python -m http.server --directory _build/html/ --bind=$HOSTNAME
```

## Merge request issue tracking

- Before opening or updating a GitLab MR, search GitLab issues/work items for
  candidates that match the change and check their scope and status.
- Add `Closes #<iid>` to the MR description only when the MR fully resolves
  that open issue; GitLab closes it when the MR is merged. Use `Related to
  #<iid>` for partial work or follow-up issues, not a closing keyword.
- If the match or completion is unclear, do not guess. Ask the user which issue
  to link. If no matching issue is found, say so and ask whether they want one
  linked.
- When discussing a merge, remind the user which issues will close
  automatically. Do not close issues manually.

## Release workflow

- GitLab is the canonical repository for changes, `main`, releases, and
  version tags. Merge MRs on GitLab; manually synchronize the merged `main`
  commit to GitHub after checking ancestry and remote refs.
- GitHub PRs may run checks, but must not be merged on GitHub. Import their
  head branches into GitLab and review them through MRs targeting GitLab
  `main`.
- Create release tags on GitLab first, then manually push only that tag to
  GitHub. Do not push all tags, overwrite divergent refs, or force-push. Use
  `.opencode/skills/sync/SKILL.md` for the safe procedure.
- The `master` branch is deprecated. Do not merge changes into it or use it for
  releases.
- Follow `doc/contribute/maintainers.rst` for the human contribution and
  release runbook. Use `.opencode/skills/gitlab-contribution/SKILL.md` when
  asked to submit changes to GitLab and `.opencode/skills/release/SKILL.md`
  for releases. Keep the runbook and skills synchronized when the workflow
  changes.
- Release jobs publish to the pyku project's package registry and create the
  GitLab Release. GitHub Actions and Pages run after the relevant refs are
  manually synchronized to GitHub.
