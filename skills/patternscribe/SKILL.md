---
name: patternscribe
description: Use when the user corrects you, refuses an action, or restates how they want something done — to record the preference so later sessions stop repeating the mistake. Also use when the user asks to run patternscribe, to remember or record a preference, what you have learned about how they work, how they would have done something, or wants your point of view grounded in their past corrections.
argument-hint: "[suggest | lead | show | why <rule> | forget <rule> | config]"
---

# Patternscribe

Subcommand: `$ARGUMENTS`

## Who started this run

- **The user asked** — they typed `/patternscribe`, or told you in their own words to run
  it, remember something, show the profile, and so on. Always do it, whatever the
  config says. Map their words to a subcommand below; "remember that" is **capture**.
- **You started it on your own** because the user corrected you, refused an action, or
  restated a preference. First run `python3 "$PLUGIN_SCRIPTS/config.py" get auto_capture`.
  If it prints `false`, save nothing, and end your reply with this line so the user
  can keep it if they want to:

  > Not saved for future sessions — run `/patternscribe` to keep this one.

  Then carry on with the task. Do not say you will remember it, avoid it "from now on",
  or anything else implying it outlasts this session — with nothing saved, it won't.
  Otherwise do **capture** only, report it in one line, and go straight back to the
  work you were doing. Never start **lead**, **suggest** or **forget** on your own.

Dispatch:

- empty → **capture**: distil this session into the profile now
- `suggest` (or `pov`, `advise`) → **suggest**: capture first, then print your point of
  view against the refreshed profile, changing nothing
- `lead` → **lead**: capture first, then continue the work under the profile
- `show` (or `list`) → **show**
- `why <text>` → **why**: the journal evidence behind that rule
- `forget <text>` → **forget**
- `config` (or `settings`) → **config**

Anything else: treat it as a question about the profile. Read `PATTERNS.md` and answer
from it, saying plainly when it has nothing to say on the matter.

## Overview

This project keeps a profile of how its owner wants work done, learned from what they
corrected in past sessions. The profile lives at `<data_dir>/PATTERNS.md`, the evidence
behind it at `<data_dir>/journal.md`, and `<data_dir>` is always `.patternscribe/` at the
project root.

There are no hooks and no background process. The profile changes only inside a live
session: when the user asks, or — unless `auto_capture` is `false` — when you notice a
correction and capture it yourself.

**Core principle:** learn before you advise. An opinion that ignores the correction the
user gave two minutes ago is worse than no opinion, because it sounds informed.

## Paths

Resolve everything through the config rather than assuming a layout:

```bash
PLUGIN_SCRIPTS="${CLAUDE_SKILL_DIR}/../../scripts"
python3 "$PLUGIN_SCRIPTS/config.py" show          # merged settings
python3 "$PLUGIN_SCRIPTS/config.py" path data     # <data_dir>
bash "$PLUGIN_SCRIPTS/bootstrap.sh"               # create it if missing (idempotent)
```

## Before you edit the profile

If `use_superpowers` is true and the superpowers skills are available, invoke
`superpowers:writing-skills` before rewriting `PATTERNS.md`, and
`superpowers:verification-before-completion` before reporting done.

If it is true but superpowers is not installed here, mention how to install it — once
per session, not every time.

If it is false, or superpowers is not available, follow this instead. It is the same
discipline, inlined so this plugin stands alone:

1. Read the current `PATTERNS.md` in full before changing a line of it.
2. Write each bullet as an instruction someone could act on, not as an observation
   about the user.
3. After writing, re-read what you wrote and delete anything that is true of every
   project rather than this one.
4. State plainly what you changed. If you changed nothing, say that.

## capture — `/patternscribe`

Distil the session you are in right now. This session's id is `${CLAUDE_SESSION_ID}`.

1. Run `bash "$PLUGIN_SCRIPTS/bootstrap.sh"`.
2. Read `<data_dir>/PATTERNS.md`.
3. Work from the conversation you are in — you do not need the transcript file, you were
   there. Identify what the user corrected, refused, or restated, and ask of each one:
   *would this apply to a different task?* If not, it is not a pattern.
