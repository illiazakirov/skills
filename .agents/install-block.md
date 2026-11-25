# The canonical install block

One install story, one wording. `README.md` and every page under `docs/` say **this** and nothing else. Change it here first, then propagate.

## Routes

Lead with installs that update themselves. Fall back to copied files, labelled "manual updates", only for agents that have no such install. Call a route managed only if it updates without the user running a command.

Every managed route installs from this repo's own marketplace, `illiazakirov` (`.claude-plugin/marketplace.json`), which lists one plugin per promoted bucket, named after the bucket, each with its `plugin.json` in the bucket folder (`skills/marketing/` is the plugin `marketing`, which holds brand). Those routes reinstall only when that plugin's `version` changes. The Release workflow runs `npm run version`, which copies each plugin's `package.json` version into its `plugin.json`, so users get a release when the "chore: version skills" PR merges.

| Agent | Route | Updates itself? | Verified |
| --- | --- | --- | --- |
| Claude Code | `@illiazakirov` marketplace | Yes, when the plugin version changes | 2026-11-25, Claude Code 2.1.332; since the move to bucket plugins only the install and the skill inventory |
| Codex | `@illiazakirov` marketplace | Yes, at startup | 2026-11-25, Codex 0.167.1, as the plugin `brand`; not rerun as `marketing` |
| Copilot CLI | `@illiazakirov` marketplace | Yes, after a one-time `autoUpdate: true` | Nobody has run this yet |
| VS Code | Chat: Install Plugin From Source | Yes, daily | Nobody has run this yet |
| Gemini CLI | `gemini skills install` (copies a bucket) | No | Nobody has run this yet |
| Everyone else | skills.sh (copies) | No. Run `npx skills@latest update` | Nobody has run this yet |

Verified means: installed from a local path to this marketplace, `brand intake <dir> --headless` stopped at its first question with `WAITING`, and the critic ran as a separate subagent. A route nobody has run stays labelled so until someone does.

## Claude Code

<canonical-block name="claude-code">

```bash
claude plugin marketplace add illiazakirov/skills
claude plugin install marketing@illiazakirov
```

Then type `/brand intake` (or `/marketing:brand intake` where another skill is named `brand`). Headless: `claude -p "/brand intake <brand dir> --headless" --allowedTools Read Write Edit Glob Grep 'Bash(python3:*)' 'Bash(mkdir:*)'`; a headless run cannot ask for permission, so the tools are allowed on the command line.

</canonical-block>

## Codex

Codex runs brand in its default `workspace-write` sandbox. Two things are needed, and full access is not one of them:

- network access inside the sandbox, for Google Fonts, the domain check and fal;
- `chrome-headless-shell` instead of Google Chrome, which the sandbox does not let start. brand's screenshot script falls back to running it in one process.

The brand directory has to be inside the workspace: in a studio, run Codex from the studio's root.

<canonical-block name="codex">

```bash
codex plugin marketplace add illiazakirov/skills
codex plugin add marketing@illiazakirov
npx @puppeteer/browsers install chrome-headless-shell@stable   # prints the path of the binary
export BRAND_CHROME="<that path>"
```

In `~/.codex/config.toml`:

```toml
[sandbox_workspace_write]
network_access = true
```

Then ask for `$brand intake`. Headless: `codex exec -s workspace-write '$brand intake ./brand --headless'`.

</canonical-block>

## GitHub Copilot (CLI and VS Code)

<canonical-block name="copilot">

```bash
copilot plugin marketplace add illiazakirov/skills
copilot plugin install marketing@illiazakirov
```

Then, once, add to `~/.copilot/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "illiazakirov": { "source": { "source": "github", "repo": "illiazakirov/skills" }, "autoUpdate": true }
  }
}
```

In VS Code, run **Chat: Install Plugin From Source** and enter `https://github.com/illiazakirov/skills`. It updates daily.

</canonical-block>

## Gemini CLI

Gemini doesn't read `.claude-plugin`, and `--path` takes one bucket. One install per bucket gives exactly that bucket's skills.

<canonical-block name="gemini">

```bash
gemini skills install https://github.com/illiazakirov/skills.git --path skills/marketing
```

Re-run to update.

</canonical-block>

## Every other agent, or editable files (skills.sh)

<canonical-block name="other-agents">

```bash
npx skills@latest add illiazakirov/skills -a <agent>  # cursor, opencode, windsurf, amp, ...; omit -a to choose
```

To update, run `npx skills@latest update`, and re-run `add` to pick up new skills.

</canonical-block>

Use the single-skill form wherever one skill is named on its own:

<canonical-block name="skills-sh-one-skill">

```bash
npx skills@latest add illiazakirov/skills --skill=<name>
```

</canonical-block>

`skills@latest` is the pinned spelling everywhere.

## The two kinds of route are exclusive

A plugin is a managed, read-only bundle you subscribe to. skills.sh and Gemini write files you own and edit. Installing both leaves the user with every skill twice: always say "pick one per agent".
