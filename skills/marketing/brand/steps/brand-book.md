# Brand book

Step 5, the last of the brand pipeline. It decides nothing. Everything in the book was fixed by an earlier step and approved by the owner, and a script sets it: you never write a line of the book yourself. If a line is wrong, it is changed in the step it came from, and the book is built again.

The owner is the CEO who created the brand. The **Strategist** speaks in this step, and signs once at its start.

```
brand/05-brand-book/
  index.html             # the book: one self-contained page in the brand's style
  brand-book.pdf         # the same, printed; absent when no Chrome was found
  brand-book.md          # the same content as text: the single input for other agents
  summary.md
  review/
    source.html          # the page before bundling
    print.html           # the printed book, the source of the PDF
    shots/               # the screenshots of the surfaces and the example pages
    book-01.json / .html # the review page

brand/out/               # the kit, exported on approval by export_kit.py (contract, section 8)
```

Read `reference/step-protocol.md` first and follow it. Then read `reference/review-page.md`. The commands of this step:

```
python3 "$GW/scripts/check_contract.py" check brand
python3 "$GW/scripts/check_contract.py" check --step 05-brand-book brand
python3 "$GW/scripts/check_contract.py" hash 05-brand-book brand
python3 "$GW/scripts/render_book.py" brand [--approve] [--no-pdf]
python3 "$GW/scripts/render_review.py" <data.json>
python3 "$GW/scripts/screenshot.py" <url or file> <output.png> [--width W] [--height H]
python3 "$GW/scripts/export_kit.py" brand [--check]
```

## What the book is

The brand map is the working state; the book is the handover, to people (a designer, a developer, an agency) and to agents that build a landing page, a campaign or a screen. `render_book.py` builds it in a fixed composition:

1. The cover: the logo, the name, the motto, `In one line` of The Brief.
2. **Strategy**: Strategy on one page, then the seven plates.
3. **Brand platform**: Platform on one page with the board, then its plates.
4. **Identity**: Identity on one page, the four plates, then each surface.
5. **Design system**: the Interface plate, the sheet, and the landing page, sign-in and sign-up at 1440 and at 390.
6. **How to use this**: a fixed text and the table of the brand's files.

Each plate is a scene of its own: its slots, word for word, in a layout and with a motion on scroll that belong to its tool. Without JavaScript, with reduced motion and in the PDF the scenes are plain pages.

Only the slots of a plate go in, never its `Rationale`. Every block is numbered. The page has a light and a dark theme with a switch; the PDF is always light. The PDF is not the page printed: it is a document of fixed 16:9 pages with one frame and a few templates, in which a block never breaks inside a page; the script names any page whose text does not fit. Everything is in English, as the plates are; brand copy stays in the market language. `brand-book.md` holds the same sections, the plates as text with the paths of their files, and a table of every token.

## The owner's answers

Every point of this step at which you wait for the CEO is a question in `brand/owner/`, asked and answered as the step protocol describes in "Asking the owner" (`python3 "$GW/scripts/owner.py"`). Read the answered ones before you start: they are settled, and the step continues from the first point without an answer. With `--headless` there is no briefing, benchmark or link in the chat, and no question whether to go on: the run continues until a question waits.

| Id | Kind | Asked |
|---|---|---|
| `05-brand-book.book.shots-NN` | `approve` | with `screenshots: manual`: whether the listed images are in `review/shots/` now |
| `05-brand-book.book.review-NN` | `approve` | the book; a `no` carries the corrections by block number |
| `05-brand-book.step.approve-NN` | `approve` | closing the step; on yes the kit is exported |

The kit is exported to `brand/out/` on approval. Delivering it into the project the brand is for (`export_kit.py brand --deliver <dir>`) is not part of this step: the owner or the studio runs it.

## Before you start

1. Do "Before the step starts" from the step protocol. Every earlier step must be `approved` or `skipped`. A `stale` step means the book would hold something the owner has not confirmed: stop and send the owner to `brand status`.
2. Say the opening, word for word:

> **Strategist:** Everything is approved. The last step gathers it into one book: the strategy, the platform, the identity and the design system, each opening with its page of headlines, then its plates. The agency adds nothing and decides nothing here. If something in the book is wrong, it is changed in the step it came from, and the book is made again.

