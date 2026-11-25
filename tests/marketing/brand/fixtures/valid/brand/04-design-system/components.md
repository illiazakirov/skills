---
step: 04-design-system
status: approved
source: generated
---

# Components

## Atoms

### Button

- For: The one action of a view; the accent only for the primary.
- States: default, hover, focus, active, disabled
- Tokens: color.accent, color.accent-hover, color.on-accent, radius.control, size.control, shadow.raised, type.label
- At 390: full width when it stands alone.
- Accessibility: native element, visible focus ring, checked at the contrast of the tokens.

### Link

- For: Moving to another page from within text.
- States: default, hover, focus
- Tokens: color.link, color.focus
- At 390: full width when it stands alone.
- Accessibility: native element, visible focus ring, checked at the contrast of the tokens.

### Text input

- For: One line of text the reader types.
- States: default, focus, disabled, error
- Tokens: color.surface, color.control-border, color.focus, color.error, radius.control, size.control, type.body
- At 390: full width when it stands alone.
- Accessibility: native element, visible focus ring, checked at the contrast of the tokens.

### Text area

- For: Several lines of text.
- States: default, focus, disabled, error
- Tokens: color.surface, color.control-border, color.focus, radius.card, type.body
- At 390: full width when it stands alone.
- Accessibility: native element, visible focus ring, checked at the contrast of the tokens.

### Select

- For: One choice from a short list.
- States: default, focus, disabled
- Tokens: color.surface, color.control-border, radius.control, size.control
- At 390: full width when it stands alone.
- Accessibility: native element, visible focus ring, checked at the contrast of the tokens.

### Checkbox

- For: A yes or no that the reader confirms.
- States: unchecked, checked, focus, disabled
- Tokens: color.accent, color.control-border, radius.badge
- At 390: full width when it stands alone.
- Accessibility: native element, visible focus ring, checked at the contrast of the tokens.

### Radio

- For: One of two to five options, all visible.
- States: unselected, selected, focus, disabled
- Tokens: color.accent, color.control-border
- At 390: full width when it stands alone.
- Accessibility: native element, visible focus ring, checked at the contrast of the tokens.

### Switch

- For: A setting that takes effect at once.
- States: off, on, focus, disabled
- Tokens: color.accent, color.control-border, motion.duration, motion.easing
- At 390: full width when it stands alone.
- Accessibility: native element, visible focus ring, checked at the contrast of the tokens.

### Badge

- For: A short status beside a title.
- States: neutral, accent
- Tokens: color.surface, color.text-muted, radius.badge, type.label
- At 390: full width when it stands alone.
- Accessibility: native element, visible focus ring, checked at the contrast of the tokens.

### Avatar

- For: A person, by photograph or initials.
- States: image, initials
- Tokens: color.surface, color.text, radius.badge
- At 390: full width when it stands alone.
- Accessibility: native element, visible focus ring, checked at the contrast of the tokens.

### Divider

- For: A quiet line between groups.
- States: default
- Tokens: color.border, border.width
- At 390: full width when it stands alone.
- Accessibility: native element, visible focus ring, checked at the contrast of the tokens.

## Molecules

### Form field

- For: A label, an input, help and an error, always together.
- States: default, error
- Tokens: color.text, color.text-muted, color.error, space.xs, type.label, type.small
- At 390: full width when it stands alone.
- Accessibility: native element, visible focus ring, checked at the contrast of the tokens.

### Notice

- For: A message about the state of something.
- States: info, success, warning, error
- Tokens: color.info, color.info-bg, color.success, color.success-bg, color.warning, color.warning-bg, color.error, color.error-bg, radius.card
- At 390: full width when it stands alone.
- Accessibility: native element, visible focus ring, checked at the contrast of the tokens.

### Card

- For: A unit of content that stands on its own.
- States: default, hover
- Tokens: color.surface, color.border, shadow.card, radius.card, space.l
- At 390: full width when it stands alone.
- Accessibility: native element, visible focus ring, checked at the contrast of the tokens.

## Organisms

### Header

- For: The logo, the navigation and one action.
- States: default, menu open at 390
- Tokens: color.bg, color.border, layout.content, layout.gutter
- At 390: full width when it stands alone.
- Accessibility: native element, visible focus ring, checked at the contrast of the tokens.

### Hero

- For: The main promise, a lead and the first action.
- States: default
- Tokens: type.headline, type.lead, space.section
- At 390: full width when it stands alone.
- Accessibility: native element, visible focus ring, checked at the contrast of the tokens.

### Benefits

- For: Three reasons, side by side.
- States: default
- Tokens: type.subtitle, type.body, space.xl
- At 390: full width when it stands alone.
- Accessibility: native element, visible focus ring, checked at the contrast of the tokens.

### Testimonial

- For: One quotation with its author.
- States: default
- Tokens: type.title, color.text-muted
- At 390: full width when it stands alone.
- Accessibility: native element, visible focus ring, checked at the contrast of the tokens.

### Call to action

- For: The closing invitation to act.
- States: default
- Tokens: color.surface, type.title, space.section
- At 390: full width when it stands alone.
- Accessibility: native element, visible focus ring, checked at the contrast of the tokens.

### Sign-in form

- For: Email and password, one button.
- States: default, error
- Tokens: space.m, radius.card, shadow.card
- At 390: full width when it stands alone.
- Accessibility: native element, visible focus ring, checked at the contrast of the tokens.

### Footer

- For: The name, the links, the small print.
- States: default
- Tokens: color.border, type.small, color.text-muted
- At 390: full width when it stands alone.
- Accessibility: native element, visible focus ring, checked at the contrast of the tokens.

## Pages

### Landing

- File: pages/landing.html
- Uses: Header, Hero, Benefits, Testimonial, Call to action, Footer

### Sign-in

- File: pages/sign-in.html
- Uses: Header, Sign-in form, Footer

### Sign-up

- File: pages/sign-up.html
- Uses: Header, Form field, Checkbox, Button, Notice, Footer