4. Apply the merge rules in `references/patterns-format.md`, all six, in order. They
   are not optional; the counter discipline is what makes the file trustworthy. Decay
   needs `python3 "$PLUGIN_SCRIPTS/config.py" get decay_sessions`.
   A session counts once. If `journal.md` already has blocks for this session id, it
   was captured earlier in this session: add only evidence those blocks do not already
   cover, and do not increment a rule this session already counted, or bump
   `sessions analyzed` again.
5. Append the evidence to `<data_dir>/journal.md`, headed with this session's id.
6. Report what changed in one line.

## suggest — `/patternscribe suggest`

Give your point of view, grounded in what this user actually wants.

1. Run **capture** first, in full. Do not skip it because the session feels
   uneventful — the correction you are about to reason from may be from ten minutes ago.
2. Re-read the refreshed `PATTERNS.md`.
3. Look at what is actually in front of you: the current task, the diff
   (`git diff`, `git diff --staged`), the files under discussion.
4. Print this and change nothing:

```
How you'd have done this
  - <the approach the profile implies, concretely>
Where the current approach diverges
  - <specific conflict>  (rule: "<the rule>", seen Nx)
What I'd do instead
  - <actionable steps>
Not sure about
  - <where the profile is silent, so this part is my opinion, not theirs>
  - <where two live rules conflict: both, with counts and #K — and which looks current>
```

The last section is not optional. Without it, a guess is indistinguishable from a
learned preference, and the user cannot tell which parts to trust.

Never resolve a conflict between two live rules silently, and never by picking the
higher count: the older rule usually has more sightings precisely because it is older.
Show both under **Not sure about**, and say the higher `#K` is probably the current one.

If the profile is empty or silent on everything that matters here, say so directly —
"nothing learned about this yet, so this is just my read" — and give the opinion anyway.

## lead — `/patternscribe lead`

Same two learning steps as **suggest**, then do the work instead of printing about it.
Before starting, state in one or two lines which rules you are working under, so the
user can see the basis when they come back. Stop and ask if the profile is silent on a
decision that would be expensive to reverse.

Treat two live rules that conflict the same way as silence: before writing anything that
depends on the choice, ask which applies, showing both with their counts and `#K`. Then
capture the answer — it is a correction like any other, and the merge rules replace the
losing rule so the question does not come up again.

## show — `/patternscribe show`

Print `PATTERNS.md`, highest counts first. Note how many sessions it was built from
(the header) and where the file is, so the user can edit it by hand.

## why — `/patternscribe why <text>`

Search `<data_dir>/journal.md` for the rule and show the dated evidence: what was said,
when, in which session. If the rule is in `PATTERNS.md` but has no journal entry, say so
— it was probably hand-written, which is worth knowing.

## forget — `/patternscribe forget <text>`

1. Show the user the exact bullet you are about to remove and its evidence.
2. Remove it from `PATTERNS.md` and add a dated "removed" entry to `journal.md` saying
   the user asked for it.
3. If they want it gone permanently, re-add it under `## Archive` marked `(pinned)`
   with `do not re-learn` — pinned bullets are never rewritten, so it cannot come back.

## config — `/patternscribe config`

Run `python3 "$PLUGIN_SCRIPTS/config.py" show`, explain the resolved values, and edit
`<project>/.patternscribe/config.json` when asked. That file holds only overrides; anything
absent falls back to the plugin's `config.default.json`.

## Red Flags

These thoughts mean stop — you are about to make the profile worse:

| Thought | Reality |
|---|---|
| "I'll add this rule, it might be useful" | A rule nobody asked for is noise that outranks real ones. |
| "This is close enough to an existing rule, I'll add it anyway" | Near-duplicates are how this file dies. Increment the count. |
| "I'll give my opinion first and capture afterwards" | Then the opinion ignores the correction you just got. |
| "The session was quiet, nothing to capture" | Fine — say "no new patterns". Do not invent one. |
| "I'll record that they wanted invoice.py fixed" | That is a task, not a pattern. |
| "The profile is stale, I'll rewrite it properly" | Rewriting drops counts and pins. Merge, never replace. |
| "This rule is obviously right, it can outrank a pin" | Pinned means a person decided. You do not overrule that. |
| "I'll note the API key so I remember the setup" | Never. Secrets, file contents and personal data stay out. |
| "The project's context file already says this, but restating helps" | It is already in front of every session. Skip it. |

## References

- `references/patterns-format.md` — the file contract: sections, counters, pins, decay,
  and the merge rules. Read before any edit to `PATTERNS.md`.
