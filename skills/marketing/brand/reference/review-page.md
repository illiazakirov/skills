# brand — review page v0.1

Status: proposed; awaiting the owner's approval of the template.

A review page shows finished items together, each at its own size, with the critic's remarks and, where there is one, its reference. It offers no variants. The identity step uses it for the surfaces, which are assembled from decisions already fixed; the owner answers in the chat with corrections by item number. A choice between variants uses the choice page instead (`choice-page.md`).

## 1. How a page is made

```
python3 scripts/render_review.py brand/03-identity/review/surfaces-01.json
```

writes `surfaces-01.html` beside the data file, from `templates/review-page.html`. Nothing is written when the data breaks a rule. A page is named `<name>-<cycle>`, with the cycle as two digits; each round of corrections is a new page. `examples/review-page/` holds a complete example.

## 2. Data file

```json
{
  "lang": "en",
  "title": "Surfaces",
  "question": "The surfaces, built from the fixed logo, colors, type pair and motto.",
  "cycle": 1,
  "items": [
    {
      "title": "Site hero",
      "note": "Light and dark.",
      "file": "../surfaces/site-hero.html",
      "width": 1440,
      "height": 900,
      "critic": ["The lead is narrower than on the reference."],
      "reference": {
        "image": "../../02-brand-platform/moodboard/refs/aihero-home.png",
        "caption": "aihero.dev: one headline, one lead, one action.",
        "source": "https://www.aihero.dev/"
      }
    }
  ]
}
```

| Key | Required | Value |
|---|---|---|
| `lang` | yes | the owner's language, as a BCP 47 tag |
| `title` | yes | the name of the review |
| `question` | no | what the owner is looking at |
| `cycle` | no | the cycle number, from 1 |
| `labels` | no | the page's fixed labels in the owner's language; the keys of `choice-page.md` section 3 |
| `items` | yes | one or more items; an item's number is its position in the list |
| `items[].title` | yes | the name of the item |
| `items[].note` | no | a remark on the item |
| `items[].file` | yes | `.html` shown live, or `.svg`, `.png`, `.jpg`, `.webp` shown as an image |
| `items[].width`, `items[].height` | yes | the size the item is made for, in pixels |
| `items[].critic` | yes | the critic's standing remarks; an empty list when there are none |
| `items[].reference` | no | `image`, `caption` and optional `source`, as on a choice page |

All paths are relative to the data file. All text is in the owner's language. Unknown keys are errors.

## 3. The shell

The same neutral shell as the choice page: the bar with the title, the cycle and the theme switch; the question and how to answer; one band per item with a large number. In a band, the item stands on the left at its own size, scaled down to fit and never up, and the critic's remarks stand on the right with the reference under them.

The theme switch changes the shell and is passed to every live item. An item that has only one theme (an OG image, for example) simply ignores it; a review item is not required to listen.
