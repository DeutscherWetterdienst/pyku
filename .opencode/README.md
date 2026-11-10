# Opencode configuration

- `opencode.jsonc` – core configuration.
- `skills/DOCSTRINGS.md` – doc‑string style guide used by the `docstrings`
  skill.
- `skills/TESTING.md` – test execution with pytest in the active environment.
- `skills/release/SKILL.md` – dual-source GitLab/GitHub maintenance and release
  workflow; keep it synchronized with `doc/contribute/maintainers.rst`.
- Graphify data lives in `../graphify-out`; the agent can query it
  automatically.

Run `opencode debug config` to inspect the resolved configuration and
`opencode debug skill` to list the available skills.
