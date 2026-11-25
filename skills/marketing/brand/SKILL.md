---
name: brand
description: A brand agency that leads a project from the founder's own story through strategy, a brand platform, a visual identity and a UI design system to a brand book, and hands over the finished brand as one kit with instructions for agents. Use when the owner wants to brand a project or a product, name it, find its positioning, voice, logo, colors, type or design tokens, continue an existing brand, check where a brand stands, or when a studio starts or runs an order.
---

# brand

A brand agency in six steps. Each step runs in its own session; the files in the brand directory are the only memory between them.

## The skill root

The skill root is the folder that holds this `SKILL.md`. Every path in this skill (`steps/`, `reference/`, `scripts/`, `templates/`, `profiles/`, `critic.md`) is relative to it. Resolve it once to an absolute path. In shell commands, set it as `GW` and keep it quoted, because the path may contain spaces:

```
GW="<absolute path of the skill root>"
python3 "$GW/scripts/check_contract.py" check brand
```

## What to run

The request names a step and, optionally, the brand directory and `--headless`: `brand <step> [<brand directory>] [--headless]`. Read the step's file and follow it.

| Step | File | What it does | Ends with |
|---|---|---|---|
| `intake` | `steps/intake.md` | the kickoff: the founder tells the story | The Brief |
| `strategy` | `steps/strategy.md` | seven sessions: Golden Circle, Lean Canvas, ICP and Jobs-to-be-Done, Positioning, Brand Wheel, Marketing Mix, Messaging | Strategy on one page |
| `brand-platform` | `steps/brand-platform.md` | Archetype, Voice, Name (for an unnamed brand), Mood with a moodboard | Platform on one page, the Creative Brief |
| `identity` | `steps/identity.md` | Logo, Color, Typography, Motto, then the brand's surfaces | Identity on one page |
| `design-system` | `steps/design-system.md` | Interface, then tokens, components and three example pages | the System on one page |
| `brand-book` | `steps/brand-book.md` | the book, built from everything approved | the brand book and the kit |
| `status` | `steps/status.md` | checks the pipeline and offers the next step | a report and one question |

- An argument that is not a step in the table, a path or `--headless` (a typo such as `identiy`): name the valid steps and stop. Do not guess which one was meant.
- No step named, or a request in plain words ("where is my brand at", "what's next"): run `status`, also when there is no pipeline yet. It ends by offering the next step, which the owner starts with a yes.
- A plain request to begin ("let's start a brand") with no `<brand directory>/pipeline.yaml`: run `intake`.
- The brand directory is `brand/` in the current directory unless a path is given, for example a studio order `~/studio/orders/<order>`.
- `--headless`: no person answers in the chat; see `reference/step-protocol.md`.

## Requirements

- Python 3. The scripts use the standard library only.
- Chrome, Chromium, Edge or Brave, found in the usual application paths, on the `PATH`, or in `BRAND_CHROME`. The identity and design-system steps stop without one.
- Network access: Google Fonts, the domain check of name candidates, and paid image generation when it is chosen.
- An agent that can start a subagent with a fresh context window. Every visual variant is judged first by an independent critic (`critic.md`); the identity and design-system steps stop when no subagent can be started, and never judge their own variants instead.
- Optional: a fal.ai key, asked for only when paid image generation is chosen in the brand-platform step. That step says where it goes.
- Optional: Figma tools connected in the session, for exporting the design system to a Figma file.
