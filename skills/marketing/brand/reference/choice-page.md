# brand — choice page v0.1

Status: agreed; the owner approved the template on 2026-11-14.

A choice page shows the owner three or four variants, each beside its reference and the critic's remarks. The owner answers in the chat. Every choice page in every step is rendered from one template, so the pages differ only in what they present.

## 1. How a page is made

A skill never writes the page's HTML. It writes a data file, and a script of the skill renders it:

```
python3 scripts/render_choice.py brand/03-identity/review/direction-01.json
```

This writes `direction-01.html` beside the data file. The script reads `templates/choice-page.html`, has no dependencies, and writes nothing when the data breaks a rule (section 4).

Files in `review/`:

```
review/
  decisions.md
  direction-01.json        # data, written by the skill
  direction-01.html        # the page, rendered by the script
  direction-01/            # the variants of this page
    variant-1.html
    variant-2.html
    variant-3.html
```

A page is named `<choice>-<cycle>`, with the cycle as two digits. Each new cycle of the same choice is a new page; earlier pages stay. `Page` in `decisions.md` names the rendered `.html` file.

`examples/choice-page/` holds a complete example.

## 2. Data file

```json
{
  "lang": "en",
  "title": "Layout and hero",
  "question": "Which layout is closest to how the site should look?",
  "cycle": 1,
  "viewports": [
    { "width": 1440, "height": 900 },
    { "width": 390, "height": 844 }
  ],
  "variants": [
    {
      "title": "Editorial: one column, large serif headline",
      "note": "The text leads; no image.",
      "file": "layout-01/variant-1.html",
      "reference": {
        "image": "../moodboard/refs/aihero-home.png",
        "caption": "aihero.dev: the density of the first screen and one clear action.",
        "source": "https://www.aihero.dev/"
      },
      "critic": [
        "The lower third of the screen is empty at 1440."
      ]
    }
  ]
}
```

| Key | Required | Value |
|---|---|---|
| `lang` | yes | the owner's language, as a BCP 47 tag |
| `title` | yes | the name of the choice |
| `question` | no | what the owner is asked to decide |
| `cycle` | no | the cycle number, from 1 |
| `labels` | no | the page's fixed labels in the owner's language (section 3) |
| `viewports` | no | the widths the variants are shown at; the first is the default. Defaults to 1440 × 900. With more than one, the page shows a width switch |
| `variants` | yes | three or four variants; a variant's number is its position in the list |
| `variants[].title` | yes | a short name for the variant |
| `variants[].note` | no | what distinguishes this variant |
| `variants[].file` | yes | the variant: `.html` shown live, or `.svg`, `.png`, `.jpg`, `.webp` shown as an image |
| `variants[].reference.image` | yes | the reference screenshot: `.png`, `.jpg` or `.webp` |
| `variants[].reference.caption` | yes | what exactly is taken from the reference |
| `variants[].reference.source` | no | the URL the screenshot was taken from |
| `variants[].critic` | yes | the critic's remarks, a list of strings; an empty list when the critic has none |

All paths are relative to the data file. All text is written in the owner's language. Unknown keys are errors.

## 3. Labels

The template's labels are English by default. A skill passes them in the owner's language under `labels`; any key left out stays English.

| Key | Default |
|---|---|
| `variant` | Variant |
| `reference` | Reference |
| `critic` | Critic |
| `no_remarks` | No remarks. |
| `theme` | Theme |
| `light` | Light |
| `dark` | Dark |
| `width` | Width |
| `cycle` | Cycle |
| `open` | Open full size |
| `source` | Source |
| `answer` | Answer in the chat with the number of the variant and your comment, for example: “2, but with the type from 4”. |

## 4. Rules the script enforces

The page is not written unless all of these hold:

- there are three or four variants;
- every variant has a reference, and its screenshot exists as a file;
- every variant has a caption for its reference and a list of critic's remarks;
- every variant file exists;
- every live (`.html`) variant listens for the theme (section 5).

## 5. Live variants and the theme

The theme switch changes the shell and every live variant together. The page sends the theme to each variant frame; the variant applies it. A live variant must therefore:

1. style both themes through the `data-theme` attribute of `<html>`, with the values `light` and `dark`;
2. contain this listener:

```html
<script>addEventListener('message',function(e){if(e.data&&e.data.brandTheme)document.documentElement.dataset.theme=e.data.brandTheme})</script>
```

The reference is a screenshot and does not change with the theme. An image variant does not change either; it is shown on the shell's surface, which does.

A live variant is rendered at the chosen viewport width and scaled down to fit its column. "Open full size" opens it unscaled in a new tab.

## 6. The shell

The template's look is fixed and neutral so that it does not influence how variants are perceived: black, white and grey only; one system typeface; hairlines and no other decoration. It is recognizable through its structure, which is the same on every page:

1. a bar with the choice, the cycle, the width switch and the theme switch;
2. the question and how to answer;
3. one band per variant: a large number, the title and note, then the variant on the left with the critic's remarks under it and the reference on the right with its caption under it.

A skill must not restyle or restructure the page. A change to the shell is a change to `templates/choice-page.html`, approved by the owner.
