# The system pages

The design system step shows a brand's interface on pages that are the same for every brand: the components in `templates/system/system.css` and the compositions in `scripts/render_system.py`. A brand gives only its tokens (`design-tokens.md`), its copy, its logo and its fonts, so two variants differ only in their tokens.

```
python3 scripts/render_system.py sheet <tokens.json> <output.html> --brand brand
python3 scripts/render_system.py build brand
```

- `sheet` renders one variant of the Interface choice: buttons in their states, a field with help and one with an error, a select, a card, the choices, the four notices. The tokens and the components are inlined into the page.
- `build` writes `brand/04-design-system/reference/`: `index.html` (the whole system on one page), `sheet.html`, `system.css`, and `pages/landing.html`, `pages/sign-in.html`, `pages/sign-up.html`. These load `tokens.css`, `system.css`, `03-identity/fonts/fonts.css` and the logo by relative path.

Both refuse, and write nothing, when a token of `design-tokens.md` section 4 is missing, a contrast pair fails, `tokens.css` is out of date (`build` only) or `copy.json` breaks the format below. Without the identity's logo files the pages show the brand's name; without its `fonts.css` the faces fall back to the fallbacks in `font.display` and `font.text`. Exit codes: 0 rendered, 1 a rule is broken, 2 a file cannot be read.

Every page has a light and a dark theme through `data-theme` on `<html>`, follows the reader's setting until it is switched, and carries the theme listener of `choice-page.md`, so it can stand on a choice or review page. The narrow layout starts at 600 pixels, as the `narrow` tokens do.

## 1. The system page

`reference/index.html` has a theme switch in its bar and five parts. Every block is numbered, from 1, so the owner corrects by number:

1. **Foundations**: the color roles with their light and dark values, the contrast of every pair, the type scale set in the brand's copy, spacing and layout, radii and borders, shadows, motion, the icons.
2. **Atoms**: button (primary, secondary, quiet; default, hover, focus, active, disabled), link, text input, text area, select, checkbox, radio, switch, badge, avatar, divider.
3. **Molecules**: form field, notice, card.
4. **Organisms**: header (the navigation folds into a menu at 600 pixels and below), hero, benefits, testimonial, call to action, sign-in form, footer.
5. **Pages**: the landing page, sign-in and sign-up as frames at 1440 and at 390, each opening at full size. They are an example of assembly, not the design of a site.

The icons are twenty icons of Lucide, copied into `templates/system/icons/` with the license (ISC; the icons derived from Feather, MIT). Their size and stroke are the tokens `icon.size` and `icon.stroke`.

## 2. `copy.json`

The copy of every page, in the market language, written by the Copywriter in the brand's voice. Every value is a text that is not empty; every key is required; a list has exactly the length shown. Unknown keys are errors.

```json
{
  "lang": "uk",
  "nav": ["...", "...", "..."],
  "header_button": "...",
  "hero": {"headline": "the Main promise", "lead": "...", "button": "...", "secondary": "..."},
  "benefits": {"title": "...", "items": [{"title": "...", "text": "..."}, {"title": "...", "text": "..."}, {"title": "...", "text": "..."}]},
  "testimonial": {"quote": "...", "name": "...", "role": "..."},
  "call": {"headline": "...", "text": "...", "button": "..."},
  "footer": {"text": "...", "links": ["...", "...", "..."]},
  "sign_in": {"title": "...", "email": "...", "password": "...", "button": "...", "switch": "...", "switch_link": "..."},
  "sign_up": {"title": "...", "name": "...", "email": "...", "password": "...", "terms": "...", "button": "...", "error": "...", "switch": "...", "switch_link": "..."},
  "ui": {
    "placeholder": "an example email address",
    "help": "...",
    "select": "the label of the select",
    "options": ["...", "...", "..."],
    "checkbox": "...",
    "radios": ["...", "..."],
    "switch": "...",
    "badge": "...",
    "notices": {"info": "...", "success": "...", "warning": "...", "error": "..."},
    "card": {"title": "...", "text": "..."}
  }
}
```

| Key | Holds |
|---|---|
| `lang` | the market language, as a BCP 47 tag |
| `nav`, `header_button` | the three links of the header and its one action |
| `hero` | the headline (the `Main promise`), the lead, the first action and a second one |
| `benefits` | the title of the band and three benefits |
| `testimonial` | one quotation, its author and the author's role; a plausible one, marked as an example in `components.md` until a real one exists |
| `call` | the closing invitation: headline, one sentence, the action |
| `footer` | one line of small print and three links |
| `sign_in`, `sign_up` | the titles, the labels, the buttons, the line that switches between the two; `sign_up.error` is the error shown on the email field |
| `ui` | the copy of the atoms and molecules on the system page and the sheet |
