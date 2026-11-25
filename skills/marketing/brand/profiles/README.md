# Profiles

A profile adapts the pipeline to one type of project. The skills are shared; everything that differs between types lives here, in one file per type: `profiles/<profile id>.md`. The profile id is the value of `profile` in `brand/pipeline.yaml`.

Profiles in this version:

| Profile id | File | Status |
|---|---|---|
| `personal-brand` | `personal-brand.md` | untested |
| `b2b-saas` | not written yet | |
| `consumer-app` | not written yet | |
| `local-business` | not written yet | |
| `physical-product` | not written yet | |

A skill that needs a profile whose file does not exist stops and says so.

## Format

A profile is a markdown file with these parts, in this order. The headings are literal.

| Part | Read by | Content |
|---|---|---|
| `Status: untested` or `Status: tested` | all | the line after the title. A profile is `untested` until it has passed one real run |
| `## Strategy questions` | `strategy` | one `###` heading per strategy tool, named as in the profile above, with the questions specific to this type, asked in the Dig phase of that session |
| `## Marketing mix` | `strategy` | `4P` or `7P` |
| `## Platform questions` | `brand-platform` | one `###` heading per session (`Archetype`, `Voice`, `Name`, `Mood`), with the questions specific to this type, asked in the Dig phase of that session; below them, anything the type changes in a session |
| `## Identity questions` | `identity` | two `###` headings, `Logo` and `Surfaces`: the questions specific to this type, asked in the Dig phase of the Logo session and before the surfaces are built |
| `## Surfaces` | `identity` | the surfaces the identity is tested on |
| `## Components` | `design-system` | components needed beyond the base set, or `None beyond the base set.` |
| `## Pages` | `design-system` | example pages needed beyond the landing page, sign-in and sign-up, or `None beyond the base set.` |
