# brand — artifact contract v1.0

Status: agreed. Version 1.0 (2026-11-25) is the first release; its rules are those of 0.3. Version 0.3 (2026-11-24) lets the brand directory live outside the project it serves (section 1), adds the delivery of the kit to another directory and the kit format `brand-kit/2` (section 8), and the owner's answers as files (section 9). Version 0.2 (2026-11-19) removed the research and validation steps, renumbered the steps and added plates (section 5.1).

This document defines what a valid brand directory looks like. It is the source of truth for that shape. Skills write artifacts to this contract, and `scripts/check_contract.py` checks them against it.

Every name in this document (directories, files, frontmatter keys, YAML keys, headings) is literal and case-sensitive.

## 1. Layout

The **brand directory** is the directory that holds `pipeline.yaml`: the working state of one brand. It lives in one of two places, and nothing in it depends on which:

- **in the project**: `brand/` at the root of the project the brand is for. This is the default: every script and skill uses `brand` in the current directory when it is given no path.
- **in a studio**: `<studio>/orders/<order>/`, one directory per order, beside the orders of other customers. The project the brand is for holds only the delivered kit (section 8).

In this document `brand/` names the brand directory, wherever it is. It holds `pipeline.yaml` and one directory per step:

| Step directory | Skill |
|---|---|
| `00-intake` | `intake` |
| `01-strategy` | `strategy` |
| `02-brand-platform` | `brand-platform` |
| `03-identity` | `identity` |
| `04-design-system` | `design-system` |
| `05-brand-book` | `brand-book` |

The step directory name is the step's identifier everywhere: in `pipeline.yaml`, in frontmatter and on the command line.

Files in a step directory fall into three kinds:

- **Artifacts**: the files and directories listed in section 5.
- **`summary.md`**: required in every step (section 4).
- **`review/`**: rendered pages for the owner to look at: the choice pages with `review/decisions.md` (section 6), and the HTML plates of intake, strategy, the brand platform and the identity (section 5.1). Required in `02-brand-platform`, `03-identity` and `04-design-system`; allowed in any other step.

A step must not add a file or directory at the top level of its step directory that is not listed here. Files whose name starts with a dot are ignored.

`brand/map.html` is the brand map: one page with every finished plate, rendered by `scripts/render_plates.py`. It is generated, never edited by hand, not checked, and not part of any step version.

`brand/out/` is the kit: the product of the whole pipeline, exported by `scripts/export_kit.py` once the brand book is approved (section 8). It is generated, never edited by hand, not part of any step version, and not checked by `check_contract.py`; `export_kit.py --check` says whether it is current. Everything else in `brand/` is the working state of the pipeline.

`brand/owner/` holds the owner's answers: the questions a step asked and the answers it was given (section 9). It is not part of any step version and not checked by `check_contract.py`; `scripts/owner.py` validates every file it reads or writes.

