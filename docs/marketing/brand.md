# brand

A brand agency inside your coding agent. Install it from the [hub README](../../README.md#install).

## What it does

brand takes a business described in the founder's own words and leads it, one session at a time, through strategy, a brand platform, a visual identity and a UI design system to a brand book. At the end it hands over the finished brand as one directory, the **kit**: logo files, fonts, design tokens, components, the book as a page and a PDF, and instructions written for the agents and people who build with it.

The agency speaks in three roles (Strategist, Copywriter, Art Director), explains every tool before using it, shows each one filled in for Apple in 1997 to 2001 as a benchmark, proposes instead of only asking, and fixes nothing without the founder's explicit yes. Every visual choice is made between three variants on a page in the browser, each judged first by a critic that runs as a separate subagent and sees only two screenshots.

| Step | Ask for | What happens | Ends with |
|---|---|---|---|
| 0 | `brand intake` | the kickoff: the founder tells the story | The Brief |
| 1 | `brand strategy` | seven sessions: Golden Circle, Lean Canvas, ICP and Jobs-to-be-Done, Positioning, Brand Wheel, Marketing Mix, Messaging | Strategy on one page |
| 2 | `brand brand-platform` | Archetype, Voice, Name (for an unnamed brand), Mood with a moodboard | Platform on one page, the Creative Brief |
| 3 | `brand identity` | Logo, Color, Typography, Motto, then the brand's surfaces | Identity on one page |
| 4 | `brand design-system` | Interface, then tokens, components and three example pages | the System on one page |
| 5 | `brand brand-book` | the book is built from everything approved | the brand book and the kit |

`brand` on its own (or `brand status`) checks the pipeline, reports each step, flags steps made stale by a later change, and ends with one question: "Continue with <the next step>? Answer "yes" to start it now." A yes starts that step right there. Without a brand yet, the next step is the kickoff. Each step runs in its own session; the files are the only memory between them.

How you type it depends on the agent:

| Agent | Interactive | Headless |
|---|---|---|
| Claude Code | `/brand intake` | `claude -p "/brand intake <brand dir> --headless" --allowedTools Read Write Edit Glob Grep 'Bash(python3:*)' 'Bash(mkdir:*)'` (see [Claude Code](#claude-code)) |
| Codex | `$brand intake` | `codex exec -s workspace-write '$brand intake ./brand --headless'` |
| Others | ask for "brand intake", or just "let's start a brand" | not verified yet |

## When to reach for it

- You are starting a product, a company or a personal brand and want strategy, a name, a voice and an identity that hold together, not a logo on its own.
- You want a design system your coding agents can build with: W3C design tokens, components, and an `AGENTS.md` that tells them how to use the brand.
- You run a studio and brand many customers: brand keeps every order's working state in the studio and delivers only the kit.

It is not for a quick logo, and not for a brand that already exists and only needs a page or two.

## Requirements

- Python 3. The scripts use the standard library only; nothing to install.
- Chrome, Chromium, Edge or Brave, for screenshots, the critic and the PDF of the book. It is looked for in the usual application paths, on the `PATH`, and in `$BRAND_CHROME`. The identity and design-system steps stop without one.
- Network access, for Google Fonts (the typeface pair is downloaded into the brand), the domain check of name candidates, and paid images when they are chosen.
- An agent that can start a subagent with a fresh context window, for the critic. The identity and design-system steps stop without one.
- Optional: a [fal.ai](https://fal.ai) key, for generated images in the moodboard and logo sketches. See [Generated images](#generated-images).
- Optional: Figma tools connected in the session, for exporting the design system to a Figma file.

### Claude Code

brand reads its own files and runs its scripts with `python3`, so Claude Code asks for permission the first times it does. To stop being asked, allow them in your settings (`.claude/settings.json` of the project, or your user settings):

```json
{ "permissions": { "allow": ["Read", "Bash(python3:*)", "Bash(mkdir:*)"] } }
```

A headless run (`claude -p`) cannot ask, so it needs the same tools on the command line, plus writing the brand directory:

```bash
claude -p "/brand intake <brand dir> --headless" --allowedTools Read Write Edit Glob Grep "Bash(python3:*)" "Bash(mkdir:*)"
```

Without them a headless run stops before it reads the step. `claude plugin list` shows where the plugin `marketing` is installed (`Read from`), and brand is its `brand/` folder; for an install from GitHub the path holds the version, so it changes with every release.

### Codex

brand runs in Codex's default `workspace-write` sandbox; it never needs full access. It needs two things there:

1. **Network access.** In `~/.codex/config.toml`:
   ```toml
   [sandbox_workspace_write]
   network_access = true
   ```
2. **chrome-headless-shell.** The sandbox does not let Google Chrome start (it denies Chrome the process rendezvous it needs). `chrome-headless-shell` starts there when it runs as one process, and brand falls back to that by itself for screenshots and the PDF of the book:
   ```bash
   npx @puppeteer/browsers install chrome-headless-shell@stable   # prints the path of the binary
   export BRAND_CHROME="<that path>"
   ```

The brand directory has to be inside the workspace. In a studio, run Codex from the studio's root, so `orders/` is inside it.

Verified on 2026-11-25 with Codex 0.167.1: install, a headless intake, screenshots, the critic as a separate subagent, and the PDF of a real brand book. The other steps were not run end to end inside the sandbox.

## Quick start: a brand for your own project

In the project's repository, ask for `brand` and answer "yes" to the kickoff, or ask for `brand intake` directly.

brand creates `brand/` at the root of the project and keeps all its working state there: `pipeline.yaml`, one directory per step, the rendered plates and choice pages, and `brand/map.html`, the brand map, which gains a plate after every session. Go on with the step each session names at its end, or ask for `brand` and say yes to what it offers.

When the brand book is approved, the kit is exported to `brand/out/`. Give that directory to any designer, developer or agent; agents start with `AGENTS.md`.

## Running as a studio

brand can also be run by a studio for many customers. The working state of every order stays with the studio; the customer's repository receives only the kit.

```
studio/
  .env                  FAL_KEY=<key>, shared by every order; git-ignored
  orders/<order>/       the brand directory of one order
```

Every step takes the brand directory as its first argument: `brand intake ~/studio/orders/acme`.

Deliver the kit into the customer's repository, and check later whether that copy is still current (`GW` is the skill root):

```
python3 "$GW/scripts/export_kit.py" ~/studio/orders/acme --deliver ~/code/acme/docs/brand
python3 "$GW/scripts/export_kit.py" ~/studio/orders/acme --check --deliver ~/code/acme/docs/brand
```

The delivered kit carries nothing of the working state: no steps, no review pages, no `pipeline.yaml`, no key, no path back into the studio.

## Running without a person: the owner's answers as files

Every point at which a step waits for the owner (a question of the interview, a choice of candidates or variants, the approval of a plate, a tool switch, a paid batch, the closing of a step) is written as a question to `<brand>/owner/questions/<id>.json`: what is asked, the options and what each one means, the recommendation, and the page to look at. The step continues only from an answer in `<brand>/owner/answers/<id>.json`.

- **Interactive** (the default): the owner answers in the chat, and the skill records the answer.
- **Headless**: add `--headless`. Another program or agent writes the answers; the run stops at the first question without one and prints `WAITING <id>: <question>`. Run the same step again once it is answered.

A run never makes up an answer. An orchestrator drives an order like this (`GW` is the skill root, `O` the order), here with Claude Code:

```
mkdir -p $O
python3 "$GW/scripts/owner.py" answer $O 00-intake.kickoff.story --text "..." --by orchestrator   # answers known ahead
claude -p "/brand intake $O --headless" --allowedTools Read Write Edit Glob Grep "Bash(python3:*)" "Bash(mkdir:*)"

python3 "$GW/scripts/owner.py" pending $O        # WAITING lines, exit code 3 while something waits
python3 "$GW/scripts/owner.py" answer $O <id> (--choice <option | yes | no> | --text "...") [--comment "..."] --by orchestrator
claude -p "/brand <step> $O --headless" --allowedTools Read Write Edit Glob Grep "Bash(python3:*)" "Bash(mkdir:*)"     # continues from the first unanswered question
```

With Codex, run `codex exec -s workspace-write '$brand <step> <order> --headless'` from the studio's root instead.

A step is finished when its status in `$O/pipeline.yaml` is `approved`. `brand status $O --headless` asks nothing and ends with `NEXT brand <step> $O --headless`, the step to run next. The ids of intake are fixed (`00-intake.kickoff.story`, `.profile`, `.market-language`, `.name`, `00-intake.brief.approve-01`, `00-intake.step.approve-01`), so a whole kickoff can be answered ahead. The formats are in [`reference/contract.md`](../../skills/marketing/brand/reference/contract.md), section 9.

## Generated images

Nothing about images is asked at install or at the kickoff. In the brand-platform step's Mood session the owner chooses how images are made: `fal` (generated with fal.ai, within a budget the owner names), `svg-only` or `none`. Only when `fal` is chosen:

- **In a project**, brand creates `brand/.env` (and `brand/.gitignore` with `.env` in it). The file explains itself:
  ```
  # brand: paid image generation with fal.ai
  # 1. Create a key at https://fal.ai/dashboard/keys
  # 2. Replace the placeholder below with it, save this file. Never commit it.
  # 3. Ask your agent to check the key: it never sees or prints it.
  FAL_KEY=put-fal-key-here
  ```
- **In a studio**, the key is the studio's, in `<studio>/.env` in the same format, and nothing is created per order.

The key is read from the studio's `.env`, else `brand/.env`, else the environment variable `FAL_KEY`. Files come first because some agents do not pass environment variables into their sandbox. `--check-key` says where the key was found, or where to put it; it never prints the key, and fal checks the key itself at the first generation. The key is never asked for in the chat, never committed and never copied into a kit. Before every paid batch the agent states the count and the price and waits for a yes.

## What the kit holds

| Path | What it is |
|---|---|
| `AGENTS.md`, `README.md` | how to use the kit: read order, every file, the files each task needs, the rules |
| `brand.md`, `brand.json` | the whole brand as text, and every line of every plate as data |
| `book/` | the brand book: one self-contained page and, with Chrome, a PDF |
| `logo/` | `full.svg`, `mark.svg`, `mono.svg`, `dark.svg` |
| `fonts/` | the font files, `fonts.css` and their licenses |
| `tokens/` | `tokens.json` (W3C design tokens, with dark and narrow groups) and `tokens.css` |
| `system/` | `components.md`, `system.css`, every component drawn, a landing page, sign-in and sign-up |
| `surfaces/` | the brand on its surfaces (site hero, social image, avatar, signature) |
| `manifest.json` | the versions it was built from and every file with its hash |

## Common questions

**Which agents does it work on?** Verified on Claude Code and Codex. Copilot, VS Code, Gemini CLI and skills.sh agents should work the same way, since nothing in the skill depends on one agent, but nobody has run them yet.

**My agent cannot start subagents. Can I still use it?** Intake, strategy, brand platform and the brand book, yes. The identity and design-system steps stop at the critic and say why: brand never judges its own variants.

**Do I need a fal key?** No. Without one, everything is drawn as SVG.

**Can I run it in another language?** Yes. The conversation is held in the founder's language; the fixed texts are translated sentence for sentence. Brand copy is in the market language; the plates are in English.

## It's working if

- After `brand intake`, `brand/pipeline.yaml` and `brand/00-intake/brief.md` exist, and the brief says your idea back in five lines.
- Every session ends with a plate in the brand map and names the next step.
- Every page of variants shows each variant's critic remarks.
- `brand status` reports no errors, and after the brand book, `brand/out/AGENTS.md` exists.

## Known limitations

- Only the `personal-brand` profile exists. The other four (`b2b-saas`, `consumer-app`, `local-business`, `physical-product`) are accepted at intake, but a step that needs the profile stops and says so.
- Everything fixed in the skill and every plate is in English. The conversation is held in the founder's language by translating the fixed texts sentence for sentence; brand copy (the name, the motto, the voice examples) is in the market language.
- Headless Chrome will not lay out a page narrower than about 500 px, so a "390 px" screenshot is a 500 px layout, framed or cropped. The critic never sees a true phone layout.
- The character of an interface lives only in the design tokens; the components and the example pages are the same for every brand. A component a profile adds gets a description but no drawing.
- `system.css` has optional brand extras of the buttons (a sheen, facet shadows) whose tokens are not yet described in `reference/design-tokens.md` or checked.
- Headless runs are proven for intake and the start of the strategy. The question ids of the later steps follow the pattern of the contract but have not been run headless end to end.
- The pages of the skill itself (plates, brand map, choice pages) share one plain house style.

## For maintainers

| Path | What it holds |
|---|---|
| `skills/marketing/brand/SKILL.md` | the router and the requirements |
| `skills/marketing/brand/steps/` | one file per step, with each session's fixed texts and benchmarks |
| `skills/marketing/brand/critic.md` | the critic's instructions, given to a fresh subagent |
| `skills/marketing/brand/scripts/` | the check of the contract, the renderers, the kit, `owner.py`; standard library only |
| `skills/marketing/brand/templates/`, `profiles/`, `examples/` | page templates and the design system base, per-profile parts, examples of the page formats |
| `skills/marketing/brand/reference/` | the step protocol, the [contract](../../skills/marketing/brand/reference/contract.md) (every file and rule, enforced by `check_contract.py`) and the page formats |
| `tests/marketing/brand/` | the test suite and a complete, valid brand directory as a fixture |

```
python3 -m unittest discover -s tests
npm run check-agnostic
```

`reference/contract.md` is the source of truth: change it first, then the scripts and steps, then the tests.

The icons in `templates/system/icons/` are from Lucide, under the ISC license.
