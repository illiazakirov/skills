# Skills

My agent skills and plugins, for any coding agent and any model.

Each one is a set of plain instructions and, where it needs them, standard-library scripts. None of them depends on one harness: they run the same in Claude Code, Codex, GitHub Copilot, Gemini CLI, Cursor and anything else that reads the Agent Skills format. Every skill here is something I use on real work.

## Install

A plugin updates itself. skills.sh and Gemini copy editable files into your setup, and you update them by hand. Pick one per agent, because installing both gives you every skill twice. A plugin holds one field: `marketing@illiazakirov` brings brand, and its skills show up as `marketing:<skill>`.

<details>
<summary><strong>Claude Code</strong></summary>

```bash
claude plugin marketplace add illiazakirov/skills
claude plugin install marketing@illiazakirov
```

Updates itself when a new version is released.

</details>

<details>
<summary><strong>Codex</strong></summary>

```bash
codex plugin marketplace add illiazakirov/skills
codex plugin add marketing@illiazakirov
```

Updates itself at startup. brand needs network access in the sandbox and `chrome-headless-shell`; see [its page](docs/marketing/brand.md#codex).

</details>

<details>
<summary><strong>GitHub Copilot</strong> (CLI and VS Code)</summary>

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

In VS Code, run **Chat: Install Plugin From Source** and enter `https://github.com/illiazakirov/skills`. It updates daily. Nobody has run this route yet.

</details>

<details>
<summary><strong>Gemini CLI</strong> (manual updates)</summary>

```bash
gemini skills install https://github.com/illiazakirov/skills.git --path skills/marketing
```

Re-run to update. Nobody has run this route yet.

</details>

<details>
<summary><strong>Any other agent, or editable files</strong> (manual updates)</summary>

```bash
npx skills@latest add illiazakirov/skills -a <agent>  # cursor, opencode, windsurf, amp, ...; omit -a to choose
```

To update, run `npx skills@latest update`, and re-run `add` to pick up new skills. Nobody has run this route yet.

</details>

## Marketing

### brand

**[brand](./skills/marketing/brand/SKILL.md)**: a brand agency inside your coding agent. It takes a business described in the founder's own words and leads it, one session at a time, through strategy, a brand platform, a visual identity and a UI design system to a brand book. At the end it hands over the finished brand as one directory, the kit: logo files, fonts, design tokens, components, the book as a page and a PDF, and instructions written for the agents and people who build with it.

Three roles (Strategist, Copywriter, Art Director) explain every tool before using it, show it filled in for a benchmark brand, propose instead of only asking, and fix nothing without your explicit yes. Every visual choice is made between three variants in the browser, each judged first by an independent critic.

```
brand intake      the kickoff: you tell the story
brand             where the brand stands, and the next step: answer "yes" to start it
```

[Read more](./docs/marketing/brand.md). Install only this skill with skills.sh: `npx skills@latest add illiazakirov/skills --skill=brand`.

## Reference

Skills are grouped by field in bucket folders under `skills/`. Each bucket has its own `README.md`.

- **[marketing](./skills/marketing/README.md)**: brand, positioning, identity.

## License

[MIT](LICENSE).
