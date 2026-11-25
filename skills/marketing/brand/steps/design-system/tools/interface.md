# Interface

Fixed text of the one session of the design system. Show `Briefing` word for word; ask the `Dig` questions as written; show the `Sharpness tests` as a checklist; say the `Link` as written. This session has no benchmark.

## Briefing

**Strategist:** Session 1 of 1: **Interface**.

**Where it comes from.** Brad Frost, "Atomic Design", 2013. An interface is built the way matter is: atoms (a button, a field), molecules (a field with its label and its error), organisms (a header, a sign-in form), then templates and pages.

**The idea.** The identity says who the brand is. The interface says how it behaves when someone touches it: how round, how deep, how dense, how fast. One character, held in every part, makes a hundred screens feel like one brand.

**Why now.** The logo, the colors and the type are fixed. They are not reopened here; everything an interface needs grows from them.

**What we will leave with.** The character of the interface in five lines and the headline, the **Interface idea**; then the whole system on one page.

From here the Art Director leads.

## Dig

1. Name up to three sites or apps whose interface you like. What do you like in each?
2. Where will people use your product more often: on a phone or on a computer?

## Sharpness tests

- With the logo and the colors covered, the button and the card still feel like this brand, not like a template.
- The Interface idea follows from the Character of the platform.
- Every control can be hit with a thumb: at least 44 px high at 390.
- Text reaches 4.5 to 1 and the borders of controls 3 to 1 on their backgrounds, in both themes.
- "Never" forbids something a designer would be tempted to do.

## Link

Next: the System. The Art Director builds every part from this character and assembles a landing page and the sign-in pages from them; you correct them by number.

## Notes for the agency

- The Strategist gives the briefing. There is no benchmark: after the briefing, ask whether the idea is clear, then the Art Director leads and signs once: `**Art Director:**`.
- The Dig has two questions. Question 1 gives the references of this step: take a screenshot of each site the CEO names into `review/refs/` and measure them into `review/level.md` (see the skill). If he names none, propose three from the `Territory` and the board and let him confirm them. Question 2 decides the density: a product used mostly on a phone gets the larger controls.
- The minting of this session is the choice of a character on a choice page, as the skill describes. When the character is fixed, the Art Director proposes the slots in words; the `Interface idea` gets three candidate wordings.
- `Interface idea` is at most 12 words: what the character of the interface says, not a list of its parts.
- `Shape` names the radii in pixels: controls, cards, badges.
- `Depth` starts with `Flat` (no borders, no shadows), `Ruled` (lines, no shadows) or `Raised` (shadows), then says how.
- `Density` has the form `8 px unit, 44 px controls`: the base unit of the spacing and the height of a control at 1440.
- `Motion` is at most 15 words: how long a change of state takes and how it moves.
- `Never` has exactly three lines.
- The lines must agree with the fixed `tokens.json`: the radii, the depth, the unit, the height of a control and the duration are read off it.
- The headline slot is `Interface idea`.