The opening is English; when the conversation is in another language, say it in that language, sentence for sentence, adding and dropping nothing. The same holds for every quoted text of this skill.

The step asks the owner nothing until the book is shown.

## Building the book

1. Run `render_book.py brand`.
   - With `screenshots: headless-chrome` in `pipeline.yaml` it takes the screenshots itself, light, and prints the PDF.
   - With `manual`, or without Chrome, it lists the images to place in `review/shots/`, with the page and the size of each, and stops. Ask the owner to take them, or take them with `screenshot.py` if a browser turns up, then run it again. Without Chrome there is no PDF; say so, and record it in `summary.md`.
   - It stops, and writes nothing, when a plate is missing or still a draft, when the identity is not approved, or when the pages of the design system are missing. Each of these belongs to the step it names; send the owner there.
2. Open `index.html` in a browser, or take screenshots of it at 1440 and at 390 and open them. Look for what is broken, not for what you would design differently: a font that fell back to a system face, a missing image, text that overflows at 390. A broken thing is fixed where it comes from (a font file in the identity, a page of the design system), never in the book.
3. Run `check --step 05-brand-book brand` and fix what it reports at its source.

There is no critic in this step: the composition is fixed and draws nothing new, and every piece of it was seen by the critic in its own step.

## The review

1. Write `review/book-NN.json` as `review-page.md` describes, with two items: `../index.html` at 1440 × 900 and at 390 × 844, each with a height that shows a good part of it. Render it with `render_review.py` and give the owner two paths: the review page and `index.html` itself. Then say, word for word:

> **Strategist:** Here is the brand book. Every block is numbered. Read it as the person who will receive it: a designer, a developer, an agency. Name what is wrong by its number; it is fixed where it was decided.

2. He answers with numbers ("17: the license line is wrong"). For each: name the step and the file the line comes from, and send it there. A line of a plate changes in that step's skill; its step then becomes `stale`, and so does the book. When those changes are approved, run `render_book.py brand` again and make a new review page, `book-NN` with the next number.
3. A remark about the book itself (the order, the cover, the numbering) is not changed here: record it in `summary.md` under `Open questions`, as feedback on brand.

## Summary

`brand/05-brand-book/summary.md`, in English:

- `Decisions`: this step decides nothing about the brand. Record the paths of the three files, the size of `index.html`, and whether `brand-book.pdf` exists. The kit is not recorded here: it is exported after the summary and lives outside the step.
- `Constraints on later steps`: `brand/out/` (the kit) is the single input for landing pages, campaigns and screens, and its `AGENTS.md` the first file an agent reads; the book and the kit are built again, never edited, when an earlier step changes.
- `Open questions`: remarks about the book itself; anything the earlier steps left open (their own `Open questions`) that the work to follow will meet; a missing PDF. `None.` when there is nothing.

## Closing

Close the step as the step protocol describes. Before asking for approval: `check --step 05-brand-book` is clean and the book was built after the last change to any earlier step. Ask for an explicit yes. On yes, run `render_book.py brand --approve`, which writes `brand-book.md` with `status: approved`, record the version and the status, and run the full check.

Then export the kit: `export_kit.py brand`. It writes `brand/out/`, the product of the whole pipeline: only the finished files (the book, the logo, the fonts, the tokens, the design system, the surfaces), `brand.md` and `brand.json` for agents, `AGENTS.md` and `README.md` that say what is where and how to use it, and `manifest.json`. It refuses while the check is not clean or a step is not approved; fix the cause, never the kit. Everything else in `brand/` stays as the working state of the pipeline. The kit is never edited by hand; it is exported again whenever the book is approved again.

Then, as Strategist, say the closing, word for word:

> **Strategist:** The brand is complete. Everything finished is in one directory, `brand/out/`: the book as a page and a PDF, the logo, the fonts, the tokens, the design system and the surfaces, with `AGENTS.md`, which tells an agent what is where. Hand that directory to a designer, a developer or an agent that builds a page, a campaign or a screen. When you change an earlier step, the book and the kit are out of date; run this step again and both are made anew.

When there is no PDF, say the closing as it is, then add one sentence of your own: the PDF was not made, and why; the kit then has none either.
