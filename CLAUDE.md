This repo is a hub of skills and plugins: `github.com/illiazakirov/skills`. Each product is promoted on its own, and every one is installed from here.

## Layout

Skills are organized into bucket folders under `skills/`, one per field:

- `marketing/`: brand, positioning, identity (promoted)
- `in-progress/`: beta, public on purpose, feedback wanted, not shipped in any plugin (create it with its first skill)
- `misc/`: kept around but rarely used, not promoted (create it with its first skill)
- `deprecated/`: no longer used (create it with its first skill)

A new field gets a new bucket. A promoted bucket is one listed in the top-level `README.md`.

## Invariants

Every skill in a promoted bucket has:

- a reference in the top-level `README.md`, linking its name to its `SKILL.md`, with a one-paragraph pitch and its single-skill skills.sh line;
- a line in its bucket's `README.md`, grouped into **User-invoked** and **Model-invoked**;
- a human-facing docs page at `docs/<bucket>/<skill-name>.md` with the sections **What it does**, **When to reach for it**, **Common questions** and **It's working if**;
- a place in its bucket's plugin. A promoted bucket is one plugin, named after the bucket, so its skills show up as `<bucket>:<skill>` (`marketing:brand`). The bucket folder holds the plugin's `.claude-plugin/plugin.json`, which lists every skill of the bucket in `skills`, and a private `package.json` whose version is the source of truth (`npm run version` copies it into `plugin.json`). The bucket has an entry in `.claude-plugin/marketplace.json` and is listed in `workspaces` in the root `package.json`.

Skills in `in-progress/`, `misc/` and `deprecated/` appear in none of these.

Install commands are copied verbatim from [.agents/install-block.md](./.agents/install-block.md). Run `claude plugin validate . --strict` after touching a manifest. There is one plugin per promoted bucket, never one per skill and never one for the whole repo.

## Every skill works with any agent and any model

Read [.agents/agnostic.md](./.agents/agnostic.md) before writing or changing a skill. `npm run check-agnostic` enforces the mechanical part, and CI runs it. In short: paths relative to the skill's own folder, no harness variables, tool names, agent types or slash syntax, subagents started with a fresh context window from a prompt file inside the skill.

Every `SKILL.md` is either user-invoked or model-invoked; see [.agents/invocation.md](./.agents/invocation.md). Every skill carries `agents/openai.yaml` beside its `SKILL.md`, for the Codex picker.

## Releases

Changesets, with npm workspaces: every plugin (bucket) folder is a package. Add a changeset (`npx changeset`) to a change a user would notice. The Release workflow opens the "chore: version skills" PR; merging it releases.

## Local use

`scripts/link-skills.sh` links every skill outside `deprecated/` and `misc/` into `~/.claude/skills` and `~/.agents/skills`. Re-run it after adding, removing or renaming a skill. Do not run it while a plugin of this repo is installed, or every linked skill appears twice.

## Working documents stay local

Specs, plans, design histories, decision records and notes on how this repo was built are working documents. They live in the local checkout only and never go into git, not even for a single commit:

- `docs/superpowers/`: specs and plans;
- `docs/<bucket>/<skill>/`: a skill's spec and design history (its public page is `docs/<bucket>/<skill>.md`);
- `.agents/adr/`: decision records.

`.gitignore` covers these folders. A new working document goes into one of them, or the folder is added to both `.gitignore` and `scripts/check-local.sh`.

Nothing in git names a place on anyone's machine: no home directories, no paths to the owner's other projects, no temporary or scratch directories, no memory files, and no links into the ignored folders. A tracked file that needs a working document says what it holds, not where it lives. Example paths in docs are generic (`~/studio/orders/acme`).

`npm run check-local` enforces both, and CI runs it. Run it before every commit.

## Writing

No em-dashes in this repo's prose; rewrite the sentence instead. Name a person you do not know as "the owner" or "they".

## brand

brand's own rules are its contract, `skills/marketing/brand/reference/contract.md`, and the maintainer section of [docs/marketing/brand.md](./docs/marketing/brand.md#for-maintainers). Its spec and design history are local working documents in `docs/marketing/brand/`; the tests that compare the skill with them are skipped where they are missing. Its tests run with `python3 -m unittest discover -s tests`; `reference/contract.md` changes first, then the scripts and steps, then the tests.
