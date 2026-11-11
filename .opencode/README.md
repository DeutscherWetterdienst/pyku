# Opencode configuration

- `opencode.jsonc` – core configuration.
- `skills/DOCSTRINGS.md` – doc‑string style guide used by the `docstrings`
  skill.
- `skills/TESTING.md` – test execution with pytest in the active environment.
- `skills/gitlab-contribution/SKILL.md` – submit pyku changes through GitLab
  merge requests, including importing GitHub pull requests.
- `skills/release/SKILL.md` – canonical GitLab release workflow and manual
  GitHub synchronization; keep it synchronized with
  `doc/contribute/maintainers.rst`.
- `skills/sync/SKILL.md` – guarded GitLab-to-GitHub branch and tag
  synchronization.
- Graphify data lives in `../graphify-out`; the agent can query it
  automatically.

Run `opencode debug config` to inspect the resolved configuration and
`opencode debug skill` to list the available skills.
