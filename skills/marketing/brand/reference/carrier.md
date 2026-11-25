# The carrier and the logo sheet

The identity step shows its variants on two pages that are the same for every brand, so that a variant differs from its neighbors only in what the choice is about. `scripts/render_carrier.py` renders both from a data file:

```
python3 scripts/render_carrier.py carrier <data.json> <output.html>
python3 scripts/render_carrier.py sheet <data.json> <output.html>
```

Paths in a data file are relative to that file. Both pages style a light and a dark theme through `data-theme` on `<html>`, carry the theme listener of `choice-page.md`, and work at 1440 and at 390 wide, so they can be used as live variants of a choice page. Exit codes: 0 rendered, 1 the data breaks a rule (nothing is written), 2 the data file cannot be read.

## 1. The carrier

One neutral layout: a header with the logo alone, the main promise as the headline, one paragraph and one button, and under the button the motto, when there is one. The variants of the Color, Typography and Motto sessions are carriers.

| Key | Required | Holds |
|---|---|---|
| `name` | yes | the brand name |
| `promise` | yes | the headline: the `Main promise`, in the market language |
| `paragraph` | yes | one paragraph in the brand's voice, in the market language |
| `button` | yes | the label of the button |
| `lang` | no | the language tag of the page; `en` when absent |
| `logo` | no | the path of the logo as an SVG file, placed in the header; without it the name is set as plain text |
| `logo_dark` | no | the path of the logo for the dark theme; needs `logo` |
| `motto` | no | the motto, set as a closing line of copy under the button; never beside the logo |
| `colors` | no | `light` and `dark`, each with any of `background`, `text` and `accent` as `#RRGGBB` |
| `fonts` | no | `display` and `text`, each a family name, and `css`, the stylesheet that declares them |

What is left out stays neutral: black and white, the system typeface. So a color variant gives `colors` and no `fonts` until the type pair is fixed, and a type variant gives the fixed colors and its own `fonts`.

`fonts.css` is a relative path (after the pair is fixed: the `fonts/fonts.css` of the step) or, while candidates are compared, an address at `https://fonts.googleapis.com/`. Nothing else is loaded from the network.

The label of the button is set in whichever of the theme's background and text colors reads better on the accent.

## 2. The logo sheet

One logo candidate: the full logo large, the mark alone, the full logo on dark, the mark at 24, 32 and 48 pixels high, and the logo in a header on light and on dark.

| Key | Required | Holds |
|---|---|---|
| `name` | yes | the brand name, for the title of the page |
| `full` | yes | the path of the full logo, an SVG file |
| `mark` | yes | the path of the mark alone |
| `dark` | no | the path of the logo for dark backgrounds; without it `full` is shown on dark |
| `mono` | no | the path of the one-color mark, drawn in `currentColor`; with it the three sizes are shown on dark as well |
| `lang` | no | the language tag of the page |
| `header_label` | no | the caption above the header rows, in the owner's language; `In a header` when absent |

An SVG file is placed in the page as it is. A file that holds a script or an event handler is refused: a logo is shapes only.
