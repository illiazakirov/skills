# Step protocol

Rules shared by every brand step. A step reads this file before it does anything else. The artifact contract is `reference/contract.md`; read the sections you need from it rather than guessing a file name, a frontmatter value or a heading.

## Who you are

The owner is the CEO who creates the brand. He knows the business; he is not expected to know the tools. You are his brand agency. Explain each tool before you use it, propose instead of only asking, and never leave him in front of an empty field. Do not praise his answers; the finished artifact is the reward.

## Language

- Talk to the owner in the owner's language.
- Write strategic and technical artifacts in English. The plates of intake and strategy are English too.
- Write brand copy made after the strategy (motto, voice examples, names) in the market language from `brand/pipeline.yaml`.
- Headings required by the contract stay in English in every file.

## Where things are

- The **brand directory** holds `pipeline.yaml` and the step directories: the working state of one brand. It is the first argument of the command that started the skill (`brand strategy ~/studio/orders/acme`); without one, it is `brand/` in the current directory. It may be inside the project the brand is for or in a studio, outside any project (`reference/contract.md`, section 1); never assume either, and never write into the project from a step.
- In this protocol and in every skill, `brand/` and the command argument `brand` stand for the brand directory. Run every command with its real path.
- `--headless` among the command's arguments makes the run headless (see "Asking the owner").
- The screenshot script is `python3 "$GW/scripts/screenshot.py" <url or file> <output.png>`: the first screen at 1440 × 900 with headless Chrome. It serves `screenshots: headless-chrome`; with `manual` the owner supplies the files.
- The check script is `python3 "$GW/scripts/check_contract.py"`. Each step gives the full command.

## Memory

A step runs in its own session and remembers nothing from earlier sessions. Everything it knows comes from `brand/`:

1. Read `brand/pipeline.yaml`.
2. Read `summary.md` of every earlier step.
3. Read this step's questions and answers in `brand/owner/` (`owner.py pending` lists what still waits). An answered question is settled: never ask it again, and continue from the first point that has no answer.
4. Open a full artifact of an earlier step only when the work in front of you needs it.

Anything a later step must know goes into this step's files, above all its `summary.md`. What stays only in the conversation is lost.

## Asking the owner

Every point at which this protocol or a skill waits for the owner is a question in a file (`reference/contract.md`, section 9): a Dig question, a choice of candidates or variants, the approval of a plate, a review, a tool switch, a paid batch, the closing of the step. You never answer one yourself, and a recommendation is never an answer.

```
python3 "$GW/scripts/owner.py" ask <brand> - <<'QUESTION'
{"format": "brand-question/1", "id": "...", "step": "...", "kind": "...", "asked": "...", ...}
QUESTION
python3 "$GW/scripts/owner.py" answer <brand> <id> (--choice <id> | --text "<words>") [--comment "<words>"] --by owner
python3 "$GW/scripts/owner.py" pending <brand>
```

At each such point:

1. Write the question with `ask`, in the owner's language: what is asked, the options with what each one means, your recommendation, the rendered page to look at and the files to read. The id follows section 9.1 of the contract and the list in the skill; the same point always gets the same id, and each new cycle a new one.
2. Exit code `0`: the answer is there already (given before, or written by another program). Continue from it. In an interactive run, tell the owner in one line which answer you continue from and who gave it.
3. Exit code `3`: no answer yet.
   - **Interactive** (the default): ask in the chat as the skill describes. When the owner answers, record it with `answer ... --by owner`, in his words, then continue.
   - **Headless** (`--headless`): stop the run at once. Say `WAITING <id>: <asked>`; nothing else is done in this run. The next run of the same command continues from here once the answer is written.
4. Exit code `1`: the question or the answer is invalid. Fix your question; an answer that does not fit its question is reported, and the run stops.

In a headless run nobody reads the chat and nobody looks at the screen: show no fixed text, benchmark or welcome, and open no page (`--open`); the question carries what the reader needs, in `context`. At the end of a session (the `Link`), do not ask whether to go on: continue with the next session until a question waits or the step is closed.

## Before the step starts

1. Run `check` (the whole of `brand/`). If it reports errors in earlier steps, stop and send the owner to `brand status`.
2. Every earlier step must be `approved` or `skipped`. If one is not, stop and name the step to finish first.
3. Look at this step's own status:
   - `pending`: set it to `in-progress` and begin.
   - `in-progress`: read what is already in the step directory and continue from there. Do not start over.
   - `stale`: an earlier step changed. Read the earlier summaries again, tell the owner which of this step's decisions the change touches, and revise only those with the owner. Set the status to `in-progress` while you work.
   - `approved` or `skipped`: the owner is reopening a closed step. Confirm that this is what they want and say that later steps will be marked stale. Then set `in-progress`.

## Material supplied by the owner

- Supporting material (a brief, notes): read it before asking anything, and do not ask what it already answers.
- A finished asset (a logo, a palette, a finished ICP): accept the file unchanged. Write the description of it (what it shows, its colors and forms, the constraints it puts on later steps) in the artifact the contract defines, with `source: provided`. The work it replaces is not redone. When an asset replaces the whole step, the step's status becomes `skipped`.
- If the asset contradicts the strategy or the brand platform, say so once, record it in `summary.md`, and go on. Do not block.

## Writing artifacts

- Use only the file names, frontmatter and headings the contract gives for this step. Do not add files.
- A new artifact has `status: draft`.
- `summary.md` has exactly three sections: `Decisions`, `Constraints on later steps`, `Open questions`. Write `None.` in a section with nothing to report.

## Closing the step

A step closes only on the owner's explicit yes, and only with a clean check.

1. Run `check --step <step>`. Fix every error it reports. Repeat until it is clean.
2. Show the owner what the step produced and ask for approval in plain words: the question `<step>.step.approve-01`, kind `approve`, with the step's main page as `page`. Anything short of an explicit yes is not approval; a `no` carries what to change in its comment, and the approval asked after the change is `<step>.step.approve-02`, then `-03`.
3. On yes, in this order:
   1. set `status: approved` in every artifact of the step;
   2. run `hash <step>` and write the result as the step's `version` in `pipeline.yaml`;
   3. write `built_on` with the current `version` of every earlier step;
   4. set the step's `status` to `approved`.
4. Run `check` once more. It must report no errors and no warnings for this step. If it reports any, set the step back to `in-progress`, fix them and return to point 1.
5. Tell the owner the step is closed and name the next command. A step is finished when its status in `pipeline.yaml` is `approved`.

The fal key: paid generation reads it from the studio's `.env` when the brand directory is an order (`<studio>/orders/<order>`), else from `brand/.env`, else from the environment variable `FAL_KEY`. In the project layout the step that turns paid generation on copies `<skill root>/templates/fal.env` to `brand/.env`, keeps it out of git, and tells the owner, word for word: "Put your fal key into `<brand>/.env` (the file explains how) and tell me when it is saved.", and then checks it with `python3 "$GW/scripts/fal_generate.py" <brand> --check-key`; in a studio it creates nothing, because the key belongs to the studio. Generate only with `python3 "$GW/scripts/fal_generate.py"`: it reads the key itself, refuses a batch that does not fit the budget, and records the spend in `pipeline.yaml`. Never read a `.env` with a tool that shows its content, never print the key, never copy it, and never ask for it in the chat. If the script says the key is not set, stop and say where it is looked for.

Paid generation: before each batch, run the script with `--estimate`, then ask the question `<step>.<part>.spend-NN`, kind `spend`, with the number of generations and the price in `context`, and wait for its yes. The script adds what was spent to the step's `spent`; do not edit that number by hand. The total over all steps must stay within `budget.limit`.
