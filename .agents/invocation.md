# Model-invoked vs user-invoked

Every `SKILL.md` in this repo is a skill. The one axis that splits them is **invocation**, who can reach it:

- **User-invoked**: reachable **only by a person typing its name**. Set `disable-model-invocation: true` in the frontmatter and `policy.allow_implicit_invocation: false` in `agents/openai.yaml`. The `description` is **human-facing**: a one-line summary for someone browsing commands. No trigger lists.
- **Model-invoked**: reachable by **the model or a person**. The default: no `disable-model-invocation`, no `policy` block. The `description` is **model-facing** and keeps rich trigger phrasing ("Use when the owner wants..., mentions..., asks for...") so the agent reaches for it on its own. The test: _could the agent usefully reach for this without being told?_

Keep `SKILL.md` and `agents/openai.yaml` in sync: a skill is user-invoked in every harness or in none. Every `agents/openai.yaml` also holds `interface.display_name` and `interface.short_description` for the Codex picker.

Bucket `README.md`s and the top-level `README.md` group entries into **User-invoked** and **Model-invoked**.

## Dependencies between skills

A skill that needs another one says so as an instruction to invoke it by name: "Invoke the `grilling` skill." It never names the harness's mechanism for that (a tool, a slash command), and never links into the other skill's folder: shared material lives inside the skill that owns it, and other skills reach it by invoking that skill.

Only a model-invoked skill can be reached this way. When a step needs a user-invoked skill first, it tells the person to run it, by name.