The fal key. `scripts/fal_generate.py` reads it in a studio (the brand directory's parent is named `orders`), from the line `FAL_KEY=<key>` in `<studio>/.env`; otherwise from the same line in `brand/.env`; otherwise from the environment variable `FAL_KEY`. Files come first because some agents do not pass environment variables into their sandbox. In the project layout, the step that turns paid generation on copies `templates/fal.env` to `brand/.env`: comment lines that say where to get the key, how to fill it in and how to check it, then `FAL_KEY=put-fal-key-here`; and it creates `brand/.gitignore` with the line `.env`; in a studio it creates neither, because the key belongs to the studio. A `.env` is never committed and never copied into a kit. Neither file is checked, and neither affects a step version.

## 2. `pipeline.yaml`

### 2.1 YAML subset

The check script has no dependencies and reads only this subset of YAML, which also applies to frontmatter:

- nested mappings, indented with two spaces; no tabs;
- one `key: value` per line; values are scalars;
- a scalar may be wrapped in single or double quotes;
- `#` starts a comment at the start of a line or after whitespace;
- no lists, flow syntax (`{}`, `[]`), multi-line strings, anchors or tags.

All scalars are read as strings and then validated. `on` and `off` are therefore the plain words, not booleans. A general YAML 1.1 parser would read them as booleans, so any other tool that reads `pipeline.yaml` must treat `true` as `on` and `false` as `off`.

### 2.2 Schema

```yaml
order: acme
profile: personal-brand
market_language: uk

tools:
  image_generation: svg-only
  screenshots: manual
  figma_export: off

budget:
  limit: 20.00

steps:
  00-intake:
    status: approved
    version: 3e7a90d1c2b4
    spent: 0
  01-strategy:
    status: approved
    version: 9f2c41ab07d3
    built_on:
      00-intake: 3e7a90d1c2b4
    spent: 0
  02-brand-platform:
    status: in-progress
    built_on:
      00-intake: 3e7a90d1c2b4
      01-strategy: 9f2c41ab07d3
    spent: 0
  03-identity:
    status: pending
    spent: 0
  # ... every step directory from section 1 is listed
```

| Key | Required | Value |
|---|---|---|
| `order` | no | the name of the order, `[a-z0-9]` and inner `-`; written by intake when the brand directory is not named `brand`: the directory's name |
| `profile` | yes | `b2b-saas`, `consumer-app`, `local-business`, `personal-brand` or `physical-product` |
| `market_language` | yes | a BCP 47 language tag, for example `uk` or `en-US` |
| `tools.image_generation` | yes | `fal`, `svg-only` or `none` |
| `tools.screenshots` | yes | `headless-chrome` or `manual` |
| `tools.figma_export` | yes | `on` or `off` |
| `budget.limit` | yes | a non-negative number, in US dollars; `0` when no paid generation is used |
| `steps.<step>` | yes, for all six steps | a mapping, see below |
| `steps.<step>.status` | yes | `pending`, `in-progress`, `approved`, `stale` or `skipped` |
| `steps.<step>.version` | when the status is `approved`, `stale` or `skipped` | a step version (section 2.3) |
| `steps.<step>.built_on` | when the status is `approved` or `stale`, except for `00-intake` | a mapping from every earlier step to the version of it this step was built on |
| `steps.<step>.spent` | yes | a non-negative number, in US dollars |

All three `tools` keys must be present with an explicit value. The script fills in no defaults. `intake` writes the base mode (`svg-only`, `manual`, `off`) without asking; the step that first needs a tool asks the owner and changes the value.

Unknown keys at any level are errors.

Rules across keys:

- The sum of `spent` over all steps must not exceed `budget.limit`.
- `built_on` may name only steps that come earlier in the pipeline.
- A step with status `approved` requires every earlier step to be `approved` or `skipped`.
- A `pending` step has no `version` and no `built_on`.

### 2.3 Step versions

The version of a step is a hash of its directory's content:

1. Take every file under the step directory, recursively, except anything under `review/` and any file or directory whose name starts with a dot.
2. Sort the paths (relative to the step directory, with `/` separators) by byte order.
3. Feed a SHA-256 hash, for each file in order: the path in UTF-8, a NUL byte, the SHA-256 hex digest of the file's bytes, a newline.
4. The version is the first 12 hex characters of the result.

`check_contract.py hash <step>` prints this value. A skill never computes it by hand.

When a step is approved, its skill sets the artifact statuses first, then writes the step's `version`, and `built_on` with the current `version` of every earlier step.

### 2.4 Version mismatches

The script compares versions but changes nothing. It reports two kinds of warning:

- **changed since approval**: the step is `approved` and the hash of its directory differs from its `version`;
- **built on an older version**: the step is `approved` and a value in its `built_on` differs from the current `version` of that earlier step.

Warnings do not affect the exit code. The conductor reads them and proposes marking steps `stale`.

## 3. Frontmatter

Every markdown artifact listed in section 5 starts with a frontmatter block. `summary.md`, `review/decisions.md` and non-markdown files carry none.

```markdown
---
step: 01-strategy
status: approved
source: generated
---
```

| Key | Value |
|---|---|
| `step` | the name of the step directory the file is in |
| `status` | `draft` or `approved` |
| `source` | `generated` or `provided` |

Exactly these three keys; any other key is an error.

Rules:

- `status: draft` means the owner has not confirmed the file. An `approved` step holds no `draft` artifact.
- In `01-strategy` each tool file is approved on its own, at the end of its session. While the step is `in-progress`, the files that say `approved` are the finished sessions.
- `source: provided` marks a finished asset supplied by the owner. The file then holds the agent's description of the asset, under the same required sections where they apply.

## 4. `summary.md`

Required in every step that is `approved`, `stale` or `skipped`. No frontmatter. It contains exactly these three second-level headings, in this order, and no others:

```markdown
# Summary: <step directory>

## Decisions

## Constraints on later steps

## Open questions
```

Each section has content. A section with nothing to report says `None.`

## 5. Artifacts and required sections

A required section is a second-level heading (`## Name`) that matches exactly and has content under it. A file may hold further sections, and the order of sections is free. Headings are always in English, also in files whose content is in the market language.

The "From" column says where each heading comes from: **spec** means brand's specification names it, **framework** means it is the standard part of the named framework, **proposed** means it was added when this contract was written and agreed with the owner.

### 5.1 Plates

The artifacts of `00-intake` (except `idea.md`), of `01-strategy`, of `02-brand-platform` (except `creative-brief.md`) and of `03-identity`, and `interface.md` of `04-design-system`, are plates. A plate is the literal, short answer in the slots of one tool: the lines that are later set in the brand book.

- Each slot is a required section. Its content is either exactly one line, or a list in which every line starts with `- `.
- A slot may limit the number of list items, the number of words per line or item, and the shape of the line. Words are counted by splitting on whitespace.
- A plate file may hold further sections. `Rationale` is the usual one: where each line came from, the owner's own words, the candidates that were rejected. Only the slots go into the brand book.
- Plates are written in English.
- `scripts/render_plates.py` renders each plate to `review/<name>.html` in its step directory and all of them to `brand/map.html`.

The list in `scripts/check_contract.py` (`PLATES`) is authoritative; the tables below repeat it.

### `00-intake`

| File | Required | Slots |
|---|---|---|
| `idea.md` | yes | not a plate; one required section, `Idea` |
| `brief.md` | yes | `Brand`, `In one line` (12 words), `For whom`, `Why now`, `Ambition`: one line each |

`Idea` holds the idea in the owner's own words and language, unedited. `brief.md` is The Brief, the agency's reading of it.

### `01-strategy`

Lists are written "n" (exactly n items) or "n-m". A number of words in brackets is the limit per line or per item.

| File | Slots |
|---|---|
| `golden-circle.md` | `Why`: one line (15), starts with `We believe` or `I believe` · `How`: list of 3 (6) · `What`: one line (12) |
| `lean-canvas.md` | `Problem`: list of 3 (10) · `Existing alternatives`: one line · `Customer segments`: list of 1-2 · `Early adopter`: one line · `Unique value proposition`: one line (15) · `Solution`: list of 3 · `Channels`: list of 1-3 · `Revenue streams`: list of 1-3 · `Cost structure`: list of 1-3 · `Key metrics`: list of 1-3 · `Unfair advantage`: one line |
| `icp.md` | `Who`, `Situation`, `Trigger`, `Tried before`, `Where to find`: one line each · `Main job`: one line of the form `When ..., I want to ..., so I can ...` · `Functional`, `Emotional`, `Social`: one line each · `Other customers`: optional, list of 1-2 |
| `positioning.md` | `Competitive alternatives`: list of 1-3 · `Unique attributes`: list of 3 · `Value`: list of 3 · `Target segment`: one line · `Market category`: one line (5) · `Positioning statement`: one line (50) of the form `For ... Unlike ...` |
| `brand-wheel.md` | `Attributes`: list of 3-5 · `Functional benefits`: list of 3 · `Emotional benefits`: list of 3 · `Values`: list of 3 (2) · `Personality`: list of 3-5, each `Trait: what it means in practice` · `Essence`: one line of 2 to 4 words |
| `marketing-mix.md` | `Product`, `Price`, `Place`, `Promotion`: one line each (20) · optional, for a 7P profile: `People`, `Process`, `Physical evidence`: one line each (20) |
| `messaging.md` | `Main promise`: one line (12) · `Proofs`: list of 3, each `Claim: fact` · `Objections`: list of 3, each the objection in double quotes followed by the answer |

All seven files are required. The headline slots, set large on the page "Strategy on one page", are `Why`, `Unique value proposition`, `Main job`, `Positioning statement`, `Essence` and `Main promise`.

### `02-brand-platform`

Four plates, one per session, and the creative brief.

| File | Required | Slots |
|---|---|---|
| `archetype.md` | yes | `Primary archetype`, `Secondary archetype`: one line each, one of the twelve archetypes, and the two differ · `Character`: one line (12) of the form `The ... who ...` · `Why this pair`: one line (20) · `Personality`: list of 3-5, each `Trait, but not X: what it means in practice` |
| `voice.md` | yes | `Voice`: one line (15) of the form `We sound like ..., never like ...` · `Tone`: list of 4, one per dimension in the order below, each `Dimension: N of 5. Why` · `We write like this`: list of 3-5 · `We never write`: list of 3-5 · `Examples`: list of 4, each `Situation. Right: ... Wrong: ...` |
| `name.md` | no | `Name`: one line (3) · `Domain`: one line · `What it says`: one line (15) · `Rejected`: optional, list of 1-3, each `Name: reason` |
| `mood.md` | yes | `Territory`: one line of 2 to 4 words · `Mood words`: list of 3 (1) · `Takes`: list of 3-5 · `Excludes`: list of 3 |

The headline slots, set large on the page "Platform on one page", are `Character`, `Voice`, `Name` and `Territory`.

- The twelve archetypes: Innocent, Everyman, Hero, Outlaw, Explorer, Creator, Ruler, Magician, Lover, Caregiver, Jester, Sage.
- The four tone dimensions, in this order: `Formal–casual`, `Serious–funny`, `Respectful–irreverent`, `Matter-of-fact–enthusiastic`. A position is 1 to 5: 1 is the first pole, 5 the second. A plain hyphen between the poles is accepted.
- `Examples` in `voice.md` and the name itself are in the market language; they are the one exception to English plates.
- `name.md` exists only when the brand was unnamed at intake. When the step is checked strictly, `Brand` in `00-intake/brief.md` must equal `Name` of an approved `name.md`; without `name.md`, `Brand` must not be `Unnamed`.

| Other artifact | Required | Content |
|---|---|---|
| `creative-brief.md` | yes | sections `Brand`, `Strategy`, `Audience`, `Character`, `Voice`, `Mood`, `Given`, `Constraints`; not a plate: each line is copied from a plate |
| `moodboard/` | yes | not empty |
| `given/` | no | the assets the owner handed over and `inventory.md`; when the directory exists it is not empty |

`moodboard/` holds `index.md`, the rendered `board.html` and the images, as `moodboard.md` describes. The check script only requires the directory to be non-empty; `scripts/render_moodboard.py` enforces the format.

`mood.md` with `source: provided` records the short Mood session, in which everything visual was given: no choice page was shown, so `review/decisions.md` is not required.

### `03-identity`

Four plates, one per session, and the files they describe.

| File | Required | Slots |
|---|---|---|
| `logo.md` | yes | `Logo idea`: one line (12) · `Kind`: one line, one of `Wordmark`, `Symbol and wordmark`, `Monogram` · `Construction`: one line (20) · `Minimum size`: list of 2, `Full logo: N px high` then `Mark: N px high` · `Clear space`: one line · `Never`: list of 3 |
| `color.md` | yes | `Color idea`: one line (12) · `Palette`: list of 3-6, each `Name - #RRGGBB - role` · `Accent is for`: one line · `Accent is never for`: one line · `Contrast`: list of 4, each `Color on Color: N to 1` |
| `typography.md` | yes | `Type idea`: one line (12) · `Display`, `Text`: one line each, `Family - weights - role` · `Sizes`: list of 3, `Headline`, `Lead` and `Body` in this order, each `Name: N px at 1440, N px at 390` · `License`: one line |
| `motto.md` | yes | `Motto`: one line (6) · `What it says`: one line (15) · `Where it stands`: one line · `Rejected`: optional, list of 1-3, each `Motto - reason` |

The headline slots, set large on the page "Identity on one page", are `Logo idea`, `Color idea`, `Type idea` and `Motto`.

- A palette line holds one color. Its role is one or more of `background on light`, `text on light`, `background on dark`, `text on dark`, `accent` and `secondary`, separated by commas. Each of the first five is carried by exactly one color; `secondary` by at most one.
- `Contrast` is calculated, not written: `check_contract.py contrast "<palette line>" ...` prints its four lines (text on background for the light and the dark theme, then the accent on each background), and the check script reports a line that does not follow from the palette. The ratio is the WCAG 2 contrast ratio, rounded to one decimal. Body text must reach 4.5 to 1 in both themes. An accent line ends with `, large text only` under 4.5 to 1 and with `, not for text` under 3 to 1.
- `Motto`, and the mottos in `Rejected`, are in the market language. Everything else is in English.
- `Where it stands` says where the motto is read as copy (the end of a text, a bio, a signature). The motto is not a part of the logo and is never locked up with it: no plate, variant or surface sets it beside the logo or under it.
- A plate with `source: provided` records an asset the owner handed over and asked to keep: its session showed no choice page, so `review/decisions.md` has no choice for it.

| File | Required | Rule |
|---|---|---|
| `logo/full.svg` | yes | an SVG document: the mark and the name |
| `logo/mark.svg` | yes | an SVG document: the mark alone |
| `logo/mono.svg` | yes | an SVG document: one color, `currentColor` |
| `logo/dark.svg` | yes | an SVG document: for dark backgrounds |
| `fonts/` | yes | not empty |
| `surfaces/` | yes | not empty |

`fonts/` holds the files of the type pair (`.woff2`), a `fonts.css` that declares them with relative URLs, and the license text of each family. Surfaces, the plates and the design system load fonts only from here, never from a remote server. `scripts/fetch_font.py` fills it for fonts from Google Fonts.

Once the step is `approved` in `pipeline.yaml`, `scripts/render_plates.py` sets every plate of every step, the one-pages and the brand map in the brand's colors and type, with the logo in the masthead.

### `04-design-system`

One plate, from the Interface session, and the system built from it.

| File | Required | Slots or sections |
|---|---|---|
| `interface.md` | yes | `Interface idea`: one line (12) · `Shape`: one line that names the radii in pixels · `Depth`: one line that starts with `Flat`, `Ruled` or `Raised` · `Density`: one line, `N px unit, N px controls` · `Motion`: one line (15) · `Never`: list of 3 |
| `components.md` | yes | `Atoms`, `Molecules`, `Organisms`, `Pages` |

The headline slot is `Interface idea`. A plate with `source: provided` records a design system the owner asked to keep: `review/decisions.md` then has no `Interface` choice, only `System`.

| File | Required | Rule |
|---|---|---|
| `tokens.json` | yes | a JSON object in the format of `design-tokens.md`, with every token of its section 4 |
| `tokens.css` | yes | exactly what `scripts/build_tokens.py` writes from `tokens.json` |
| `copy.json` | yes | a JSON object in the format of `system.md` |
| `reference/index.html`, `reference/sheet.html`, `reference/system.css` | yes | not empty; written by `scripts/render_system.py build` |
| `reference/pages/landing.html`, `reference/pages/sign-in.html`, `reference/pages/sign-up.html` | yes | not empty; written by the same script |

The rules that span files:

- **Contrast.** Every pair of color roles that `check_contract.py tokens <tokens.json>` prints reaches its minimum in the light and in the dark theme: 4.5 to 1 for text (`text`, `text-muted` and `link` on the backgrounds, `on-accent` on the accent and its hover, each functional color on its background, `error` on the page), 3 to 1 for `control-border` and `focus`. A role color is opaque.
- **The identity.** `color.bg`, `color.text` and `color.accent` are the identity's `background on light`, `text on light` and `accent`, and in the dark theme its `background on dark`, `text on dark` and the same accent. `font.display` and `font.text` start with the families of `Display` and `Text`. `type.headline`, `type.lead` and `type.body` have the sizes of `Sizes`, at 1440 and, through the `narrow` group, at 390.
- **Touch.** `size.control` is at least 44 px through the `narrow` group.
- **`components.md`.** Under `Atoms`: `Button`, `Link`, `Text input`, `Text area`, `Select`, `Checkbox`, `Radio`, `Switch`, `Badge`, `Avatar`, `Divider`. Under `Molecules`: `Form field`, `Notice`, `Card`. Under `Organisms`: `Header`, `Hero`, `Benefits`, `Testimonial`, `Call to action`, `Sign-in form`, `Footer`. Each is a third-level heading with exactly the lines `- For:`, `- States:`, `- Tokens:`, `- At 390:`, `- Accessibility:`, in this order; a section may hold further components with the same lines. `Tokens` names tokens of `tokens.json` by their path, never under `palette`, `dark` or `narrow`. Under `Pages`: `Landing`, `Sign-in`, `Sign-up`, each with `- File:` and `- Uses:`; the file exists under `reference/`.

### `05-brand-book`

| File | Required | Required sections or rule |
|---|---|---|
| `brand-book.md` | yes | `Strategy`, `Brand platform`, `Identity`, `Design system`, `How to use this` |
| `index.html` | yes | not empty |
| `brand-book.pdf` | no | not empty when present |

All three are written by `scripts/render_book.py` from the approved plates, the tokens and the files of the identity, and never edited by hand. `index.html` is one self-contained file: fonts, styles and images are embedded, and it loads nothing from the network or from other files. `brand-book.pdf` is the same page printed by headless Chrome; it is absent when no Chrome was found. All three are in English; brand copy stays in the market language.

## 6. `review/decisions.md`

Required in `02-brand-platform` (unless `mood.md` says `source: provided`), `03-identity` and `04-design-system`; checked wherever it exists. No frontmatter.

```markdown
# Decisions

## 1. Direction

- Page: direction-02.html
- Decision: 2, with the type from 4
- Comment: the mark in 2 is calmer; keep the serif from 4
- Status: fixed
```

- Each choice is one second-level heading of the form `## <number>. <name>`, numbered from 1 without gaps.
- Each choice has the four lines `Page`, `Decision`, `Comment` and `Status`, in this order.
- `Page` names the choice page in `review/` that the decision was made on. The file must exist. Choice pages are rendered from a data file as described in `choice-page.md`. A review of finished items without variants (the surfaces of `03-identity`) is recorded the same way, and its `Page` names a review page, described in `review-page.md`.
- `Decision` and `Comment` record the owner's answer in the owner's words. `Comment` may be empty.
- `Status` is `open` or `fixed`. A choice is `fixed` only on the owner's explicit decision.
- An `approved` step has at least one choice and no `open` choice.

## 7. What is checked when

How strictly a step is checked depends on its status in `pipeline.yaml`:

| Step status | Check |
|---|---|
| `pending` | The directory may be absent. If it exists, the files in it are validated. |
| `in-progress` | Files that exist are validated. Missing files are not errors. |
| `approved`, `stale` | Every required file must exist and be valid. |
| `skipped` | `summary.md` must exist. Files that exist are validated; missing artifacts are not errors, because the owner's asset stands in for the step's work and need not match the contract's file names. |

"Validated" means: the frontmatter is present and valid, the required sections are present with content, the slots of a plate keep their limits (section 5.1), and the rules of sections 3, 4 and 6 hold.

`--step <step>` checks `pipeline.yaml` and that one step, and requires every file of the step as if it were `approved`, whatever its current status. A skill runs this before it asks the owner to close the step. Because the owner has not confirmed yet, `status: draft` in an artifact is not an error under `--step`; it is an error only once the step's own status is `approved` or `stale`.

Commands:

```
python3 scripts/check_contract.py check [--step <step>] [<path to brand/>]
python3 scripts/check_contract.py hash <step> [<path to brand/>]
python3 scripts/check_contract.py contrast "<palette line>" ...
python3 scripts/check_contract.py tokens <tokens.json>
```

The path is the brand directory and defaults to `./brand`. Exit codes: `0` when there are no errors (warnings may be present), `1` when there are contract errors, `2` when `brand/` or `pipeline.yaml` cannot be read.

## 8. The kit: `out/`

`brand/out/` is what the pipeline hands on: one directory with only the finished, approved files, in a layout that is the same for every brand, and with instructions for the agents and people who receive it. Nothing in it links outside it, names a path of the brand directory, or holds an absolute path; it can be delivered to any directory (section 8.1).

| Path | Content | From |
|---|---|---|
| `AGENTS.md` | the entry point for an agent: read order, every file and what it is for, the files each task needs, the rules | a fixed text of `export_kit.py`, with the brand's name, market language and surfaces |
| `README.md` | the same for a person, in short | a fixed text of `export_kit.py` |
| `brand.md` | the brand book as text, with the paths of the kit | `render_book.py` (`book_md` with `kit`) |
| `brand.json` | `format`, `name`, `motto`, `in_one_line`, `profile`, `market_language`, and `plates`: step → plate name (without `.md`) → `title` and `slots`; a slot is a string (one line) or a list of strings | the approved plates and The Brief |
| `manifest.json` | `format`, `name`, `order` (only when `pipeline.yaml` names one), `built_from` (step → version), `files` (path → `sha256`, `bytes`) for every other file | written last |
| `book/index.html`, `book/brand-book.pdf` | the brand book; the PDF only when the book has one | `05-brand-book/` |
| `logo/full.svg`, `mark.svg`, `mono.svg`, `dark.svg` | the logo | `03-identity/logo/` |
| `fonts/` | the font files, `fonts.css`, the licenses | `03-identity/fonts/` |
| `surfaces/` | the surfaces and their images | `03-identity/surfaces/` |
| `tokens/tokens.json`, `tokens/tokens.css` | the tokens | `04-design-system/` |
| `system/components.md`, `system/system.css`, `system/index.html`, `system/sheet.html`, `system/pages/` | the design system | `04-design-system/components.md` and `reference/` |

`format` is `brand-kit/2` in both JSON files. (`brand-kit/1` had no `order` and told the reader to change the brand "in the project's `brand/`".) Rules:

- The kit is exported only when every step is `approved` or `skipped`, `05-brand-book` is `approved`, `brand-book.md` says `status: approved`, and `check` reports no error and no warning.
- Every relative `href`, `src` and `url()` of a copied `.html` or `.css` file is rewritten to point at the kit's copy of its target. A link to a file the kit does not hold stops the export.
- Nothing of the working state goes in: no `Rationale`, `summary.md`, `review/`, `pipeline.yaml`, `owner/`, `.env`, moodboard, `given/` or `idea.md`.
- `AGENTS.md`, `README.md` and `brand.md` say that the kit is rebuilt, never edited, and that the brand is changed in the brand working directory it was built from (naming the order when there is one), by the step that owns the line, after which the kit is built and delivered again. They do not say where that directory is.
- The kit is written whole and swapped in; an existing `out/` is replaced only when its `manifest.json` names a `brand-kit/` format.
- `export_kit.py --check` reports the kit out of date when a step version differs from `built_from`, the format is not the current one, or a file differs from its hash.

### 8.1 Delivery

The project a brand is for receives the kit as a copy, in a directory it names (`docs/brand/` unless the order says otherwise). The copy is generated: nothing in it is edited by hand, and nothing is added to it.

- `--deliver <dir>` copies `brand/out/` to `<dir>` as it is. It refuses when `brand/out/` is not current; it never exports.
- The copy is written whole and swapped in; an existing `<dir>` is replaced only when its `manifest.json` names a `brand-kit/` format.
- `--check --deliver <dir>` reports the delivered kit out of date when `brand/out/` is not current, `<dir>/manifest.json` differs from `brand/out/manifest.json`, a file differs from its hash, or `<dir>` holds a file the manifest does not list. Names that start with a dot are ignored.

```
python3 scripts/export_kit.py [<path to brand/>] [--check] [--deliver <dir>]
```

Exit codes: `0` exported or delivered (with `--check`: current), `1` not ready, a link outside the kit, a target that is not a kit, or (with `--check`) out of date, `2` `brand/` or `pipeline.yaml` cannot be read.

## 9. The owner's answers: `owner/`

Every point at which a step waits for the owner is a **question**: a choice between variants or candidates, an answer in the owner's own words, the approval of a plate or a step, the switch of a tool, one batch of paid generation. A skill never decides such a point itself. It writes the question to a file, and continues only from an answer in a file. The answer may come from the owner in the chat (an interactive run), or be written by another program or agent (a headless run, or answers placed before the run).

```
owner/
  questions/<id>.json
  answers/<id>.json
```

Both are written by `scripts/owner.py`; a skill never writes them by hand. A question is never changed once asked, and an answer is never changed once given: a new cycle is a new question.

### 9.1 Ids

`<step>.<part>.<point>`: the step directory, the part of the step (`kickoff`, a tool's name such as `golden-circle`, `surfaces`, `system`, `book`, or `step` for the step as a whole), and the point, each `[a-z0-9]` with inner `-`. A point asked again in cycles ends in `-NN`, from `-01`. The id names the same point in every run, so an answer can be written before the question is asked. Each step lists its ids; the general points are:

| Point | Kind | What is asked |
|---|---|---|
| `dig-N` | `choice` or `text` | the N-th question of the session's Dig |
| `<slot>` | `choice` | the candidate for a headline slot (the slot's heading in lower case, spaces as `-`) |
| `plate-NN` | `approve` | the plate as shown, in cycle NN |
| `choice-NN` | `choice` | the variant on the choice page of cycle NN |
| `review-NN` | `approve` | a review page of finished items: `yes`, or `no` with the corrections by number |
| `spend-NN` | `spend` | the NN-th batch of paid generation in the part |
| `approve-NN` | `approve` | under the part `step`: closing the step, in cycle NN |

### 9.2 Question

```json
{
  "format": "brand-question/1",
  "id": "02-brand-platform.mood.choice-01",
  "step": "02-brand-platform",
  "kind": "choice",
  "asked": "Which territory is closest to how the brand should feel?",
  "context": "Three territories as small boards; the reference images are on the page.",
  "options": [
    {"id": "1", "label": "Quiet workshop", "means": "raw paper, daylight, hand-set type"},
    {"id": "2", "label": "Night studio", "means": "dark ground, one warm light, close crops"},
    {"id": "3", "label": "Open field", "means": "air, horizon lines, pale colors"}
  ],
  "recommended": "2",
  "free": true,
  "page": "02-brand-platform/review/territory-01.html",
  "files": ["02-brand-platform/moodboard/index.md"]
}
```

| Key | Required | Value |
|---|---|---|
| `format` | yes | `brand-question/1` |
| `id` | yes | the id (section 9.1); the file is named after it |
| `step` | yes | the step directory, the first part of the id |
| `kind` | yes | `choice`, `text`, `approve` or `spend` |
| `asked` | yes | the question, in the owner's language |
| `context` | no | what the reader needs to answer: what each answer leads to, the price of a batch |
| `options` | for `choice` | two or more, each `id` (unique), `label`, `means`; not allowed for other kinds |
| `recommended` | no | for `choice`, an option id; the agency's recommendation, never an answer |
| `proposed` | no | for `text`, the agency's proposed wording; never an answer |
| `free` | no | for `choice`, `true` when the owner may answer in his own words instead of an option |
| `page` | no | the rendered page to look at, relative to the brand directory; it exists |
| `files` | no | other files to read, relative to the brand directory; each exists |

An `approve` or `spend` question has the implied options `yes` and `no`.

### 9.3 Answer

```json
{
  "format": "brand-answer/1",
  "id": "02-brand-platform.mood.choice-01",
  "choice": "2",
  "comment": "with the colors from 3",
  "by": "owner"
}
```

| Key | Required | Value |
|---|---|---|
| `format` | yes | `brand-answer/1` |
| `id` | yes | the id of the question |
| `choice` | for `approve` and `spend`; for `choice` unless `text` is given | an option id; `yes` or `no` |
| `text` | for `text`; for `choice` only when the question is `free` | the owner's own words |
| `comment` | no | what the owner added; for `approve` with `no`, what to change |
| `by` | yes | who gave the answer: `owner` in the chat, or the name of the program or agent that wrote it |

An answer written before its question is checked against the question once the question is asked. An answer that does not fit its question (an option that does not exist, `text` for a question that is not `free`) is an error, and the step stops.

### 9.4 Running without a person

- **Interactive** (the default): the skill writes the question; when an answer is already there, it tells the owner which answer it continues from; otherwise it asks in the chat and records the reply with `--by owner`.
- **Headless** (`--headless` in the command): the skill writes the question; when no answer is there, it stops at once and prints `WAITING <id>: <asked>`. It shows no fixed text to anyone, and does not ask whether to go on to the next session: it goes on until the first unanswered question or the end of the step.
- In both, a step reads its answered questions on every start; an answered question is settled and is not asked again. A step that stopped in the middle of a session continues from its first unanswered question.
- A step is finished when its status in `pipeline.yaml` is `approved`.

```
python3 scripts/owner.py ask <brand> <question.json>
python3 scripts/owner.py get <brand> <id>
python3 scripts/owner.py answer <brand> <id> (--choice <id> | --text <text>) [--comment <text>] --by <who>
python3 scripts/owner.py pending <brand>
```

`ask` writes the question (the same question asked again is accepted; a different one under the same id is an error) and then behaves as `get`. `get` prints the answer as JSON. `answer` writes an answer, checked against its question when there is one; it never replaces an answer. `pending` prints one line per unanswered question.

Exit codes: `0` answered (`pending`: nothing is waiting), `1` an invalid question or answer, `2` the brand directory cannot be read, `3` waiting for an answer.
