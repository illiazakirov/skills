# brand — moodboard v0.1

Status: agreed with the owner on 2026-11-17.

The moodboard is built at the brand platform step and lives in `brand/02-brand-platform/moodboard/`. Its rule: "real references from screenshots and generated images, each captioned with what exactly is taken from it".

## 1. Files

```
moodboard/
  index.md        # the list of images with captions; later steps read this
  board.html      # the board, rendered from index.md for the owner
  paper-1.png     # generated images and SVG studies
  refs/           # screenshots of references added at this step
    studio-home.png
```

Screenshots of other brands stay in the moodboard's `refs/` directory. They are named by path in the index and are never copied next to the brand's own images.

## 2. `index.md`

```markdown
# Moodboard

Quiet workshop: calm, dense, typographic. Nothing decorative.

## 1. aihero home

- File: refs/aihero-home.png
- Source: https://www.aihero.dev/
- Takes: the density of the first screen and one clear action

## 2. Paper texture

- File: paper-1.png
- Source: generated
- Takes: the warm grain of the background
```

- A `#` title, then an optional introduction, then one `## <number>. <name>` heading per image, numbered from 1 without gaps.
- Each image has exactly the lines `File`, `Source` and `Takes`, in this order.
- `File` is a path relative to the index: `.png`, `.jpg`, `.webp` or `.svg`. The file must exist.
- `Source` is the URL a screenshot was taken from, the word `generated` (an image or a study made by the agency), or the word `given` (material the owner handed over, named by its path in `../given/`).
- `Takes` says what exactly is taken from the image. It may not be empty.
- No frontmatter. The file is written in English.

## 3. Rendering

```
python3 scripts/render_moodboard.py brand/02-brand-platform/moodboard/index.md
```

writes `board.html` beside the index, from `templates/moodboard.html`. Nothing is written when the index breaks a rule. For `index.md` one more rule holds: every image file in the moodboard directory itself must be listed.

The same script renders any other `<name>.md` in this format to `<name>.html`; `--lang <tag>` sets the page language. The brand platform step uses this for the boards of the mood territories shown on its choice page: a rendered board listens for the choice page's theme, so it is a valid live variant.

The template is the same neutral shell as the choice page: black, white and grey, one system typeface.

## 4. Generated images

With `image_generation: fal`:

```
python3 scripts/fal_generate.py brand 02-brand-platform <output dir> <name> --prompt "<text>" [--count N] [--estimate]
```

- reads the key from the studio's `.env`, else `brand/.env`, else the environment (`fal_generate.py --check-key` says which), and never prints it;
- refuses a batch that costs more than what is left of `budget.limit`;
- writes `<name>-<n>.png` and adds the price of each generated image to the step's `spent` in `pipeline.yaml`;
- `--estimate` prints the price and the remaining budget and calls nothing. A skill runs it first, tells the owner the price and generates only after their yes.

The default model is `fal-ai/flux-2-pro`, at $0.03 for an image of up to one megapixel (fal.ai, checked on 2026-11-17). Another model is passed with `--model`, with `--price` when the script has no price for it.

With `svg-only` the same role is played by studies written as SVG files. With `none` the moodboard holds real references only.
