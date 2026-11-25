# Changelog

## 1.0.0 — 2026-11-25

The first release, with one skill: brand.

- Six steps (intake, strategy, brand platform, identity, design system, brand book) and `status`, each session with a briefing, an Apple benchmark, an interview, candidates or variants, a plate and a link to the next session.
- Plates rendered as HTML in the shape of their tool, the brand map, and the one-page views; after the identity, every page is set in the brand's own colors and type.
- Choice pages with three variants judged by a critic agent; review pages corrected by number.
- A design system in W3C design tokens with dark and narrow groups, a component set and three example pages.
- The brand book as a self-contained page, a PDF of fixed pages, and a text for agents.
- The kit (`brand-kit/2`): the finished brand in one directory, with `AGENTS.md`; delivered into the project it is for with `export_kit.py --deliver`, and checked with `--check --deliver`.
- The brand directory may live in the project (`brand/`) or in a studio, one directory per order.
- The owner's answers as files (`owner.py`): every point that waits for the owner is a question in a file, answered in the chat or by another program; `--headless` runs stop at the first unanswered question.
- The artifact contract (`reference/contract.md`) is enforced by `check_contract.py`.
