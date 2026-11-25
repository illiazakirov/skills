# brand — design tokens v0.1

Status: agreed with the owner on 2026-11-18.

`brand/04-design-system/tokens.json` is the single source of the design system's values. `tokens.css` is generated from it and never edited by hand:

```
python3 scripts/build_tokens.py brand/04-design-system/tokens.json            # writes tokens.css
python3 scripts/build_tokens.py brand/04-design-system/tokens.json --check    # fails if tokens.css is out of date
```

`examples/design-tokens/` holds a small example of both files.

## 1. Format

The file follows the W3C Design Tokens Community Group format module, version 2025.10:

- a group is an object; a token is an object with `$value`; `$type` stands on the token or on a group above it; `$description` is optional;
- names use lowercase letters, digits and hyphens. This is stricter than the format, so that every path can become a CSS property name;
- `"{group.token}"` refers to another token of the same type. `$ref` is not supported.

| `$type` | `$value` |
|---|---|
| `color` | `{"colorSpace": "srgb", "components": [r, g, b], "alpha": 0.5, "hex": "#rrggbb"}`; components from 0 to 1; `alpha` and `hex` optional; a `hex` must agree with the components. Only `srgb` in this version |
| `dimension` | `{"value": 16, "unit": "px"}`; `px` or `rem` |
| `duration` | `{"value": 120, "unit": "ms"}`; `ms` or `s` |
| `fontFamily` | a name or a list of names |
| `fontWeight` | a number from 1 to 1000, or a name such as `bold` |
| `number` | a number |
| `cubicBezier` | four numbers |
| `shadow` | an object with `color`, `offsetX`, `offsetY`, `blur`, `spread` and optional `inset`, or a list of them |
| `typography` | an object with exactly `fontFamily`, `fontSize`, `fontWeight`, `letterSpacing`, `lineHeight` |

Other types of the format (border, transition, gradient, stroke style) are not supported in this version.

## 2. Themes

The format has no notion of themes. The convention here: the top-level group `dark` holds the dark theme. A token `dark.color.bg` overrides `color.bg`; it must have the same type, and the token it overrides must exist. Only what differs in the dark theme is listed. Aliases never point into `dark`.

The top-level group `narrow` holds what differs at 600 pixels wide and below, the phone layout: `narrow.type.body` overrides `type.body`. The same rules apply as for `dark`. `dark` and `narrow` do not combine: a value that differs in both is not supported in this version.

## 3. `tokens.css`

- Each token becomes a custom property named by its path: `color.bg` → `--color-bg`.
- Tokens outside `dark` and `narrow` are declared on `:root`; tokens in `dark` on `:root[data-theme="dark"]`, and tokens in `narrow` on `:root` inside `@media (max-width: 600px)`, under the name of the token they override.
- An alias becomes `var(--…)`, so a dark override of a primitive flows through to everything that refers to it.
- A `typography` token becomes five properties: `--<path>-font-family`, `-font-size`, `-font-weight`, `-letter-spacing`, `-line-height`.

Another platform is added later by writing another builder over the same `tokens.json`.

## 4. The tokens of a brand

The components shipped with the skill (`templates/system/system.css`) use these tokens, so every `brand/04-design-system/tokens.json` has them all; `check_contract.py` refuses a file that misses one. A brand may add primitives under `palette` and refer to them; components never name a primitive.

| Group | Tokens | Type |
|---|---|---|
| `color` | `bg`, `surface`, `border`, `control-border`, `text`, `text-muted`, `accent`, `accent-hover`, `on-accent`, `link`, `focus`, `error`, `error-bg`, `success`, `success-bg`, `warning`, `warning-bg`, `info`, `info-bg` | `color` |
| `font` | `display`, `text` | `fontFamily` |
| `type` | `headline`, `title`, `subtitle`, `lead`, `body`, `small`, `label` | `typography` |
| `space` | `xs`, `s`, `m`, `l`, `xl`, `section` | `dimension` |
| `radius` | `control`, `card`, `badge` | `dimension` |
| `border` | `width`, `control` | `dimension` |
| `shadow` | `card`, `raised` | `shadow` |
| `size` | `control` | `dimension` |
| `icon` | `size` | `dimension` |
| `icon` | `stroke` | `number` |
| `motion` | `duration` | `duration` |
| `motion` | `easing` | `cubicBezier` |
| `layout` | `content`, `gutter` | `dimension` |

`dark` overrides at least the color roles that differ in the dark theme; `narrow` overrides at least the sizes of `type` that the identity fixed for 390.
